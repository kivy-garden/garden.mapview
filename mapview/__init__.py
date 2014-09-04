# coding=utf-8
"""
MapView
=======

.. author:: Mathieu Virbel <mat@kivy.org>

MapView is a Kivy widget that display maps.
"""

__all__ = ["MapView", "MapSource", "MapMarker", "MapLayer", "MarkerMapLayer"]
__version__ = "0.2"

MIN_LATITUDE = -90.
MAX_LATITUDE = 90.
MIN_LONGITUDE = -180.
MAX_LONGITUDE = 180.
CACHE_DIR = "cache"

from mapview.types import Coordinate
from mapview.source import MapSource
from mapview.view import MapView, MapMarker, MapLayer, MarkerMapLayer
