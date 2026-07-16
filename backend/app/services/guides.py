from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import GuideCard
from app.services.guide_generator import generate_guide_content
from app.services.plans import PlanError, format_datetime, get_plan_model_for_user


ALLOWED_GENERATE_STATUSES = {"ready", "in-progress", "completed"}


class GuideError(Exception):
    def __init__(self, code, message, status_code):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def serialize_guide(guide):
    return {
        "id": guide.id,
        "planId": guide.plan_id,
        "destination": guide.plan.destination,
        "childIntro": guide.child_intro or [],
        "questions": guide.questions or [],
        "focusItems": guide.focus_items or [],
        "audioUrl": guide.audio_url,
        "createdAt": format_datetime(guide.created_at),
        "updatedAt": format_datetime(guide.updated_at),
    }


def get_guide_model(plan):
    return GuideCard.query.filter_by(plan_id=plan.id).first()


def sqlite_next_guide_id():
    if db.engine.dialect.name != "sqlite":
        return None
    max_id = db.session.query(db.func.max(GuideCard.id)).scalar()
    return (max_id or 0) + 1


def get_guide(user, plan_id):
    plan = get_plan_model_for_user(user, plan_id)
    guide = get_guide_model(plan)
    if guide is None:
        raise GuideError("GUIDE_NOT_FOUND", "Guide not found", 404)
    return serialize_guide(guide)


def generate_guide(user, plan_id):
    plan = get_plan_model_for_user(user, plan_id)
    if plan.status not in ALLOWED_GENERATE_STATUSES:
        raise GuideError("PLAN_NOT_READY", "Plan not ready", 409)

    existing = get_guide_model(plan)
    if existing is not None:
        return serialize_guide(existing), False

    content = generate_guide_content(plan)
    guide = GuideCard(
        id=sqlite_next_guide_id(),
        plan_id=plan.id,
        child_intro=content["child_intro"],
        questions=content["questions"],
        focus_items=content["focus_items"],
        audio_url=content["audio_url"],
    )

    try:
        db.session.add(guide)
        db.session.commit()
        return serialize_guide(guide), True
    except IntegrityError:
        db.session.rollback()
        existing = get_guide_model(plan)
        if existing is not None:
            return serialize_guide(existing), False
        raise GuideError("DATABASE_ERROR", "Database error", 500)
    except SQLAlchemyError:
        db.session.rollback()
        raise GuideError("DATABASE_ERROR", "Database error", 500)
