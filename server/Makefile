format:
	.venv/bin/ruff check --fix --unsafe-fixes src/
	.venv/bin/ruff format src/

lint:
	.venv/bin/ruff check src/

fix:
	.venv/bin/ruff check --fix src/

test:
	pytest --cov=src

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov

all: format lint test 