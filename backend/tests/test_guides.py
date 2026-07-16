import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Child, ExplorationPlan, GuideCard, User
from app.services.guide_generator import generate_guide_content


@pytest.fixture()
def guides_db(app):
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def auth_headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def create_user(user_id, phone):
    user = User(id=user_id, phone=phone, nickname="童旅用户")
    db.session.add(user)
    db.session.commit()
    return user


def create_child(child_id, user_id, age_group="7-12"):
    child = Child(
        id=child_id,
        user_id=user_id,
        name="小小探索家",
        age=7 if age_group == "7-12" else 5,
        age_group=age_group,
        interests=[],
        is_default=True,
    )
    db.session.add(child)
    db.session.commit()
    return child


def create_plan(
    plan_id,
    user_id,
    child_id,
    *,
    status="ready",
    destination="故宫博物院",
    interests=None,
):
    plan = ExplorationPlan(
        id=plan_id,
        user_id=user_id,
        child_id=child_id,
        title=f"{destination}亲子探索",
        destination=destination,
        age_group="7-12",
        duration="3小时",
        interests=interests or ["历史故事"],
        status=status,
    )
    db.session.add(plan)
    db.session.commit()
    return plan


def create_guide(guide_id, plan_id):
    guide = GuideCard(
        id=guide_id,
        plan_id=plan_id,
        child_intro=["故宫以前是皇帝和家人生活、工作的地方。", "屋顶、宫门和台阶里藏着很多古代礼仪。"],
        questions=["你觉得这么大的宫殿是谁住的？", "你发现屋顶上有什么特别的东西？"],
        focus_items=["屋顶", "宫门", "颜色"],
        audio_url=None,
    )
    db.session.add(guide)
    db.session.commit()
    return guide


def test_get_guide_requires_token(client):
    response = client.get("/api/v1/plans/100/guide")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_get_guide_missing_plan_returns_plan_not_found(client, app, guides_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.get("/api/v1/plans/999/guide", headers=auth_headers(app, 1))

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "PLAN_NOT_FOUND"


def test_other_user_cannot_read_or_generate_guide(client, app, guides_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_user(2, "13800138001")
        create_child(10, 1)
        create_plan(100, 1, 10)

    get_response = client.get("/api/v1/plans/100/guide", headers=auth_headers(app, 2))
    post_response = client.post("/api/v1/plans/100/guide/generate", headers=auth_headers(app, 2))

    assert get_response.status_code == 404
    assert get_response.get_json()["error"]["code"] == "PLAN_NOT_FOUND"
    assert post_response.status_code == 404
    assert post_response.get_json()["error"]["code"] == "PLAN_NOT_FOUND"


def test_get_guide_without_guide_returns_not_found_without_creating(client, app, guides_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10)

    response = client.get("/api/v1/plans/100/guide", headers=auth_headers(app, 1))

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "GUIDE_NOT_FOUND"
    with app.app_context():
        assert GuideCard.query.count() == 0


def test_get_guide_returns_existing_guide_structure(client, app, guides_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, destination="故宫博物院")
        create_guide(500, 100)

    response = client.get("/api/v1/plans/100/guide", headers=auth_headers(app, 1))

    assert response.status_code == 200
    guide = response.get_json()["data"]["guide"]
    assert guide["id"] == 500
    assert guide["planId"] == 100
    assert guide["destination"] == "故宫博物院"
    assert guide["childIntro"][0] == "故宫以前是皇帝和家人生活、工作的地方。"
    assert guide["focusItems"] == ["屋顶", "宫门", "颜色"]
    assert guide["audioUrl"] is None
    assert "child_intro" not in guide
    assert "focus_items" not in guide
    assert "audioStatus" not in guide


def test_post_generate_requires_token(client):
    response = client.post("/api/v1/plans/100/guide/generate")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_post_generate_missing_plan_returns_plan_not_found(client, app, guides_db):
    with app.app_context():
        create_user(1, "13800138000")

    response = client.post("/api/v1/plans/999/guide/generate", headers=auth_headers(app, 1))

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "PLAN_NOT_FOUND"


def test_post_generate_draft_plan_returns_plan_not_ready(client, app, guides_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, status="draft")

    response = client.post("/api/v1/plans/100/guide/generate", headers=auth_headers(app, 1))

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "PLAN_NOT_READY"


def test_post_generate_creates_guide_and_returns_plan_destination(client, app, guides_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10, destination="故宫博物院")

    response = client.post("/api/v1/plans/100/guide/generate", headers=auth_headers(app, 1))

    assert response.status_code == 201
    guide = response.get_json()["data"]["guide"]
    assert guide["destination"] == "故宫博物院"
    assert guide["childIntro"] == [
        "故宫以前是皇帝和家人生活、工作的地方。",
        "屋顶、宫门和台阶里藏着很多古代礼仪。",
        "今天不用记很多名字，认真观察就很好。",
    ]
    assert guide["questions"] == [
        "你觉得这么大的宫殿是谁住的？",
        "你发现屋顶上有什么特别的东西？",
        "为什么这里很多地方都是红色和黄色？",
    ]
    assert guide["focusItems"] == ["屋顶", "宫门", "颜色"]
    assert guide["audioUrl"] is None
    assert "audioStatus" not in guide
    with app.app_context():
        assert GuideCard.query.count() == 1


def test_post_generate_is_idempotent_for_existing_guide(client, app, guides_db):
    with app.app_context():
        create_user(1, "13800138000")
        create_child(10, 1)
        create_plan(100, 1, 10)

    first = client.post("/api/v1/plans/100/guide/generate", headers=auth_headers(app, 1))
    second = client.post("/api/v1/plans/100/guide/generate", headers=auth_headers(app, 1))

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.get_json()["data"]["guide"]["id"] == first.get_json()["data"]["guide"]["id"]
    with app.app_context():
        assert GuideCard.query.count() == 1


def test_palace_generator_template_has_required_structure(app):
    with app.app_context():
        plan = ExplorationPlan(
            destination="故宫博物院",
            age_group="7-12",
            interests=["古代生活", "建筑礼仪"],
        )

    content = generate_guide_content(plan)

    assert len(content["child_intro"]) >= 2
    assert len(content["questions"]) >= 2
    assert len(content["focus_items"]) >= 3
    assert content["audio_url"] is None
    assert all(isinstance(item, str) and item.strip() for item in content["child_intro"])


def test_fallback_generator_template_has_required_structure(app):
    with app.app_context():
        plan = ExplorationPlan(
            destination="国家博物馆",
            age_group="7-12",
            interests=["文物", "历史"],
        )

    content = generate_guide_content(plan)

    assert len(content["child_intro"]) >= 2
    assert len(content["questions"]) >= 2
    assert len(content["focus_items"]) >= 3
    assert content["audio_url"] is None
    assert "国家博物馆" in content["child_intro"][0]
