# Gandalf MCP Server Test Suite

This directory contains comprehensive tests for the Gandalf MCP server, ensuring functionality, security, performance, and reliability.

## Test Structure

### Test Categories

- **Core Tests**: Basic server functionality, JSON-RPC compliance, initialization
- **File Tests**: File operations, listing, filtering, relevance scoring  
- **Project Tests**: Project information, git integration, statistics
- **Context Intelligence Tests**: File prioritization, relevance scoring, context analysis
- **Security Tests**: Security validation, input sanitization, edge cases
- **Performance Tests**: Performance benchmarks, load testing, stress testing
- **Integration Tests**: End-to-end workflows and tool interactions
- **Workspace Detection Tests**: Project root identification and workspace detection
- **Logging Tests**: RPC message logging and file operation tracking

### Test Suites

| Suite                  | File                            | Tests | Description                                                     |
| ---------------------- | ------------------------------- | ----- | --------------------------------------------------------------- |
| `core`                 | `core-tests.sh`                 | 12    | Basic server functionality, initialization, JSON-RPC compliance |
| `file`                 | `file-tests.sh`                 | 13    | File operations, listing, filtering, relevance scoring          |
| `project`              | `project-tests.sh`              | 9     | Project information, git integration, statistics                |
| `context-intelligence` | `context-intelligence-tests.sh` | 13    | Context intelligence, relevance scoring, file prioritization    |
| `security`             | `security-tests.sh`             | 10    | Security validation, input sanitization, edge cases             |
| `performance`          | `performance-tests.sh`          | 15    | Performance benchmarks, load testing, stress testing            |
| `integration`          | `integration-tests.sh`          | 7     | End-to-end workflows, multi-tool scenarios                      |
| `workspace-detection`  | `workspace-detection-tests.sh`  | 8     | Workspace detection and project root identification             |
| `rpc-logging`          | `rpc-logging-tests.sh`          | 6     | JSON-RPC message logging and analysis                           |
| `file-logging`         | `file-logging-tests.sh`         | 4     | File operation logging and tracking                             |

**Total: 97 test cases**

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

All test files follow the same pattern:

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

- **File Tests**: `create_standard_project()` - Multi-file project with various types and directories
- **Context Intelligence Tests**: `create_context_intelligence_project()` - Complex project for context intelligence testing
- **Performance Tests**: `create_large_project_structure()` - Large project with many files for performance testing
- **Security Tests**: `create_security_project()` - Project structure for security testing
- **Project Tests**: `create_project_test_structure()` - Specialized structure with git history for project operation tests
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
./gandalf/tests/test-suite-manager.sh
# or
./gandalf/tests/test-suite-manager.sh all
```

### Individual Test Suites

```bash
./gandalf/tests/test-suite-manager.sh core
./gandalf/tests/test-suite-manager.sh file
./gandalf/tests/test-suite-manager.sh project
./gandalf/tests/test-suite-manager.sh context-intelligence
./gandalf/tests/test-suite-manager.sh security
./gandalf/tests/test-suite-manager.sh performance
./gandalf/tests/test-suite-manager.sh integration
./gandalf/tests/test-suite-manager.sh workspace-detection
./gandalf/tests/test-suite-manager.sh rpc-logging
./gandalf/tests/test-suite-manager.sh file-logging
```

### Test Categories

```bash
# Unit tests (core functionality)
./gandalf/tests/test-suite-manager.sh unit
./gandalf/tests/test-suite-manager.sh security
./gandalf/tests/test-suite-manager.sh performance
./gandalf/tests/test-suite-manager.sh smoke
```

### Test Options

```bash
./gandalf/tests/test-suite-manager.sh --verbose
./gandalf/tests/test-suite-manager.sh --timing
./gandalf/tests/test-suite-manager.sh --count
./gandalf/tests/test-suite-manager.sh --help
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
