# coding=utf-8
"""
Geojson layer
=============

.. note::

    Currently experimental and a work in progress. It requires the new
    Kivy's Tesselator, based on libtess2. See
    `tesselator branch <https://github.com/kivy/kivy/tree/tesselator>`_
"""

__all__ = ["GeoJsonMapLayer"]


import json
from kivy.properties import StringProperty, ObjectProperty
from mapview.view import MapLayer
from mapview.downloader import Downloader


def flatten(l):
    return [item for sublist in l for item in sublist]


class GeoJsonMapLayer(MapLayer):

    source = StringProperty()
    geojson = ObjectProperty()
    #features = ListProperty()

    def reposition(self):
        if self.geojson:
            print "Reload geojson"
            self.on_geojson(self, self.geojson)

    def on_geojson(self, instance, geojson):
        if self.parent is None:
            return
        #self.features = []
        self.canvas.clear()
        self._geojson_part(geojson)

    def on_source(self, instance, value):
        if value.startswith("http://") or value.startswith("https://"):
            Downloader.instance().download(value, self._load_geojson_url)
        else:
            with open(fn, "rb") as fd:
                geojson = json.load(fd)
            self.geojson = geojson

    def _load_geojson_url(self, url, r):
        self.geojson = r.json()

    def _geojson_part(self, part):
        tp = part["type"]
        if tp == "FeatureCollection":
            for feature in part["features"]:
                self._geojson_part_f(feature)
        elif tp == "Feature":
            self._geojson_part_f(part)
        else:
            # unhandled geojson part
            pass

    def _geojson_part_f(self, feature):
        properties = feature["properties"]
        geometry = feature["geometry"]
        graphics = self._geojson_part_geometry(geometry)
        for g in graphics:
            self.canvas.add(g)

    def _geojson_part_geometry(self, geometry):
        from kivy.graphics import Mesh, Line, Color
        from kivy.graphics.tesselator import Tesselator, WINDING_ODD, TYPE_POLYGONS
        tp = geometry["type"]
        graphics = []
        if tp == "Polygon":
            tess = Tesselator()
            for c in geometry["coordinates"]:
                xy = list(self._lonlat_to_xy(c))
                xy = flatten(xy)
                tess.add_contour(xy)

            tess.tesselate(WINDING_ODD, TYPE_POLYGONS)

            graphics.append(Color(1, 0, 0, .5))
            for vertices in tess.meshes:
                indices = range(len(vertices) / 4)
                graphics.append(Mesh(
                    vertices=vertices, indices=indices, mode="triangle_fan"))

        return graphics

    def _lonlat_to_xy(self, lonlats):
        view = self.parent
        map_source = view.map_source
        zoom = view.zoom
        dx = view.delta_x
        dy = view.delta_y
        for lon, lat in lonlats:
            yield (map_source.get_x(zoom, lon) + dx, map_source.get_y(zoom, lat) + dy)
