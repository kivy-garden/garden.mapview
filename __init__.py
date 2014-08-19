# coding=utf-8
"""
MapView
=======

.. author:: Mathieu Virbel <mat@kivy.org>

MapView is a Kivy widget that display maps.
"""

__all__ = ["MapView", "MapSource"]
__version__ = "0.1"

from os.path import join, exists, dirname
from os import makedirs
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.properties import NumericProperty, ObjectProperty
from kivy.graphics import Canvas, Color, Rectangle, PushMatrix, Translate, \
    PopMatrix
from math import cos, ceil, log, tan, pi, atan, exp
from random import choice
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
import requests
from kivy.lang import Builder
from kivy.compat import string_types


MIN_LATITUDE = -90.
MAX_LATITUDE = 90.
MIN_LONGITUDE = -180.
MAX_LONGITUDE = 180.
MAX_WORKERS = 5
CACHE_DIR = "cache"


Builder.load_string("""
<MapView>:
    canvas.before:
        StencilPush
        Rectangle:
            pos: self.pos
            size: self.size
        StencilUse
    canvas.after:
        StencilUnUse
        Rectangle:
            pos: self.pos
            size: self.size
        StencilPop

<MapMarker>:
    size_hint: None, None
    size: "48dp", "48dp"
    source: root.default_marker_fn

""")


def clamp(x, minimum, maximum):
    return max(minimum, min(x, maximum))


class Downloader(object):
    _instance = None

    @staticmethod
    def instance():
        if Downloader._instance is None:
            Downloader._instance = Downloader()
        return Downloader._instance

    def __init__(self):
        super(Downloader, self).__init__()
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        self._futures = []
        Clock.schedule_interval(self._check_executor, 1 / 60.)
        if not exists(CACHE_DIR):
            makedirs(CACHE_DIR)

    def download_tile(self, tile):
        future = self.executor.submit(self._load_tile, tile)
        self._futures.append(future)

    def download(self, url, callback, **kwargs):
        future = self.executor.submit(self._download_url, url, callback, kwargs)
        self._futures.append(future)

    def _download_url(self, url, callback, kwargs):
        r = requests.get(url, **kwargs)
        return callback, (url, r, )

    def _load_tile(self, tile):
        if tile.state == "done":
            return
        cache_fn = tile.cache_fn
        if exists(cache_fn):
            return setattr, (tile, "source", cache_fn)
        tile_y = tile.map_source.get_row_count(tile.zoom) - tile.tile_y - 1
        uri = tile.map_source.url.format(z=tile.zoom, x=tile.tile_x, y=tile_y,
                              s=choice(tile.map_source.subdomains))
        #print "Download {}".format(uri)
        data = requests.get(uri, timeout=5).content
        with open(cache_fn, "wb") as fd:
            fd.write(data)
        #print "Downloaded {} bytes: {}".format(len(data), uri)
        return setattr, (tile, "source", cache_fn)

    def _check_executor(self, dt):
        try:
            for future in as_completed(self._futures[:], 0):
                self._futures.remove(future)
                try:
                    result = future.result()
                except:
                    import traceback; traceback.print_exc()
                    # make an error tile?
                    continue
                if result is None:
                    continue
                callback, args = result
                callback(*args)
        except TimeoutError:
            pass


class Tile(Rectangle):
    @property
    def cache_fn(self):
        map_source = self.map_source
        fn = map_source.cache_fmt.format(
            image_ext=map_source.image_ext,
            cache_key=map_source.cache_key,
            **self.__dict__)
        return join(CACHE_DIR, fn)


class MapSource(object):
    # list of available providers
    # cache_key: (is_overlay, minzoom, maxzoom, url, attribution)
    providers = {
        "osm": (0, 0, 19, "http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            ""),
        "osm-hot": (0, 0, 19, "http://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
            ""),
        "osm-de": (0, 0, 18, "http://{s}.tile.openstreetmap.de/tiles/osmde/{z}/{x}/{y}.png",
            "Tiles @ OSM DE"),
        "osm-fr": (0, 0, 20, "http://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png",
            "Tiles @ OSM France"),
        "cyclemap": (0, 0, 17, "http://{s}.tile.opencyclemap.org/cycle/{z}/{x}/{y}.png",
            "Tiles @ Andy Allan"),
        "openseamap": (0, 0, 19, "http://tiles.openseamap.org/seamark/{z}/{x}/{y}.png",
            "Map data @ OpenSeaMap contributors"),
        "thunderforest-cycle": (0, 0, 19, "http://{s}.tile.thunderforest.com/cycle/{z}/{x}/{y}.png",
            "@ OpenCycleMap via OpenStreetMap"),
        "thunderforest-transport": (0, 0, 19, "http://{s}.tile.thunderforest.com/transport/{z}/{x}/{y}.png",
            "@ OpenCycleMap via OpenStreetMap"),
        "thunderforest-landscape": (0, 0, 19, "http://{s}.tile.thunderforest.com/landscape/{z}/{x}/{y}.png",
            "@ OpenCycleMap via OpenStreetMap"),
        "thunderforest-outdoors": (0, 0, 19, "http://{s}.tile.thunderforest.com/outdoors/{z}/{x}/{y}.png",
            "@ OpenCycleMap via OpenStreetMap"),
        "mapquest-osm": (0, 0, 19, "http://otile{s}.mqcdn.com/tiles/1.0.0/map/{z}/{x}/{y}.jpeg",
            "Tiles Courtesy of Mapquest", {"subdomains": "1234", "image_ext": "jpeg"}),
        "mapquest-aerial": (0, 0, 19, "http://oatile{s}.mqcdn.com/tiles/1.0.0/sat/{z}/{x}/{y}.jpeg",
            "Tiles Courtesy of Mapquest", {"subdomains": "1234", "image_ext": "jpeg"}),
        # more to add with
        # https://github.com/leaflet-extras/leaflet-providers/blob/master/leaflet-providers.js
    }

    def __init__(self,
        url="http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        cache_key="osm", min_zoom=0, max_zoom=19, tile_size=256,
        image_ext="png", attribution="", subdomains="abc"):
        super(MapSource, self).__init__()
        self.url = url
        self.cache_key = cache_key
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom
        self.tile_size = tile_size
        self.image_ext = image_ext
        self.attribution = attribution
        self.subdomains = subdomains
        self.cache_fmt = "{cache_key}_{zoom}_{tile_x}_{tile_y}.{image_ext}"

    @staticmethod
    def from_provider(key):
        provider = MapSource.providers[key]
        options = {}
        is_overlay, min_zoom, max_zoom, url, attribution = provider[:5]
        if len(provider) > 5:
            options = provider[5]
        return MapSource(cache_key=key, min_zoom=min_zoom,
                         max_zoom=max_zoom, url=url, attribution=attribution,
                         **options)

    def get_x(self, zoom, lon):
        """Get the x position on the map using this map source's projection
        (0, 0) is located at the top left.
        """
        lon = clamp(lon, MIN_LONGITUDE, MAX_LONGITUDE)
        return ((lon + 180.) / 360. * pow(2., zoom)) * self.tile_size

    def get_y(self, zoom, lat):
        """Get the y position on the map using this map source's projection
        (0, 0) is located at the top left.
        """
        lat = clamp(-lat, MIN_LATITUDE, MAX_LATITUDE)
        lat = lat * pi / 180.
        return ((1.0 - log(tan(lat) + 1.0 / cos(lat)) / pi) / \
            2. * pow(2., zoom)) * self.tile_size

    def get_lon(self, zoom, x):
        """Get the longitude to the x position in the map source's projection
        """
        dx = x / float(self.tile_size)
        lon = dx / pow(2., zoom) * 360. - 180.
        return clamp(lon, MIN_LONGITUDE, MAX_LONGITUDE)

    def get_lat(self, zoom, y):
        """Get the latitude to the y position in the map source's projection
        """
        dy = y / float(self.tile_size)
        n = pi - 2 * pi * dy / pow(2., zoom)
        lat = -180. / pi * atan(.5 * (exp(n) - exp(-n)))
        return clamp(lat, MIN_LATITUDE, MAX_LATITUDE)

    def get_row_count(self, zoom):
        """Get the number of tiles in a row at this zoom level
        """
        if zoom == 0:
            return 1
        return 2 << (zoom - 1)

    def get_col_count(self, zoom):
        """Get the number of tiles in a col at this zoom level
        """
        if zoom == 0:
            return 1
        return 2 << (zoom - 1)

    def get_min_zoom(self):
        """Return the minimum zoom of this source
        """
        return 0

    def get_max_zoom(self):
        """Return the maximum zoom of this source
        """
        return 19

    def fill_tile(self, tile):
        """Add this tile to load within the downloader
        """
        if tile.state == "done":
            return
        if exists(tile.cache_fn):
            tile.source = tile.cache_fn
        else:
            Downloader.instance().download_tile(tile)


class MapMarker(Image):
    anchor_x = NumericProperty(0.5)
    anchor_y = NumericProperty(0)
    lat = NumericProperty(0)
    lon = NumericProperty(0)

    @property
    def default_marker_fn(self):
        return join(dirname(__file__), "icons", "marker.png")


class MapLayer(Widget):
    viewport_x = NumericProperty(0)
    viewport_y = NumericProperty(0)

    def reposition(self):
        pass


class MarkerMapLayer(MapLayer):

    def reposition(self):
        mapview = self.parent
        set_marker_position = self.set_marker_position
        for marker in self.children:
            set_marker_position(mapview, marker)

    def set_marker_position(self, mapview, marker):
        x = mapview.map_source.get_x(mapview.zoom, marker.lat)
        y = mapview.map_source.get_y(mapview.zoom, marker.lon)
        marker.x = int(x - marker.width * marker.anchor_x)
        marker.y = int(y - marker.height * marker.anchor_y)


class MapView(Widget):
    lon = NumericProperty()
    lat = NumericProperty()
    zoom = NumericProperty(5)
    map_source = ObjectProperty(MapSource())
    viewport_x = NumericProperty(0)
    viewport_y = NumericProperty(0)

    __events__ = ["on_map_relocated"]

    # Public API

    def unload(self):
        """Unload the view and all the layers.
        It also cancel all the remaining downloads.
        """
        self.remove_all_tiles()

    def center_on(self, lat, lon):
        """Center the map on the coordinate (lat, lon)
        """
        map_source = self.map_source
        zoom = self.zoom
        lon = clamp(lon, MIN_LONGITUDE, MAX_LONGITUDE)
        lat = clamp(lat, MIN_LATITUDE, MAX_LATITUDE)
        x = map_source.get_x(zoom, lon) - self.width / 2.
        y = map_source.get_y(zoom, lat) - self.height / 2.
        self._update_coords(x, y)
        self.remove_all_tiles()
        self.load_visible_tiles(False)

    def set_zoom_at(self, zoom, x, y):
        """Sets the zoom level, leaving the (x, y) at the exact same point
        in the view.
        """
        zoom = clamp(zoom,
                     self.map_source.get_min_zoom(),
                     self.map_source.get_max_zoom())
        if zoom == self.zoom:
            return

        x, y = self._get_x_y_for_zoom_level(zoom, x, y)
        self.zoom = zoom
        self._update_coords(x, y)
        self.remove_all_tiles()
        self.load_visible_tiles(False)

    def get_latlon_at(self, x, y, zoom=None):
        """Return the current (lat, lon) within the (x, y) widget coordinate
        """
        if zoom is None:
            zoom = self.zoom
        return (
            self.map_source.get_lat(zoom, y + self.viewport_y),
            self.map_source.get_lon(zoom, x + self.viewport_x))

    def add_marker(self, marker, layer=None):
        """Add a marker into the layer. If layer is None, it will be added in
        the default marker layer. If there is no default marker layer, a new
        one will be automatically created
        """
        if layer is None:
            if not self._default_marker_layer:
                layer = MarkerMapLayer()
                self.add_layer(layer)
            else:
                layer = self._default_marker_layer
        layer.add_widget(marker)
        layer.set_marker_position(self, marker)

    def remove_marker(self, marker):
        """Remove a marker from its layer
        """
        marker.detach()

    def add_layer(self, layer):
        """Add a new layer to update at the same time the base tile layer
        """
        if self._default_marker_layer is None and \
            isinstance(layer, MarkerMapLayer):
            self._default_marker_layer = layer
        self._layers.append(layer)
        c = self.canvas
        self.canvas = self.canvas_layers
        super(MapView, self).add_widget(layer)
        self.canvas = c

    def remove_layer(self, layer):
        """Remove the layer
        """
        self._layers.remove(layer)
        self.canvas = self.canvas_layers
        super(MapView, self).remove_widget(layer)
        self.canvas = c

    def sync_to(self, other):
        """Reflect the lat/lon/zoom of the other MapView to the current one.
        """
        if self.zoom != other.zoom:
            self.set_zoom_at(other.zoom, *self.center)
        self.center_on(*other.get_latlon_at(*self.center))


    # Private API

    def __init__(self, **kwargs):
        from kivy.base import EventLoop
        EventLoop.ensure_window()
        self.canvas = Canvas()
        with self.canvas:
            PushMatrix()
            self.g_translate = Translate()
            self.canvas_map = Canvas()
            self.canvas_layers = Canvas()
            PopMatrix()
        self._tiles = []
        self._tilemap = {}
        self._layers = []
        self._default_marker_layer = None
        super(MapView, self).__init__(**kwargs)

    def add_widget(self, widget):
        if isinstance(widget, MapMarker):
            self.add_marker(widget)
        elif isinstance(widget, MapLayer):
            self.add_layer(widget)
        else:
            super(MapView, self).add_widget(widget)

    def remove_widget(self, widget):
        if isinstance(widget, MapMarker):
            self.remove_marker(widget)
        elif isinstance(widget, MapLayer):
            self.remove_layer(widget)
        else:
            super(MapView, self).remove_widget(widget)

    def _get_x_y_for_zoom_level(self, zoom, x, y):
        deltazoom = pow(2, zoom - self.zoom)
        nx = (self.viewport_x + x) * deltazoom - x
        ny = (self.viewport_y + y) * deltazoom - y
        return nx, ny

    def on_map_relocated(self, zoom, lat, lon):
        pass

    def on_viewport_x(self, instance, value):
        p = self.g_translate.xy
        self.g_translate.xy = (self.x -int(value), p[1])

    def on_viewport_y(self, instance, value):
        p = self.g_translate.xy
        self.g_translate.xy = (p[0], self.y -int(value))

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return
        d = None
        if "button" in touch.profile and touch.button in ("scrolldown", "scrollup"):
            d = 1 if touch.button == "scrollup" else -1
        elif touch.is_double_tap:
            d = 1
        if d is not None:
            self.set_zoom_at(self.zoom + d, touch.x, touch.y)
        else:
            touch.grab(self)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return
        self._update_coords(
            self.viewport_x - touch.dx,
            self.viewport_y - touch.dy)
        self.load_visible_tiles(True)
        return True

    def _update_coords(self, x, y):
        zoom = self.zoom
        self.viewport_x = x
        self.viewport_y = y
        self.lon = self.map_source.get_lon(zoom, x + self.width / 2.)
        self.lat = self.map_source.get_lat(zoom, y + self.height / 2.)
        for layer in self._layers:
            layer.reposition()
        self.dispatch("on_map_relocated", self.zoom, self.lon, self.lat)

    def load_visible_tiles(self, relocate=False):
        map_source = self.map_source
        zoom = self.zoom
        dirs = [0, 1, 0, -1, 0]

        size = map_source.tile_size
        max_x_end = map_source.get_col_count(zoom)
        max_y_end = map_source.get_row_count(zoom)
        x_count = int(ceil(self.width / float(size))) + 1
        y_count = int(ceil(self.height / float(size))) + 1

        tile_x_first = int(clamp(self.viewport_x / float(size), 0, max_x_end))
        tile_y_first = int(clamp(self.viewport_y / float(size), 0, max_y_end))
        tile_x_last = tile_x_first + x_count
        tile_y_last = tile_y_first + y_count
        tile_x_last = int(clamp(tile_x_last, tile_x_first, max_x_end))
        tile_y_last = int(clamp(tile_y_last, tile_y_first, max_y_end))

        x_count = tile_x_last - tile_x_first
        y_count = tile_y_last - tile_y_first

        #print "Range {},{} to {},{}".format(
        #    tile_x_first, tile_y_first,
        #    tile_x_last, tile_y_last)

        # Get rid of old tiles first
        for tile in self._tiles[:]:
            tile_x = tile.tile_x
            tile_y = tile.tile_y
            if tile_x < tile_x_first or tile_x >= tile_x_last or \
               tile_y < tile_y_first or tile_y >= tile_y_last:
                tile.state = "done"
                self.tile_map_set(tile_x, tile_y, False)
            elif relocate:
                tile.pos = (tile_x * size, tile_y * size)

        # Load new tiles if needed
        x = tile_x_first + x_count / 2 - 1
        y = tile_y_first + y_count / 2 - 1
        arm_max = max(x_count, y_count) + 2
        arm_size = 1
        turn = 0
        while arm_size < arm_max:
            for i in range(arm_size):
                if not self.tile_in_tile_map(x, y) and \
                   y >= tile_y_first and y < tile_y_last and \
                   x >= tile_x_first and x < tile_x_last:
                    self.load_tile(x, y, size, zoom)

                x += dirs[turn % 4 + 1]
                y += dirs[turn % 4]

            if turn % 2 == 1:
                arm_size += 1

            turn += 1

    def load_tile(self, x, y, size, zoom):
        map_source = self.map_source
        if self.tile_in_tile_map(x, y) or zoom != self.zoom:
            return
        self.load_tile_for_source(self.map_source, 1., size, x, y)
        # XXX do overlay support
        self.tile_map_set(x, y, True)

    def load_tile_for_source(self, map_source, opacity, size, x, y):
        tile = Tile(size=(size, size))
        tile.tile_x = x
        tile.tile_y = y
        tile.zoom = self.zoom
        tile.pos = (x * size, y * size)
        tile.map_source = map_source
        tile.state = "loading"
        map_source.fill_tile(tile)
        self.canvas_map.add(tile)
        self._tiles.append(tile)

    def remove_all_tiles(self):
        self.canvas_map.clear()
        for tile in self._tiles:
            tile.state = "done"
        del self._tiles[:]
        self._tilemap = {}

    def tile_map_set(self, tile_x, tile_y, value):
        key = tile_y * self.map_source.get_col_count(self.zoom) + tile_x
        if value:
            self._tilemap[key] = value
        else:
            self._tilemap.pop(key, None)

    def tile_in_tile_map(self, tile_x, tile_y):
        key = tile_y * self.map_source.get_col_count(self.zoom) + tile_x
        return key in self._tilemap

    def on_size(self, instance, size):
        for layer in self._layers:
            layer.size = size
        self.remove_all_tiles()
        self.load_visible_tiles(False)
        self.center_on(self.lon, self.lat)

    def on_map_source(self, instance, source):
        if isinstance(source, string_types):
            self.map_source = MapSource.from_provider(source)
        elif isinstance(source, (tuple, list)):
            cache_key, min_zoom, max_zoom, url, attribution, options = source
            self.map_source = MapSource(url=url, cache_key=cache_key,
                                        min_zoom=min_zoom, max_zoom=max_zoom,
                                        attribution=attribution, **options)
        elif isinstance(source, MapSource):
            self.map_source = source
        else:
            raise Exception("Invalid map source provider")
        self.zoom = clamp(self.zoom,
                          self.map_source.min_zoom, self.map_source.max_zoom)
        self.remove_all_tiles()
        self.load_visible_tiles()

if __name__ == "__main__":
    from kivy.base import runTouchApp
    from kivy.lang import Builder
    try:
        root = Builder.load_string("""
#:import MapSource __main__.MapSource

<Toolbar@BoxLayout>:
    size_hint_y: None
    height: '48dp'
    padding: '4dp'
    spacing: '4dp'

    canvas:
        Color:
            rgba: .2, .2, .2, .6
        Rectangle:
            pos: self.pos
            size: self.size

<ShadedLabel@Label>:
    size: self.texture_size
    canvas.before:
        Color:
            rgba: .2, .2, .2, .6
        Rectangle:
            pos: self.pos
            size: self.size

RelativeLayout:

    MapView:
        id: mapview
        lon: 50.6394
        lat: 3.057
        zoom: 15

        on_map_relocated: mapview2.sync_to(self)
        on_map_relocated: mapview3.sync_to(self)

        MapMarker:
            lon: 50.6394
            lat: 3.057

    MapView:
        id: mapview2
        size_hint: None, None
        size: 256, 256
        map_source: "osm-hot"
        center_y: root.center_y
        center_x: root.width / 4.

        ShadedLabel:
            text: "OSM Hot"
            pos: mapview2.pos

    MapView:
        id: mapview3
        size_hint: None, None
        size: 256, 256
        map_source: "thunderforest-transport"
        center_y: root.center_y
        center_x: (root.width / 4.) * 3

        ShadedLabel:
            text: "Thunderforest Transport"
            pos: mapview3.pos

    Toolbar:
        top: root.top
        Button:
            text: "Move to Lille, France"
            on_release: mapview.center_on(50.6394, 3.057)
        Button:
            text: "Move to Sydney, Autralia"
            on_release: mapview.center_on(-33.867, 151.206)
        Spinner:
            text: "mapnik"
            values: MapSource.providers.keys()
            on_text: mapview.map_source = self.text

    Toolbar:
        Label:
            text: "Longitude: {}".format(mapview.lon)
        Label:
            text: "Latitude: {}".format(mapview.lat)
        """)
        runTouchApp(root)
    finally:
        #root.ids.mapview.unload()
        pass
