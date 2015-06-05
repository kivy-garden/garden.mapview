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
from kivy.graphics import Canvas, PushMatrix, PopMatrix, MatrixInstruction, Translate, Scale
from mapview.view import MapLayer
from mapview.downloader import Downloader


def flatten(l):
    return [item for sublist in l for item in sublist]


class GeoJsonMapLayer(MapLayer):

    source = StringProperty()
    geojson = ObjectProperty()
    #features = ListProperty()
    initial_zoom = None
    first_time = True

    def __init__(self, **kwargs):
        super(GeoJsonMapLayer, self).__init__(**kwargs)
        with self.canvas:
            self.canvas_polygon = Canvas()
            self.canvas_line = Canvas()
        with self.canvas_polygon.before:
            PushMatrix()
            self.g_matrix = MatrixInstruction()
            self.g_scale = Scale()
            self.g_translate = Translate()
        with self.canvas_polygon:
            self.g_canvas_polygon = Canvas()
        with self.canvas_polygon.after:
            PopMatrix()

    def reposition(self):
        vx, vy = self.parent.delta_x, self.parent.delta_y
        pzoom = self.parent.zoom
        zoom = self.initial_zoom
        if zoom is None:
            self.initial_zoom = zoom = pzoom
        if zoom != pzoom:
            diff = 2 ** (pzoom - zoom)
            vx /= diff
            vy /= diff
            self.g_scale.x = self.g_scale.y = diff
        else:
            self.g_scale.x = self.g_scale.y = 1.
        self.g_translate.xy = vx, vy
        self.g_matrix.matrix = self.parent._scatter.transform

        if self.geojson:
            update = not self.first_time
            self.on_geojson(self, self.geojson, update=update)
            self.first_time = False

    def on_geojson(self, instance, geojson, update=False):
        if self.parent is None:
            return
        if not update:
            # print "Reload geojson (polygon)"
            self.g_canvas_polygon.clear()
            self._geojson_part(geojson, geotype="Polygon")
        # print "Reload geojson (LineString)"
        self.canvas_line.clear()
        self._geojson_part(geojson, geotype="LineString")

    def on_source(self, instance, value):
        if value.startswith("http://") or value.startswith("https://"):
            Downloader.instance().download(value, self._load_geojson_url)
        else:
            with open(value, "rb") as fd:
                geojson = json.load(fd)
            self.geojson = geojson

    def _load_geojson_url(self, url, r):
        self.geojson = r.json()

    def _geojson_part(self, part, geotype=None):
        tp = part["type"]
        if tp == "FeatureCollection":
            for feature in part["features"]:
                if geotype and feature["geometry"]["type"] != geotype:
                    continue
                self._geojson_part_f(feature)
        elif tp == "Feature":
            if geotype and feature["geometry"]["type"] == geotype:
                self._geojson_part_f(part)
        else:
            # unhandled geojson part
            pass

    def _geojson_part_f(self, feature):
        properties = feature["properties"]
        geometry = feature["geometry"]
        graphics = self._geojson_part_geometry(geometry, properties)
        for g in graphics:
            tp = geometry["type"]
            if tp == "Polygon":
                self.g_canvas_polygon.add(g)
            else:
                self.canvas_line.add(g)

    def _geojson_part_geometry(self, geometry, properties):
        from kivy.graphics import Mesh, Line, Color
        from kivy.graphics.tesselator import Tesselator, WINDING_ODD, TYPE_POLYGONS
        from kivy.utils import get_color_from_hex
        from kivy.metrics import dp
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
            for vertices, indices in tess.meshes:
                graphics.append(Mesh(
                    vertices=vertices, indices=indices,
                    mode="triangle_fan"))

        elif tp == "LineString":
            stroke = get_color_from_hex(properties.get("stroke", "#ffffff"))
            stroke_width = dp(properties.get("stroke-width"))
            xy = list(self._lonlat_to_xy(geometry["coordinates"]))
            xy = flatten(xy)
            graphics.append(Color(*stroke))
            graphics.append(Line(points=xy, width=stroke_width))

        return graphics

    def _lonlat_to_xy(self, lonlats):
        view = self.parent
        zoom = view.zoom
        for lon, lat in lonlats:
            p = view.get_window_xy_from(lat, lon, zoom)
            p = p[0] - self.parent.delta_x, p[1] - self.parent.delta_y
            p = self.parent._scatter.to_local(*p)
            yield p
