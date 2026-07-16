import secrets
import sys
from pathlib import Path

from sqlalchemy import select


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db
from app.models import Child, ExplorationPlan, GuideCard, Task, TaskSubmission, User


def assert_success(response, expected_status=200):
    payload = response.get_json()
    if response.status_code != expected_status or not payload["success"]:
        raise RuntimeError("Unexpected tasks smoke response")
    return payload


def assert_error(response, expected_status, expected_code):
    payload = response.get_json()
    if response.status_code != expected_status:
        raise RuntimeError("Unexpected tasks smoke error status")
    if payload["success"] is not False:
        raise RuntimeError("Unexpected tasks smoke success flag")
    if payload["error"]["code"] != expected_code:
        raise RuntimeError("Unexpected tasks smoke error code")
    return payload


def count_users():
    return db.session.query(User).count()


def count_children():
    return db.session.query(Child).count()


def count_plans():
    return db.session.query(ExplorationPlan).count()


def count_guides():
    return db.session.query(GuideCard).count()


def count_tasks():
    return db.session.query(Task).count()


def count_submissions():
    return db.session.query(TaskSubmission).count()


def login(client, phone, code):
    payload = assert_success(client.post("/api/v1/auth/login", json={"phone": phone, "code": code}))
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


def create_plan(client, token, destination="故宫博物院", title="故宫亲子探索"):
    payload = assert_success(
        client.post(
            "/api/v1/plans",
            json={
                "title": title,
                "destination": destination,
                "duration": "3小时",
                "interests": ["历史故事", " 古建筑 ", "历史故事"],
            },
            headers=auth_headers(token),
        ),
        expected_status=201,
    )
    return payload["data"]["plan"]


def assert_task_list_shape(tasks, plan_id):
    if len(tasks) != 3:
        raise RuntimeError("Expected exactly three tasks")
    if [task["order"] for task in tasks] != [1, 2, 3]:
        raise RuntimeError("Task order is incorrect")
    if any(task["planId"] != plan_id for task in tasks):
        raise RuntimeError("Task planId is incorrect")
    if any(task["ageGroup"] != "7-12" for task in tasks):
        raise RuntimeError("Task ageGroup does not match plan")
    if any(task["status"] != "not-started" for task in tasks):
        raise RuntimeError("Generated tasks must be not-started")
    if any(task["record"] != {"imageUrl": None, "note": ""} for task in tasks):
        raise RuntimeError("Generated task record is incorrect")


def main():
    suffix = secrets.randbelow(100000000)
    phone_a = f"135{suffix:08d}"
    phone_b = f"134{suffix:08d}"
    created_user_ids = set()

    app = create_app("development")

    with app.app_context():
        client = app.test_client()
        initial_users = count_users()
        initial_children = count_children()
        initial_plans = count_plans()
        initial_guides = count_guides()
        initial_tasks = count_tasks()
        initial_submissions = count_submissions()

        try:
            user_a_id, token_a = login(client, phone_a, app.config["DEV_FIXED_CODE"])
            user_b_id, token_b = login(client, phone_b, app.config["DEV_FIXED_CODE"])
            created_user_ids.update({user_a_id, user_b_id})

            child_a_id = create_child(client, token_a, "Task Smoke A")
            create_child(client, token_b, "Task Smoke B")

            plan_a = create_plan(client, token_a)
            plan_b = create_plan(client, token_b, title="用户 B 故宫探索")
            if plan_a["childId"] != child_a_id or plan_a["status"] != "ready":
                raise RuntimeError("User A plan is invalid")
            if plan_b["status"] != "ready":
                raise RuntimeError("User B plan is invalid")

            empty_tasks = assert_success(
                client.get(f"/api/v1/plans/{plan_a['id']}/tasks", headers=auth_headers(token_a))
            )["data"]
            if empty_tasks != {"tasks": [], "taskCount": 0}:
                raise RuntimeError("Initial task list is not empty")
            if count_tasks() != initial_tasks:
                raise RuntimeError("GET tasks created tasks")

            assert_error(
                client.get(f"/api/v1/plans/{plan_a['id']}/tasks", headers=auth_headers(token_b)),
                404,
                "PLAN_NOT_FOUND",
            )
            assert_error(
                client.post(
                    f"/api/v1/plans/{plan_a['id']}/tasks/generate",
                    headers=auth_headers(token_b),
                ),
                404,
                "PLAN_NOT_FOUND",
            )

            generated = assert_success(
                client.post(
                    f"/api/v1/plans/{plan_a['id']}/tasks/generate",
                    headers=auth_headers(token_a),
                ),
                expected_status=201,
            )["data"]["tasks"]
            assert_task_list_shape(generated, plan_a["id"])
            if count_tasks() != initial_tasks + 3:
                raise RuntimeError("Task count did not increase by three")
            if count_submissions() != initial_submissions:
                raise RuntimeError("Task submissions count changed")

            generated_ids = [task["id"] for task in generated]
            fetched = assert_success(
                client.get(f"/api/v1/plans/{plan_a['id']}/tasks", headers=auth_headers(token_a))
            )["data"]["tasks"]
            if [task["id"] for task in fetched] != generated_ids:
                raise RuntimeError("GET tasks did not return generated task ids")

            detail = assert_success(
                client.get(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{generated_ids[0]}",
                    headers=auth_headers(token_a),
                )
            )["data"]["task"]
            if detail["id"] != generated_ids[0] or detail["title"] != "找屋顶上的小兽":
                raise RuntimeError("Task detail is incorrect")
            assert_error(
                client.get(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{generated_ids[0]}",
                    headers=auth_headers(token_b),
                ),
                404,
                "PLAN_NOT_FOUND",
            )

            repeated = assert_success(
                client.post(
                    f"/api/v1/plans/{plan_a['id']}/tasks/generate",
                    headers=auth_headers(token_a),
                )
            )["data"]["tasks"]
            if [task["id"] for task in repeated] != generated_ids:
                raise RuntimeError("Repeated generate returned different ids")
            if count_tasks() != initial_tasks + 3:
                raise RuntimeError("Repeated generate changed task count")

            plan_detail = assert_success(
                client.get(f"/api/v1/plans/{plan_a['id']}", headers=auth_headers(token_a))
            )["data"]["plan"]
            if plan_detail["taskCount"] != 3:
                raise RuntimeError("Plan detail taskCount is incorrect")

            plans = assert_success(client.get("/api/v1/plans", headers=auth_headers(token_a)))["data"]["plans"]
            plan_counts = {plan["id"]: plan["taskCount"] for plan in plans}
            if plan_counts.get(plan_a["id"]) != 3:
                raise RuntimeError("Plan list taskCount is incorrect")

            started = assert_success(
                client.post(f"/api/v1/plans/{plan_a['id']}/start", headers=auth_headers(token_a))
            )["data"]["plan"]
            if started["taskCount"] != 3 or started["status"] != "in-progress":
                raise RuntimeError("Started plan taskCount is incorrect")

            fallback_plan = create_plan(
                client,
                token_a,
                destination="国家博物馆",
                title="国家博物馆亲子探索",
            )
            fallback_tasks = assert_success(
                client.post(
                    f"/api/v1/plans/{fallback_plan['id']}/tasks/generate",
                    headers=auth_headers(token_a),
                ),
                expected_status=201,
            )["data"]["tasks"]
            assert_task_list_shape(fallback_tasks, fallback_plan["id"])
            if not any("国家博物馆" in (task["summary"] or "") for task in fallback_tasks):
                raise RuntimeError("Fallback tasks do not include destination context")

        finally:
            ids_from_database = db.session.scalars(
                select(User.id).where(User.phone.in_([phone_a, phone_b]))
            ).all()
            created_user_ids.update(ids_from_database)
            if created_user_ids:
                plan_ids = db.session.scalars(
                    select(ExplorationPlan.id).where(ExplorationPlan.user_id.in_(created_user_ids))
                ).all()
                if plan_ids:
                    ExplorationPlan.query.filter(ExplorationPlan.id.in_(plan_ids)).delete(
                        synchronize_session=False
                    )
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
        if count_tasks() != initial_tasks:
            raise RuntimeError("Smoke tasks count was not restored")
        if count_submissions() != initial_submissions:
            raise RuntimeError("Smoke task submissions count was not restored")

    print("phase4b1 tasks checks passed")


if __name__ == "__main__":
    main()
