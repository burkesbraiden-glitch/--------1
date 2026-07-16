import secrets
import sys
from pathlib import Path

from sqlalchemy import select


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db
from app.models import Child, User
from app.services.auth import mock_openid_from_code


def count_users():
    return db.session.query(User).count()


def count_children():
    return db.session.query(Child).count()


def assert_success(response):
    payload = response.get_json()
    if response.status_code != 200 or not payload["success"]:
        raise RuntimeError("Unexpected auth smoke response")
    return payload


def main():
    phone = f"139{secrets.randbelow(100000000):08d}"
    mock_code = f"phase2b1-{secrets.token_hex(8)}"
    mock_openid = mock_openid_from_code(mock_code)
    created_user_ids = set()

    app = create_app("development")

    with app.app_context():
        client = app.test_client()
        initial_users = count_users()
        initial_children = count_children()

        try:
            send_code_payload = assert_success(
                client.post("/api/v1/auth/send-code", json={"phone": phone})
            )
            if "code" in send_code_payload["data"]:
                raise RuntimeError("Verification code leaked in response")

            wrong_code_response = client.post(
                "/api/v1/auth/login",
                json={"phone": phone, "code": "000000"},
            )
            if wrong_code_response.status_code != 401:
                raise RuntimeError("Wrong verification code was not rejected")

            login_payload = assert_success(
                client.post(
                    "/api/v1/auth/login",
                    json={"phone": phone, "code": app.config["DEV_FIXED_CODE"]},
                )
            )
            first_user_id = login_payload["data"]["user"]["id"]
            created_user_ids.add(first_user_id)
            access_token = login_payload["data"]["accessToken"]
            if not access_token:
                raise RuntimeError("Access token is missing")
            if count_users() != initial_users + 1:
                raise RuntimeError("Phone login did not create exactly one user")
            if count_children() != initial_children:
                raise RuntimeError("Phone login changed children count")

            me_payload = assert_success(
                client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            )
            if me_payload["data"]["user"]["id"] != first_user_id:
                raise RuntimeError("/auth/me returned a different user")

            second_login_payload = assert_success(
                client.post(
                    "/api/v1/auth/login",
                    json={"phone": phone, "code": app.config["DEV_FIXED_CODE"]},
                )
            )
            if second_login_payload["data"]["user"]["id"] != first_user_id:
                raise RuntimeError("Repeated phone login returned a different user")
            if count_users() != initial_users + 1:
                raise RuntimeError("Repeated phone login created duplicate user")

            wechat_payload = assert_success(
                client.post("/api/v1/auth/mock-wechat-login", json={"mockCode": mock_code})
            )
            wechat_user_id = wechat_payload["data"]["user"]["id"]
            created_user_ids.add(wechat_user_id)
            if count_users() != initial_users + 2:
                raise RuntimeError("Mock WeChat login did not create exactly one user")

            repeated_wechat_payload = assert_success(
                client.post("/api/v1/auth/mock-wechat-login", json={"mockCode": mock_code})
            )
            if repeated_wechat_payload["data"]["user"]["id"] != wechat_user_id:
                raise RuntimeError("Repeated mock WeChat login returned a different user")
            if count_users() != initial_users + 2:
                raise RuntimeError("Repeated mock WeChat login created duplicate user")

            logout_payload = assert_success(
                client.post(
                    "/api/v1/auth/logout",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            )
            if logout_payload["data"] != {"loggedOut": True}:
                raise RuntimeError("Logout response is incorrect")

        finally:
            ids_from_database = db.session.scalars(
                select(User.id).where(
                    (User.phone == phone) | (User.wechat_openid == mock_openid)
                )
            ).all()
            created_user_ids.update(ids_from_database)
            if created_user_ids:
                User.query.filter(User.id.in_(created_user_ids)).delete(
                    synchronize_session=False
                )
                db.session.commit()

        if count_users() != initial_users:
            raise RuntimeError("Smoke users count was not restored")
        if count_children() != initial_children:
            raise RuntimeError("Smoke children count changed")

    print("phase2b1 auth checks passed")


if __name__ == "__main__":
    main()
