from typing import Dict, List

import requests
import threading


class BadResponse(Exception):
    """The response code was unexpected"""
    pass


class ObjectNotFound(Exception):
    """Could not find the desired object"""
    pass


class ShuttleService:
    _BASE_URL = 'https://feeds.transloc.com/3/'

    def __init__(self, agency_id: int):
        """
        Initialize a shuttle service session for the given agency ID
        :param agency_id: The agency ID
        """
        self.session = requests.session()
        self.agency_id = agency_id

    def get_routes(self) -> List[Dict]:
        """
        Get all routes for the current shuttle agency
        :return: A list of all routes
        """
        return self._generic_request('routes')['routes']

    def get_stops(self) -> List[Dict]:
        """
        Get details on all stops for the current shuttle agency
        :return: A list of all stops
        """
        return self._generic_request('stops')['stops']

    def get_vehicle_statuses(self) -> List[Dict]:
        """
        Get details on all currently active vehicles
        :return: A list of all currently active vehicles
        """
        return self._generic_request('vehicle_statuses')['vehicles']

    def get_stop_ids_for_route(self, route_id: int) -> List[Dict]:
        """
        Get stop IDs for the given route ID
        :param route_id: The route ID
        :return: A list of stop IDs
        :raises ObjectNotFound: if the route ID could not be found
        """
        for route in self._generic_request('stops', params={'include_routes': True})['routes']:
            if route['id'] == route_id:
                return route['stops']
        raise ObjectNotFound(f'Route ID {route_id} not found')

    def _generic_request(self, endpoint: str, params: Dict = None, method: str = 'GET', timeout: int = 10, **kwargs) -> Dict:
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


class Shuttle:
    def __init__(self, update_rate: int):
        """
        Representation of a TransLoc shuttle which keeps itself updated
        """
        pass
