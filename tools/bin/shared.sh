#!/usr/bin/env bash
# Minimal shared utilities for Gandalf scripts

export GANDALF_HOME="${GANDALF_HOME:-$HOME/.gandalf}"

load_env_variables() {
    local env_file="${1:-$GANDALF_ROOT/.env}"
    if [[ -f "$env_file" ]]; then
        source "$env_file"
    fi
}
