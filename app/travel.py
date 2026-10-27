"""Travel distance and time between points.

Default is straight line x ROAD_FACTOR (what fares already use). With
OSRM_URL set, road distance and time come from OSRM's table API. Any
error or timeout falls back to the straight-line numbers, so a request
never fails because of the map server."""
import json
import logging
import urllib.request

from . import config as C
from .matching import haversine

log = logging.getLogger("foodloop.travel")


def _key(p):
    return (round(p[0], 6), round(p[1], 6))


def _line(a, b):
    km = haversine(a[0], a[1], b[0], b[1]) * C.ROAD_FACTOR
    return km, km / C.AVG_SPEED_KMH * 60


def _osrm_table(pts):
    """(km matrix, minutes matrix) from OSRM, or None on any problem."""
    coords = ";".join(f"{p[1]},{p[0]}" for p in pts)
    url = (f"{C.OSRM_URL}/table/v1/driving/{coords}"
           "?annotations=distance,duration")
    try:
        with urllib.request.urlopen(url, timeout=C.OSRM_TIMEOUT_S) as r:
            d = json.load(r)
        if d.get("code") != "Ok":
            return None
        km = [[None if x is None else x / 1000 for x in row]
              for row in d["distances"]]
        mn = [[None if x is None else x / 60 for x in row]
              for row in d["durations"]]
        if any(x is None for row in km + mn for x in row):
            return None
        return km, mn
    except Exception as e:                       # never break a request
        log.warning("OSRM unavailable, using straight lines: %s", e)
        return None


class Travel:
    """Look up km / minutes between any two of the points given."""

    def __init__(self, points):
        pts = list(dict.fromkeys(_key(p) for p in points))
        self.idx = {p: i for i, p in enumerate(pts)}
        self.source = "haversine"
        self._km = self._mn = None
        if C.OSRM_URL and len(pts) > 1:
            got = _osrm_table(pts)
            if got:
                self._km, self._mn = got
                self.source = "osrm"

    def _pair(self, a, b):
        if self._km is not None:
            i, j = self.idx[_key(a)], self.idx[_key(b)]
            return self._km[i][j], self._mn[i][j]
        return _line(a, b)

    def km(self, a, b):
        return self._pair(a, b)[0]

    def minutes(self, a, b):
        return self._pair(a, b)[1]

    def path_km(self, pts):
        return sum(self.km(a, b) for a, b in zip(pts, pts[1:]))

    def path_minutes(self, pts):
        return sum(self.minutes(a, b) for a, b in zip(pts, pts[1:]))
