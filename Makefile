.PHONY: build test

setup:
	python3 setup.py bdist_wheel

test:
	python -m unittest test
