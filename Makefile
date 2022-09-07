test:
	bash scripts/tests.sh

lint:
	pre-commit run --all

build:
	rm ./setup.py; \
	rm -rf ./dist; \
 	dephell deps convert; \
 	poetry build; \
 	pre-commit run --all;
