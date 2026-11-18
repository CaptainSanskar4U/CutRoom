PY=.venv/bin/python
HOST?=0.0.0.0
PORT?=3000
.PHONY: setup serve worker test e2e models
setup:
	bash scripts/setup.sh
serve:
	$(PY) -m uvicorn cutroom.api:app --host $(HOST) --port $(PORT) --proxy-headers
worker:
	$(PY) -m cutroom.worker
models:
	$(PY) -m scripts.bootstrap_models
test:
	$(PY) -m pytest -q
e2e:
	$(PY) tests/e2e_live.py --base-url http://127.0.0.1:$(PORT)
