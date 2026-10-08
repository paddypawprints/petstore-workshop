.PHONY: run test lint format typecheck package-login package-authorizer package-photos

PYTHON ?= python

run:
	$(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff check --fix .

typecheck:
	$(PYTHON) -m mypy app lambdas tests

package-login:
	mkdir -p dist
	cd lambdas/login && zip -j ../../dist/login.zip handler.py

package-authorizer:
	mkdir -p dist
	cd lambdas/authorizer && zip -j ../../dist/authorizer.zip handler.py

package-photos:
	mkdir -p dist
	cd lambdas/photos && zip -j ../../dist/photos.zip handler.py
