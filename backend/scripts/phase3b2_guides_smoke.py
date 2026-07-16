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
        raise RuntimeError("Unexpected guides smoke response")
    return payload


def assert_error(response, expected_status, expected_code):
    payload = response.get_json()
    if response.status_code != expected_status:
        raise RuntimeError("Unexpected guides smoke error status")
    if payload["success"] is not False:
        raise RuntimeError("Unexpected guides smoke success flag")
    if payload["error"]["code"] != expected_code:
        raise RuntimeError("Unexpected guides smoke error code")
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


def create_plan(client, token, destination="故宫博物院", title="故宫亲子探索"):
    payload = assert_success(
        client.post(
            "/api/v1/plans",
            json={
                "title": title,
                "destination": destination,
                "duration": "3小时",
                "interests": ["历史故事", " 建筑礼仪 ", "历史故事"],
            },
            headers=auth_headers(token),
        ),
        expected_status=201,
    )
    return payload["data"]["plan"]


def assert_guide_shape(guide, expected_destination):
    if guide["destination"] != expected_destination:
        raise RuntimeError("Guide destination does not match plan")
    if not isinstance(guide["childIntro"], list) or len(guide["childIntro"]) < 2:
        raise RuntimeError("Guide childIntro shape is invalid")
    if not isinstance(guide["questions"], list) or len(guide["questions"]) < 2:
        raise RuntimeError("Guide questions shape is invalid")
    if not isinstance(guide["focusItems"], list) or len(guide["focusItems"]) < 3:
        raise RuntimeError("Guide focusItems shape is invalid")
    if guide["audioUrl"] is not None:
        raise RuntimeError("Guide audioUrl must be null")


def main():
    suffix = secrets.randbelow(100000000)
    phone_a = f"137{suffix:08d}"
    phone_b = f"136{suffix:08d}"
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

            child_a_id = create_child(client, token_a, "Guide Smoke A")
            create_child(client, token_b, "Guide Smoke B")

            plan_a = create_plan(client, token_a)
            plan_b = create_plan(client, token_b, title="用户 B 故宫探索")

            if plan_a["childId"] != child_a_id:
                raise RuntimeError("User A plan did not use User A child")
            if plan_a["status"] != "ready" or plan_b["status"] != "ready":
                raise RuntimeError("Smoke plans must be ready")

            assert_error(
                client.get(f"/api/v1/plans/{plan_a['id']}/guide", headers=auth_headers(token_a)),
                404,
                "GUIDE_NOT_FOUND",
            )
            if count_guides() != initial_guides:
                raise RuntimeError("GET guide created a guide card")

            assert_error(
                client.get(f"/api/v1/plans/{plan_a['id']}/guide", headers=auth_headers(token_b)),
                404,
                "PLAN_NOT_FOUND",
            )
            assert_error(
                client.post(
                    f"/api/v1/plans/{plan_a['id']}/guide/generate",
                    headers=auth_headers(token_b),
                ),
                404,
                "PLAN_NOT_FOUND",
            )

            generated = assert_success(
                client.post(
                    f"/api/v1/plans/{plan_a['id']}/guide/generate",
                    headers=auth_headers(token_a),
                ),
                expected_status=201,
            )["data"]["guide"]
            if count_guides() != initial_guides + 1:
                raise RuntimeError("Guide count did not increase by one")
            assert_guide_shape(generated, plan_a["destination"])

            repeated = assert_success(
                client.post(
                    f"/api/v1/plans/{plan_a['id']}/guide/generate",
                    headers=auth_headers(token_a),
                )
            )["data"]["guide"]
            if repeated["id"] != generated["id"]:
                raise RuntimeError("Repeated generate returned a different guide")
            if count_guides() != initial_guides + 1:
                raise RuntimeError("Repeated generate changed guide count")

            fetched = assert_success(
                client.get(f"/api/v1/plans/{plan_a['id']}/guide", headers=auth_headers(token_a))
            )["data"]["guide"]
            if fetched["id"] != generated["id"]:
                raise RuntimeError("GET guide returned a different guide")

            guide_columns = {column["name"] for column in inspect(db.engine).get_columns("guide_cards")}
            if "destination" in guide_columns:
                raise RuntimeError("guide_cards must not contain destination")
            forbidden_audio_columns = {"audio_status", "is_playing", "is_paused", "play_state"}
            if guide_columns & forbidden_audio_columns:
                raise RuntimeError("guide_cards must not contain audio UI state")

            fallback_plan = create_plan(
                client,
                token_a,
                destination="国家博物馆",
                title="国家博物馆亲子探索",
            )
            fallback_guide = assert_success(
                client.post(
                    f"/api/v1/plans/{fallback_plan['id']}/guide/generate",
                    headers=auth_headers(token_a),
                ),
                expected_status=201,
            )["data"]["guide"]
            assert_guide_shape(fallback_guide, "国家博物馆")

            draft_plan = ExplorationPlan(
                user_id=user_a_id,
                child_id=child_a_id,
                title="草稿探索计划",
                destination="颐和园",
                age_group="7-12",
                duration="2小时",
                interests=["园林"],
                status="draft",
            )
            db.session.add(draft_plan)
            db.session.commit()

            assert_error(
                client.post(
                    f"/api/v1/plans/{draft_plan.id}/guide/generate",
                    headers=auth_headers(token_a),
                ),
                409,
                "PLAN_NOT_READY",
            )

        finally:
            ids_from_database = db.session.scalars(
                select(User.id).where(User.phone.in_([phone_a, phone_b]))
            ).all()
            created_user_ids.update(ids_from_database)
            if created_user_ids:
                plan_ids = db.session.scalars(
                    select(ExplorationPlan.id).where(
                        ExplorationPlan.user_id.in_(created_user_ids)
                    )
                ).all()
                if plan_ids:
                    GuideCard.query.filter(GuideCard.plan_id.in_(plan_ids)).delete(
                        synchronize_session=False
                    )
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

    print("phase3b2 guide checks passed")


if __name__ == "__main__":
    main()
