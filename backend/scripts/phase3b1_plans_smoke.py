import secrets
import sys
from pathlib import Path

from sqlalchemy import inspect, select


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db
from app.models import Child, ExplorationPlan, GuideCard, User


def assert_success(response, expected_status=200):
    payload = response.get_json()
    if response.status_code != expected_status or not payload["success"]:
        raise RuntimeError("Unexpected plans smoke response")
    return payload


def assert_error(response, expected_status, expected_code):
    payload = response.get_json()
    if response.status_code != expected_status:
        raise RuntimeError("Unexpected plans smoke error status")
    if payload["success"] is not False:
        raise RuntimeError("Unexpected plans smoke success flag")
    if payload["error"]["code"] != expected_code:
        raise RuntimeError("Unexpected plans smoke error code")
    return payload


def count_users():
    return db.session.query(User).count()


def count_children():
    return db.session.query(Child).count()


def count_plans():
    return db.session.query(ExplorationPlan).count()


def count_guides():
    return db.session.query(GuideCard).count()


def login(client, phone, code):
    payload = assert_success(
        client.post("/api/v1/auth/login", json={"phone": phone, "code": code})
    )
    return payload["data"]["user"]["id"], payload["data"]["accessToken"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def create_child(client, token, name):
    payload = assert_success(
        client.post(
            "/api/v1/children",
            json={"name": name, "age": 7, "ageGroup": "7-12", "interests": ["历史"]},
            headers=auth_headers(token),
        ),
        expected_status=201,
    )
    return payload["data"]["child"]["id"]


def main():
    suffix = secrets.randbelow(100000000)
    phone_a = f"139{suffix:08d}"
    phone_b = f"138{suffix:08d}"
    created_user_ids = set()

    app = create_app("development")

    with app.app_context():
        client = app.test_client()
        initial_users = count_users()
        initial_children = count_children()
        initial_plans = count_plans()
        initial_guides = count_guides()

        try:
            user_a_id, token_a = login(client, phone_a, app.config["DEV_FIXED_CODE"])
            user_b_id, token_b = login(client, phone_b, app.config["DEV_FIXED_CODE"])
            created_user_ids.update({user_a_id, user_b_id})

            child_a_id = create_child(client, token_a, "Smoke A")
            create_child(client, token_b, "Smoke B")

            plan_payload = {
                "title": "故宫亲子探索",
                "destination": "故宫博物院",
                "duration": "3小时",
                "interests": ["历史故事", " 古建筑 ", "历史故事"],
            }
            created_plan = assert_success(
                client.post(
                    "/api/v1/plans",
                    json=plan_payload,
                    headers=auth_headers(token_a),
                ),
                expected_status=201,
            )["data"]["plan"]
            first_plan_id = created_plan["id"]
            if created_plan["childId"] != child_a_id:
                raise RuntimeError("Default child was not selected")
            if created_plan["status"] != "ready":
                raise RuntimeError("Created plan status is incorrect")
            if created_plan["taskCount"] != 0:
                raise RuntimeError("taskCount must be zero")
            if count_plans() != initial_plans + 1:
                raise RuntimeError("Plan count did not increase by one")
            if count_guides() != initial_guides:
                raise RuntimeError("Guide cards count changed")

            wrong_age_group = dict(plan_payload, ageGroup="3-6")
            assert_error(
                client.post(
                    "/api/v1/plans",
                    json=wrong_age_group,
                    headers=auth_headers(token_a),
                ),
                400,
                "VALIDATION_ERROR",
            )

            other_child_payload = dict(plan_payload, childId=child_a_id)
            assert_error(
                client.post(
                    "/api/v1/plans",
                    json=other_child_payload,
                    headers=auth_headers(token_b),
                ),
                404,
                "CHILD_NOT_FOUND",
            )

            second_plan = assert_success(
                client.post(
                    "/api/v1/plans",
                    json=dict(plan_payload, title="第二个探索计划"),
                    headers=auth_headers(token_a),
                ),
                expected_status=201,
            )["data"]["plan"]

            user_a_plans = assert_success(
                client.get("/api/v1/plans", headers=auth_headers(token_a))
            )["data"]["plans"]
            user_b_plans = assert_success(
                client.get("/api/v1/plans", headers=auth_headers(token_b))
            )["data"]["plans"]
            user_a_plan_ids = {plan["id"] for plan in user_a_plans}
            user_b_plan_ids = {plan["id"] for plan in user_b_plans}
            if {first_plan_id, second_plan["id"]} - user_a_plan_ids:
                raise RuntimeError("User A plan list is missing plans")
            if user_b_plan_ids & user_a_plan_ids:
                raise RuntimeError("User B can see User A plans")

            assert_error(
                client.get(f"/api/v1/plans/{first_plan_id}", headers=auth_headers(token_b)),
                404,
                "PLAN_NOT_FOUND",
            )
            assert_error(
                client.patch(
                    f"/api/v1/plans/{first_plan_id}",
                    json={"title": "越权修改"},
                    headers=auth_headers(token_b),
                ),
                404,
                "PLAN_NOT_FOUND",
            )
            assert_error(
                client.post(
                    f"/api/v1/plans/{first_plan_id}/start",
                    headers=auth_headers(token_b),
                ),
                404,
                "PLAN_NOT_FOUND",
            )

            patched_plan = assert_success(
                client.patch(
                    f"/api/v1/plans/{first_plan_id}",
                    json={
                        "title": "更新后的探索计划",
                        "destination": "国家博物馆",
                        "interests": ["文物", " 文物 "],
                    },
                    headers=auth_headers(token_a),
                )
            )["data"]["plan"]
            if patched_plan["title"] != "更新后的探索计划":
                raise RuntimeError("Patch did not update title")
            if patched_plan["destination"] != "国家博物馆":
                raise RuntimeError("Patch did not update destination")
            if patched_plan["interests"] != ["文物"]:
                raise RuntimeError("Patch did not normalize interests")
            if patched_plan["status"] != "ready":
                raise RuntimeError("Patch changed status")

            started_plan = assert_success(
                client.post(
                    f"/api/v1/plans/{first_plan_id}/start",
                    headers=auth_headers(token_a),
                )
            )["data"]["plan"]
            if started_plan["status"] != "in-progress":
                raise RuntimeError("Start did not move plan to in-progress")
            repeated_start = assert_success(
                client.post(
                    f"/api/v1/plans/{first_plan_id}/start",
                    headers=auth_headers(token_a),
                )
            )["data"]["plan"]
            if repeated_start["id"] != first_plan_id or repeated_start["status"] != "in-progress":
                raise RuntimeError("Repeated start is not idempotent")
            if repeated_start["taskCount"] != 0:
                raise RuntimeError("taskCount changed after start")

            plan_columns = {column["name"] for column in inspect(db.engine).get_columns("exploration_plans")}
            if "task_count" in plan_columns:
                raise RuntimeError("task_count column must not exist")
            if count_guides() != initial_guides:
                raise RuntimeError("Guide cards count changed after plan flow")

        finally:
            ids_from_database = db.session.scalars(
                select(User.id).where(User.phone.in_([phone_a, phone_b]))
            ).all()
            created_user_ids.update(ids_from_database)
            if created_user_ids:
                ExplorationPlan.query.filter(
                    ExplorationPlan.user_id.in_(created_user_ids)
                ).delete(synchronize_session=False)
                Child.query.filter(Child.user_id.in_(created_user_ids)).delete(
                    synchronize_session=False
                )
                User.query.filter(User.id.in_(created_user_ids)).delete(
                    synchronize_session=False
                )
                db.session.commit()

        if count_users() != initial_users:
            raise RuntimeError("Smoke users count was not restored")
        if count_children() != initial_children:
            raise RuntimeError("Smoke children count was not restored")
        if count_plans() != initial_plans:
            raise RuntimeError("Smoke plans count was not restored")
        if count_guides() != initial_guides:
            raise RuntimeError("Smoke guide cards count was not restored")

    print("phase3b1 plans checks passed")


if __name__ == "__main__":
    main()
