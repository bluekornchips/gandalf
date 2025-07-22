format:
	python3 -m isort src/ tests/
	ruff check --fix --unsafe-fixes src/
	ruff format src/
	ruff format tests/

lint:
	ruff check src/

isort:
	python3 -m isort src/ tests/

isort-check:
	python3 -m isort --check-only --diff src/ tests/

typecheck:
	mypy src/

test:
	pytest --cov=src

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov

all: format lint typecheck test

check: isort-check lint typecheck