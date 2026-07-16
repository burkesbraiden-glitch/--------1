import pytest

from app import create_app


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def app_with_database_check():
    def _create(checker):
        return create_app("testing", database_checker=checker)

    return _create
