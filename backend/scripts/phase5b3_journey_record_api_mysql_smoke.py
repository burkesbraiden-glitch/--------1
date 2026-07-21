import argparse
import hashlib
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db
from app.models import Child, ExplorationPlan, GuideCard, JourneyRecord, Task, TaskSubmission, User
from app.services.auth import token_payload_for_user


EXPECTED_REVISION = "d2842a9e808b"
LOCK_NAME = "tonglvji:phase5b3:journey_record_api_mysql_smoke"
CANDIDATE_PLAN_IDS = (118, 100)
ALLOWED_PLAN_STATUSES = {"ready", "in-progress", "completed"}
FORBIDDEN_PUBLIC_KEYS = {
    "custom_title",
    "cover_submission_id",
    "finalized_at",
    "created_at",
    "updated_at",
    "image_url",
    "image_path",
    "storage_key",
    "_storage_key",
    "_sa_instance_state",
}


class SmokeFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise SmokeFailure(message)


def sha256_text(value):
    return None if value is None else hashlib.sha256(value.encode("utf-8")).hexdigest()


def code_heads():
    config = Config()
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return tuple(ScriptDirectory.from_config(config).get_heads())


def revision_state():
    current = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    heads = code_heads()
    require(len(heads) == 1, "migration code must have exactly one head")
    require(current == heads[0] == EXPECTED_REVISION, "migration current/head mismatch")
    return current, heads[0]


def file_fingerprint(path):
    digest = hashlib.sha256()
    count = 0
    total_bytes = 0
    if not path.exists():
        return {"count": 0, "bytes": 0, "sha256": digest.hexdigest()}
    for item in sorted((item for item in path.rglob("*") if item.is_file()), key=lambda item: item.as_posix()):
        relative_name = item.relative_to(path).as_posix()
        content_digest = hashlib.sha256(item.read_bytes()).hexdigest()
        size = item.stat().st_size
        digest.update(relative_name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(content_digest.encode("ascii"))
        digest.update(b"\n")
        count += 1
        total_bytes += size
    return {"count": count, "bytes": total_bytes, "sha256": digest.hexdigest()}


def upload_fingerprint():
    return {
        "uploads": file_fingerprint(BACKEND_DIR / "uploads"),
        "var_uploads": file_fingerprint(BACKEND_DIR / "var" / "uploads"),
    }


def global_counts():
    return {
        "users": User.query.count(),
        "children": Child.query.count(),
        "exploration_plans": ExplorationPlan.query.count(),
        "guide_cards": GuideCard.query.count(),
        "tasks": Task.query.count(),
        "task_submissions": TaskSubmission.query.count(),
        "journey_records": JourneyRecord.query.count(),
    }


def select_candidate():
    for plan_id in CANDIDATE_PLAN_IDS:
        plan = db.session.get(ExplorationPlan, plan_id)
        if plan is None or plan.status not in ALLOWED_PLAN_STATUSES:
            continue
        user = db.session.get(User, plan.user_id)
        child = db.session.get(Child, plan.child_id)
        if user is None or child is None or child.user_id != user.id:
            continue
        if JourneyRecord.query.filter_by(plan_id=plan.id).count() != 0:
            continue
        tasks = Task.query.filter_by(plan_id=plan.id).order_by(Task.id).all()
        if not tasks:
            continue
        submissions = (
            TaskSubmission.query.join(Task)
            .filter(Task.plan_id == plan.id)
            .order_by(TaskSubmission.id)
            .all()
        )
        image_submission = next((submission for submission in submissions if submission.image_url), None)
        if not submissions or image_submission is None:
            continue
        return {
            "plan_id": plan.id,
            "user": user,
            "tasks": tasks,
            "submissions": submissions,
            "image_submission_id": image_submission.id,
            "image_task_id": image_submission.task_id,
            "image_storage_keys": tuple(
                submission.image_url for submission in submissions if submission.image_url
            ),
        }
    raise SmokeFailure("no safe candidate among planId 118 and planId 100")


def candidate_fingerprint(candidate):
    plan = db.session.get(ExplorationPlan, candidate["plan_id"])
    require(plan is not None, "candidate plan disappeared")
    tasks = (
        Task.query.filter_by(plan_id=plan.id)
        .order_by(Task.id)
        .all()
    )
    submissions = (
        TaskSubmission.query.join(Task)
        .filter(Task.plan_id == plan.id)
        .order_by(TaskSubmission.id)
        .all()
    )
    return {
        "plan": (
            plan.id,
            plan.user_id,
            plan.child_id,
            plan.title,
            plan.status,
            plan.created_at,
            plan.updated_at,
        ),
        "tasks": tuple(
            (task.id, task.plan_id, task.title, task.sort_order, task.created_at, task.updated_at)
            for task in tasks
        ),
        "submissions": tuple(
            (
                submission.id,
                submission.task_id,
                submission.status,
                sha256_text(submission.note),
                sha256_text(submission.image_url),
                submission.completed_at,
                submission.created_at,
                submission.updated_at,
            )
            for submission in submissions
        ),
    }


def complete_fingerprint(candidate):
    db.session.expire_all()
    return {
        "global": global_counts(),
        "candidate": candidate_fingerprint(candidate),
        "uploads": upload_fingerprint(),
    }


def assert_public_payload(payload, image_storage_keys):
    if isinstance(payload, dict):
        for key, value in payload.items():
            require("_" not in key and key not in FORBIDDEN_PUBLIC_KEYS, "public response exposed an internal field")
            assert_public_payload(value, image_storage_keys)
    elif isinstance(payload, list):
        for value in payload:
            assert_public_payload(value, image_storage_keys)
    else:
        require(payload is None or isinstance(payload, (bool, int, float, str)), "public response has an unexpected value")
        if isinstance(payload, str):
            require(all(key not in payload for key in image_storage_keys), "public response exposed a storage key")


def expect_response(response, status_code, *, success=None, error_code=None):
    require(response.status_code == status_code, f"unexpected HTTP status {response.status_code}")
    payload = response.get_json()
    require(isinstance(payload, dict), "API response is not a JSON object")
    if success is not None:
        require(payload.get("success") is success, "unexpected API success envelope")
    if error_code is not None:
        require(payload.get("error", {}).get("code") == error_code, "unexpected API error code")
    return payload


def log_api(method, path, response):
    print(f"api {method} {path} status={response.status_code}")


def clean_up(record_id, candidate, marker, marker_written, post_created, run_started_at):
    if record_id is None:
        return "not-needed"
    record = db.session.get(JourneyRecord, record_id)
    if record is None:
        return "already-absent"
    plan_id = candidate["plan_id"]
    plan_record_count = JourneyRecord.query.filter_by(plan_id=plan_id).count()
    primary_identity_matches = (
        record.id == record_id
        and record.plan_id == plan_id
        and (marker in (record.custom_title or "") or marker in (record.summary or ""))
    )
    first_level = primary_identity_matches and plan_record_count == 1
    if first_level:
        db.session.delete(record)
        db.session.commit()
        return "first-level"
    second_level = (
        not marker_written
        and post_created
        and record.id == record_id
        and record.plan_id == plan_id
        and record.created_at >= run_started_at - timedelta(seconds=5)
        and record.status == "draft"
        and record.finalized_at is None
        and record.custom_title is None
        and record.summary is None
        and record.cover_submission_id is None
        and plan_record_count == 1
    )
    if second_level:
        db.session.delete(record)
        db.session.commit()
        return "second-level"
    if primary_identity_matches:
        raise SmokeFailure(
            "HIGH PRIORITY: temporary record cleanup plan count is unsafe; "
            f"recordId={record_id} planId={plan_id} planRecordCount={plan_record_count}"
        )
    raise SmokeFailure(f"HIGH PRIORITY: temporary record cleanup could not be proven; recordId={record_id} planId={plan_id}")


def run_api_sequence(app, candidate, marker, state):
    plan_id = candidate["plan_id"]
    image_submission_id = candidate["image_submission_id"]
    image_task_id = candidate["image_task_id"]
    image_storage_keys = candidate["image_storage_keys"]
    headers = {
        "Authorization": f"Bearer {token_payload_for_user(candidate['user'], app.config)['accessToken']}"
    }
    client = app.test_client()
    record_path = f"/api/v1/plans/{plan_id}/journey-record"

    response = client.get("/api/v1/journey-records")
    log_api("GET", "/api/v1/journey-records", response)
    expect_response(response, 401, success=False, error_code="UNAUTHORIZED")

    response = client.get(record_path, headers=headers)
    log_api("GET", record_path, response)
    expect_response(response, 404, success=False, error_code="JOURNEY_RECORD_NOT_FOUND")

    response = client.post(record_path, headers=headers)
    log_api("POST", record_path, response)
    created = expect_response(response, 201, success=True)["data"]
    record = created["journeyRecord"]
    require(created["created"] is True and record["status"] == "draft", "first POST did not create a draft")
    state["record_id"] = record["id"]
    state["post_created"] = True
    require(record["planId"] == plan_id and record["createdAt"] and record["updatedAt"], "created record metadata mismatch")
    require(JourneyRecord.query.count() == state["baseline"]["global"]["journey_records"] + 1, "unexpected journey record count")

    response = client.patch(
        record_path,
        json={"customTitle": marker, "summary": marker},
        headers=headers,
    )
    log_api("PATCH", record_path, response)
    marked = expect_response(response, 200, success=True)["data"]["journeyRecord"]
    require(marked["id"] == state["record_id"] and marked["planId"] == plan_id, "marker PATCH targeted the wrong record")
    require(marker in marked["customTitle"] and marker in marked["summary"], "marker PATCH did not persist")
    state["marker_written"] = True
    marker_updated_at = marked["updatedAt"]

    response = client.post(record_path, headers=headers)
    log_api("POST", record_path, response)
    repeated_create = expect_response(response, 200, success=True)["data"]
    repeated_record = repeated_create["journeyRecord"]
    require(repeated_record["id"] == state["record_id"], "repeated POST returned a different record")
    require(repeated_record["customTitle"] == marker and repeated_record["summary"] == marker, "repeated POST overwrote marker")
    require(repeated_record["updatedAt"] == marker_updated_at, "repeated POST changed updatedAt")

    response = client.get(record_path, headers=headers)
    log_api("GET", record_path, response)
    detail = expect_response(response, 200, success=True)["data"]["journeyRecord"]
    require(detail["id"] == state["record_id"] and detail["customTitle"] == marker, "GET detail mismatch")
    require("entries" in detail, "GET detail omitted entries")
    assert_public_payload(detail, image_storage_keys)

    response = client.get("/api/v1/journey-records", headers=headers)
    log_api("GET", "/api/v1/journey-records", response)
    listed = expect_response(response, 200, success=True)["data"]["items"]
    list_item = next((item for item in listed if item["id"] == state["record_id"]), None)
    require(list_item is not None and "entries" not in list_item, "GET list record mismatch")
    assert_public_payload(list_item, image_storage_keys)

    summary = f"{marker}\nmysql api smoke summary"
    response = client.patch(record_path, json={"summary": summary}, headers=headers)
    log_api("PATCH", record_path, response)
    updated = expect_response(response, 200, success=True)["data"]["journeyRecord"]
    require(updated["customTitle"] == marker and updated["summary"] == summary, "summary PATCH mismatch")

    response = client.patch(record_path, json={"summary": summary}, headers=headers)
    log_api("PATCH", record_path, response)
    no_op = expect_response(response, 200, success=True)["data"]["journeyRecord"]
    require(no_op["updatedAt"] == updated["updatedAt"], "no-op PATCH changed updatedAt")

    response = client.patch(
        record_path,
        json={"coverSubmissionId": image_submission_id},
        headers=headers,
    )
    log_api("PATCH", record_path, response)
    covered = expect_response(response, 200, success=True)["data"]["journeyRecord"]
    expected_cover_url = f"/api/v1/plans/{plan_id}/tasks/{image_task_id}/submission/image"
    require(covered["coverSubmissionId"] == image_submission_id, "cover submission mismatch")
    require(covered["coverImageUrl"] == expected_cover_url, "cover image URL is not protected")
    assert_public_payload(covered, image_storage_keys)

    response = client.post(f"{record_path}/finalize", headers=headers)
    log_api("POST", f"{record_path}/finalize", response)
    finalized = expect_response(response, 200, success=True)["data"]["journeyRecord"]
    require(finalized["status"] == "finalized" and finalized["finalizedAt"], "finalize did not finalize")

    response = client.post(f"{record_path}/finalize", headers=headers)
    log_api("POST", f"{record_path}/finalize", response)
    repeated_finalized = expect_response(response, 200, success=True)["data"]["journeyRecord"]
    require(repeated_finalized["status"] == "finalized", "repeated finalize changed status")
    require(repeated_finalized["finalizedAt"] == finalized["finalizedAt"], "repeated finalize changed finalizedAt")
    require(repeated_finalized["updatedAt"] == finalized["updatedAt"], "repeated finalize changed updatedAt")

    before_blocked_patch = {
        key: repeated_finalized[key]
        for key in ("customTitle", "summary", "coverSubmissionId", "finalizedAt", "updatedAt")
    }
    response = client.patch(record_path, json={"summary": "should not be saved"}, headers=headers)
    log_api("PATCH", record_path, response)
    expect_response(response, 409, success=False, error_code="JOURNEY_RECORD_FINALIZED")
    db.session.expire_all()
    persisted = db.session.get(JourneyRecord, state["record_id"])
    require(persisted is not None, "temporary record disappeared before cleanup")
    require(
        persisted.custom_title == before_blocked_patch["customTitle"]
        and persisted.summary == before_blocked_patch["summary"]
        and persisted.cover_submission_id == before_blocked_patch["coverSubmissionId"],
        "finalized PATCH mutated the record",
    )


def main():
    parser = argparse.ArgumentParser(description="JourneyRecord real MySQL API smoke test")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="validate without JourneyRecord writes")
    mode.add_argument("--execute", action="store_true", help="run controlled API writes and cleanup")
    args = parser.parse_args()
    execute = args.execute
    run_started_at = datetime.now(UTC).replace(tzinfo=None)
    marker = f"__phase5b3_mysql_smoke__{uuid.uuid4().hex}"
    app = create_app("development")
    lock_connection = None
    lock_acquired = False
    candidate = None
    state = {"record_id": None, "marker_written": False, "post_created": False, "baseline": None}
    exit_code = 0

    try:
        require(app.testing is False, "TestingConfig is not allowed")
        with app.app_context():
            require(db.engine.dialect.name == "mysql", "MySQL is required")
            db.session.execute(text("SELECT 1")).scalar_one()
            current, head = revision_state()
            print(f"dialect={db.engine.dialect.name}")
            print(f"testing={str(app.testing).lower()}")
            print(f"migration_current={current}")
            print(f"migration_head={head}")

            lock_connection = db.engine.connect()
            lock_result = lock_connection.execute(text("SELECT GET_LOCK(:name, 0)"), {"name": LOCK_NAME}).scalar_one()
            require(lock_result == 1, "MySQL advisory lock is unavailable")
            lock_acquired = True
            print("advisory_lock=acquired")

            candidate = select_candidate()
            plan_id = candidate["plan_id"]
            print(
                f"candidate_planId={plan_id} task_count={len(candidate['tasks'])} "
                f"submission_count={len(candidate['submissions'])} image_submission_count="
                f"{sum(1 for submission in candidate['submissions'] if submission.image_url)}"
            )
            state["baseline"] = complete_fingerprint(candidate)
            require(state["baseline"]["global"]["journey_records"] == 0, "journey_records must be zero before smoke")
            print("fingerprint=collected")

            if execute:
                run_api_sequence(app, candidate, marker, state)
                print(f"recordId={state['record_id']}")
            else:
                after = complete_fingerprint(candidate)
                require(after == state["baseline"], "dry-run changed database or uploads")
                print("write_operations=not-executed")
                print("dry_run=passed")
    except Exception as error:
        exit_code = 1
        print(f"ERROR: {error}", file=sys.stderr)
    finally:
        if candidate is not None:
            with app.app_context():
                if execute:
                    try:
                        cleanup_level = clean_up(
                            state["record_id"],
                            candidate,
                            marker,
                            state["marker_written"],
                            state["post_created"],
                            run_started_at,
                        )
                        print(f"cleanup={cleanup_level}")
                    except Exception as error:
                        db.session.rollback()
                        exit_code = 1
                        print(f"ERROR: {error}", file=sys.stderr)
                if state["baseline"] is not None:
                    try:
                        restored = complete_fingerprint(candidate)
                        require(restored == state["baseline"], "database or uploads did not fully restore")
                        print("fingerprint_restored=true")
                    except Exception as error:
                        exit_code = 1
                        print(f"ERROR: {error}", file=sys.stderr)
        if lock_connection is not None:
            try:
                if lock_acquired:
                    released = lock_connection.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": LOCK_NAME}).scalar_one()
                    require(released == 1, "MySQL advisory lock release failed")
                    print("advisory_lock=released")
            except Exception as error:
                exit_code = 1
                print(f"ERROR: {error}", file=sys.stderr)
            finally:
                lock_connection.close()
        with app.app_context():
            db.session.remove()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
