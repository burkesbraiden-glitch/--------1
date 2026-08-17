import pytest
from sqlalchemy import JSON
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Attraction, AttractionGuide


@pytest.fixture()
def attraction_db(app):
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def make_attraction(attraction_id, *, name="故宫博物院", city="北京"):
    return Attraction(
        id=attraction_id,
        name=name,
        city=city,
        district="东城区",
        summary="在宫殿建筑中观察历史与礼仪。",
        tags=["历史", "古建筑"],
    )


def make_guide(guide_id, attraction_id):
    return AttractionGuide(
        id=guide_id,
        attraction_id=attraction_id,
        overview="从建筑细节开始亲子探索。",
        highlights=["屋顶", "宫门"],
        visit_tips=["提前规划参观顺序"],
        family_tips=["让孩子挑选一个细节记录"],
    )


def test_attraction_columns_constraints_and_json_defaults():
    table = Attraction.__table__

    assert set(table.c.keys()) == {
        "id",
        "name",
        "city",
        "district",
        "address",
        "summary",
        "tags",
        "recommended_duration_minutes",
        "cover_image",
        "is_active",
        "created_at",
        "updated_at",
    }
    assert table.c.id.primary_key is True
    assert table.c.name.nullable is False
    assert table.c.name.index is True
    assert table.c.city.nullable is False
    assert table.c.city.index is True
    assert isinstance(table.c.tags.type, JSON)
    assert table.c.tags.default.arg(None) == []
    assert table.c.tags.default.arg(None) is not table.c.tags.default.arg(None)
    assert table.c.is_active.nullable is False
    assert table.c.is_active.index is True
    assert table.c.is_active.default.arg is True
    assert table.c.is_active.server_default is not None
    assert any(
        constraint.name == "city_name_unique" and {column.name for column in constraint.columns} == {"city", "name"}
        for constraint in table.constraints
    )


def test_attraction_guide_columns_and_one_to_one_relationship():
    table = AttractionGuide.__table__

    assert set(table.c.keys()) == {
        "id",
        "attraction_id",
        "overview",
        "highlights",
        "visit_tips",
        "family_tips",
        "created_at",
        "updated_at",
    }
    assert table.c.attraction_id.nullable is False
    assert table.c.attraction_id.unique is True
    assert table.c.attraction_id.index is True
    assert list(table.c.attraction_id.foreign_keys)[0].target_fullname == "attractions.id"
    assert list(table.c.attraction_id.foreign_keys)[0].ondelete == "CASCADE"
    assert Attraction.guide.property.mapper.class_ is AttractionGuide
    assert Attraction.guide.property.uselist is False
    assert AttractionGuide.attraction.property.mapper.class_ is Attraction
    assert AttractionGuide.attraction.property.back_populates == "guide"


def test_attraction_and_guide_can_be_created_and_linked(app, attraction_db):
    with app.app_context():
        attraction = make_attraction(1)
        db.session.add(attraction)
        db.session.commit()
        db.session.add(make_guide(10, attraction.id))
        db.session.commit()

        assert db.session.get(Attraction, 1).guide.id == 10
        assert db.session.get(AttractionGuide, 10).attraction.id == 1


def test_duplicate_city_and_name_is_blocked(app, attraction_db):
    with app.app_context():
        db.session.add(make_attraction(1))
        db.session.commit()
        db.session.add(make_attraction(2))

        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_deleting_attraction_cascades_to_guide(app, attraction_db):
    with app.app_context():
        attraction = make_attraction(1)
        db.session.add(attraction)
        db.session.commit()
        db.session.add(make_guide(10, attraction.id))
        db.session.commit()

        db.session.delete(attraction)
        db.session.commit()

        assert AttractionGuide.query.count() == 0
