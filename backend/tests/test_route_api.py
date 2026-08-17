import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Attraction, Route, User


@pytest.fixture()
def route_api_db(app):
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def auth_headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def add_user(user_id):
    user = User(id=user_id, phone=f"1370000{user_id:04d}", nickname=f"路线用户{user_id}")
    db.session.add(user)
    db.session.commit()
    return user


def add_attraction(attraction_id, *, city="北京", is_active=True):
    attraction = Attraction(
        id=attraction_id,
        name=f"景点{attraction_id}",
        city=city,
        district="东城区",
        summary="适合亲子观察的文化景点。",
        tags=["历史"],
        recommended_duration_minutes=120,
        cover_image="cover.jpg",
        is_active=is_active,
    )
    db.session.add(attraction)
    db.session.commit()
    return attraction


def assert_error(response, status_code, code):
    assert response.status_code == status_code
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == code
    assert set(payload["error"]) == {"code", "message", "details"}


def route_payload(response):
    assert response.get_json()["success"] is True
    return response.get_json()["data"]["route"]


def create_route(client, app, *, user_id=1, **data):
    payload = {"title": "北京探索", "city": "北京"}
    payload.update(data)
    response = client.post("/api/v1/routes", json=payload, headers=auth_headers(app, user_id))
    assert response.status_code == 201
    return route_payload(response)


def create_day(client, app, route_id, **data):
    response = client.post(f"/api/v1/routes/{route_id}/days", json=data, headers=auth_headers(app, 1))
    assert response.status_code == 201
    return route_payload(response)["days"][-1]


def create_stop(client, app, route_id, day_id, **data):
    response = client.post(
        f"/api/v1/routes/{route_id}/days/{day_id}/stops",
        json=data,
        headers=auth_headers(app, 1),
    )
    assert response.status_code == 201
    day = next(day for day in route_payload(response)["days"] if day["id"] == day_id)
    return day["stops"][-1]


def test_route_endpoints_require_jwt(client):
    assert_error(client.get("/api/v1/routes"), 401, "UNAUTHORIZED")
    assert_error(client.post("/api/v1/routes", json={}), 401, "UNAUTHORIZED")
    assert_error(client.patch("/api/v1/routes/1/days/reorder", json={"dayIds": []}), 401, "UNAUTHORIZED")
    assert_error(client.post("/api/v1/routes/1/days/1/stops", json={}), 401, "UNAUTHORIZED")


def test_route_create_list_detail_update_delete_and_pagination(client, app, route_api_db):
    with app.app_context():
        add_user(1)
        add_user(2)
    first = create_route(client, app, title="第一条", startDate="2026-08-20", endDate="2026-08-22")
    second = create_route(client, app, title="第二条")
    other = create_route(client, app, user_id=2, title="其他用户")

    listing = client.get("/api/v1/routes?limit=1&offset=1", headers=auth_headers(app, 1))
    assert listing.status_code == 200
    assert listing.get_json()["data"]["total"] == 2
    assert listing.get_json()["data"]["limit"] == 1
    assert len(listing.get_json()["data"]["items"]) == 1
    assert set(listing.get_json()["data"]["items"][0]) == {"id", "title", "city", "startDate", "endDate", "status", "createdAt", "updatedAt"}

    detail = client.get(f"/api/v1/routes/{first['id']}", headers=auth_headers(app, 1))
    assert detail.status_code == 200
    assert route_payload(detail)["startDate"] == "2026-08-20"
    updated = client.patch(f"/api/v1/routes/{first['id']}", json={"title": "新标题"}, headers=auth_headers(app, 1))
    assert route_payload(updated)["title"] == "新标题"
    assert_error(client.get(f"/api/v1/routes/{other['id']}", headers=auth_headers(app, 1)), 404, "ROUTE_NOT_FOUND")
    deleted = client.delete(f"/api/v1/routes/{second['id']}", headers=auth_headers(app, 1))
    assert deleted.status_code == 200
    assert deleted.get_json()["success"] is True
    assert deleted.get_json()["data"] == {}
    assert deleted.get_json()["message"] == "Route deleted"


@pytest.mark.parametrize(
    "body",
    [None, [], "text"],
)
def test_route_api_rejects_non_object_json(client, app, route_api_db, body):
    with app.app_context():
        add_user(1)
    kwargs = {"json": body} if body is not None else {"data": "", "content_type": "application/json"}
    assert_error(client.post("/api/v1/routes", headers=auth_headers(app, 1), **kwargs), 400, "VALIDATION_ERROR")


@pytest.mark.parametrize(
    "payload,code",
    [
        ({"title": "北京", "city": "北京", "startDate": "bad"}, "VALIDATION_ERROR"),
        ({"title": "北京", "city": "北京", "startDate": "2026-08-22", "endDate": "2026-08-20"}, "INVALID_ROUTE_DATE_RANGE"),
    ],
)
def test_route_api_rejects_invalid_dates(client, app, route_api_db, payload, code):
    with app.app_context():
        add_user(1)
    assert_error(client.post("/api/v1/routes", json=payload, headers=auth_headers(app, 1)), 400, code)


def test_day_crud_resequence_date_validation_and_wrong_parent(client, app, route_api_db):
    with app.app_context():
        add_user(1)
    route = create_route(client, app, startDate="2026-08-20", endDate="2026-08-22")
    first = create_day(client, app, route["id"], date="2026-08-20", title="第一天")
    second = create_day(client, app, route["id"], date="2026-08-21")

    patched = client.patch(f"/api/v1/routes/{route['id']}/days/{first['id']}", json={"title": "更新"}, headers=auth_headers(app, 1))
    assert route_payload(patched)["days"][0]["title"] == "更新"
    assert_error(client.post(f"/api/v1/routes/{route['id']}/days", json={"date": "2026-08-23"}, headers=auth_headers(app, 1)), 400, "ROUTE_DAY_DATE_OUT_OF_RANGE")
    assert_error(client.patch(f"/api/v1/routes/{route['id']}/days/999", json={"title": "x"}, headers=auth_headers(app, 1)), 404, "ROUTE_DAY_NOT_FOUND")
    deleted = client.delete(f"/api/v1/routes/{route['id']}/days/{first['id']}", headers=auth_headers(app, 1))
    assert [(day["id"], day["dayNumber"]) for day in route_payload(deleted)["days"]] == [(second["id"], 1)]


def test_stop_crud_constraints_resequence_and_wrong_parent(client, app, route_api_db):
    with app.app_context():
        add_user(1)
        add_attraction(1)
        add_attraction(2, is_active=False)
        add_attraction(3, city="广州")
    route = create_route(client, app)
    first_day = create_day(client, app, route["id"])
    other_day = create_day(client, app, route["id"])
    first = create_stop(client, app, route["id"], first_day["id"], attractionId=1, note="上午")
    second = create_stop(client, app, route["id"], first_day["id"], attractionId=1)

    assert_error(client.post(f"/api/v1/routes/{route['id']}/days/{first_day['id']}/stops", json={"attractionId": 2}, headers=auth_headers(app, 1)), 404, "ATTRACTION_NOT_FOUND")
    assert_error(client.post(f"/api/v1/routes/{route['id']}/days/{first_day['id']}/stops", json={"attractionId": 3}, headers=auth_headers(app, 1)), 400, "ATTRACTION_CITY_MISMATCH")
    patched = client.patch(f"/api/v1/routes/{route['id']}/days/{first_day['id']}/stops/{first['id']}", json={"note": "下午"}, headers=auth_headers(app, 1))
    assert route_payload(patched)["days"][0]["stops"][0]["note"] == "下午"
    for payload in ({"attractionId": 1}, {"sortOrder": 2}, {"routeDayId": other_day["id"]}):
        assert_error(client.patch(f"/api/v1/routes/{route['id']}/days/{first_day['id']}/stops/{first['id']}", json=payload, headers=auth_headers(app, 1)), 400, "VALIDATION_ERROR")
    assert_error(client.patch(f"/api/v1/routes/{route['id']}/days/{other_day['id']}/stops/{first['id']}", json={"note": "x"}, headers=auth_headers(app, 1)), 404, "ROUTE_STOP_NOT_FOUND")
    deleted = client.delete(f"/api/v1/routes/{route['id']}/days/{first_day['id']}/stops/{first['id']}", headers=auth_headers(app, 1))
    assert [(stop["id"], stop["sortOrder"]) for stop in route_payload(deleted)["days"][0]["stops"]] == [(second["id"], 1)]


def test_day_reorder_api_validates_and_returns_detail_in_new_order(client, app, route_api_db):
    with app.app_context():
        add_user(1)
    route = create_route(client, app, status="ready")
    first = create_day(client, app, route["id"])
    second = create_day(client, app, route["id"])
    with app.app_context():
        db.session.get(Route, route["id"]).status = "ready"
        db.session.commit()

    response = client.patch(f"/api/v1/routes/{route['id']}/days/reorder", json={"dayIds": [second["id"], first["id"]]}, headers=auth_headers(app, 1))
    detail = route_payload(response)
    assert response.status_code == 200
    assert [day["id"] for day in detail["days"]] == [second["id"], first["id"]]
    assert detail["status"] == "draft"
    for payload in ({"dayIds": [first["id"]]}, {"dayIds": [first["id"], first["id"]]}, {"dayIds": [999, first["id"]]}, {}):
        assert_error(client.patch(f"/api/v1/routes/{route['id']}/days/reorder", json=payload, headers=auth_headers(app, 1)), 400, "INVALID_ROUTE_DAY_ORDER" if payload else "VALIDATION_ERROR")


def test_stop_reorder_api_validates_returns_detail_and_preserves_inactive_history(client, app, route_api_db):
    with app.app_context():
        add_user(1)
        attraction = add_attraction(1)
        attraction_id = attraction.id
    route = create_route(client, app, status="ready")
    day = create_day(client, app, route["id"])
    first = create_stop(client, app, route["id"], day["id"], attractionId=1)
    second = create_stop(client, app, route["id"], day["id"], attractionId=1)
    with app.app_context():
        db.session.get(Route, route["id"]).status = "ready"
        db.session.get(Attraction, attraction_id).is_active = False
        db.session.commit()

    response = client.patch(f"/api/v1/routes/{route['id']}/days/{day['id']}/stops/reorder", json={"stopIds": [second["id"], first["id"]]}, headers=auth_headers(app, 1))
    detail = route_payload(response)
    assert response.status_code == 200
    stops = detail["days"][0]["stops"]
    assert [stop["id"] for stop in stops] == [second["id"], first["id"]]
    assert detail["status"] == "draft"
    assert stops[0]["attraction"] == {
        "id": 1, "name": "景点1", "city": "北京", "district": "东城区", "summary": "适合亲子观察的文化景点。", "recommendedDurationMinutes": 120, "coverImage": "cover.jpg"
    }
    for payload in ({"stopIds": [first["id"]]}, {"stopIds": [first["id"], first["id"]]}, {"stopIds": [999, first["id"]]}, {}):
        assert_error(client.patch(f"/api/v1/routes/{route['id']}/days/{day['id']}/stops/reorder", json=payload, headers=auth_headers(app, 1)), 400, "INVALID_ROUTE_STOP_ORDER" if payload else "VALIDATION_ERROR")
