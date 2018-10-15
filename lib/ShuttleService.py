from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple

import requests
import pytz


class BadResponse(Exception):
    """The response code was unexpected"""
    pass


class ObjectNotFound(Exception):
    """Could not find the desired object"""
    pass


class _GenericDictObj:
    def __init__(self, data: Dict):
        self.__dict__ = data


class Stop(_GenericDictObj):
    def __init__(self, data: Dict):
        super().__init__(data)
        self.position = tuple(self.position)

    def at_stop(self, point: Tuple[float, float], box_size: int) -> bool:
        """
        Check if the point is within a square of width box_size centered at this stop's position
        :param point: The point to check
        :param box_size: The width and height of the box to check in meters
        :return: True if the point is considered at the stop, False otherwise
        """
        # multiply by 0.00001 since 0.00001 is ~1 meter in geographic coordinates
        width = box_size / 2 * 0.00001
        if self.position[0] - width <= point[0] <= self.position[0] + width and \
                self.position[1] - width <= point[1] <= self.position[1] + width:
            return True
        return False

    def __str__(self):
        return f'<ID: {self.id}, Name: {self.name}>'

    def __repr__(self):
        return self.__str__()


class Route(_GenericDictObj):
    pass


class Shuttle(_GenericDictObj):
    """
    A single shuttle
    :note: Use a ShuttleService to work with many shuttles in real-time
    """

    def __init__(self, data: Dict, detailed: bool = False):
        """
        Creates a shuttle object from a JSON response
        :param data: the data to use
        :param detailed: whether to convert self.next_stop to a Stop object, and retrieve self.stop_ids and self.stops.
        Setting detailed to True may pull newer data than is indicated by self.timestamp
        """
        super().__init__(data)
        self._ss = None
        if detailed:
            self._ss = ShuttleService(self.agency_id)
            try:
                self.next_stop = self._ss.get_stop(self.next_stop)
            except ObjectNotFound:
                self.next_stop = None
            self.stop_ids = self._ss.get_stop_ids_for_route(self.route_id)
            self.stops = self._ss.get_stops(key_filter={'id': self.stop_ids})

        self.position = tuple(self.position)
        self.timestamp = datetime.fromtimestamp(float(self.timestamp) / 1000, tz=pytz.utc)

    def update(self, detailed: bool = False):
        """
        Re-initialize this shuttle with updated information
        :param detailed: whether to convert self.next_stop to a Stop object, and retrieve self.stop_ids and self.stops.
        Setting detailed to True may pull newer data than is indicated by self.timestamp
        :return: None
        """
        if self._ss is None:
            self._ss = ShuttleService(self.agency_id)
        self.__init__(self._ss.get_shuttle_status(self.id, raw=True), detailed=detailed)


class ShuttleManager:
    """
    Used to keep track of a TransLoc shuttle service in real-time
    """

    def __init__(self, agency_id: int):
        self._ss = ShuttleService(agency_id)

    def shuttles(self, detailed: bool = False, key_filter: Dict = None) -> List[Shuttle]:
        """
        Get the currently active shuttles for the current service.
        Do not create references to shuttles unless you know what you are doing! They do not update themselves.
        :param detailed: whether to convert self.next_stop to a Stop object, and retrieve self.stop_ids and self.stops.
        Setting detailed to True may pull newer data than is indicated by self.timestamp
        :param key_filter: A dictionary to filter the shuttles by. See _filter_results for details
        :return: A list of the shuttles currently active for the current service
        """
        return self._ss.get_shuttle_statuses(detailed=detailed, key_filter=key_filter)


class ShuttleService:
    """
    Represents a TransLoc shuttle service.
    Use **kwargs to pass arguments directly to the web request
    """
    _BASE_URL = 'https://feeds.transloc.com/3/'

    def __init__(self, agency_id: int):
        """
        Initialize a shuttle service session for the given agency ID
        :param agency_id: The agency ID
        """
        self.session = requests.session()
        self.agency_id = agency_id

    def get_route(self, route_id: int, **kwargs):
        """
        Get a single route
        :param route_id: the ID of the route
        :param kwargs: additional kwargs are passed to the web request
        :return: The desired route
        :raises ObjectNotFound: if the route could not be found
        """
        try:
            return self.get_routes(key_filter={'id': route_id}, **kwargs)[0]
        except IndexError:
            raise ObjectNotFound(f'Route ID "{route_id} not found')

    def get_routes(self, key_filter: Dict = None, **kwargs) -> List[Route]:
        """
        Get all routes for the current shuttle agency
        :param key_filter: A dictionary to filter the results by. See _filter_results for details
        :param kwargs: additional kwargs are passed to the web request
        :return: A list of all routes
        """
        return [Route(r) for r in self._generic_request('routes', desired_key='routes', key_filter=key_filter, **kwargs)]

    def get_stop(self, stop_id: int, **kwargs):
        """
        Get a single stop
        :param stop_id: the ID of the stop
        :param kwargs: additional kwargs are passed to the web request
        :return: The desired stop
        :raises ObjectNotFound: if the stop could not be found
        """
        try:
            return self.get_stops(key_filter={'id': stop_id}, **kwargs)[0]
        except IndexError:
            raise ObjectNotFound(f'Stop ID "{stop_id} not found')

    def get_stops(self, key_filter: Dict = None, **kwargs) -> List[Stop]:
        """
        Get details on all stops for the current shuttle agency
        :param key_filter: A dictionary to filter the results by. See _filter_results for details
        :param kwargs: additional kwargs are passed to the web request
        :return: A list of all stops
        """
        return [Stop(s) for s in self._generic_request('stops', desired_key='stops', key_filter=key_filter, **kwargs)]

    def get_shuttle_status(self, shuttle_id: int, detailed: bool = False, raw: bool = False, **kwargs) -> [Shuttle, Dict]:
        """
        Get the status of a single shuttle
        :param shuttle_id: the ID of the shuttle
        :param detailed: whether to convert self.next_stop to a Stop object, and retrieve self.stop_ids and self.stops.
        Setting detailed to True may pull newer data than is indicated by self.timestamp
        :param raw: If true, do not convert the JSON into an object
        :param kwargs: additional kwargs are passed to the web request
        :return: the status of the shuttle
        :raises ObjectNotFound: if the shuttle status could not be found
        """
        try:
            return self.get_shuttle_statuses(key_filter={'id': shuttle_id}, detailed=detailed, raw=raw, **kwargs)[0]
        except IndexError:
            raise ObjectNotFound(f'Shuttle ID "{shuttle_id}" status not found')

    def get_shuttle_statuses(self, key_filter: Dict = None, detailed: bool = False, raw: bool = False, **kwargs) -> [List[Shuttle], List[Dict]]:
        """
        Get details on all currently active shuttles
        :param detailed: whether to convert self.next_stop to a Stop object, and retrieve self.stop_ids and self.stops.
        Setting detailed to True may pull newer data than is indicated by self.timestamp
        :param raw: If true, do not convert the JSON into an object
        :param key_filter: A dictionary to filter the results by. See _filter_results for details
        :param kwargs: additional kwargs are passed to the web request
        :return: A list of all currently active shuttles
        """
        if raw:
            return self._generic_request('vehicle_statuses', desired_key='vehicles', key_filter=key_filter, **kwargs)
        return [Shuttle(v, detailed=detailed) for v in self._generic_request('vehicle_statuses', desired_key='vehicles', key_filter=key_filter, **kwargs)]

    def get_stop_ids_for_route(self, route_id: int, **kwargs) -> List[int]:
        """
        Get stop IDs for a single route
        :param route_id: The route ID to get stops for
        :param kwargs: additional kwargs are passed to the web request
        :return: A list of route IDs
        """
        try:
            return self.get_stop_ids_for_routes(key_filter={'id': route_id}, **kwargs)[route_id]
        except IndexError:
            raise ObjectNotFound(f'Route ID "{route_id}" not found')

    def get_stop_ids_for_routes(self, key_filter: Dict = None, **kwargs) -> Dict[int, List]:
        """
        Get stop IDs by route for the current shuttle agency
        :param key_filter: A dictionary to filter the results by. See _filter_results for details
        :param kwargs: additional kwargs are passed to the web request
        :return: A dict mapping route IDs to stops
        """
        data = self._generic_request('stops', params={'include_routes': True}, desired_key='routes', key_filter=key_filter, **kwargs)

        ret = {}
        for d in data:
            ret[d['id']] = d['stops']

        return ret

    @classmethod
    def _filter_results(cls, results: List[Dict], key_filter: Dict) -> List[Dict]:
        """
        Filter the results list of dicts by the key-value pairs in the key_filter dict
        :param results: The list of dicts to filter
        :param key_filter: The dict to filter with
        :return: A list where each item is a dict whose key-value pairs are at least equal to the key-value pairs
        in the key_filter dict. If a value in key_filter is a list, at least one of the values must match.
        """
        if key_filter is None or not key_filter:
            return results

        filtered_results = []
        for result in results:
            if all(result.get(key) == value or (isinstance(value, list) and result.get(key) in value) for key, value in key_filter.items()):
                filtered_results.append(result)
        return filtered_results

    def _generic_request(self, endpoint: str, params: Dict = None, method: str = 'GET',
                         timeout: int = 10, desired_key: str = None, key_filter: Dict = None, **kwargs) -> [Dict, List[Dict]]:
        """
        Send a request to the transloc api
        :param endpoint: The endpoint to query
        :param params: The params to send
        :param method: The method to form the request as
        :param timeout: The request timeout
        :param desired_key: An optional key to return from the JSON response, instead of the entire JSON object
        :param key_filter: A dictionary to filter the results by. See _filter_results for details
        :param kwargs: kwargs passed to the web request
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
            if desired_key is not None:
                try:
                    response = res.json()[desired_key]
                except KeyError:
                    raise KeyError(f'Desired key "{desired_key}" was not found')
            else:
                response = res.json()
            if key_filter is not None:
                return ShuttleService._filter_results(response, key_filter)
            return response

        except ValueError:
            raise ValueError(f'{method} request for {endpoint}{method} was not valid JSON')
