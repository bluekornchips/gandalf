format-py:
	ruff check --fix --unsafe-fixes server/
	ruff format server/

format-sh:
	find ./cli -name "*.sh" -exec shfmt --ln=bats -w {} \;

lint-py:
	ruff check server/

test-py:
	python -m pytest server/tests/ -v

test-sh:
	bats --timing $$(find ./cli -name "*-tests.sh" -type f)

typecheck-py:
	python3 -m mypy server/

install-py:
	pip install ".[dev]"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d \( -name ".venv" \) -exec rm -rf {} +
	find . -type d \( -name ".pytest_cache" -o -name "htmlcov" -o -name ".mypy_cache" -o -name "*.egg-info" -o -name ".ruff_cache" -o -name "htmlcov_server" \) -exec rm -rf {} +
	find . -type f -name ".coverage" -exec rm -f {} +

all: format-py format-sh lint-py typecheck-py test-py test-sh