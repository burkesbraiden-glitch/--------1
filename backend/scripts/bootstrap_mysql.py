import secrets
import subprocess
from pathlib import Path
from urllib.parse import quote


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BACKEND_DIR / ".env"
MYSQL_LOGIN_PATH = "tonglvji_admin"
DATABASE_NAME = "tonglvji"
APP_USER = "tonglvji_app"
APP_HOST = "127.0.0.1"


def sql_quote(value):
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def run_admin_sql(sql):
    subprocess.run(
        ["mysql", f"--login-path={MYSQL_LOGIN_PATH}"],
        input=sql,
        text=True,
        check=True,
    )


def build_database_url(password):
    encoded_password = quote(password, safe="")
    return (
        f"mysql+pymysql://{APP_USER}:{encoded_password}"
        f"@{APP_HOST}:3306/{DATABASE_NAME}?charset=utf8mb4"
    )


def write_env(database_url):
    secret_key = secrets.token_urlsafe(48)
    jwt_secret_key = secrets.token_urlsafe(48)
    ENV_PATH.write_text(
        "\n".join(
            [
                "APP_ENV=development",
                f"SECRET_KEY={secret_key}",
                f"JWT_SECRET_KEY={jwt_secret_key}",
                f"DATABASE_URL={database_url}",
                "DEV_FIXED_CODE=123456",
                "CORS_ORIGINS=http://localhost:5173",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main():
    app_password = secrets.token_urlsafe(32)
    sql = f"""
CREATE DATABASE IF NOT EXISTS `{DATABASE_NAME}`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS {sql_quote(APP_USER)}@{sql_quote(APP_HOST)}
  IDENTIFIED BY {sql_quote(app_password)};
ALTER USER {sql_quote(APP_USER)}@{sql_quote(APP_HOST)}
  IDENTIFIED BY {sql_quote(app_password)};
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, INDEX, REFERENCES
  ON `{DATABASE_NAME}`.* TO {sql_quote(APP_USER)}@{sql_quote(APP_HOST)};
FLUSH PRIVILEGES;
"""
    run_admin_sql(sql)
    write_env(build_database_url(app_password))
    print("mysql bootstrap completed")


if __name__ == "__main__":
    main()
