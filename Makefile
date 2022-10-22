test:
	pytest --cov="runtime_config" .

test-multi-versions:
	bash scripts/tests.sh

lint:
	pre-commit run --all

build:
	rm -rf ./dist; \
	poetry build
