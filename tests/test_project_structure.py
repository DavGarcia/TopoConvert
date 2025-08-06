"""Test project structure and configuration files."""
import os
import sys
from pathlib import Path

# Use tomllib for Python 3.11+, fallback to tomli for 3.9-3.10
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def test_root_files_exist():
    """Test that all required root files exist."""
    root_dir = Path(__file__).parent.parent
    required_files = [
        'pyproject.toml',
        '.gitignore',
        'README.md',
        'LICENSE',
        'CONTRIBUTING.md',
    ]
    
    for file in required_files:
        file_path = root_dir / file
        assert file_path.exists(), f"Missing required file: {file}"


def test_pyproject_toml_valid():
    """Test that pyproject.toml has valid structure and content."""
    root_dir = Path(__file__).parent.parent
    pyproject_path = root_dir / 'pyproject.toml'
    
    if pyproject_path.exists():
        with open(pyproject_path, 'rb') as f:
            data = tomllib.load(f)
        
        # Check project metadata
        assert 'project' in data
        assert data['project']['name'] == 'topoconvert'
        assert 'version' in data['project']
        assert 'dependencies' in data['project']
        
        # Check CLI entry point
        assert 'project' in data
        assert 'scripts' in data['project']
        assert 'topoconvert' in data['project']['scripts']


def test_gitignore_has_python_patterns():
    """Test that .gitignore includes Python-specific patterns."""
    root_dir = Path(__file__).parent.parent
    gitignore_path = root_dir / '.gitignore'
    
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            content = f.read()
        
        # Check for common Python patterns
        patterns = ['__pycache__', '*.py[cod]', '.pytest_cache', '*.egg-info']
        for pattern in patterns:
            assert pattern in content, f".gitignore missing pattern: {pattern}"