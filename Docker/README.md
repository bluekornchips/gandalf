# Gandalf Shell Testing - Docker

Lightweight container for cross-platform shell script testing.

## Quick Start

```bash
# Build and run all tests using the gandalf CLI
./gandalf docker-test

# Run specific test types in Docker
./gandalf docker-test --shell
./gandalf docker-test --python
```

## Manual Docker Usage

```bash
# Build image manually
docker build -f gandalf/Docker/Dockerfile -t gandalf-shell:latest .

# Run tests directly in container
docker run --rm gandalf-shell:latest

# Interactive shell access
docker run -it --rm gandalf-shell:latest /bin/bash
```

## Commands

CLI

- `./gandalf docker-test` - Run all tests in container
- `./gandalf docker-test --shell` - Shell tests only in container
- `./gandalf docker-test --python` - Python tests only in container

Docker

- `docker run --rm gandalf-shell:latest` - Run default tests
- `docker run --rm gandalf-shell:latest gdlf test --shell` - Shell tests
- `docker run --rm gandalf-shell:latest gdlf test --python` - Python tests

## Files

- `Dockerfile` - Ubuntu 22.04 with essential tools
- `.dockerignore` - Build optimization
