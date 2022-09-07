test:
	bash scripts/tests.sh

lint:
	pre-commit run --all

build:
	rm -rf ./dist; \
	poetry build
