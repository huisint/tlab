

test: mypy unittest

mypy:
	mypy tlab tests

unittest:
	coverage run -m unittest
	coverage html
	coverage report
