# Database
You'll have to spin up a database to run some tests, 
strawberry-chemist requires psql features.
The easiest way to do this is to use docker:

    cd test
    docker-compose up -d

Then you can run the tests with:

    pytest

# Coverage
To run the tests with coverage:

    cd <repo-root>
    coverage run --source=. -m pytest

Get the coverage report:

    coverage report -m --omit="test/*"

Or 

    coverage html --omit="test/*"


# Need to improve
Coverage of [type.py](../type.py) is quite poor,
mainly because I need to decide if I want to exclude
some parts of it or not.
