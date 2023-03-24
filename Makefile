logs:
	@pipenv run textual console

run:
	@pipenv run textual run src/app.py

dev:
	@pipenv run textual run src/app.py --dev

lint:
	@pipenv run black .
	@pipenv run isort .
