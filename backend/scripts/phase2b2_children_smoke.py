import secrets
import sys
from pathlib import Path

from sqlalchemy import select


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db
from app.models import Child, User


def count_users():
    return db.session.query(User).count()


def count_children():
    return db.session.query(Child).count()


def random_phone():
    return f"139{secrets.randbelow(100000000):08d}"


def assert_success(response):
    payload = response.get_json()
    if response.status_code not in {200, 201} or not payload["success"]:
        raise RuntimeError("Unexpected success response")
    return payload


def assert_error(response, status_code, code):
    payload = response.get_json()
    if response.status_code != status_code or payload["error"]["code"] != code:
        raise RuntimeError("Unexpected error response")


def login(client, phone, code):
    payload = assert_success(
        client.post("/api/v1/auth/login", json={"phone": phone, "code": code})
    )
    return payload["data"]["accessToken"], payload["data"]["user"]["id"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def main():
    app = create_app("development")
    phone_a = random_phone()
    phone_b = random_phone()
    created_user_ids = set()

    with app.app_context():
        client = app.test_client()
        initial_users = count_users()
        initial_children = count_children()

        try:
            token_a, user_a_id = login(client, phone_a, app.config["DEV_FIXED_CODE"])
            token_b, user_b_id = login(client, phone_b, app.config["DEV_FIXED_CODE"])
            created_user_ids.update({user_a_id, user_b_id})

            list_a = assert_success(client.get("/api/v1/children", headers=auth_header(token_a)))
            if list_a["data"] != {"children": [], "currentChild": None}:
                raise RuntimeError("User A initial children response is not empty")

            first_child = assert_success(
                client.post(
                    "/api/v1/children",
                    json={"name": "小小探索家", "age": 7, "city": "北京", "interests": ["历史"]},
                    headers=auth_header(token_a),
                )
            )["data"]["child"]
            if first_child["isDefault"] is not True:
                raise RuntimeError("First child was not default")

            second_child = assert_success(
                client.post(
                    "/api/v1/children",
                    json={"name": "小小观察员", "age": 6, "isDefault": False},
                    headers=auth_header(token_a),
                )
            )["data"]["child"]
            if second_child["isDefault"] is not False:
                raise RuntimeError("Second child should not be default")

            second_child = assert_success(
                client.patch(
                    f"/api/v1/children/{second_child['id']}",
                    json={"isDefault": True},
                    headers=auth_header(token_a),
                )
            )["data"]["child"]
            if second_child["isDefault"] is not True:
                raise RuntimeError("Second child default switch failed")

            first_child_after = assert_success(
                client.get(
                    f"/api/v1/children/{first_child['id']}",
                    headers=auth_header(token_a),
                )
            )["data"]["child"]
            if first_child_after["isDefault"] is not False:
                raise RuntimeError("First child was not unset as default")

            list_a = assert_success(client.get("/api/v1/children", headers=auth_header(token_a)))
            if list_a["data"]["currentChild"]["id"] != second_child["id"]:
                raise RuntimeError("Current child is not the new default")

            list_b = assert_success(client.get("/api/v1/children", headers=auth_header(token_b)))
            if list_b["data"] != {"children": [], "currentChild": None}:
                raise RuntimeError("User B should not see User A children")

            assert_error(
                client.get(f"/api/v1/children/{first_child['id']}", headers=auth_header(token_b)),
                404,
                "CHILD_NOT_FOUND",
            )
            assert_error(
                client.patch(
                    f"/api/v1/children/{first_child['id']}",
                    json={"name": "越权"},
                    headers=auth_header(token_b),
                ),
                404,
                "CHILD_NOT_FOUND",
            )
            assert_error(
                client.post(
                    "/api/v1/children",
                    json={"name": "错误年龄组", "age": 7, "ageGroup": "3-6"},
                    headers=auth_header(token_a),
                ),
                400,
                "VALIDATION_ERROR",
            )

            patched = assert_success(
                client.patch(
                    f"/api/v1/children/{first_child['id']}",
                    json={"age": 8},
                    headers=auth_header(token_a),
                )
            )["data"]["child"]
            if patched["ageGroup"] != "7-12":
                raise RuntimeError("Patch age did not sync ageGroup")

            assert_error(
                client.patch(
                    f"/api/v1/children/{second_child['id']}",
                    json={"isDefault": False},
                    headers=auth_header(token_a),
                ),
                409,
                "DEFAULT_CHILD_REQUIRED",
            )

            if count_children() != initial_children + 2:
                raise RuntimeError("Unexpected children count during smoke")

        finally:
            ids_from_database = db.session.scalars(
                select(User.id).where(User.phone.in_([phone_a, phone_b]))
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
            raise RuntimeError("Smoke children count was not restored")

    print("phase2b2 children checks passed")


if __name__ == "__main__":
    main()
