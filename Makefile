logs:
	@pipenv run textual console

run:
	@kitty -e pipenv run textual run src/app.py --dev

lint:
	@pipenv run black .
	@pipenv run isort .
