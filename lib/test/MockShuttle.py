import ShuttleService
import random
import datetime
from itertools import cycle
from typing import List, Tuple


class MockShuttle:
    STOPS_BY_ROUTE_ID = {4004706: [4211460, 4132090, 4208462], 4011456: [4208464, 4111538, 4211462, 4151398, 4220780, 4211464, 4211466, 4132090],
                         4011458: [4220778, 4220774, 4132090], 4011460: [4220776, 4151398, 4220780, 4211466, 4132090, 4208464, 4111538, 4211462, 4211464]}

    def __init__(self):
        self.id = random.randrange(100000, 200000)
        self.route_id = random.choice(list(MockShuttle.STOPS_BY_ROUTE_ID))
        self.timestamp = datetime.datetime.now().astimezone(datetime.timezone(datetime.timedelta(seconds=0)))

        self._stops = cycle(MockShuttle.STOPS_BY_ROUTE_ID[self.route_id])
        self._ss = ShuttleService.ShuttleService(307)

    @property
    def position(self) -> Tuple[float, float]:
        if random.random() < 0.10:
            return self._ss.get_stop(self._stops.__next__()).position
        return 40.737898, -74.037995

    def __str__(self):
        return f'ID: {self.id}, Route ID: {self.route_id}'


class MockShuttleManager:
    @classmethod
    def shuttles(cls) -> List[MockShuttle]:
        random_shuttles = []
        for _ in range(random.randrange(3, 6)):
            random_shuttles.append(MockShuttle())
        return random_shuttles
