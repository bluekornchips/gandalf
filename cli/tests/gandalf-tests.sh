#!/usr/bin/env bats
#
# Gandalf CLI Tests
# Tests for the gandalf CLI entry point (gandalf.sh)
#

GIT_ROOT="$(git rev-parse --show-toplevel)"
SCRIPT="${GIT_ROOT}/gandalf.sh"
[[ ! -f "${SCRIPT}" ]] && echo "Script not found: ${SCRIPT}" >&2 && exit 1

setup() {
	source "${SCRIPT}"

	GANDALF_ROOT="$(mktemp -d)"

	TEST_VERSION="1.2.3"

	echo "${TEST_VERSION}" >"${GANDALF_ROOT}/VERSION"

	export GANDALF_ROOT
}

mock_install() {
	INSTALL_SCRIPT="$(mktemp -d)/install.sh"
	cat <<EOF >"${INSTALL_SCRIPT}"
#!/usr/bin/env bash
exit 0
EOF
	chmod +x "${INSTALL_SCRIPT}"
}

########################################################
# get_version
########################################################
@test "get_version:: returns version from VERSION file" {
	run get_version
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "${TEST_VERSION}"
}

@test "get_version:: returns unknown when VERSION file does not exist" {
	rm -f "${GANDALF_ROOT}/VERSION"

	run get_version
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "unknown"
}

########################################################
# gandalf
########################################################
@test "gandalf:: shows help for -h" {
	run gandalf -h
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Usage:"
}

@test "gandalf:: shows help for --help" {
	run gandalf --help
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Usage:"
}

@test "gandalf:: shows version for -v" {
	run gandalf -v
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "${TEST_VERSION}"
}

@test "gandalf:: routes --install option" {
	mock_install

	run gandalf --install
	[[ "$status" -eq 0 ]]
}
