import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Attraction, AttractionGuide, User


@pytest.fixture()
def attraction_api_db(app):
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def auth_headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def add_user(user_id=1):
    user = User(id=user_id, phone=f"13800138{user_id:03d}", nickname="童旅用户")
    db.session.add(user)
    db.session.commit()
    return user


def add_attraction(attraction_id, *, name, city="北京", summary="适合亲子观察的文化景点。", is_active=True):
    attraction = Attraction(
        id=attraction_id,
        name=name,
        city=city,
        district="东城区",
        address=None,
        summary=summary,
        tags=["历史"],
        recommended_duration_minutes=120,
        cover_image=None,
        is_active=is_active,
    )
    db.session.add(attraction)
    db.session.commit()
    return attraction


def add_guide(guide_id, attraction_id):
    guide = AttractionGuide(
        id=guide_id,
        attraction_id=attraction_id,
        overview="从一个细节开始探索景点故事。",
        highlights=["建筑"],
        visit_tips=["预留休息时间"],
        family_tips=["让孩子选择想记录的发现"],
    )
    db.session.add(guide)
    db.session.commit()
    return guide


def assert_error(response, status_code, code):
    assert response.status_code == status_code
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == code
    assert "data" not in payload


def test_attraction_list_requires_jwt(client):
    assert_error(client.get("/api/v1/attractions"), 401, "UNAUTHORIZED")


def test_attraction_list_returns_active_items_in_success_envelope(client, app, attraction_api_db):
    with app.app_context():
        add_user()
        add_attraction(1, name="故宫博物院")
        add_attraction(2, name="停用景点", is_active=False)

    response = client.get("/api/v1/attractions", headers=auth_headers(app, 1))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["message"] == "ok"
    assert payload["data"]["total"] == 1
    assert payload["data"]["items"][0]["name"] == "故宫博物院"
    assert "isActive" not in payload["data"]["items"][0]


def test_attraction_list_applies_city_keyword_and_pagination(client, app, attraction_api_db):
    with app.app_context():
        add_user()
        add_attraction(1, name="故宫博物院", summary="在宫殿中认识古建筑。")
        add_attraction(2, name="上海博物馆", city="上海", summary="通过文物了解中华文明。")

    city = client.get("/api/v1/attractions?city=%20%E5%8C%97%E4%BA%AC%20", headers=auth_headers(app, 1))
    keyword = client.get("/api/v1/attractions?keyword=%E4%B8%AD%E5%8D%8E%E6%96%87%E6%98%8E", headers=auth_headers(app, 1))
    page = client.get("/api/v1/attractions?limit=1&offset=1", headers=auth_headers(app, 1))

    assert [item["id"] for item in city.get_json()["data"]["items"]] == [1]
    assert [item["id"] for item in keyword.get_json()["data"]["items"]] == [2]
    assert page.get_json()["data"]["total"] == 2
    assert page.get_json()["data"]["offset"] == 1
    assert len(page.get_json()["data"]["items"]) == 1


@pytest.mark.parametrize("query", ("limit=0", "limit=101", "limit=oops", "offset=-1", "offset=oops"))
def test_attraction_list_rejects_invalid_pagination(client, app, attraction_api_db, query):
    with app.app_context():
        add_user()

    assert_error(client.get(f"/api/v1/attractions?{query}", headers=auth_headers(app, 1)), 400, "VALIDATION_ERROR")


def test_attraction_detail_returns_success_and_hides_missing_or_inactive(client, app, attraction_api_db):
    with app.app_context():
        add_user()
        add_attraction(1, name="故宫博物院")
        add_attraction(2, name="停用景点", is_active=False)

    detail = client.get("/api/v1/attractions/1", headers=auth_headers(app, 1))
    assert detail.status_code == 200
    assert detail.get_json()["data"]["attraction"]["id"] == 1
    assert_error(client.get("/api/v1/attractions/999", headers=auth_headers(app, 1)), 404, "ATTRACTION_NOT_FOUND")
    assert_error(client.get("/api/v1/attractions/2", headers=auth_headers(app, 1)), 404, "ATTRACTION_NOT_FOUND")


def test_attraction_guide_returns_success_and_not_found_envelope(client, app, attraction_api_db):
    with app.app_context():
        add_user()
        attraction = add_attraction(1, name="故宫博物院")
        add_guide(10, attraction.id)
        add_attraction(2, name="无攻略景点")

    guide = client.get("/api/v1/attractions/1/guide", headers=auth_headers(app, 1))
    assert guide.status_code == 200
    assert guide.get_json()["data"]["guide"]["attractionId"] == 1
    assert_error(client.get("/api/v1/attractions/2/guide", headers=auth_headers(app, 1)), 404, "ATTRACTION_GUIDE_NOT_FOUND")
    assert_error(client.get("/api/v1/attractions/999/guide", headers=auth_headers(app, 1)), 404, "ATTRACTION_NOT_FOUND")
