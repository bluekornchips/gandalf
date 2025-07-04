# Contributing to Gandalf

Development guidelines for Gandalf MCP Server.

## Requirements

- Python 3.10+
- Git
- pytest, bats, shellcheck, black

## Workflow

1. Check existing issues
2. Create new descriptive issue
3. Branch from main
4. Write tests (90% coverage required)
5. Update docs
6. Run `./gandalf.sh lembas`, confirm tests pass
7. Submit PR

## Areas to Contribute

- Performance optimization
- IDE integration
- Documentation
- Testing
- Bug fixes

## Testing

Must maintain 90% test coverage.

```bash
# Python tests
pytest --cov=src --cov-report=html

# Shell tests
bats tests/

# Full validation
./gandalf.sh lembas
```

## Getting Help

- [GitHub Discussions](https://github.com/bluekornchips/gandalf/discussions)
- [GitHub Issues](https://github.com/bluekornchips/gandalf/issues)

Before asking: check docs, search existing issues, provide context.
