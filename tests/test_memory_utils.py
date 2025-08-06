"""Test memory monitoring utilities."""

import pytest
import time
import psutil
from tests.memory_utils import (
    MemoryMonitor,
    MemorySnapshot,
    MemoryStats,
    memory_limit,
    memory_profiling,
    memory_tracking,
    MemoryLeakDetector,
    create_memory_stress_test,
    memory_benchmark
)


class TestMemorySnapshot:
    """Test MemorySnapshot functionality."""
    
    def test_memory_snapshot_creation(self):
        """Test memory snapshot creation."""
        snapshot = MemorySnapshot(
            timestamp=time.time(),
            rss=100.0,
            vms=200.0,
            available_system=1000.0,
            percent_used=50.0
        )
        
        assert snapshot.rss == 100.0
        assert snapshot.vms == 200.0
        assert snapshot.available_system == 1000.0
        assert snapshot.percent_used == 50.0


class TestMemoryStats:
    """Test MemoryStats functionality."""
    
    def test_memory_stats_properties(self):
        """Test memory statistics calculations."""
        initial = MemorySnapshot(100.0, 50.0, 100.0, 1000.0, 10.0)
        final = MemorySnapshot(200.0, 75.0, 120.0, 900.0, 15.0)
        peak = MemorySnapshot(300.0, 100.0, 150.0, 800.0, 20.0)
        
        stats = MemoryStats(initial, final, peak, [initial, peak, final])
        
        assert stats.memory_increase == 25.0  # 75 - 50
        assert stats.peak_increase == 50.0   # 100 - 50
        assert stats.duration == 100.0       # 200 - 100


class TestMemoryMonitor:
    """Test MemoryMonitor functionality."""
    
    def test_memory_monitor_basic_usage(self):
        """Test basic memory monitoring."""
        monitor = MemoryMonitor()
        
        with monitor as m:
            # Do some work that uses memory
            data = [i for i in range(1000)]
            m.sample()  # Take a manual sample
        
        # Monitor should have collected stats
        assert monitor.initial_snapshot is not None
        assert monitor.final_snapshot is not None
        assert monitor.peak_snapshot is not None
    
    def test_memory_monitor_with_limit(self):
        """Test memory monitoring with limits."""
        # Set a very low limit that should be exceeded
        monitor = MemoryMonitor(max_memory_mb=1.0)  # 1MB limit
        
        with pytest.raises(MemoryError):
            with monitor:
                # Allocate more than 1MB
                large_data = b'x' * (2 * 1024 * 1024)  # 2MB
                monitor.sample()
    
    def test_memory_monitor_sampling(self):
        """Test memory monitoring with sampling enabled."""
        monitor = MemoryMonitor(enable_sampling=True, sample_interval=0.01)
        
        with monitor:
            for i in range(5):
                data = [j for j in range(100)]
                monitor.sample()
                time.sleep(0.01)
        
        # Should have collected multiple samples
        assert len(monitor.samples) > 1


class TestMemoryDecorators:
    """Test memory monitoring decorators."""
    
    def test_memory_limit_decorator(self):
        """Test memory limit decorator with a function that should not exceed limits."""
        # Get baseline memory usage first
        import psutil
        process = psutil.Process()
        baseline_mb = process.memory_info().rss / (1024 * 1024)
        
        # Set limit well above baseline to allow for small allocations
        limit_mb = baseline_mb + 50.0  # Allow 50MB above baseline
        
        @memory_limit(max_memory_mb=limit_mb)
        def small_function():
            return [i for i in range(1000)]  # Small allocation
        
        result = small_function()
        assert len(result) == 1000
    
    def test_memory_limit_enforcement(self):
        """Test that memory limit decorator actually enforces limits."""
        @memory_limit(max_memory_mb=1.0)  # Very low limit that should be exceeded
        def memory_intensive_function():
            # Allocate 5MB of data
            return b'x' * (5 * 1024 * 1024)
        
        # Should raise MemoryError when limit is exceeded
        with pytest.raises(MemoryError, match="exceeded limit"):
            memory_intensive_function()
    
    def test_memory_profiling_decorator(self):
        """Test memory profiling decorator."""
        @memory_profiling(enable_sampling=True)
        def profiled_function():
            return [i for i in range(1000)]
        
        result = profiled_function()
        assert len(result) == 1000


class TestMemoryLeakDetector:
    """Test memory leak detection."""
    
    def test_leak_detector_no_leak(self):
        """Test leak detector with no memory leak."""
        detector = MemoryLeakDetector(tolerance_mb=5.0)
        detector.establish_baseline()
        
        # Do some work that shouldn't leak
        for i in range(10):
            data = [j for j in range(100)]
            del data
        
        has_leak, difference = detector.check_for_leaks()
        assert not has_leak
    
    def test_leak_detector_baseline_establishment(self):
        """Test baseline establishment."""
        detector = MemoryLeakDetector()
        baseline = detector.establish_baseline()
        
        assert baseline > 0
        assert detector.baseline_memory == baseline


class TestMemoryStressTests:
    """Test memory stress testing utilities."""
    
    def test_create_memory_stress_test(self):
        """Test memory stress test creation."""
        stress_test = create_memory_stress_test(
            target_memory_mb=10.0,
            chunk_size_mb=2.0
        )
        
        chunks_allocated = stress_test()
        assert chunks_allocated == 5  # 10MB / 2MB per chunk
    
    def test_memory_benchmark(self):
        """Test memory benchmarking utility."""
        def test_function(n):
            # Make the function do more work to ensure measurable execution time
            result = []
            for i in range(n):
                result.append(i * 2)  # Simple computation
            time.sleep(0.001)  # Small delay to ensure measurable time
            return result
        
        benchmark_result = memory_benchmark(test_function, 1000)
        
        assert 'result' in benchmark_result
        assert 'execution_time' in benchmark_result
        assert 'memory_stats' in benchmark_result
        assert 'peak_memory_mb' in benchmark_result
        assert 'memory_increase_mb' in benchmark_result
        assert 'sample_count' in benchmark_result
        
        assert len(benchmark_result['result']) == 1000
        # Allow for timer resolution issues on Windows/macOS - execution_time can be 0.0
        assert benchmark_result['execution_time'] >= 0
        assert benchmark_result['peak_memory_mb'] > 0


class TestMemoryTrackingContext:
    """Test memory tracking context manager."""
    
    def test_memory_tracking_context(self, capsys):
        """Test memory tracking context manager."""
        with memory_tracking(enable_sampling=True):
            # Do some memory-using work
            data = [i for i in range(1000)]
            time.sleep(0.1)
        
        # Should print memory stats
        captured = capsys.readouterr()
        assert "Memory Stats:" in captured.out
        assert "Initial=" in captured.out
        assert "Peak=" in captured.out
        assert "Final=" in captured.out


class TestIntegrationWithPsutil:
    """Test integration with psutil for real memory monitoring."""
    
    def test_real_memory_monitoring(self):
        """Test monitoring actual memory usage."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        with MemoryMonitor() as monitor:
            # Allocate some memory
            large_list = [i for i in range(10000)]
            monitor.sample()
            
            # Memory should have increased
            current_memory = process.memory_info().rss
            assert current_memory >= initial_memory
        
        # Verify monitor captured the increase
        assert monitor.final_snapshot.rss >= monitor.initial_snapshot.rss