from sqlalchemy import CheckConstraint, JSON

from app import create_app
from app.extensions import db
from app.models import Child, ExplorationPlan, GuideCard, User


def _check_sql(table):
    return {
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }


def _assert_list_default(column):
    assert callable(column.default.arg)
    assert column.default.arg(None) == []
    assert column.default.arg(None) is not column.default.arg(None)


def test_plan_and_guide_tables_are_registered():
    create_app("testing")

    assert "exploration_plans" in db.metadata.tables
    assert "guide_cards" in db.metadata.tables


def test_exploration_plan_columns_and_constraints():
    table = ExplorationPlan.__table__

    assert set(table.c.keys()) == {
        "id",
        "user_id",
        "child_id",
        "title",
        "destination",
        "age_group",
        "duration",
        "interests",
        "status",
        "created_at",
        "updated_at",
    }
    assert "task_count" not in table.c
    assert table.c.id.primary_key is True
    assert table.c.user_id.nullable is False
    assert table.c.user_id.index is True
    assert table.c.child_id.nullable is False
    assert table.c.child_id.index is True
    assert table.c.title.nullable is False
    assert table.c.title.type.length == 120
    assert table.c.destination.nullable is False
    assert table.c.destination.type.length == 120
    assert table.c.age_group.nullable is False
    assert table.c.age_group.type.length == 16
    assert table.c.duration.nullable is False
    assert table.c.duration.type.length == 32
    assert table.c.interests.nullable is False
    assert isinstance(table.c.interests.type, JSON)
    _assert_list_default(table.c.interests)
    assert table.c.status.nullable is False
    assert table.c.status.type.length == 24
    assert table.c.status.default.arg == "draft"
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False

    check_sql = _check_sql(table)
    assert "age_group IN ('3-6', '7-12')" in check_sql
    assert "status IN ('draft', 'ready', 'in-progress', 'completed')" in check_sql


def test_exploration_plan_foreign_keys():
    user_foreign_keys = list(ExplorationPlan.__table__.c.user_id.foreign_keys)
    child_foreign_keys = list(ExplorationPlan.__table__.c.child_id.foreign_keys)

    assert len(user_foreign_keys) == 1
    assert user_foreign_keys[0].target_fullname == "users.id"
    assert user_foreign_keys[0].ondelete == "CASCADE"

    assert len(child_foreign_keys) == 1
    assert child_foreign_keys[0].target_fullname == "children.id"
    assert child_foreign_keys[0].ondelete == "RESTRICT"


def test_guide_card_columns_and_constraints():
    table = GuideCard.__table__

    assert set(table.c.keys()) == {
        "id",
        "plan_id",
        "child_intro",
        "questions",
        "focus_items",
        "audio_url",
        "created_at",
        "updated_at",
    }
    assert "destination" not in table.c
    for playback_field in ("audio_status", "is_playing", "is_paused", "play_state"):
        assert playback_field not in table.c

    assert table.c.id.primary_key is True
    assert table.c.plan_id.nullable is False
    assert table.c.plan_id.unique is True
    assert table.c.plan_id.index is True
    assert table.c.child_intro.nullable is False
    assert isinstance(table.c.child_intro.type, JSON)
    _assert_list_default(table.c.child_intro)
    assert table.c.questions.nullable is False
    assert isinstance(table.c.questions.type, JSON)
    _assert_list_default(table.c.questions)
    assert table.c.focus_items.nullable is False
    assert isinstance(table.c.focus_items.type, JSON)
    _assert_list_default(table.c.focus_items)
    assert table.c.audio_url.nullable is True
    assert table.c.audio_url.type.length == 500
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False


def test_guide_card_plan_foreign_key():
    foreign_keys = list(GuideCard.__table__.c.plan_id.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "exploration_plans.id"
    assert foreign_keys[0].ondelete == "CASCADE"


def test_plan_guide_relationship_is_one_to_zero_or_one():
    assert ExplorationPlan.guide_card.property.mapper.class_ is GuideCard
    assert ExplorationPlan.guide_card.property.uselist is False
    assert GuideCard.plan.property.mapper.class_ is ExplorationPlan
    assert GuideCard.plan.property.back_populates == "guide_card"


def test_user_child_plan_relationships_are_configured_without_child_delete_cascade():
    assert User.exploration_plans.property.mapper.class_ is ExplorationPlan
    assert User.exploration_plans.property.back_populates == "user"
    assert "delete-orphan" in User.exploration_plans.property.cascade

    assert Child.exploration_plans.property.mapper.class_ is ExplorationPlan
    assert Child.exploration_plans.property.back_populates == "child"
    assert "delete-orphan" not in Child.exploration_plans.property.cascade
    assert "delete" not in Child.exploration_plans.property.cascade

    assert ExplorationPlan.user.property.mapper.class_ is User
    assert ExplorationPlan.child.property.mapper.class_ is Child


def test_existing_user_and_child_model_fields_are_unchanged():
    assert set(User.__table__.c.keys()) == {
        "id",
        "phone",
        "nickname",
        "city",
        "wechat_openid",
        "created_at",
        "updated_at",
    }
    assert set(Child.__table__.c.keys()) == {
        "id",
        "user_id",
        "name",
        "age",
        "city",
        "age_group",
        "interests",
        "is_default",
        "created_at",
        "updated_at",
    }
