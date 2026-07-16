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
        raise RuntimeError("Unexpected task submissions smoke response")
    return payload


def assert_error(response, expected_status, expected_code):
    payload = response.get_json()
    if response.status_code != expected_status:
        raise RuntimeError("Unexpected task submissions smoke error status")
    if payload["success"] is not False:
        raise RuntimeError("Unexpected task submissions smoke success flag")
    if payload["error"]["code"] != expected_code:
        raise RuntimeError("Unexpected task submissions smoke error code")
    return payload


def count_model(model):
    return db.session.query(model).count()


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


def create_plan(client, token, title):
    payload = assert_success(
        client.post(
            "/api/v1/plans",
            json={
                "title": title,
                "destination": "故宫博物院",
                "duration": "3小时",
                "interests": ["历史故事", "古建筑"],
            },
            headers=auth_headers(token),
        ),
        expected_status=201,
    )
    return payload["data"]["plan"]


def get_submission_count_for_tasks(task_ids):
    return TaskSubmission.query.filter(TaskSubmission.task_id.in_(task_ids)).count()


def main():
    suffix = secrets.randbelow(100000000)
    phone_a = f"136{suffix:08d}"
    phone_b = f"137{suffix:08d}"
    created_user_ids = set()

    app = create_app("development")

    with app.app_context():
        client = app.test_client()
        initial = {
            User: count_model(User),
            Child: count_model(Child),
            ExplorationPlan: count_model(ExplorationPlan),
            GuideCard: count_model(GuideCard),
            Task: count_model(Task),
            TaskSubmission: count_model(TaskSubmission),
        }

        try:
            user_a_id, token_a = login(client, phone_a, app.config["DEV_FIXED_CODE"])
            user_b_id, token_b = login(client, phone_b, app.config["DEV_FIXED_CODE"])
            created_user_ids.update({user_a_id, user_b_id})

            create_child(client, token_a, "Submission Smoke A")
            create_child(client, token_b, "Submission Smoke B")
            plan_a = create_plan(client, token_a, "A 的故宫探索")
            plan_b = create_plan(client, token_b, "B 的故宫探索")

            tasks_a = assert_success(
                client.post(
                    f"/api/v1/plans/{plan_a['id']}/tasks/generate",
                    headers=auth_headers(token_a),
                ),
                expected_status=201,
            )["data"]["tasks"]
            tasks_b = assert_success(
                client.post(
                    f"/api/v1/plans/{plan_b['id']}/tasks/generate",
                    headers=auth_headers(token_b),
                ),
                expected_status=201,
            )["data"]["tasks"]
            task_ids_a = [task["id"] for task in tasks_a]
            task_ids_b = [task["id"] for task in tasks_b]

            assert_error(
                client.post(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[0]}/submission/start",
                    headers=auth_headers(token_a),
                ),
                409,
                "PLAN_NOT_STARTED",
            )

            started_plan = assert_success(
                client.post(f"/api/v1/plans/{plan_a['id']}/start", headers=auth_headers(token_a))
            )["data"]["plan"]
            if started_plan["status"] != "in-progress":
                raise RuntimeError("Plan did not start")

            detail = assert_success(
                client.get(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[0]}",
                    headers=auth_headers(token_a),
                )
            )["data"]["task"]
            if detail["status"] != "not-started":
                raise RuntimeError("Initial task status is incorrect")

            started_task = assert_success(
                client.post(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[0]}/submission/start",
                    headers=auth_headers(token_a),
                ),
                expected_status=201,
            )["data"]["task"]
            if started_task["status"] != "in-progress":
                raise RuntimeError("Task did not start")
            if get_submission_count_for_tasks(task_ids_a) != 1:
                raise RuntimeError("Start did not create exactly one submission")

            repeated_start = assert_success(
                client.post(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[0]}/submission/start",
                    headers=auth_headers(token_a),
                )
            )["data"]["task"]
            if repeated_start["status"] != "in-progress" or get_submission_count_for_tasks(task_ids_a) != 1:
                raise RuntimeError("Repeated start is not idempotent")

            note_one = "我发现屋檐上的小兽排成了一队。"
            patched = assert_success(
                client.patch(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[0]}/submission",
                    json={"note": note_one},
                    headers=auth_headers(token_a),
                )
            )["data"]["task"]
            if patched["record"]["note"] != note_one or patched["record"]["imageUrl"] is not None:
                raise RuntimeError("Patched note or imageUrl is incorrect")

            completed = assert_success(
                client.post(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[0]}/submission/complete",
                    headers=auth_headers(token_a),
                )
            )["data"]["task"]
            completed_at = completed["completedAt"]
            if completed["status"] != "completed" or completed_at is None:
                raise RuntimeError("Task did not complete")

            repeated_complete = assert_success(
                client.post(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[0]}/submission/complete",
                    headers=auth_headers(token_a),
                )
            )["data"]["task"]
            if repeated_complete["completedAt"] != completed_at or get_submission_count_for_tasks(task_ids_a) != 1:
                raise RuntimeError("Repeated complete is not idempotent")

            note_two = "完成后补充：最大的小兽站在最前面。"
            patched_completed = assert_success(
                client.patch(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[0]}/submission",
                    json={"note": note_two},
                    headers=auth_headers(token_a),
                )
            )["data"]["task"]
            if patched_completed["record"]["note"] != note_two or patched_completed["completedAt"] != completed_at:
                raise RuntimeError("Completed task note patch changed completedAt")

            task_two_note = "第二个任务先保存文字。"
            task_two = assert_success(
                client.patch(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[1]}/submission",
                    json={"note": task_two_note},
                    headers=auth_headers(token_a),
                )
            )["data"]["task"]
            if task_two["status"] != "in-progress":
                raise RuntimeError("Patch did not auto-create in-progress submission")

            task_three = assert_success(
                client.post(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[2]}/submission/complete",
                    json={"note": "第三个任务直接完成。"},
                    headers=auth_headers(token_a),
                )
            )["data"]["task"]
            if task_three["status"] != "completed":
                raise RuntimeError("Direct complete did not create completed submission")

            assert_error(
                client.patch(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[0]}/submission",
                    json={"note": "B 不能改 A"},
                    headers=auth_headers(token_b),
                ),
                404,
                "PLAN_NOT_FOUND",
            )
            assert_error(
                client.patch(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_b[0]}/submission",
                    json={"note": "跨 plan task"},
                    headers=auth_headers(token_a),
                ),
                404,
                "TASK_NOT_FOUND",
            )

            listed = assert_success(
                client.get(f"/api/v1/plans/{plan_a['id']}/tasks", headers=auth_headers(token_a))
            )["data"]["tasks"]
            statuses = {task["id"]: task["status"] for task in listed}
            if statuses != {
                task_ids_a[0]: "completed",
                task_ids_a[1]: "in-progress",
                task_ids_a[2]: "completed",
            }:
                raise RuntimeError("Task list statuses are incorrect")
            if any(task["record"]["imageUrl"] is not None for task in listed):
                raise RuntimeError("imageUrl must remain null")

            final_task_two = assert_success(
                client.post(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[1]}/submission/complete",
                    headers=auth_headers(token_a),
                )
            )["data"]["task"]
            if final_task_two["status"] != "completed":
                raise RuntimeError("Task two did not complete")

            plan_detail = assert_success(
                client.get(f"/api/v1/plans/{plan_a['id']}", headers=auth_headers(token_a))
            )["data"]["plan"]
            if plan_detail["status"] != "in-progress":
                raise RuntimeError("Plan must remain in-progress")
            if get_submission_count_for_tasks(task_ids_a) != 3:
                raise RuntimeError("Submission count must be exactly three")

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

        for model, count in initial.items():
            if count_model(model) != count:
                raise RuntimeError("Smoke baseline was not restored")

    print("phase4b2 task submission checks passed")


if __name__ == "__main__":
    main()
