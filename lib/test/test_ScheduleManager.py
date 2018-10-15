import os

import pytest

import ShuttleService
import ScheduleManager


pytest.skip('Need to integrate gen_schedules.py', allow_module_level=True)


class TestScheduleManager:
    sm = ScheduleManager.ScheduleManager(307, os.path.join(os.getcwd(), 'schedules', 'generated'), 'America/New_York')

    def test_get_route_name(self):
        ss = ShuttleService.ShuttleService(307)

        TestScheduleManager.sm.get_route_name(ss.get_routes()[0].id)

        with pytest.raises(ScheduleManager.UnknownRoute):
            TestScheduleManager.sm.get_route_name(1)

    def test_stops_by_route(self):
        assert isinstance(TestScheduleManager.sm.stops_by_route(), dict)

    def test_validate_stop(self):
        assert TestScheduleManager.sm.validate_stop(1, 1)
        assert not TestScheduleManager.sm.validate_stop(1, 1)
        assert TestScheduleManager.sm.validate_stop(2, 1)
        assert TestScheduleManager.sm.validate_stop(2, 2)

    @pytest.mark.skip(reason='Undergoing rewrite')
    def test_paper_schedules(self):
        assert True

    @pytest.mark.skip(reason='Undergoing rewrite')
    def test_get_nearest_time(self):
        assert True
