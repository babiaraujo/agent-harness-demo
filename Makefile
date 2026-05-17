.PHONY: install naive harness both clean

install:
	pip install -r requirements.txt

naive:
	python naive_agent.py

harness:
	python harness_agent.py

both: naive harness

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
