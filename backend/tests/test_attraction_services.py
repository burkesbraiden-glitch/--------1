import pytest

from app.extensions import db
from app.models import Attraction, AttractionGuide
from app.services.attractions import (
    AttractionError,
    get_attraction,
    get_attraction_guide,
    list_attractions,
    serialize_attraction,
    serialize_attraction_guide,
)


@pytest.fixture()
def attraction_service_db(app):
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def add_attraction(
    attraction_id,
    *,
    name,
    city="北京",
    district="东城区",
    summary="适合亲子观察的文化景点。",
    is_active=True,
):
    attraction = Attraction(
        id=attraction_id,
        name=name,
        city=city,
        district=district,
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


def test_list_returns_only_active_attractions_in_stable_order(app, attraction_service_db):
    with app.app_context():
        add_attraction(3, name="天坛公园")
        add_attraction(2, name="故宫博物院")
        add_attraction(1, name="隐藏景点", is_active=False)

        data = list_attractions()

        assert [item["name"] for item in data["items"]] == ["天坛公园", "故宫博物院"]
        assert data["total"] == 2
        assert data["limit"] == 20
        assert data["offset"] == 0


def test_list_filters_city_after_trimming(app, attraction_service_db):
    with app.app_context():
        add_attraction(1, name="故宫博物院", city="北京")
        add_attraction(2, name="上海博物馆", city="上海")

        data = list_attractions(city=" 北京 ")

        assert [item["id"] for item in data["items"]] == [1]


def test_list_searches_name_and_summary_and_ignores_blank_keyword(app, attraction_service_db):
    with app.app_context():
        add_attraction(1, name="故宫博物院", summary="在宫殿中认识古建筑。")
        add_attraction(2, name="中国国家博物馆", summary="通过文物了解中华文明。")

        assert [item["id"] for item in list_attractions(keyword="故宫")["items"]] == [1]
        assert [item["id"] for item in list_attractions(keyword=" 中华文明 ")["items"]] == [2]
        assert {item["id"] for item in list_attractions(keyword="   ")["items"]} == {1, 2}


def test_list_applies_limit_and_offset_without_changing_total(app, attraction_service_db):
    with app.app_context():
        add_attraction(1, name="北海公园")
        add_attraction(2, name="故宫博物院")
        add_attraction(3, name="景山公园")

        data = list_attractions(limit=1, offset=1)

        assert data["total"] == 3
        assert data["limit"] == 1
        assert data["offset"] == 1
        assert [item["name"] for item in data["items"]] == ["故宫博物院"]


@pytest.mark.parametrize("kwargs", ({"limit": 0}, {"limit": 101}, {"limit": "1"}, {"offset": -1}, {"offset": "0"}))
def test_list_rejects_invalid_pagination(app, attraction_service_db, kwargs):
    with app.app_context():
        with pytest.raises(AttractionError) as error:
            list_attractions(**kwargs)

        assert error.value.code == "VALIDATION_ERROR"
        assert error.value.status_code == 400


def test_get_attraction_returns_serialized_active_attraction(app, attraction_service_db):
    with app.app_context():
        attraction = add_attraction(1, name="故宫博物院")

        assert get_attraction(attraction.id) == serialize_attraction(attraction)


@pytest.mark.parametrize("attraction_id,is_active", ((999, None), (1, False)))
def test_get_attraction_hides_missing_and_inactive_records(app, attraction_service_db, attraction_id, is_active):
    with app.app_context():
        if is_active is not None:
            add_attraction(attraction_id, name="停用景点", is_active=is_active)

        with pytest.raises(AttractionError) as error:
            get_attraction(attraction_id)

        assert error.value.code == "ATTRACTION_NOT_FOUND"
        assert error.value.status_code == 404


def test_get_attraction_guide_returns_active_attraction_guide(app, attraction_service_db):
    with app.app_context():
        attraction = add_attraction(1, name="故宫博物院")
        guide = add_guide(10, attraction.id)

        assert get_attraction_guide(attraction.id) == serialize_attraction_guide(guide)


@pytest.mark.parametrize(
    "attraction_id,is_active,with_guide,code",
    (
        (999, None, False, "ATTRACTION_NOT_FOUND"),
        (1, False, True, "ATTRACTION_NOT_FOUND"),
        (1, True, False, "ATTRACTION_GUIDE_NOT_FOUND"),
    ),
)
def test_get_attraction_guide_hides_missing_inactive_and_missing_guide(
    app, attraction_service_db, attraction_id, is_active, with_guide, code
):
    with app.app_context():
        if is_active is not None:
            attraction = add_attraction(attraction_id, name="景点", is_active=is_active)
            if with_guide:
                add_guide(10, attraction.id)

        with pytest.raises(AttractionError) as error:
            get_attraction_guide(attraction_id)

        assert error.value.code == code
        assert error.value.status_code == 404


def test_serializers_use_camel_case_and_do_not_expose_internal_fields(app, attraction_service_db):
    with app.app_context():
        attraction = add_attraction(1, name="故宫博物院")
        guide = add_guide(10, attraction.id)

        attraction_data = serialize_attraction(attraction)
        guide_data = serialize_attraction_guide(guide)

        assert attraction_data == {
            "id": 1,
            "name": "故宫博物院",
            "city": "北京",
            "district": "东城区",
            "address": None,
            "summary": "适合亲子观察的文化景点。",
            "tags": ["历史"],
            "recommendedDurationMinutes": 120,
            "coverImage": None,
        }
        assert guide_data == {
            "id": 10,
            "attractionId": 1,
            "overview": "从一个细节开始探索景点故事。",
            "highlights": ["建筑"],
            "visitTips": ["预留休息时间"],
            "familyTips": ["让孩子选择想记录的发现"],
        }
