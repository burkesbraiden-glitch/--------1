import json
from datetime import date

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import event

from app.extensions import db
from app.models import Attraction, Child, ExplorationPlan, GuideCard, Route, RouteDay, RouteStop, Task, User


@pytest.fixture()
def generation_api_db(app):
    next_plan_id = 10000

    def assign_plan_id(_mapper, _connection, target):
        nonlocal next_plan_id
        if target.id is None:
            target.id = next_plan_id
            next_plan_id += 1

    with app.app_context():
        event.listen(ExplorationPlan, "before_insert", assign_plan_id)
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()
        event.remove(ExplorationPlan, "before_insert", assign_plan_id)


def auth_headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def seed_generation_api_data():
    owner = User(id=1, phone="13800138000", nickname="路线家长")
    other_user = User(id=2, phone="13900139000", nickname="其他家长")
    child = Child(
        id=10,
        user_id=1,
        name="孩子甲",
        age=8,
        age_group="7-12",
        interests=["古建筑"],
        is_default=True,
    )
    other_child = Child(
        id=20,
        user_id=2,
        name="其他孩子",
        age=9,
        age_group="7-12",
        interests=["历史"],
        is_default=True,
    )
    attraction_one = Attraction(
        id=100,
        name="故宫博物院",
        city="北京",
        district="东城区",
        address="景山前街4号",
        summary="观察屋檐上的小兽。",
        tags=["历史"],
        recommended_duration_minutes=60,
    )
    attraction_two = Attraction(
        id=101,
        name="中国国家博物馆",
        city="北京",
        summary="寻找一件文物。",
        tags=["文物"],
        recommended_duration_minutes=90,
    )
    other_attraction = Attraction(
        id=200,
        name="广州博物馆",
        city="广州",
        summary="其他路线景点。",
        tags=["历史"],
    )
    route = Route(
        id=1,
        user_id=1,
        title="北京文化探索",
        city="北京",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 2),
        status="ready",
    )
    day = RouteDay(id=1000, route_id=1, day_number=1, date=date(2026, 10, 1), title="故宫观察日")
    first_stop = RouteStop(id=10000, route_day_id=1000, attraction_id=100, sort_order=1, note="先看屋顶。")
    second_stop = RouteStop(id=10001, route_day_id=1000, attraction_id=101, sort_order=2, note="再看文物。")
    other_route = Route(id=2, user_id=2, title="广州探索", city="广州", status="ready")
    other_day = RouteDay(id=2000, route_id=2, day_number=1)
    other_stop = RouteStop(id=20000, route_day_id=2000, attraction_id=200, sort_order=1)
    db.session.add_all([
        owner,
        other_user,
        child,
        other_child,
        attraction_one,
        attraction_two,
        other_attraction,
        route,
        day,
        first_stop,
        second_stop,
        other_route,
        other_day,
        other_stop,
    ])
    db.session.commit()
    return {
        "route_id": route.id,
        "child_id": child.id,
        "other_child_id": other_child.id,
        "first_stop_id": first_stop.id,
        "second_stop_id": second_stop.id,
        "other_route_id": other_route.id,
        "other_stop_id": other_stop.id,
        "attraction_one_id": attraction_one.id,
    }


def generate(client, app, route_id, payload, *, user_id=1):
    return client.post(
        f"/api/v1/routes/{route_id}/exploration-plans/generate",
        json=payload,
        headers=auth_headers(app, user_id),
    )


def assert_error(response, status_code, code):
    assert response.status_code == status_code
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == code
    assert set(payload["error"]) == {"code", "message", "details"}


def test_generation_endpoint_requires_jwt(client):
    response = client.post("/api/v1/routes/1/exploration-plans/generate", json={})

    assert_error(response, 401, "UNAUTHORIZED")


@pytest.mark.parametrize(
    "payload",
    [None, [], "invalid", {}, {"childId": 10}, {"routeStopIds": [10000]}, {"childId": 10, "routeStopIds": [10000], "extra": True}],
)
def test_generation_endpoint_validates_only_request_body_shape(client, app, generation_api_db, payload):
    with app.app_context():
        data = seed_generation_api_data()

    kwargs = {"json": payload} if payload is not None else {"data": "", "content_type": "application/json"}
    response = client.post(
        f"/api/v1/routes/{data['route_id']}/exploration-plans/generate",
        headers=auth_headers(app, 1),
        **kwargs,
    )

    assert_error(response, 400, "VALIDATION_ERROR")


def test_generation_endpoint_returns_created_plans_in_request_order(client, app, generation_api_db):
    with app.app_context():
        data = seed_generation_api_data()

    response = generate(
        client,
        app,
        data["route_id"],
        {"childId": data["child_id"], "routeStopIds": [data["second_stop_id"], data["first_stop_id"]]},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["message"] == "Exploration plans generated"
    assert payload["data"]["routeId"] == data["route_id"]
    assert payload["data"]["childId"] == data["child_id"]
    results = payload["data"]["results"]
    assert [(item["routeStopId"], item["result"]) for item in results] == [
        (data["second_stop_id"], "created"),
        (data["first_stop_id"], "created"),
    ]
    assert set(results[0]["plan"]) == {
        "id",
        "title",
        "destination",
        "ageGroup",
        "duration",
        "taskCount",
        "interests",
        "status",
        "childId",
        "completedAt",
        "createdAt",
        "updatedAt",
    }
    assert results[0]["plan"]["destination"] == "中国国家博物馆"
    with app.app_context():
        assert ExplorationPlan.query.count() == 2
        assert Task.query.count() == 0
        assert GuideCard.query.count() == 0


def test_generation_endpoint_is_idempotent_and_does_not_refresh_source_snapshot(client, app, generation_api_db):
    with app.app_context():
        data = seed_generation_api_data()
    payload = {"childId": data["child_id"], "routeStopIds": [data["first_stop_id"]]}

    first = generate(client, app, data["route_id"], payload)
    with app.app_context():
        plan = ExplorationPlan.query.one()
        original_snapshot = json.loads(json.dumps(plan.source_snapshot))
        db.session.get(Route, data["route_id"]).title = "后续标题"
        db.session.get(Attraction, data["attraction_one_id"]).summary = "后续简介"
        db.session.commit()

    second = generate(client, app, data["route_id"], payload)

    assert first.status_code == second.status_code == 200
    assert second.get_json()["data"]["results"][0]["result"] == "existing"
    with app.app_context():
        plan = ExplorationPlan.query.one()
        assert plan.source_snapshot == original_snapshot
        assert ExplorationPlan.query.count() == 1


def test_generation_endpoint_supports_mixed_results_and_maps_service_errors(client, app, generation_api_db):
    with app.app_context():
        data = seed_generation_api_data()

    created = generate(
        client,
        app,
        data["route_id"],
        {"childId": data["child_id"], "routeStopIds": [data["first_stop_id"]]},
    )
    assert created.status_code == 200
    mixed = generate(
        client,
        app,
        data["route_id"],
        {"childId": data["child_id"], "routeStopIds": [data["first_stop_id"], data["second_stop_id"]]},
    )
    assert [(item["routeStopId"], item["result"]) for item in mixed.get_json()["data"]["results"]] == [
        (data["first_stop_id"], "existing"),
        (data["second_stop_id"], "created"),
    ]

    with app.app_context():
        db.session.get(Route, data["route_id"]).status = "draft"
        db.session.commit()
    assert_error(generate(client, app, data["route_id"], {"childId": data["child_id"], "routeStopIds": [data["first_stop_id"]]}), 409, "ROUTE_NOT_READY")
    with app.app_context():
        db.session.get(Route, data["route_id"]).status = "ready"
        db.session.commit()
    assert_error(generate(client, app, data["other_route_id"], {"childId": data["child_id"], "routeStopIds": [data["other_stop_id"]]}), 404, "ROUTE_NOT_FOUND")
    assert_error(generate(client, app, data["route_id"], {"childId": data["other_child_id"], "routeStopIds": [data["first_stop_id"]]}), 404, "CHILD_NOT_FOUND")
    assert_error(generate(client, app, data["route_id"], {"childId": data["child_id"], "routeStopIds": [data["other_stop_id"]]}), 404, "ROUTE_STOP_NOT_FOUND")
    assert_error(generate(client, app, data["route_id"], {"childId": data["child_id"], "routeStopIds": [True]}), 400, "VALIDATION_ERROR")
