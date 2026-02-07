.PHONY: help install test lint typecheck check

help:
	@echo "Targets: install test lint typecheck check"

install:
	python -m venv .venv
	. .venv/bin/activate && pip install -e ".[dev]"

test:
	. .venv/bin/activate && pytest

lint:
	. .venv/bin/activate && ruff check .

typecheck:
	. .venv/bin/activate && mypy src/vaultchef

check: test lint typecheck
