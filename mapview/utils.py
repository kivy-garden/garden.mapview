# coding=utf-8

__all__ = ["clamp"]

from math import radians, cos, sin, asin, sqrt, log


def clamp(x, minimum, maximum):
    return max(minimum, min(x, maximum))


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)

    Taken from: http://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2

    c = 2 * asin(sqrt(a))
    km = 6367 * c
    return km


def get_zoom_for_radius(radius):
    # not super accurate, sorry
    radius = radius * 1000
    equatorLength = 40075004
    widthInPixels = 1024
    metersPerPixel = equatorLength / 256
    zoomLevel = 1
    while metersPerPixel * widthInPixels > radius:
        metersPerPixel /= 2
        zoomLevel += 1
    return zoomLevel - 1
