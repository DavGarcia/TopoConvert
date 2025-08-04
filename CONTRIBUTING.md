# Contributing to TopoConvert

Thank you for your interest in contributing to TopoConvert! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our code of conduct: be respectful, inclusive, and constructive in all interactions.

## How to Contribute

### Reporting Issues

1. Check if the issue already exists in the [issue tracker](https://github.com/yourusername/topoconvert/issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Detailed description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Your environment (OS, Python version, etc.)
   - Sample data if applicable

### Suggesting Features

1. Check existing issues and discussions
2. Open a new issue with the "enhancement" label
3. Describe the feature and its use case
4. Explain why it would benefit other users

### Contributing Code

#### Setup Development Environment

```bash
# Fork and clone the repository
git clone https://github.com/yourusername/topoconvert.git
cd topoconvert

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

#### Development Workflow

1. Create a new branch for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following our coding standards

3. Write or update tests for your changes

4. Run tests locally:
   ```bash
   pytest
   ```

5. Format and lint your code:
   ```bash
   black topoconvert/
   flake8 topoconvert/
   mypy topoconvert/
   ```

6. Commit your changes:
   ```bash
   git add .
   git commit -m "Add feature: description of your changes"
   ```

7. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

8. Create a Pull Request

### Coding Standards

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting
- Add type hints where possible
- Write docstrings for all functions and classes
- Keep functions focused and small
- Write descriptive variable names

### Testing Guidelines

- Write tests for all new functionality
- Maintain or improve code coverage
- Use pytest for testing
- Place tests in the `tests/` directory
- Name test files as `test_<module_name>.py`
- Use descriptive test function names

### Documentation

- Update docstrings for API changes
- Update README.md if adding new features
- Add examples for new commands
- Keep documentation clear and concise

## Pull Request Process

1. Ensure all tests pass
2. Update documentation as needed
3. Add an entry to CHANGELOG.md (if it exists)
4. Request review from maintainers
5. Address review feedback
6. Squash commits if requested

### PR Checklist

- [ ] Tests pass locally
- [ ] Code is formatted with Black
- [ ] No linting errors
- [ ] Tests added/updated for changes
- [ ] Documentation updated
- [ ] Commit messages are clear

## Project Structure

```
topoconvert/
├── topoconvert/          # Main package
│   ├── cli.py           # CLI entry point
│   ├── commands/        # Command implementations
│   └── utils/           # Shared utilities
├── tests/               # Test suite
├── docs/                # Documentation
└── examples/            # Example data and scripts
```

## Questions?

Feel free to open an issue for any questions about contributing. We're here to help!

Thank you for contributing to TopoConvert! 🎉