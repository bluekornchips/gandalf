# Contributing to Gandalf

Development guidelines for the Gandalf MCP Server.

## Prerequisites

- Python 3.12+
- Git
- Development tools: pytest, bats, shellcheck, ruff

## Development Workflow

### 1. Setup

```bash
# Check existing issues first
# Create descriptive issue if needed
# Branch from main
git checkout -b feature/descriptive-name

# Install dependencies
cd gandalf/server
pip install -e .
```

### 2. Development

```bash
# Format code
black src/
isort src/

# Run tests during development
./gandalf test
```

### 3. Testing

```bash
# Run all tests
./gandalf test

# Extended validation
./gandalf lembas
```

### 4. Submission

```bash
# Final validation
./gandalf lembas

# Submit PR with clear description
```

## Code Standards

- **Python**: PEP 8, ruff
- **Shell**: shellcheck validation
- **Testing**: 80% coverage minimum
- **Documentation**: Update relevant docs for changes

## Testing Requirements

All contributions must include tests:

```bash
# Python tests with coverage
pytest --cov=src --cov-report=html

# Shell tests
bats tests/

# Integration tests
./gandalf test
```

Test coverage must be ≥80% for new code.

## Documentation Updates

Update documentation for:

- New features or tools
- API changes
- Configuration changes
- Breaking changes

## Areas for Contribution

- **Performance**: Optimization and caching improvements
- **IDE Integration**: Additional tool support
- **Documentation**: Clarity and completeness improvements
- **Testing**: Coverage and reliability improvements
- **Bug Fixes**: Issue resolution and stability

## Code Review Process

1. Automated checks must pass
2. Manual review by maintainers
3. Testing validation required
4. Documentation updates reviewed

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/bluekornchips/gandalf/issues)
- **Documentation**: [README](../README.md) | [Installation](INSTALLATION.md) | [API](API.md)

Before asking for help:

1. Check existing documentation
2. Search existing issues
3. Provide clear context and steps to reproduce

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
