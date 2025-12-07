# Set the python version to use
PYTHON := $(shell command -v python3.10 2>/dev/null || command -v python3.11 2>/dev/null || command -v python3.12 2>/dev/null || command -v python3 2>/dev/null)

format-py:
	$(PYTHON) -m ruff check --fix --unsafe-fixes server/
	$(PYTHON) -m ruff format server/

format-sh:
	find ./cli -name "*.sh" -exec shfmt --ln=bats -w {} \;

lint-py:
	$(PYTHON) -m ruff check server/

test-py:
	cd server && $(PYTHON) -m pytest tests/ -v

test-sh:
	bats --timing $$(find ./cli -name "*-tests.sh" -type f)

test-integration:
	bats --timing ./cli/tests/integration/test_query_cli.sh

test: test-py test-sh test-integration

typecheck-py:
	$(PYTHON) -m mypy server/

install-py:
	$(PYTHON) -m pip install ".[dev]"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d \( -name ".venv" \) -exec rm -rf {} +
	find . -type d \( -name ".pytest_cache" -o -name "htmlcov" -o -name ".mypy_cache" -o -name "*.egg-info" -o -name ".ruff_cache" -o -name "htmlcov_server" \) -exec rm -rf {} +
	find . -type f -name ".coverage" -exec rm -f {} +

all: format-py format-sh lint-py typecheck-py test-py test-sh