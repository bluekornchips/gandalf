format-python:
	python3 -m isort server/src/ server/tests/
	ruff check --fix --unsafe-fixes server/src/ server/tests/
	ruff format server/src/ server/tests/

format-sh:
	find ./cli -name "*.sh" -exec shfmt --ln=bats -w {} \;

format-all: format-python format-sh

lint:
	ruff check server/src/ server/tests/

isort-check:
	python3 -m isort --check-only --diff server/src/ server/tests/

typecheck:
	python3 -m mypy server/src/

test-sh:
	find ./cli -name "*-tests.sh" -type f -exec bats {} \;

test-py:
	pytest --cov=server/src

test-all: test-sh test-py

security:
	bandit -r server/src/ -f txt -s B603,B607

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov .mypy_cache *.*.egg-info .ruff_cache

purge: clean
	rm -rf .venv htmlcov_server

all: format lint typecheck security test