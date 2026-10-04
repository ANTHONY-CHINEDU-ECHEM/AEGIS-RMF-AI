# Aegis RMF AI developer commands.
.PHONY: install data run summary test lint evaluate figures serve up down

install:
	pip install ".[dev]"

data:
	python scripts/generate_incident_corpus.py

run:
	aegis run

summary:
	aegis summary

test:
	pytest

lint:
	ruff check src tests scripts

evaluate:
	aegis evaluate

figures:
	aegis figures

serve:
	aegis serve

up:
	docker compose up

down:
	docker compose down
