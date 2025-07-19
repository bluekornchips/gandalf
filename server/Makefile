format:
	black src/
	isort src/

lint:
	flake8 src/

test:
	pytest --cov=src

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov

run:
	../gandalf-cli run

all: format lint test 