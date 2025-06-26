#!/bin/bash

# Shared Dependency Checker for Gandalf MCP Server
# Validates system requirements including bats, Python dependencies, and core tools

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
GANDALF_ROOT="$(dirname "$SCRIPT_DIR")"

check_python_version() {
    local min_version="3.10"

    if ! command -v python3 &>/dev/null; then
        echo "Error: Python 3 not found"
        return 1
    fi

    local python_version
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)

    if [[ -z "$python_version" ]]; then
        echo "Error: Could not determine Python version"
        return 1
    fi

    if printf '%s\n' "$min_version" "$python_version" | sort -V | head -n1 | grep -q "^$min_version$"; then
        echo "Python $python_version found"
        return 0
    else
        echo "Error: Python $python_version found, but $min_version+ required"
        return 1
    fi
}

check_python_requirements() {
    local requirements_file="$GANDALF_ROOT/requirements.txt"

    if [[ ! -f "$requirements_file" ]]; then
        echo "No requirements.txt found"
        return 0
    fi

    local python_cmd="python3"
    local venv_dir="$GANDALF_ROOT/.venv"
    if [[ -d "$venv_dir" && -f "$venv_dir/bin/python3" ]]; then
        python_cmd="$venv_dir/bin/python3"
    fi

    local missing_packages=""

    while IFS= read -r line; do
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

        local package_name
        package_name=$(echo "$line" | sed 's/[><=!].*//' | tr -d '[:space:]')

        # Map pip package names to Python import names
        local import_name="$package_name"
        case "$package_name" in
        "PyYAML") import_name="yaml" ;;
        esac

        local is_optional=false
        if echo "$line" | grep -q "# optional" || [[ "$package_name" =~ ^pytest ]]; then
            is_optional=true
        fi

        if ! "$python_cmd" -c "import $import_name" &>/dev/null; then
            if [[ "$is_optional" != "true" ]]; then
                if [[ -z "$missing_packages" ]]; then
                    missing_packages="$package_name"
                else
                    missing_packages="$missing_packages $package_name"
                fi
            fi
        fi
    done <"$requirements_file"

    if [[ -n "$missing_packages" ]]; then
        echo "Error: Missing required Python packages: $missing_packages"
        echo "Install with: pip install -r $requirements_file"
        return 1
    fi

    return 0
}

check_bats() {
    if ! command -v bats &>/dev/null; then
        echo "Error: BATS not found"
        echo "Install with: brew install bats-core"
        return 1
    fi
    return 0
}

check_git() {
    if ! command -v git &>/dev/null; then
        echo "Error: Git not found"
        return 1
    fi
    return 0
}

check_jq() {
    if ! command -v jq &>/dev/null; then
        echo "Warning: jq not found (optional)"
        return 0
    fi
    return 0
}

check_gandalf_structure() {
    local required_dirs=("src" "scripts" "tests/shell")
    local required_files=("src/main.py" "gandalf.sh")

    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$GANDALF_ROOT/$dir" ]]; then
            echo "Error: Missing required directory: $dir/"
            return 1
        fi
    done

    for file in "${required_files[@]}"; do
        if [[ ! -f "$GANDALF_ROOT/$file" ]]; then
            echo "Error: Missing required file: $file"
            return 1
        fi
    done

    return 0
}

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Check system dependencies for Gandalf MCP Server.

Options:
    --python-only    Check only Python requirements
    --bats-only      Check only BATS installation  
    --core-only      Check only core dependencies (Python, Git)
    --quiet          Minimal output
    -h, --help       Show this help

Examples:
    $(basename "$0")                    # Full dependency check
    $(basename "$0") --python-only      # Check Python requirements only
    $(basename "$0") --quiet            # Silent check (exit codes only)

Exit Codes:
    0    All required dependencies satisfied
    1    Missing required dependencies
    2    Invalid arguments
EOF
}

main() {
    local check_python=true
    local check_bats=true
    local check_core=true
    local check_structure=true
    local quiet_mode=false

    while [[ $# -gt 0 ]]; do
        case $1 in
        --python-only)
            check_python=true
            check_bats=false
            check_core=false
            check_structure=false
            shift
            ;;
        --bats-only)
            check_python=false
            check_bats=true
            check_core=false
            check_structure=false
            shift
            ;;
        --core-only)
            check_python=true
            check_bats=false
            check_core=true
            check_structure=false
            shift
            ;;
        --quiet)
            quiet_mode=true
            shift
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        esac
    done

    if [[ "$quiet_mode" == "true" ]]; then
        exec >/dev/null
    fi

    local failed=false

    if [[ "$check_core" == "true" ]]; then
        if ! check_python_version; then
            failed=true
        fi
        if ! check_git; then
            failed=true
        fi
        check_jq
    fi

    if [[ "$check_python" == "true" ]]; then
        if ! check_python_requirements; then
            failed=true
        fi
    fi

    if [[ "$check_bats" == "true" ]]; then
        if ! check_bats; then
            failed=true
        fi
    fi

    if [[ "$check_structure" == "true" ]]; then
        if ! check_gandalf_structure; then
            failed=true
        fi
    fi

    if [[ "$failed" == "true" ]]; then
        exit 1
    fi

    echo "All dependencies satisfied"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
