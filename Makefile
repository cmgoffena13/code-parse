.PHONY: install ready format lint type-check test test-cov run compile

install:
	uv sync --all-extras
	uv run -- prek install

run:
	uv run -- python main.py

ready: lint format type-check test-cov

format:
	uv run -- ruff format

lint:
	uv run -- ruff check --fix

type-check:
	uv run -- ty check

test:
	uv run -- pytest -v -n auto

test-cov:
	uv run -- pytest --cov=src --cov-report=term-missing

compile:
	uv run -- nuitka src/app.py \
		--standalone \
		--onefile \
		--lto=yes \
		--assume-yes-for-downloads \
		--output-filename=cbp \
		--python-flag=no_warnings \
		--include-package=src \
		--include-data-files=pyproject.toml=pyproject.toml \
		--include-data-files=src/schema.sql=src/schema.sql \
		--noinclude-data-files=src/tests/* \
		--output-dir=dist/
