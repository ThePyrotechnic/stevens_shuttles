import ShuttleService


class TestShuttleService:
    def test_get_routes(self):
        ss = ShuttleService.ShuttleService(307)
        assert type(ss.get_routes()) == list

    def test_get_stops(self):
        ss = ShuttleService.ShuttleService(307)
        assert type(ss.get_stops()) == list

    def test_get_shuttle_statuses(self):
        ss = ShuttleService.ShuttleService(307)
        assert type(ss.get_shuttle_statuses()) == list

    def test_get_stop_ids_for_routes(self):
        ss = ShuttleService.ShuttleService(307)
        assert type(ss.get_stop_ids_for_routes()) == dict
