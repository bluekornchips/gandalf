# Gandalf MCP Server Test Suite

Comprehensive tests for the Gandalf MCP server, ensuring functionality, security, performance, and reliability.

## Test Structure

The test system is organized into separate managers:

- Main Coordinator\*\*: `../test-suite.sh` - Coordinates between shell and Python tests
- **Shell Test Manager**: `../shell-tests-manager.sh` - Handles all shell/bats tests
- **Python Test Manager**: `../python-tests-manager.sh` - Handles all Python/pytest tests

### Test Categories

- **Core Tests**: Basic server functionality, JSON-RPC compliance (Python)
- **File Tests**: File operations, listing, filtering, relevance scoring (Python)
- **Project Tests**: Project information, git integration, statistics (Shell)
- **Context Intelligence Tests**: File prioritization, relevance scoring (Python)
- **Security Tests**: Security validation, input sanitization (Python)
- **Performance Tests**: Performance benchmarks, load testing (Shell)
- **Integration Tests**: End-to-end workflows and tool interactions (Shell)
- **Workspace Detection Tests**: Project root identification (Shell)
- **Conversation Export Tests**: Conversation export functionality (Shell)

### Active Shell Test Suites

| Suite                  | File                            | Description                                           |
| ---------------------- | ------------------------------- | ----------------------------------------------------- |
| `context-intelligence` | `context-intelligence-tests.sh` | Context intelligence and relevance scoring            |
| `conversation-export`  | `conversation-export-tests.sh`  | Conversation export functionality                     |
| `core`                 | `core-tests.sh`                 | Core MCP server functionality                         |
| `file`                 | `file-tests.sh`                 | File operations                                       |
| `integration`          | `integration-tests.sh`          | Integration tests                                     |
| `performance`          | `performance-tests.sh`          | Performance and load testing                          |
| `project`              | `project-tests.sh`              | Project operations                                    |
| `security`             | `security-tests.sh`             | Security validation and edge cases                    |
| `uninstall`            | `uninstall-tests.sh`            | Uninstall script functionality and cleanup operations |
| `workspace-detection`  | `workspace-detection-tests.sh`  | Workspace detection strategies                        |

**Total Shell Tests: 131 test cases**

### Python Test Coverage

The Python test suite uses pytest and is organized into directories:

- **`core/`** - Core MCP server functionality, context intelligence, conversation analysis, file scoring, git activity
- **`tool_calls/`** - Tool implementations, conversation aggregation, export functionality, integration tests
- **`utils/`** - Utility functions, access control, performance, project operations
- **`config/`** - Configuration and constants testing

**Total Python Tests: 581 test cases**

## Tool Coverage

### File Operations

- `list_project_files` - File listing, filtering, relevance scoring

### Project Operations

- `get_project_info` - Project metadata, git integration, statistics

### Context Intelligence

- File relevance scoring and prioritization algorithms
- Git activity tracking and analysis
- Directory and file type importance weighting

## Test Standards

### Shell Test Structure

All shell test files follow this pattern:

```bash
#!/usr/bin/env bats
# Test Description

set -eo pipefail

GIT_ROOT=$(git rev-parse --show-toplevel)
GANDALF_ROOT="$GIT_ROOT/gandalf"

source "$GANDALF_ROOT/scripts/tests/fixtures/helpers/test-helpers.sh"

export GANDALF_TEST_MODE="true"
export MCP_DEBUG="false"

setup() {
    shared_setup "test-project"
}

teardown() {
    shared_teardown
}

@test "descriptive test name" {
    local response
    response=$(execute_rpc "list_project_files" '{"max_files": 10}')

    validate_jsonrpc_response "$response"

    [[ "$response" == *"content"* ]]
}
```

### Shared Test Functions

Located in `fixtures/helpers/test-helpers.sh`:

**Core Functions:**

- `execute_rpc()` - JSON-RPC request execution
- `validate_jsonrpc_response()` - Response validation
- `generate_test_id()` - Unique test ID generation

**Test Environment:**

- `shared_setup()` - Standard test environment setup
- `shared_teardown()` - Standard test environment cleanup
- `create_minimal_project()` - Basic project with README and git history

### Project Creation Functions

Each test suite has its own project creation function:

- **Project Tests**: `create_project_test_structure()` - Specialized structure with git history
- **Performance Tests**: `create_large_project_structure()` - Large project for performance testing
- **Integration Tests**: `create_integration_test_structure()` - Realistic structure for integration testing

## Running Tests

### Prerequisites

```bash
# macOS
brew install bats-core jq

# Ubuntu/Debian
apt-get install bats jq

# Verify installation
command -v bats python3 jq
```

### All Tests

```bash
# From gandalf directory
./scripts/test-suite.sh
# or
gdlf test
```

### Specific Test Types

```bash
# Shell tests only
./scripts/test-suite.sh --shell
gdlf test --shell

# Python tests only
./scripts/test-suite.sh --python
gdlf test --python
```

### Individual Test Suites

```bash
# Shell suites
./scripts/test-suite.sh context-intelligence
./scripts/test-suite.sh conversation-export
./scripts/test-suite.sh core
./scripts/test-suite.sh file
./scripts/test-suite.sh integration
./scripts/test-suite.sh performance
./scripts/test-suite.sh project
./scripts/test-suite.sh security
./scripts/test-suite.sh uninstall
./scripts/test-suite.sh workspace-detection

# Python tests (run as single suite)
./scripts/test-suite.sh python
```

### Test Categories

```bash
# Unit tests
./scripts/test-suite.sh unit

# Security tests
./scripts/test-suite.sh security

# Performance tests
./scripts/test-suite.sh performance

# Quick validation
./scripts/test-suite.sh smoke

# Fast tests for lembas validation
./scripts/test-suite.sh lembas
```

### Test Options

```bash
# Verbose output
./scripts/test-suite.sh --verbose

# Show execution timing
./scripts/test-suite.sh --timing

# Show test counts only
./scripts/test-suite.sh --count
```

## Test Data

### Mock Data Standards

All test data uses **Lord of the Rings** references:

```bash
# Example test data
TEST_USER="frodo"
TEST_PROJECT="shire-project"
TEST_FILES=("fellowship.py" "ring.js" "gandalf.md")
```

### Test Fixtures

Located in `fixtures/data/`:

- **Project structures** - Various project layouts for testing
- **Git repositories** - Pre-configured git histories
- **Configuration files** - Sample MCP configurations
- **Mock databases** - Test conversation data

## Debugging Tests

### Debug Mode

```bash
# Enable debug output
export GANDALF_DEBUG="true"
./scripts/test-suite.sh project

# Debug specific test
bats --timing gandalf/tools/tests/unit/project-tests.sh
```

### Test Isolation

```bash
# Run single test
bats --filter "project information" scripts/tests/project-tests.sh

# Run with cleanup disabled (for inspection)
export GANDALF_TEST_CLEANUP="false"
./scripts/test-suite.sh project
```

### Common Issues

**Tests failing with "command not found":**

- Ensure `bats`, `jq`, and `python3` are installed
- Check `PATH` includes required tools

**Permission errors:**

- Run `chmod +x` on test scripts
- Ensure test directories are writable

**Git-related failures:**

- Ensure git is configured with user.name and user.email
- Check git repository is properly initialized

## Contributing Tests

### Adding New Tests

1. **Choose appropriate test type** (shell vs Python)
2. **Follow naming conventions** (`feature-tests.sh` for shell)
3. **Use shared helper functions** for consistency
4. **Include proper setup/teardown** for isolation
5. **Use Lord of the Rings references** for mock data

### Test Requirements

- All tests must be isolated and repeatable
- Tests must clean up after themselves
- Mock data must use thematic references
- Tests must cover both success and failure cases
- Performance tests must include baseline measurements

### Code Coverage

- Maintain minimum 90% test coverage
- Add tests for any new functionality
- Ensure edge cases are covered
