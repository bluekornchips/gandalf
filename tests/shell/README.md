# Gandalf MCP Server Test Suite

This directory contains comprehensive tests for the Gandalf MCP server, ensuring functionality, security, performance, and reliability.

## Test Structure

The test system has been restructured into separate managers for better organization:

- **Main Coordinator**: `../test-suite.sh` - Coordinates between shell and Python tests
- **Shell Test Manager**: `../shell-tests-manager.sh` - Handles all shell/bats tests
- **Python Test Manager**: `../python-tests-manager.sh` - Handles all Python/pytest tests

### Test Categories

- **Core Tests**: Basic server functionality, JSON-RPC compliance, initialization (Python)
- **File Tests**: File operations, listing, filtering, relevance scoring (Python)
- **Project Tests**: Project information, git integration, statistics (Shell)
- **Context Intelligence Tests**: File prioritization, relevance scoring, context analysis (Python)
- **Security Tests**: Security validation, input sanitization, edge cases (Python)
- **Performance Tests**: Performance benchmarks, load testing, stress testing (Shell)
- **Integration Tests**: End-to-end workflows and tool interactions (Shell)
- **Workspace Detection Tests**: Project root identification and workspace detection (Shell)
- **Conversation Export Tests**: Conversation export functionality (Shell)

### Active Shell Test Suites

| Suite                  | File                            | Tests | Description                                                     |
| ---------------------- | ------------------------------- | ----- | --------------------------------------------------------------- |
| `project`              | `project-tests.sh`              | 9     | Project information, git integration, statistics                |
| `workspace-detection`  | `workspace-detection-tests.sh`  | 10    | Workspace detection and project root identification             |
| `conversation-export`  | `conversation-export-tests.sh`  | 12    | Conversation export functionality                               |
| `performance`          | `performance-tests.sh`          | 15    | Performance benchmarks, load testing, stress testing            |
| `integration`          | `integration-tests.sh`          | 6     | End-to-end workflows, multi-tool scenarios                      |

**Total Shell Tests: 50 test cases**

### Migrated to Python Tests

The following test suites have been migrated from shell/bats to Python/pytest for better maintainability:

- `core` - Core MCP server functionality (better JSON-RPC testing in Python)
- `file` - File operations (complex JSON handling better suited for Python)
- `context-intelligence` - Scoring algorithms (direct Python testing needed)
- `security` - Security validation (precise exception testing required)

**Total Python Tests: 163 test cases**

## Tool Coverage

### File Operations

- `list_project_files` - File listing, filtering, relevance scoring, edge cases

### Project Operations

- `get_project_info` - Project metadata, git integration, statistics

### Context Intelligence

- File relevance scoring and prioritization algorithms
- Git activity tracking and analysis
- Directory and file type importance weighting

## Test Patterns & Standards

### Consistent Structure

All shell test files follow the same pattern:

```bash
#!/usr/bin/env bats
# Test Description
# Detailed purpose and scope

set -eo pipefail

# Standard setup
GIT_ROOT=$(git rev-parse --show-toplevel)
GANDALF_ROOT="$GIT_ROOT/gandalf"

source "$GANDALF_ROOT/tests/shell/fixtures/helpers/test-helpers.sh"

export GANDALF_TEST_MODE="true"
export MCP_DEBUG="false"

setup() {
    shared_setup "test-project"
}

teardown() {
    shared_teardown
}

@test "descriptive test name" {
    # Test implementation using helper functions
    local response
    response=$(execute_rpc "list_project_files" '{"max_files": 10}')
    
    # Validation using helper functions
    validate_jsonrpc_response "$response"
    
    # Assertions
    [[ "$response" == *"content"* ]]
}
```

### Shared Functionality

Located in `fixtures/helpers/test-helpers.sh`:

**Core Functions:**

- `execute_rpc()` - JSON-RPC request execution with response filtering
- `validate_jsonrpc_response()` - Response validation and error checking
- `generate_test_id()` - Unique test ID generation for JSON-RPC requests

**Test Environment:**

- `shared_setup()` - Standard test environment setup with customizable project details
- `shared_teardown()` - Standard test environment cleanup
- `create_minimal_project()` - Basic project with README and git history (used by core and conversation tests)

### Test-Specific Project Creation Functions

Each test suite that requires a unique project structure has its own creation function:

- **Project Tests**: `create_project_test_structure()` - Specialized structure with git history for project operation tests
- **Performance Tests**: `create_large_project_structure()` - Large project with many files for performance testing
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

### All Tests (Shell + Python)

```bash
# From gandalf directory
./tests/test-suite.sh
# or
gdlf test
```

### Shell Tests Only

```bash
./tests/test-suite.sh --shell
# or
gdlf test --shell
```

### Python Tests Only

```bash
./tests/test-suite.sh --python
# or
gdlf test --python
```

### Individual Test Suites

```bash
# Shell suites
./tests/test-suite.sh project
./tests/test-suite.sh workspace-detection
./tests/test-suite.sh conversation-export
./tests/test-suite.sh performance
./tests/test-suite.sh integration

# Python suites
./tests/test-suite.sh python-core
./tests/test-suite.sh python-file
./tests/test-suite.sh python-security
./tests/test-suite.sh python-utils
./tests/test-suite.sh python-config
```

### Test Categories

```bash
# Unit tests (shell functionality)
./tests/test-suite.sh unit
./tests/test-suite.sh security    # Python security tests
./tests/test-suite.sh performance # Shell performance tests
./tests/test-suite.sh smoke       # Quick validation tests
./tests/test-suite.sh lembas       # Fast tests for lembas validation
```

### Test Options

```bash
./tests/test-suite.sh --verbose
./tests/test-suite.sh --timing
./tests/test-suite.sh --count
./tests/test-suite.sh --help
```

### Test Counts

```bash
# All tests
./tests/test-suite.sh --count
# Output: Total tests: 213
#         Shell tests (bats): 50
#         Python tests (pytest): 163

# Shell only
./tests/test-suite.sh --shell --count
# Output: 50

# Python only  
./tests/test-suite.sh --python --count
# Output: 163
```

### Reporting

```bash
# Summary output
=========================================
Test Summary:
Total suites: 10
Passed: 9
Failed: 1

Failed suites:
  - performance
```

## Migration Notes

Several test suites have been migrated from shell/bats to Python/pytest for better maintainability:

- **Core**: Server initialization and JSON-RPC handling better tested in Python
- **File**: Complex JSON-RPC testing better suited for Python
- **Context Intelligence**: Scoring algorithms need direct Python testing
- **Security**: Security validation requires precise exception testing

See `tests/MIGRATION_GAMEPLAN.md` for full migration plan.

## Helper Functions

To use test helpers in shell scripts (not BATS tests):

```bash
source "$GANDALF_ROOT/tests/shell/fixtures/helpers/test-helpers.sh"
```

Located in `fixtures/helpers/test-helpers.sh`.