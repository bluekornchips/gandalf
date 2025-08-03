#!/usr/bin/env bash
set -euo pipefail

# Timeout configurations (seconds)
[[ -z "${TEST_TIMEOUT_DEFAULT:-}" ]] && declare -r TEST_TIMEOUT_DEFAULT=30
[[ -z "${TEST_TIMEOUT_INTEGRATION:-}" ]] && declare -r TEST_TIMEOUT_INTEGRATION=300
[[ -z "${TEST_TIMEOUT_SECURITY:-}" ]] && declare -r TEST_TIMEOUT_SECURITY=120
[[ -z "${TEST_TIMEOUT_PERFORMANCE:-}" ]] && declare -r TEST_TIMEOUT_PERFORMANCE=600
[[ -z "${TEST_TIMEOUT_DEPENDENCY_CHECK:-}" ]] && declare -r TEST_TIMEOUT_DEPENDENCY_CHECK=10

# Size limits
[[ -z "${MAX_JSON_PARAM_SIZE:-}" ]] && declare -r MAX_JSON_PARAM_SIZE=10000
[[ -z "${MAX_QUERY_LENGTH:-}" ]] && declare -r MAX_QUERY_LENGTH=50000
[[ -z "${MAX_FILE_TYPES_ARRAY:-}" ]] && declare -r MAX_FILE_TYPES_ARRAY=100
[[ -z "${MAX_PATH_DEPTH:-}" ]] && declare -r MAX_PATH_DEPTH=20

# Validation bounds
[[ -z "${MIN_TIMEOUT_VALUE:-}" ]] && declare -r MIN_TIMEOUT_VALUE=1
[[ -z "${MAX_TIMEOUT_VALUE:-}" ]] && declare -r MAX_TIMEOUT_VALUE=600

# LOTR Test Data - Fellowship Members (primary test users)
if [[ -z "${FELLOWSHIP_MEMBERS:-}" ]]; then
	readonly FELLOWSHIP_MEMBERS=(
		"frodo_baggins:hobbit:ringbearer@shire.test"
		"samwise_gamgee:hobbit:gardener@shire.test"
		"legolas_greenleaf:elf:archer@mirkwood.test"
		"gimli_gloin:dwarf:warrior@erebor.test"
		"aragorn_elessar:man:king@gondor.test"
		"boromir_denethor:man:captain@minas-tirith.test"
		"peregrin_took:hobbit:guard@shire.test"
		"meriadoc_brandybuck:hobbit:esquire@shire.test"
		"gandalf_grey:wizard:guide@rivendell.test"
	)
fi

# Test Environments with Thematic Names
if [[ -z "${TEST_ENVIRONMENTS:-}" ]]; then
	readonly TEST_ENVIRONMENTS=(
		"bag-end-local:development:hobbiton.local"
		"rivendell-staging:staging:elrond.rivendell.test"
		"minas-tirith-prod:production:aragorn.gondor.test"
		"isengard-security:security:saruman-contained.test"
		"rohan-performance:load-testing:theoden.edoras.test"
	)
fi

# Mock Project Names
if [[ -z "${MOCK_PROJECTS:-}" ]]; then
	readonly MOCK_PROJECTS=(
		"there_and_back_again"
		"council_of_elrond"
		"fellowship_tracker"
		"ring_bearer_monitoring"
		"white_tree_registry"
		"palantir_communications"
		"mithril_security_suite"
	)
fi

# Test Users by Race
[[ -z "${TEST_USERS_HOBBITS:-}" ]] && readonly TEST_USERS_HOBBITS=("frodo_baggins" "samwise_gamgee" "peregrin_took" "meriadoc_brandybuck")
[[ -z "${TEST_USERS_ELVES:-}" ]] && readonly TEST_USERS_ELVES=("legolas_greenleaf" "elrond_halfelven" "galadriel_lady" "celeborn_wise")
[[ -z "${TEST_USERS_DWARVES:-}" ]] && readonly TEST_USERS_DWARVES=("gimli_gloin" "balin_fundin" "thorin_oakenshield" "dain_ironfoot")
[[ -z "${TEST_USERS_MEN:-}" ]] && readonly TEST_USERS_MEN=("aragorn_elessar" "boromir_denethor" "faramir_prince" "eomer_marshal")

# Environment configurations
[[ -z "${TEST_ENV_NAMES:-}" ]] && readonly TEST_ENV_NAMES=("hobbiton-dev" "rivendell-staging" "minas-tirith-prod" "rohan-test")
[[ -z "${TEST_DOMAINS:-}" ]] && readonly TEST_DOMAINS=("shire.test" "rivendell.test" "gondor.test" "rohan.test")

# Security patterns to detect in JSON parameters
if [[ -z "${DANGEROUS_PATTERNS:-}" ]]; then
	readonly DANGEROUS_PATTERNS=(
		"\.\.\/"
		"\/etc\/"
		"\/root"
		";"
		"&&"
		"\`"
		"\$\("
		"exec"
		"eval"
		"rm -rf"
	)
fi

# Standard error handling function
handle_error() {
	local exit_code=$?
	local line_number=$1
	local script_name="${BASH_SOURCE[1]##*/}"

	echo "$script_name failed at line $line_number (exit code: $exit_code)" >&2

	# Cleanup resources
	cleanup_resources 2>/dev/null || true

	exit $exit_code
}

# Enhanced JSON validation function
validate_json_params() {
	local params="$1"

	# Basic JSON syntax validation
	if ! echo "$params" | jq . >/dev/null 2>&1; then
		echo "Invalid JSON syntax in params: $params" >&2
		return 1
	fi

	# Validate against size limits
	local param_size=${#params}
	if [[ $param_size -gt $MAX_JSON_PARAM_SIZE ]]; then
		echo "JSON params exceed size limit (${param_size} > ${MAX_JSON_PARAM_SIZE})" >&2
		return 1
	fi

	# Validate no dangerous patterns
	local pattern
	for pattern in "${DANGEROUS_PATTERNS[@]}"; do
		if echo "$params" | grep -qE "$pattern"; then
			echo "Dangerous pattern '$pattern' detected in JSON params" >&2
			return 1
		fi
	done

	return 0
}

# Cleanup function template
cleanup_resources() {
	# Remove temporary files
	find /tmp -name "gandalf_test_*" -type f -mmin +60 -delete 2>/dev/null || true

	# Kill any remaining test processes
	pkill -f "gandalf.*test" 2>/dev/null || true
}
