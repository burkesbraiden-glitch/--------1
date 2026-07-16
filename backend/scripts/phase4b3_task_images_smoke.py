import secrets
import sys
from io import BytesIO
from pathlib import Path

from sqlalchemy import select


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db
from app.models import Child, ExplorationPlan, GuideCard, Task, TaskSubmission, User


PNG_ONE = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
PNG_TWO = b"\x89PNG\r\n\x1a\nsecond-image"
PNG_THREE = b"\x89PNG\r\n\x1a\nthird-image"


def assert_success(response, expected_status=200):
    payload = response.get_json()
    if response.status_code != expected_status or not payload["success"]:
        raise RuntimeError("Unexpected task image smoke response")
    return payload


def assert_error(response, expected_status, expected_code):
    payload = response.get_json()
    if response.status_code != expected_status:
        raise RuntimeError("Unexpected task image smoke error status")
    if payload["success"] is not False:
        raise RuntimeError("Unexpected task image smoke success flag")
    if payload["error"]["code"] != expected_code:
        raise RuntimeError("Unexpected task image smoke error code")
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


def upload_image(client, token, plan_id, task_id, data, filename="photo.png"):
    return client.post(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}/submission/image",
        data={"image": (BytesIO(data), filename)},
        headers=auth_headers(token),
        content_type="multipart/form-data",
    )


def storage_path(upload_root, storage_key):
    if not storage_key or not storage_key.startswith("task-images/"):
        raise RuntimeError("Invalid storage key")
    return upload_root / storage_key.removeprefix("task-images/")


def upload_files(upload_root):
    if not upload_root.exists():
        return set()
    return {path.name for path in upload_root.iterdir() if path.is_file()}


def cleanup_uploaded_files(upload_root, created_file_names):
    if not upload_root.exists():
        return
    for file_name in created_file_names:
        path = upload_root / file_name
        if path.exists():
            path.unlink()


def main():
    suffix = secrets.randbelow(100000000)
    phone_a = f"132{suffix:08d}"
    phone_b = f"131{suffix:08d}"
    created_user_ids = set()
    created_upload_files = set()

    app = create_app("development")

    with app.app_context():
        client = app.test_client()
        upload_root = Path(app.config["TASK_IMAGE_UPLOAD_DIR"])
        upload_root.mkdir(parents=True, exist_ok=True)
        initial_upload_files = upload_files(upload_root)
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

            create_child(client, token_a, "Image Smoke A")
            create_child(client, token_b, "Image Smoke B")
            plan_a = create_plan(client, token_a, "A 的图片探索")
            plan_b = create_plan(client, token_b, "B 的图片探索")

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

            assert_success(client.post(f"/api/v1/plans/{plan_a['id']}/start", headers=auth_headers(token_a)))

            detail = assert_success(
                client.get(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[0]}",
                    headers=auth_headers(token_a),
                )
            )["data"]["task"]
            if detail["status"] != "not-started":
                raise RuntimeError("Initial task status is incorrect")

            uploaded = assert_success(upload_image(client, token_a, plan_a["id"], task_ids_a[0], PNG_ONE))["data"][
                "task"
            ]
            if uploaded["status"] != "in-progress" or uploaded["record"]["imageUrl"] is None:
                raise RuntimeError("Upload response task is incorrect")
            if TaskSubmission.query.count() != initial[TaskSubmission] + 1:
                raise RuntimeError("Upload did not create one submission")

            submission = TaskSubmission.query.filter_by(task_id=task_ids_a[0]).one()
            first_submission_id = submission.id
            first_key = submission.image_url
            first_path = storage_path(upload_root, first_key)
            created_upload_files.add(first_path.name)
            if first_path.read_bytes() != PNG_ONE:
                raise RuntimeError("Uploaded file bytes are incorrect")
            if Path(first_key).is_absolute() or ":" in first_key:
                raise RuntimeError("Storage key leaked a filesystem path")

            image_response = client.get(uploaded["record"]["imageUrl"], headers=auth_headers(token_a))
            image_bytes = image_response.data
            if image_response.status_code != 200 or image_bytes != PNG_ONE:
                raise RuntimeError("GET image bytes are incorrect")
            if not image_response.headers["Content-Type"].startswith("image/png"):
                raise RuntimeError("GET image content type is incorrect")
            image_response.close()

            note = "我发现屋檐上的小兽排成了一队。"
            patched = assert_success(
                client.patch(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[0]}/submission",
                    json={"note": note},
                    headers=auth_headers(token_a),
                )
            )["data"]["task"]
            if patched["record"]["note"] != note or not first_path.exists():
                raise RuntimeError("Patch note lost image")

            replaced = assert_success(upload_image(client, token_a, plan_a["id"], task_ids_a[0], PNG_TWO))["data"][
                "task"
            ]
            submission = TaskSubmission.query.filter_by(task_id=task_ids_a[0]).one()
            second_key = submission.image_url
            second_path = storage_path(upload_root, second_key)
            created_upload_files.add(second_path.name)
            if submission.id != first_submission_id or first_key == second_key:
                raise RuntimeError("Replacement did not update the same submission")
            if first_path.exists() or second_path.read_bytes() != PNG_TWO:
                raise RuntimeError("Replacement file cleanup is incorrect")

            second_image = client.get(replaced["record"]["imageUrl"], headers=auth_headers(token_a))
            second_image_bytes = second_image.data
            if second_image.status_code != 200 or second_image_bytes != PNG_TWO:
                raise RuntimeError("GET image did not return replacement bytes")
            second_image.close()

            completed = assert_success(
                client.post(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[0]}/submission/complete",
                    headers=auth_headers(token_a),
                )
            )["data"]["task"]
            completed_at = completed["completedAt"]
            if completed["status"] != "completed" or completed_at is None:
                raise RuntimeError("Task did not complete")

            replaced_after_complete = assert_success(
                upload_image(client, token_a, plan_a["id"], task_ids_a[0], PNG_THREE)
            )["data"]["task"]
            submission = TaskSubmission.query.filter_by(task_id=task_ids_a[0]).one()
            third_path = storage_path(upload_root, submission.image_url)
            created_upload_files.add(third_path.name)
            if replaced_after_complete["status"] != "completed":
                raise RuntimeError("Completed task regressed after replacement")
            if replaced_after_complete["completedAt"] != completed_at:
                raise RuntimeError("CompletedAt changed after image replacement")
            if replaced_after_complete["record"]["note"] != note:
                raise RuntimeError("Note changed after image replacement")

            assert_error(upload_image(client, token_b, plan_a["id"], task_ids_a[0], PNG_ONE), 404, "PLAN_NOT_FOUND")
            assert_error(
                client.get(replaced_after_complete["record"]["imageUrl"], headers=auth_headers(token_b)),
                404,
                "PLAN_NOT_FOUND",
            )
            assert_error(upload_image(client, token_a, plan_a["id"], task_ids_b[0], PNG_ONE), 404, "TASK_NOT_FOUND")
            assert_error(
                upload_image(client, token_a, plan_a["id"], task_ids_a[1], b"not image", "note.txt"),
                400,
                "UNSUPPORTED_IMAGE_TYPE",
            )
            if TaskSubmission.query.filter_by(task_id=task_ids_a[1]).first() is not None:
                raise RuntimeError("Invalid image created a submission")

            listed = assert_success(
                client.get(f"/api/v1/plans/{plan_a['id']}/tasks", headers=auth_headers(token_a))
            )["data"]["tasks"]
            detail = assert_success(
                client.get(
                    f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[0]}",
                    headers=auth_headers(token_a),
                )
            )["data"]["task"]
            expected_url = f"/api/v1/plans/{plan_a['id']}/tasks/{task_ids_a[0]}/submission/image"
            if listed[0]["record"]["imageUrl"] != expected_url or detail["record"]["imageUrl"] != expected_url:
                raise RuntimeError("Task imageUrl response is incorrect")

            plan_detail = assert_success(
                client.get(f"/api/v1/plans/{plan_a['id']}", headers=auth_headers(token_a))
            )["data"]["plan"]
            if plan_detail["status"] != "in-progress":
                raise RuntimeError("Plan must remain in-progress")

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
            cleanup_uploaded_files(upload_root, created_upload_files)

        for model, count in initial.items():
            if count_model(model) != count:
                raise RuntimeError("Smoke baseline was not restored")
        if upload_files(upload_root) != initial_upload_files:
            raise RuntimeError("Upload directory baseline was not restored")

    print("phase4b3 task image checks passed")


if __name__ == "__main__":
    main()
