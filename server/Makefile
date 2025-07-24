format:
	python3 -m isort src/ tests/
	ruff check --fix --unsafe-fixes src/ tests/
	ruff format src/ tests/

lint:
	ruff check src/ tests/

isort-check:
	python3 -m isort --check-only --diff src/ tests/

typecheck:
	python3 -m mypy src/

test:
	pytest --cov=src

security:
	bandit -r src/ -f txt -s B603,B607
	safety check

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov .mypy_cache *.*.egg-info .ruff_cache

purge: clean
	rm -rf .venv htmlcov_server

all: format lint typecheck security test