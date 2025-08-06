"""Memory monitoring utilities for performance and stress testing."""

import psutil
import time
import functools
import gc
from typing import Optional, Callable, Any, Dict, List
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class MemorySnapshot:
    """Represents a memory usage snapshot."""
    timestamp: float
    rss: float  # Resident Set Size in MB
    vms: float  # Virtual Memory Size in MB
    available_system: float  # Available system memory in MB
    percent_used: float  # Memory usage percentage


@dataclass
class MemoryStats:
    """Statistics from memory monitoring session."""
    initial: MemorySnapshot
    final: MemorySnapshot
    peak: MemorySnapshot
    samples: List[MemorySnapshot]
    
    @property
    def memory_increase(self) -> float:
        """Memory increase from initial to final."""
        return self.final.rss - self.initial.rss
    
    @property
    def peak_increase(self) -> float:
        """Peak memory increase from initial."""
        return self.peak.rss - self.initial.rss
    
    @property
    def duration(self) -> float:
        """Duration of monitoring in seconds."""
        return self.final.timestamp - self.initial.timestamp


class MemoryMonitor:
    """Advanced memory monitoring with sampling and limits."""
    
    def __init__(
        self,
        max_memory_mb: Optional[float] = None,
        sample_interval: float = 0.1,
        enable_sampling: bool = False
    ):
        self.max_memory_mb = max_memory_mb
        self.sample_interval = sample_interval
        self.enable_sampling = enable_sampling
        
        self.process = psutil.Process()
        self.samples: List[MemorySnapshot] = []
        self.initial_snapshot: Optional[MemorySnapshot] = None
        self.final_snapshot: Optional[MemorySnapshot] = None
        self.peak_snapshot: Optional[MemorySnapshot] = None
        
        self._monitoring = False
    
    def _take_snapshot(self) -> MemorySnapshot:
        """Take a memory snapshot."""
        memory_info = self.process.memory_info()
        virtual_memory = psutil.virtual_memory()
        
        return MemorySnapshot(
            timestamp=time.time(),
            rss=memory_info.rss / 1024 / 1024,  # MB
            vms=memory_info.vms / 1024 / 1024,  # MB
            available_system=virtual_memory.available / 1024 / 1024,  # MB
            percent_used=virtual_memory.percent
        )
    
    def _update_peak(self, snapshot: MemorySnapshot) -> None:
        """Update peak memory if current is higher."""
        if self.peak_snapshot is None or snapshot.rss > self.peak_snapshot.rss:
            self.peak_snapshot = snapshot
    
    def _check_memory_limit(self, snapshot: MemorySnapshot) -> None:
        """Check if memory limit is exceeded."""
        if self.max_memory_mb and snapshot.rss > self.max_memory_mb:
            raise MemoryError(
                f"Memory usage {snapshot.rss:.2f}MB exceeded limit {self.max_memory_mb:.2f}MB"
            )
    
    def start_monitoring(self) -> None:
        """Start memory monitoring."""
        if self._monitoring:
            return
            
        self._monitoring = True
        self.initial_snapshot = self._take_snapshot()
        self.peak_snapshot = self.initial_snapshot
        
        if self.enable_sampling:
            self.samples = [self.initial_snapshot]
    
    def stop_monitoring(self) -> MemoryStats:
        """Stop monitoring and return statistics."""
        if not self._monitoring:
            raise RuntimeError("Monitoring not started")
            
        self.final_snapshot = self._take_snapshot()
        self._update_peak(self.final_snapshot)
        
        if self.enable_sampling:
            self.samples.append(self.final_snapshot)
        
        self._monitoring = False
        
        return MemoryStats(
            initial=self.initial_snapshot,
            final=self.final_snapshot,
            peak=self.peak_snapshot,
            samples=self.samples.copy()
        )
    
    def _get_current_stats(self) -> Optional[MemoryStats]:
        """Get current stats without stopping monitoring."""
        if not self._monitoring:
            return None
            
        current_snapshot = self._take_snapshot()
        self._update_peak(current_snapshot)
        
        return MemoryStats(
            initial=self.initial_snapshot,
            final=current_snapshot,
            peak=self.peak_snapshot,
            samples=self.samples.copy()
        )
    
    def sample(self) -> MemorySnapshot:
        """Take a sample and update monitoring state."""
        if not self._monitoring:
            raise RuntimeError("Monitoring not started")
            
        snapshot = self._take_snapshot()
        self._update_peak(snapshot)
        self._check_memory_limit(snapshot)
        
        if self.enable_sampling:
            self.samples.append(snapshot)
        
        return snapshot
    
    def __enter__(self):
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._monitoring:
            stats = self.stop_monitoring()
            
            # Check final memory limit
            if self.max_memory_mb and stats.peak.rss > self.max_memory_mb:
                raise MemoryError(
                    f"Peak memory usage {stats.peak.rss:.2f}MB exceeded limit {self.max_memory_mb:.2f}MB"
                )
        
        return False


def memory_limit(max_memory_mb: float, sample_interval: float = 0.1):
    """Decorator to enforce memory limits on functions."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with MemoryMonitor(max_memory_mb=max_memory_mb, sample_interval=sample_interval):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def memory_profiling(enable_sampling: bool = True, sample_interval: float = 0.1):
    """Decorator to profile memory usage of functions."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with MemoryMonitor(enable_sampling=enable_sampling, sample_interval=sample_interval) as monitor:
                result = func(*args, **kwargs)
                
                # Attach memory stats to result if possible
                if hasattr(result, '__dict__'):
                    result._memory_stats = monitor._get_current_stats()
                
                return result
        return wrapper
    return decorator


@contextmanager
def memory_tracking(max_memory_mb: Optional[float] = None, enable_sampling: bool = True):
    """Context manager for detailed memory tracking."""
    monitor = MemoryMonitor(
        max_memory_mb=max_memory_mb,
        enable_sampling=enable_sampling,
        sample_interval=0.05  # Higher frequency for detailed tracking
    )
    
    monitor.start_monitoring()
    try:
        yield monitor
    finally:
        if monitor._monitoring:
            stats = monitor.stop_monitoring()
            print(f"Memory Stats: Initial={stats.initial.rss:.2f}MB, "
                  f"Peak={stats.peak.rss:.2f}MB, Final={stats.final.rss:.2f}MB, "
                  f"Increase={stats.memory_increase:.2f}MB")


def force_garbage_collection():
    """Force garbage collection and return collected objects count."""
    collected = 0
    for generation in range(3):
        collected += gc.collect()
    return collected


class MemoryLeakDetector:
    """Detect potential memory leaks in test functions."""
    
    def __init__(self, tolerance_mb: float = 10.0):
        self.tolerance_mb = tolerance_mb
        self.baseline_memory: Optional[float] = None
    
    def establish_baseline(self) -> float:
        """Establish memory baseline after garbage collection."""
        force_garbage_collection()
        time.sleep(0.1)  # Allow cleanup
        
        memory_info = psutil.Process().memory_info()
        self.baseline_memory = memory_info.rss / 1024 / 1024  # MB
        return self.baseline_memory
    
    def check_for_leaks(self) -> tuple[bool, float]:
        """Check for memory leaks against baseline."""
        if self.baseline_memory is None:
            raise RuntimeError("Baseline not established")
        
        force_garbage_collection()
        time.sleep(0.1)
        
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_difference = current_memory - self.baseline_memory
        
        has_leak = memory_difference > self.tolerance_mb
        return has_leak, memory_difference


def memory_leak_test(tolerance_mb: float = 5.0, iterations: int = 3):
    """Decorator to detect memory leaks in test functions."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            detector = MemoryLeakDetector(tolerance_mb)
            detector.establish_baseline()
            
            # Run function multiple times to amplify leaks
            for i in range(iterations):
                result = func(*args, **kwargs)
            
            has_leak, difference = detector.check_for_leaks()
            if has_leak:
                raise MemoryError(
                    f"Potential memory leak detected: {difference:.2f}MB increase "
                    f"over {iterations} iterations (tolerance: {tolerance_mb:.2f}MB)"
                )
            
            return result
        return wrapper
    return decorator


# Utility functions for pytest integration
def pytest_configure_memory_monitoring():
    """Configure pytest for memory monitoring."""
    # This can be called in conftest.py to set up memory monitoring
    import pytest
    
    def pytest_runtest_setup(item):
        """Setup memory monitoring for each test."""
        if hasattr(item.function, '_memory_monitor'):
            item._memory_monitor = MemoryMonitor()
            item._memory_monitor.start_monitoring()
    
    def pytest_runtest_teardown(item):
        """Teardown memory monitoring for each test."""
        if hasattr(item, '_memory_monitor'):
            stats = item._memory_monitor.stop_monitoring()
            # Store stats for reporting
            item._memory_stats = stats


# Memory stress testing utilities
def create_memory_stress_test(target_memory_mb: float, chunk_size_mb: float = 10.0):
    """Create a memory stress test that allocates specific amount of memory."""
    def stress_test():
        chunks = []
        allocated_mb = 0
        
        try:
            while allocated_mb < target_memory_mb:
                # Allocate chunk_size_mb of data
                chunk_size_bytes = int(chunk_size_mb * 1024 * 1024)
                chunk = b'x' * chunk_size_bytes
                chunks.append(chunk)
                allocated_mb += chunk_size_mb
                
            # Hold memory for a brief moment
            time.sleep(0.1)
            
            return len(chunks)
            
        finally:
            # Clean up
            chunks.clear()
            force_garbage_collection()
    
    return stress_test


def memory_benchmark(func: Callable, *args, **kwargs) -> Dict[str, Any]:
    """Benchmark memory usage of a function call."""
    monitor = MemoryMonitor(enable_sampling=True, sample_interval=0.01)
    monitor.start_monitoring()
    
    try:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
    finally:
        stats = monitor.stop_monitoring()
    
    return {
        'result': result,
        'execution_time': end_time - start_time,
        'memory_stats': stats,
        'peak_memory_mb': stats.peak.rss,
        'memory_increase_mb': stats.memory_increase,
        'sample_count': len(stats.samples)
    }