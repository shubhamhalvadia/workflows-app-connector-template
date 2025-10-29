import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def set_env():
    os.environ.setdefault("ENVIRONMENT", "dev")
    yield


@pytest.fixture()
def app():
    # Import after ENV is set so CDK picks it up
    from main import app as flask_app
    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


