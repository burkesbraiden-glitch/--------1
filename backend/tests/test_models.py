from sqlalchemy import CheckConstraint

from app import create_app
from app.extensions import db
from app.models import Child, User


def test_metadata_uses_stable_naming_convention():
    convention = db.metadata.naming_convention

    assert convention["ix"] == "ix_%(table_name)s_%(column_0_name)s"
    assert convention["uq"] == "uq_%(table_name)s_%(column_0_name)s"
    assert convention["ck"] == "ck_%(table_name)s_%(constraint_name)s"
    assert convention["fk"] == "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
    assert convention["pk"] == "pk_%(table_name)s"


def test_user_and_child_tables_are_registered():
    create_app("testing")

    assert "users" in db.metadata.tables
    assert "children" in db.metadata.tables


def test_user_columns_and_login_constraints():
    table = User.__table__

    assert "age" not in table.c
    assert table.c.id.primary_key is True
    assert table.c.phone.nullable is True
    assert table.c.phone.unique is True
    assert table.c.phone.index is True
    assert table.c.wechat_openid.nullable is True
    assert table.c.wechat_openid.unique is True
    assert table.c.wechat_openid.index is True
    assert table.c.nickname.nullable is False
    assert table.c.city.nullable is True
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False

    check_sql = {
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "phone IS NOT NULL OR wechat_openid IS NOT NULL" in check_sql


def test_child_columns_and_constraints():
    table = Child.__table__

    assert table.c.id.primary_key is True
    assert table.c.user_id.nullable is False
    assert table.c.user_id.index is True
    assert table.c.name.nullable is False
    assert table.c.age.nullable is False
    assert table.c.city.nullable is True
    assert table.c.age_group.nullable is False
    assert table.c.interests.nullable is False
    assert table.c.is_default.nullable is False
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False

    check_sql = {
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "age >= 0 AND age <= 18" in check_sql
    assert "age_group IN ('3-6', '7-12')" in check_sql


def test_child_user_foreign_key_uses_delete_cascade():
    foreign_keys = list(Child.__table__.c.user_id.foreign_keys)

    assert len(foreign_keys) == 1
    foreign_key = foreign_keys[0]
    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.ondelete == "CASCADE"


def test_user_child_relationships_are_configured():
    assert User.children.property.mapper.class_ is Child
    assert Child.user.property.mapper.class_ is User
    assert "delete-orphan" in User.children.property.cascade
    assert Child.user.property.back_populates == "children"
