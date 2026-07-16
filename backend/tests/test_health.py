from app import create_app


def test_create_app_success():
    app = create_app("testing")

    assert app is not None
    assert app.config["TESTING"] is True


def test_health_returns_connected_when_database_check_succeeds(app_with_database_check):
    app = app_with_database_check(lambda: {"status": "connected", "dialect": "mysql"})
    client = app.test_client()

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["message"] == "ok"
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["service"] == "tonglvji-backend"
    assert payload["data"]["database"]["status"] == "connected"
    assert payload["data"]["database"]["dialect"] == "mysql"


def test_health_returns_503_when_database_check_fails(app_with_database_check):
    def failing_check():
        raise RuntimeError("database password must not leak")

    app = app_with_database_check(failing_check)
    client = app.test_client()

    response = client.get("/api/v1/health")

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert payload["error"]["message"] == "Database unavailable"
    assert payload["error"]["details"] == {}


def test_missing_route_returns_json_404(client):
    response = client.get("/api/v1/missing")

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "NOT_FOUND"
    assert payload["error"]["message"] == "Resource not found"
    assert payload["error"]["details"] == {}


def test_testing_config_does_not_read_development_env(app, monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql+pymysql://tonglvji_app:secret@127.0.0.1:3306/tonglvji?charset=utf8mb4",
    )

    testing_app = create_app("testing")

    assert testing_app.config["APP_ENV"] == "testing"
    assert testing_app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
