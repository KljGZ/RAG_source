.PHONY: bootstrap lint test audit pilot reproduce web monitor

bootstrap:
	python -m pip install --no-deps -e .
	pre-commit install

lint:
	ruff check .
	mypy src

test:
	pytest -q

audit:
	provtrust audit --strict

pilot:
	provtrust run-plan --config configs/experiments/v0_static.yaml --dry-run

reproduce:
	provtrust reproduce --manifest artifacts/publication/REPRODUCE.yaml --dry-run

web:
	provtrust serve --host 127.0.0.1 --port 18080

monitor:
	provtrust monitor --config configs/monitoring/remote.yaml --once
