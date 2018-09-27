from typing import Dict, List

import requests


class BadResponse(Exception):
    """The response code was unexpected"""
    pass


class ObjectNotFound(Exception):
    """Could not find the desired object"""
    pass


class _GenericDictObj:
    def __init__(self, data: Dict):
        self.__dict__ = data


class Shuttle(_GenericDictObj):
    def __init__(self, data: Dict):
        super().__init__(data)
        self.next_stop = ShuttleService(self.agency_id).get_stops()
    pass


class Stop(_GenericDictObj):
    pass


class Route(_GenericDictObj):
    @property
    def stops(self):
        return ShuttleService(self.agency_id).get_stop_ids_for_route(self.id)


class ShuttleService:
    _BASE_URL = 'https://feeds.transloc.com/3/'

    def __init__(self, agency_id: int):
        """
        Initialize a shuttle service session for the given agency ID
        :param agency_id: The agency ID
        """
        self.session = requests.session()
        self.agency_id = agency_id

    def get_routes(self, key_filter: Dict = None) -> List[Route]:
        """
        Get all routes for the current shuttle agency
        :return: A list of all routes
        """
        return [Route(r) for r in self._generic_request('routes')['routes']]

    def get_stops(self, key_filter: Dict = None) -> List[Stop]:
        """
        Get details on all stops for the current shuttle agency
        :return: A list of all stops
        """
        return [Stop(s) for s in self._generic_request('stops')['stops']]

    def get_vehicle_statuses(self, key_filter: Dict = None) -> List[Shuttle]:
        """
        Get details on all currently active vehicles
        :return: A list of all currently active vehicles
        """
        raw_resp = self._generic_request('vehicle_statuses')['vehicles']
        return [Shuttle(v) for v in raw_resp]

    def get_stop_ids(self, key_filter: Dict = None) -> List[Dict]:
        """
        Get stop IDs for the current shuttle agency
        :param key_filter: A dictionary to filter the results by. See _filter_results for details
        :return: A list of stop IDs
        :raises ObjectNotFound: if the route ID could not be found
        """
        return ShuttleService._filter_results(self._generic_request('stops', params={'include_routes': True})['routes'], key_filter)

    @classmethod
    def _filter_results(cls, results: List[Dict], key_filter: Dict) -> List[Dict]:
        """
        Filter the results list of dicts by the key-value pairs in the key_filter dict
        :param results: The list of dicts to filter
        :param key_filter: The dict to filter with
        :return: A list where each item is a dict whose key-value pairs are at least equal to the key-value pairs
        in the key_filter dict.
        """
        if key_filter is None or len(key_filter) == 0:
            return results

        filtered_results = []
        for result in results:
            if all(result.get(key) == value for key, value in key_filter.items()):
                filtered_results.append(result)
        return filtered_results

    def _generic_request(self, endpoint: str, params: Dict = None, method: str = 'GET',
                         timeout: int = 10, **kwargs) -> Dict:
        """
        Send a request to the transloc api
        :param endpoint: The endpoint to query
        :param params: The params to send
        :param method: The method to form the request as
        :param timeout: The request timeout
        :param kwargs: kwargs passed to the request
        :return: The JSON response
        :raises TimeoutError: If the request times out
        :raises BadResponse: If the response status code is greater than 200
        :raises ValueError: If the response is not valid JSON
        """
        if params is None:
            params = {}
        params['agencies'] = self.agency_id

        try:
            res = self.session.request(method, f'{self._BASE_URL}{endpoint}', params=params, timeout=timeout, **kwargs)
        except requests.exceptions.Timeout:
            raise TimeoutError(f'{method} request timed out for {endpoint}{method} ({timeout} seconds)')

        if res.status_code > 200:
            raise BadResponse(res.status_code)

        try:
            return res.json()
        except ValueError:
            raise ValueError(f'{method} request for {endpoint}{method} was not valid JSON')
