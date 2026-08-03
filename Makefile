# Fly-in - drone routing simulation
#
# Override the map on the command line, e.g.
#   make run MAP=maps/hard/02_capacity_hell.txt

PYTHON  ?= python3
PIP     ?= $(PYTHON) -m pip
MAP     ?= maps/easy/02_simple_fork.txt
FLAGS   ?= --visual --metrics --verify

MYPY_FLAGS = --warn-return-any --warn-unused-ignores \
             --ignore-missing-imports --disallow-untyped-defs \
             --check-untyped-defs

.PHONY: install run debug clean lint lint-strict test bench all help

all: lint test

install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) main.py $(MAP) $(FLAGS)

debug:
	$(PYTHON) -m pdb main.py $(MAP)

lint:
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . $(MYPY_FLAGS)

lint-strict:
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . --strict

test:
	$(PYTHON) -m pytest tests -q

bench:
	$(PYTHON) benchmark.py

clean:
	rm -rf __pycache__ */__pycache__ .mypy_cache .pytest_cache
	find . -name '*.py[co]' -delete

help:
	@echo "install      install the development dependencies"
	@echo "run          run the simulation on MAP=$(MAP)"
	@echo "debug        run the simulation under pdb"
	@echo "lint         flake8 + mypy with the mandatory flags"
	@echo "lint-strict  flake8 + mypy --strict"
	@echo "test         run the pytest suite"
	@echo "bench        solve every map and compare to the targets"
	@echo "clean        remove caches and bytecode"
