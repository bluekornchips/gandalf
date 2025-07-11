# Contributing to Gandalf

Development guidelines for the Gandalf MCP Server.

## Prerequisites

- Python 3.10+
- Git
- Development tools: pytest, bats, shellcheck, black, isort, flake8

## Development Workflow

### 1. Setup

```bash
# Check existing issues first
# Create descriptive issue if needed
# Branch from main
git checkout -b feature/descriptive-name
```

### 2. Development

```bash
# Install dependencies
cd gandalf/server
pip install -r requirements.txt

# Run tests during development
./gandalf.sh test

# Format code
black src/
isort src/
flake8 src/
```

### 3. Testing

```bash
# Run all tests
./gandalf.sh test

# Run specific test suites
./gandalf.sh test --python
./gandalf.sh test --shell

# Full validation
./gandalf.sh lembas
```

### 4. Submission

```bash
# Update documentation if needed
# Run final validation
./gandalf.sh lembas

# Submit PR with clear description
```

## Code Standards

- Python: Follow PEP 8, use black, isort, flake8
- Shell: Use shellcheck for validation
- Testing: Maintain 90% test coverage minimum
- Documentation: Update relevant docs for changes

## Testing Requirements

All contributions must include tests:

```bash
# Python tests
pytest --cov=src --cov-report=html

# Shell tests
bats tests/

# Integration tests
./gandalf.sh test --integration
```

## Documentation

Update documentation for:

- New features or tools
- API changes
- Configuration changes
- Breaking changes

## Areas for Contribution

- Performance: Optimization and caching improvements
- IDE Integration: Additional tool support
- Documentation: Clarity and completeness improvements
- Testing: Coverage and reliability improvements
- Bug Fixes: Issue resolution and stability

## Getting Help

- Issues: [GitHub Issues](https://github.com/bluekornchips/gandalf/issues)
- Discussions: [GitHub Discussions](https://github.com/bluekornchips/gandalf/discussions)

Before asking for help:

1. Check existing documentation
2. Search existing issues
3. Provide clear context and steps to reproduce

## Code Review Process

1. Automated checks must pass
2. Manual review by maintainers
3. Testing validation required
4. Documentation updates reviewed

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
