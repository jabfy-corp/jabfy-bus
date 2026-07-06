.PHONY: test demo lint install dev clean

PYTHON ?= python3

test:
	$(PYTHON) -m unittest discover -s tests -v

demo:
	$(PYTHON) -m jabfy_bus.cli demo --steps 10

lint:
	ruff check jabfy_bus tests || true

install:
	$(PYTHON) -m pip install .

dev:
	$(PYTHON) -m pip install -e ".[all]"

clean:
	rm -rf build dist *.egg-info .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
