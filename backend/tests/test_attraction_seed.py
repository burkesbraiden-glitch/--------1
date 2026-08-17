import pytest

from app.extensions import db
from app.models import Attraction, AttractionGuide
from scripts.seed_attractions import BEIJING_ATTRACTIONS, seed_attractions


@pytest.fixture()
def attraction_seed_db(app):
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def test_seed_creates_eight_beijing_attractions_and_guides(app, attraction_seed_db):
    with app.app_context():
        result = seed_attractions()

        assert result == {"createdAttractions": 8, "createdGuides": 8}
        assert Attraction.query.count() == 8
        assert AttractionGuide.query.count() == 8
        assert {item["name"] for item in BEIJING_ATTRACTIONS} == {
            "故宫博物院",
            "景山公园",
            "中国国家博物馆",
            "天坛公园",
            "颐和园",
            "北海公园",
            "恭王府博物馆",
            "孔庙和国子监博物馆",
        }
        assert all(attraction.city == "北京" and attraction.guide is not None for attraction in Attraction.query.all())


def test_seed_is_idempotent(app, attraction_seed_db):
    with app.app_context():
        seed_attractions()
        second = seed_attractions()

        assert second == {"createdAttractions": 0, "createdGuides": 0}
        assert Attraction.query.count() == 8
        assert AttractionGuide.query.count() == 8


def test_seed_adds_a_missing_guide_without_duplicating_existing_attraction(app, attraction_seed_db):
    with app.app_context():
        db.session.add(
            Attraction(
                id=1,
                name="故宫博物院",
                city="北京",
                district="东城区",
                summary="已有系统景点。",
                tags=["历史"],
            )
        )
        db.session.commit()

        result = seed_attractions()

        assert result == {"createdAttractions": 7, "createdGuides": 8}
        assert Attraction.query.filter_by(city="北京", name="故宫博物院").count() == 1
        assert Attraction.query.count() == 8
        assert AttractionGuide.query.count() == 8
