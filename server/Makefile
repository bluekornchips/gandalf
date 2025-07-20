format:
	ruff check --fix --unsafe-fixes src/
	ruff format src/
	ruff format tests/

lint:
	ruff check src/

fix:
	ruff check --fix src/

test:
	pytest --cov=src

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov

all: format lint test 