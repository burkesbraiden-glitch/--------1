import json

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import ExplorationPlan
from app.services.route_plan_generation import (
    RoutePlanGenerationError,
    generate_exploration_plans_from_route,
)
from tests.test_route_plan_generation_service import generation_db, seed_generation_context


def make_competing_plan(data):
    return ExplorationPlan(
        user_id=data['owner'].id,
        child_id=data['child_a'].id,
        route_stop_id=data['first_stop'].id,
        title='竞争请求已生成的计划',
        destination=data['first_attraction'].name,
        age_group=data['child_a'].age_group,
        duration='60分钟',
        interests=['保留原有兴趣'],
        status='ready',
        source_snapshot={'schemaVersion': 1, 'winner': 'other-request'},
    )


def test_integrity_error_retries_once_and_recovers_existing_mixed_batch_in_request_order(app, generation_db, monkeypatch):
    with app.app_context():
        data = seed_generation_context()
        original_commit = db.session.commit
        original_rollback = db.session.rollback
        commits = 0
        competing_plan = make_competing_plan(data)

        def race_commit():
            nonlocal commits
            commits += 1
            if commits == 1:
                original_rollback()
                db.session.add(competing_plan)
                original_commit()
                raise IntegrityError('insert exploration_plans', {}, Exception('duplicate route stop child'))
            original_commit()

        monkeypatch.setattr(db.session, 'commit', race_commit)

        result = generate_exploration_plans_from_route(
            data['owner'],
            data['route'].id,
            data['child_a'].id,
            [data['first_stop'].id, data['second_stop'].id],
        )

        assert commits == 2
        assert [(item['routeStopId'], item['result']) for item in result['results']] == [
            (data['first_stop'].id, 'existing'),
            (data['second_stop'].id, 'created'),
        ]
        assert result['results'][0]['plan'].id == competing_plan.id
        assert result['results'][0]['plan'].source_snapshot == {'schemaVersion': 1, 'winner': 'other-request'}
        assert [plan.route_stop_id for plan in ExplorationPlan.query.order_by(ExplorationPlan.route_stop_id)] == [
            data['first_stop'].id,
            data['second_stop'].id,
        ]
        assert json.loads(json.dumps(result['results'][0]['plan'].source_snapshot)) == {
            'schemaVersion': 1,
            'winner': 'other-request',
        }


def test_second_integrity_error_rolls_back_without_partial_write_or_unbounded_retry(app, generation_db, monkeypatch):
    with app.app_context():
        data = seed_generation_context()
        original_rollback = db.session.rollback
        commits = 0
        rollbacks = 0

        def always_conflict():
            nonlocal commits
            commits += 1
            raise IntegrityError('insert exploration_plans', {}, Exception('duplicate route stop child'))

        def track_rollback():
            nonlocal rollbacks
            rollbacks += 1
            original_rollback()

        monkeypatch.setattr(db.session, 'commit', always_conflict)
        monkeypatch.setattr(db.session, 'rollback', track_rollback)

        with pytest.raises(RoutePlanGenerationError) as error:
            generate_exploration_plans_from_route(
                data['owner'], data['route'].id, data['child_a'].id,
                [data['first_stop'].id, data['second_stop'].id],
            )

        assert error.value.code == 'DATABASE_ERROR'
        assert error.value.status_code == 500
        assert commits == 2
        assert rollbacks == 2
        assert ExplorationPlan.query.count() == 0


def test_non_integrity_database_error_does_not_retry(app, generation_db, monkeypatch):
    with app.app_context():
        data = seed_generation_context()
        original_rollback = db.session.rollback
        commits = 0
        rollbacks = 0

        def fail_commit():
            nonlocal commits
            commits += 1
            raise SQLAlchemyError('database unavailable')

        def track_rollback():
            nonlocal rollbacks
            rollbacks += 1
            original_rollback()

        monkeypatch.setattr(db.session, 'commit', fail_commit)
        monkeypatch.setattr(db.session, 'rollback', track_rollback)

        with pytest.raises(RoutePlanGenerationError) as error:
            generate_exploration_plans_from_route(
                data['owner'], data['route'].id, data['child_a'].id, [data['first_stop'].id],
            )

        assert error.value.code == 'DATABASE_ERROR'
        assert commits == 1
        assert rollbacks == 1
        assert ExplorationPlan.query.count() == 0
