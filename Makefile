.PHONY: start test

start:
	python3 hub.py &
	python3 domain.py

test:
	python3 -m pytest
