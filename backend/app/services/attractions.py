from sqlalchemy import or_

from app.models import Attraction


DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class AttractionError(Exception):
    def __init__(self, code, message, status_code):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def serialize_attraction(attraction):
    return {
        "id": attraction.id,
        "name": attraction.name,
        "city": attraction.city,
        "district": attraction.district,
        "address": attraction.address,
        "summary": attraction.summary,
        "tags": attraction.tags or [],
        "recommendedDurationMinutes": attraction.recommended_duration_minutes,
        "coverImage": attraction.cover_image,
    }


def serialize_attraction_guide(guide):
    return {
        "id": guide.id,
        "attractionId": guide.attraction_id,
        "overview": guide.overview,
        "highlights": guide.highlights or [],
        "visitTips": guide.visit_tips or [],
        "familyTips": guide.family_tips or [],
    }


def _validate_pagination(limit, offset):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
        raise AttractionError("VALIDATION_ERROR", "limit must be an integer from 1 to 100", 400)
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise AttractionError("VALIDATION_ERROR", "offset must be a non-negative integer", 400)


def _trim_optional_string(value, field_name):
    if value is None:
        return None
    if not isinstance(value, str):
        raise AttractionError("VALIDATION_ERROR", f"{field_name} must be a string", 400)
    return value.strip() or None


def list_attractions(city=None, keyword=None, limit=DEFAULT_LIMIT, offset=0):
    _validate_pagination(limit, offset)
    city = _trim_optional_string(city, "city")
    keyword = _trim_optional_string(keyword, "keyword")

    query = Attraction.query.filter_by(is_active=True)
    if city is not None:
        query = query.filter(Attraction.city == city)
    if keyword is not None:
        pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                Attraction.name.ilike(pattern),
                Attraction.summary.ilike(pattern),
            )
        )

    total = query.count()
    attractions = (
        query.order_by(Attraction.city.asc(), Attraction.name.asc(), Attraction.id.asc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return {
        "items": [serialize_attraction(attraction) for attraction in attractions],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _get_active_attraction(attraction_id):
    attraction = Attraction.query.filter_by(id=attraction_id, is_active=True).first()
    if attraction is None:
        raise AttractionError("ATTRACTION_NOT_FOUND", "Attraction not found", 404)
    return attraction


def get_attraction(attraction_id):
    return serialize_attraction(_get_active_attraction(attraction_id))


def get_attraction_guide(attraction_id):
    attraction = _get_active_attraction(attraction_id)
    if attraction.guide is None:
        raise AttractionError("ATTRACTION_GUIDE_NOT_FOUND", "Attraction guide not found", 404)
    return serialize_attraction_guide(attraction.guide)
