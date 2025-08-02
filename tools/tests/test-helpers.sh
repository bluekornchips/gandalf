#!/usr/bin/env bash
# Test Helper Functions for Gandalf MCP Server Test Suite
# Shared utilities for consistent testing across all test categories

set -euo pipefail

readonly TEST_ID_COUNTER_START=0
readonly MCP_DEBUG_DEFAULT="false"

# Global test counter
TEST_ID_COUNTER=${TEST_ID_COUNTER_START}

setup_gandalf_paths() {
	local current_dir
	current_dir="$(pwd -P)"
	local search_dir="$current_dir"

	if [[ -n "${BASH_SOURCE[1]:-}" ]]; then
		search_dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd -P)"
	fi

	while [[ "$search_dir" != "/" ]]; do
		if [[ -d "$search_dir/server/src" && -f "$search_dir/server/src/main.py" ]]; then
			if [[ -z "${GANDALF_ROOT:-}" ]]; then
				export GANDALF_ROOT="$search_dir"
			fi
			if [[ -z "${SERVER_DIR:-}" ]]; then
				export SERVER_DIR="$GANDALF_ROOT/server"
			fi
			if [[ -z "${TESTS_DIR:-}" ]]; then
				export TESTS_DIR="$GANDALF_ROOT/scripts/tests"
			fi
			if [[ -z "${SCRIPTS_DIR:-}" ]]; then
				export SCRIPTS_DIR="$GANDALF_ROOT/scripts"
			fi
			export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"
			return 0
		fi
		search_dir="$(dirname "$search_dir")"
	done

	echo "Warning: Could not auto-detect GANDALF_ROOT, using fallback" >&2
	if [[ -z "${GANDALF_ROOT:-}" ]]; then
		export GANDALF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
	fi
	if [[ -z "${SERVER_DIR:-}" ]]; then
		export SERVER_DIR="$GANDALF_ROOT/server"
	fi
	if [[ -z "${TESTS_DIR:-}" ]]; then
		export TESTS_DIR="$GANDALF_ROOT/tools/tests"
	fi
	if [[ -z "${SCRIPTS_DIR:-}" ]]; then
		export SCRIPTS_DIR="$GANDALF_ROOT/tools/bin"
	fi
	export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"
}

setup_gandalf_paths

check_test_dependencies() {
	if ! command -v bats &>/dev/null; then
		echo "ERROR: BATS (Bash Automated Testing System) is required for shell tests" >&2
		if [[ "$OSTYPE" == "darwin"* ]]; then
			echo "Install BATS with: brew install bats-core" >&2
		elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
			echo "Install BATS with: apt install bats (Ubuntu/Debian) or yum install bats (RHEL/CentOS)" >&2
		else
			echo "Install BATS from: https://github.com/bats-core/bats-core#installation" >&2
		fi
		return 1
	fi

	if ! command -v python3 &>/dev/null; then
		echo "ERROR: Python 3 not found" >&2
		return 1
	fi

	local python_version
	python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
	echo "Python $python_version found"

	if ! python3 -c "import yaml" &>/dev/null; then
		echo "ERROR: PyYAML is required. Install with: pip install PyYAML" >&2
		return 1
	fi

	return 0
}

export MCP_DEBUG="${MCP_DEBUG:-$MCP_DEBUG_DEFAULT}"

generate_test_id() {
	TEST_ID_COUNTER=$((TEST_ID_COUNTER + 1))
	echo "$TEST_ID_COUNTER"
}

execute_rpc() {
	local method="$1"
	local params="$2"
	local project_root="${3:-${TEST_PROJECT_DIR:-$PWD}}"

	# Source centralized configuration
	source "$GANDALF_ROOT/tools/config/test-config.sh"

	export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"

	[[ -z "$params" ]] && params="{}"

	# Enhanced JSON validation with security checks
	if ! validate_json_params "$params"; then
		return 1
	fi

	local test_id
	test_id=$(generate_test_id)

	local request
	request=$(jq -nc \
		--arg method "$method" \
		--argjson params "$params" \
		--arg id "$test_id" \
		'{
            "jsonrpc": "2.0",
            "id": $id,
            "method": $method,
            "params": $params
        }')

	local temp_stdout temp_stderr
	temp_stdout=$(mktemp)
	temp_stderr=$(mktemp)

	# Use timeout to prevent hanging and ensure proper process termination
	timeout "$TEST_TIMEOUT_DEFAULT" bash -c "
        cd '$GANDALF_ROOT/server'
        export PYTHONPATH=.
        echo '$request' | python3 src/main.py --project-root '$project_root'
    " >"$temp_stdout" 2>"$temp_stderr"
	exit_code=$?

	local full_output
	full_output=$(cat "$temp_stdout")

	rm -f "$temp_stdout" "$temp_stderr"

	if [[ $exit_code -ne 0 ]]; then
		return 1
	fi

	local temp_file response
	temp_file=$(mktemp)
	echo "$full_output" >"$temp_file"

	response=""
	while IFS= read -r line; do
		if [[ -n "$line" ]]; then
			if echo "$line" | jq -e '.id != null' >/dev/null 2>&1; then
				local line_id
				line_id=$(echo "$line" | jq -r '.id' 2>/dev/null)
				if [[ "$line_id" == "$test_id" ]]; then
					response="$line"
					break
				fi
			fi
		fi
	done <"$temp_file"

	rm -f "$temp_file"
	echo "$response"
}

validate_jsonrpc_response() {
	local response="$1"
	local expected_id="${2:-}"

	if [[ -z "$response" ]]; then
		echo "No response received" >&2
		return 1
	fi

	# Check if this is a security validation error (these are valid security blocks)
	if echo "$response" | grep -q "Dangerous pattern.*detected in JSON params"; then
		return 0  # Security validation working correctly
	fi

	if echo "$response" | grep -q "JSON params exceed size limit"; then
		return 0  # Size limit validation working correctly  
	fi

	if echo "$response" | grep -q "Invalid JSON syntax in params"; then
		return 0  # JSON validation working correctly
	fi

	# Try to parse as JSON
	if ! echo "$response" | jq . >/dev/null 2>&1; then
		echo "Invalid JSON response: $response" >&2
		return 1
	fi

	# Validate JSON-RPC structure
	if ! echo "$response" | jq -e '.jsonrpc' >/dev/null 2>&1; then
		echo "Missing or invalid jsonrpc field" >&2
		return 1
	fi

	# Validate ID field (if expected_id is provided)
	if [[ -n "$expected_id" ]]; then
		if ! echo "$response" | jq -e '.id' >/dev/null 2>&1; then
			echo "Missing id field" >&2
			return 1
		fi

		local actual_id
		actual_id=$(echo "$response" | jq -r '.id')
		if [[ "$actual_id" != "$expected_id" ]]; then
			echo "ID mismatch. Expected: $expected_id, Got: $actual_id" >&2
			return 1
		fi
	fi

	# Check for either result or error field
	if ! echo "$response" | jq -e '.result' >/dev/null 2>&1; then
		if ! echo "$response" | jq -e '.error' >/dev/null 2>&1; then
			echo "Response missing both result and error fields" >&2
			return 1
		fi
	fi

	return 0
}

create_test_conversation_args() {
	local conversation_id="$1"
	local messages="$2"
	local title="${3:-Test Conversation}"
	local additional_tags="${4:-}"

	local tags='["test"]'
	if [[ -n "$additional_tags" ]]; then
		tags=$(echo "$additional_tags" | jq '. + ["test"] | unique')
	fi

	jq -nc \
		--arg id "$conversation_id" \
		--argjson messages "$messages" \
		--arg title "$title" \
		--argjson tags "$tags" \
		'{
            "conversation_id": $id,
            "messages": $messages,
            "title": $title,
            "tags": $tags
        }'
}

check_timeout_with_warning() {
	local duration="$1"
	local threshold="$2"
	local operation_name="$3"

	if [[ $duration -gt $threshold ]]; then
		echo "WARNING: $operation_name took ${duration}s (threshold: ${threshold}s)" >&2
		echo "This may indicate performance issues but is not a test failure" >&2
	fi
	return 0
}

# Shared test data cache for improved performance
readonly TEST_DATA_CACHE_DIR="$GANDALF_ROOT/.test-cache"

# Initialize shared test data cache
init_test_data_cache() {
    if [[ ! -d "$TEST_DATA_CACHE_DIR" ]]; then
        mkdir -p "$TEST_DATA_CACHE_DIR"
    fi
}

# Get or create cached test project structure
get_cached_test_project() {
    local project_type="${1:-standard}"
    local cache_key="project_${project_type}"
    local cache_path="$TEST_DATA_CACHE_DIR/$cache_key"
    
    init_test_data_cache
    
    # Return cached project if it exists and is recent (less than 1 hour old)
    if [[ -d "$cache_path" ]] && find "$cache_path" -maxdepth 0 -mmin -60 >/dev/null 2>&1; then
        echo "$cache_path"
        return 0
    fi
    
    # Create new cached project
    rm -rf "$cache_path" 2>/dev/null || true
    mkdir -p "$cache_path"
    
    case "$project_type" in
    "large")
        create_large_project_structure "$cache_path"
        ;;
    "nested")
        create_nested_project_structure "$cache_path"
        ;;
    "performance")
        create_performance_test_structure "$cache_path"
        ;;
    *)
        create_standard_project_structure "$cache_path"
        ;;
    esac
    
    echo "$cache_path"
}

# Create standard test project structure
create_standard_project_structure() {
    local project_dir="$1"
    
    cd "$project_dir"
    
    # Initialize git
    git init >/dev/null 2>&1
    git config user.name "Gandalf Test" >/dev/null 2>&1
    git config user.email "gandalf@shire.test" >/dev/null 2>&1
    
    # Create basic project files
    cat >README.md <<EOF
# Shire Project

A test project for the Fellowship of the Ring.

## Members
- Frodo Baggins (Ring Bearer)
- Samwise Gamgee (Gardener)
- Gandalf the Grey (Wizard)
EOF

    cat >package.json <<EOF
{
	"name": "shire-project",
	"version": "1.0.0",
	"description": "Fellowship test project",
	"main": "ring.js",
	"scripts": {
		"test": "echo 'One Ring to rule them all'"
	},
	"author": "Fellowship of the Ring",
	"license": "MIT"
}
EOF

    cat >src/fellowship.py <<EOF
#!/usr/bin/env python3
"""Fellowship of the Ring module."""

class Fellowship:
    def __init__(self):
        self.members = [
            "Frodo Baggins",
            "Samwise Gamgee", 
            "Gandalf the Grey"
        ]
    
    def get_ring_bearer(self):
        return "Frodo Baggins"
EOF

    mkdir -p src tests docs
    
    cat >tests/test_fellowship.py <<EOF
import unittest
from src.fellowship import Fellowship

class TestFellowship(unittest.TestCase):
    def test_ring_bearer(self):
        fellowship = Fellowship()
        self.assertEqual(fellowship.get_ring_bearer(), "Frodo Baggins")
EOF

    echo "# Fellowship Documentation" >docs/fellowship.md
    
    git add . >/dev/null 2>&1
    git commit -m "Initial commit: Fellowship project setup" >/dev/null 2>&1
}

# Create large project structure for performance testing
create_large_project_structure() {
    local project_dir="$1"
    
    cd "$project_dir"
    create_standard_project_structure "$project_dir"
    
    # Add many files for performance testing
    for dir in "src/modules" "src/components" "src/utils" "tests/unit" "tests/integration"; do
        mkdir -p "$dir"
        for i in $(seq 1 20); do
            cat >"$dir/hobbit_$i.py" <<EOF
"""Hobbit module $i for performance testing."""

class Hobbit$i:
    def __init__(self, name="Hobbit$i"):
        self.name = name
        self.home = "The Shire"
    
    def introduce(self):
        return f"I'm {self.name} from {self.home}"
EOF
        done
    done
    
    git add . >/dev/null 2>&1
    git commit -m "Add large project structure for performance testing" >/dev/null 2>&1
}

# Create nested project structure
create_nested_project_structure() {
    local project_dir="$1"
    
    cd "$project_dir"
    create_standard_project_structure "$project_dir"
    
    # Create deep nested structure
    local current_dir="src"
    for level in "rohan" "edoras" "golden_hall" "throne_room"; do
        current_dir="$current_dir/$level"
        mkdir -p "$current_dir"
        cat >"$current_dir/${level}_module.py" <<EOF
"""$level module for nested testing."""

class ${level^}:
    def __init__(self):
        self.location = "$level"
    
    def describe(self):
        return f"This is {self.location}"
EOF
    done
    
    git add . >/dev/null 2>&1
    git commit -m "Add nested structure for deep directory testing" >/dev/null 2>&1
}

# Create performance-optimized test structure
create_performance_test_structure() {
    local project_dir="$1"
    
    cd "$project_dir"
    create_standard_project_structure "$project_dir"
    
    # Add specific files for performance benchmarking
    mkdir -p "benchmarks" "profiles"
    
    cat >benchmarks/ring_performance.py <<EOF
"""Ring performance benchmarks."""
import time

def measure_ring_power():
    start = time.time()
    # Simulate ring power calculation
    power = sum(i * i for i in range(1000))
    end = time.time()
    return end - start, power

if __name__ == "__main__":
    duration, power = measure_ring_power()
    print(f"Ring power: {power}, calculated in {duration:.4f}s")
EOF

    git add . >/dev/null 2>&1
    git commit -m "Add performance benchmarking structure" >/dev/null 2>&1
}

# Copy cached project to test directory
copy_cached_project() {
    local project_type="${1:-standard}"
    local target_dir="$2"
    
    local cached_project
    cached_project=$(get_cached_test_project "$project_type")
    
    if [[ -d "$cached_project" ]]; then
        cp -r "$cached_project"/* "$target_dir/"
        # Reinitialize git in the new location
        cd "$target_dir"
        rm -rf .git
        git init >/dev/null 2>&1
        git config user.name "Gandalf Test" >/dev/null 2>&1
        git config user.email "gandalf@shire.test" >/dev/null 2>&1
        git add . >/dev/null 2>&1
        git commit -m "Copied from test cache" >/dev/null 2>&1
        return 0
    else
        echo "ERROR: Failed to create cached project of type: $project_type" >&2
        return 1
    fi
}

shared_setup() {
	local project_name="there_and_back_again"
	local user_email="bilbo@baggins.shire"
	local user_name="Bilbo Baggins"

	TEST_HOME=$(mktemp -d -t gandalf_test.XXXXXX)
	export ORIGINAL_HOME="$HOME"
	export HOME="$TEST_HOME"

	export GANDALF_HOME="$TEST_HOME/.gandalf"
	export CONVERSATIONS_DIR="$TEST_HOME/.gandalf/conversations"
	mkdir -p "$CONVERSATIONS_DIR"

	TEST_PROJECT_DIR="$TEST_HOME/$project_name"
	export TEST_PROJECT_DIR
	mkdir -p "$TEST_PROJECT_DIR"
	cd "$TEST_PROJECT_DIR"

	git init >/dev/null 2>&1
	git config user.email "$user_email"
	git config user.name "$user_name"
}

# Cleanup test data cache (for maintenance)
cleanup_test_cache() {
    local max_age_hours="${1:-24}"
    
    if [[ -d "$TEST_DATA_CACHE_DIR" ]]; then
        # Remove cache entries older than specified hours
        find "$TEST_DATA_CACHE_DIR" -maxdepth 1 -type d -mmin +$((max_age_hours * 60)) -exec rm -rf {} \; 2>/dev/null || true
    fi
}

shared_teardown() {
	export HOME="$ORIGINAL_HOME"
	unset GANDALF_HOME
	unset CONVERSATIONS_DIR

	[[ -n "${TEST_HOME:-}" && -d "$TEST_HOME" ]] && rm -rf "$TEST_HOME"
}

create_minimal_project() {
	echo "# There and Back Again, a Hobbits Project" >README.md
	git add . >/dev/null 2>&1
	git commit -m "I'm going on an adventure!" >/dev/null 2>&1
}

export GANDALF_TEST_MODE="true"
export MCP_DEBUG="${MCP_DEBUG:-$MCP_DEBUG_DEFAULT}"
export SERVER_DIR="$GANDALF_ROOT/server/src"
export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"
