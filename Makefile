.PHONY: help install test lint

help:
	@echo "Targets: install test"

install:
	python -m venv .venv
	. .venv/bin/activate && pip install -e ".[dev]"

test:
	. .venv/bin/activate && pytest
