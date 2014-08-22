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
from kivy.uix.scatter import Scatter
from kivy.properties import NumericProperty, ObjectProperty, AliasProperty
from kivy.graphics import Canvas, Color, Rectangle, PushMatrix, Translate, \
    PopMatrix
from kivy.graphics.transformation import Matrix
from math import cos, ceil, log, tan, pi, atan, exp
from random import choice
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
import requests
from kivy.lang import Builder
from kivy.compat import string_types
from kivy.metrics import dp
from time import time


MIN_LATITUDE = -90.
MAX_LATITUDE = 90.
MIN_LONGITUDE = -180.
MAX_LONGITUDE = 180.
MAX_WORKERS = 5
CACHE_DIR = "cache"


Builder.load_string("""
<MapMarker>:
    size_hint: None, None
    source: root.default_marker_fn
    size: dp(48) / self.scale, dp(48) / self.scale
    allow_stretch: True

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
            return tile.set_source, (cache_fn, )
        tile_y = tile.map_source.get_row_count(tile.zoom) - tile.tile_y - 1
        uri = tile.map_source.url.format(z=tile.zoom, x=tile.tile_x, y=tile_y,
                              s=choice(tile.map_source.subdomains))
        #print "Download {}".format(uri)
        data = requests.get(uri, timeout=5).content
        with open(cache_fn, "wb") as fd:
            fd.write(data)
        #print "Downloaded {} bytes: {}".format(len(data), uri)
        return tile.set_source, (cache_fn, )

    def _check_executor(self, dt):
        start = time()
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

                # capped executor in time, in order to prevent too much slowiness.
                # seems to works quite great with big zoom-in/out
                if time() - start > 120:
                    break
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

    def set_source(self, cache_fn):
        self.source = cache_fn
        self.state = "need-animation"


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
        self.dp_tile_size = min(dp(self.tile_size), self.tile_size * 2)

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
        return ((lon + 180.) / 360. * pow(2., zoom)) * self.dp_tile_size

    def get_y(self, zoom, lat):
        """Get the y position on the map using this map source's projection
        (0, 0) is located at the top left.
        """
        lat = clamp(-lat, MIN_LATITUDE, MAX_LATITUDE)
        lat = lat * pi / 180.
        return ((1.0 - log(tan(lat) + 1.0 / cos(lat)) / pi) / \
            2. * pow(2., zoom)) * self.dp_tile_size

    def get_lon(self, zoom, x):
        """Get the longitude to the x position in the map source's projection
        """
        dx = x / float(self.dp_tile_size)
        lon = dx / pow(2., zoom) * 360. - 180.
        return clamp(lon, MIN_LONGITUDE, MAX_LONGITUDE)

    def get_lat(self, zoom, y):
        """Get the latitude to the y position in the map source's projection
        """
        dy = y / float(self.dp_tile_size)
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
        Downloader.instance().download_tile(tile)


class MapMarker(Image):
    anchor_x = NumericProperty(0.5)
    anchor_y = NumericProperty(0)
    lat = NumericProperty(0)
    lon = NumericProperty(0)
    scale = NumericProperty(1.)

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
            marker.scale = mapview.scale
            set_marker_position(mapview, marker)

    def set_marker_position(self, mapview, marker):
        dx = mapview.delta_x
        dy = mapview.delta_y
        x = mapview.map_source.get_x(mapview.zoom, marker.lat) + dx
        y = mapview.map_source.get_y(mapview.zoom, marker.lon) + dy
        marker.x = int(x - marker.width * marker.anchor_x)
        marker.y = int(y - marker.height * marker.anchor_y)


class MapView(Scatter):
    lon = NumericProperty()
    lat = NumericProperty()
    zoom = NumericProperty(5)
    _zoom = NumericProperty(0)
    map_source = ObjectProperty(MapSource())
    delta_x = NumericProperty(0)
    delta_y = NumericProperty(0)

    def _get_viewport_pos(self):
        vx, vy = self.to_local(0, 0)
        return vx - self.delta_x, vy - self.delta_y

    viewport_pos = AliasProperty(_get_viewport_pos, None, bind=[
        "transform", "pos", "scale", "size"])

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
        zoom = self._zoom
        lon = clamp(lon, MIN_LONGITUDE, MAX_LONGITUDE)
        lat = clamp(lat, MIN_LATITUDE, MAX_LATITUDE)
        x = map_source.get_x(zoom, lon) - self.width / 2. / self.scale
        y = map_source.get_y(zoom, lat) - self.height / 2. / self.scale
        self.delta_x = -x
        self.delta_y = -y
        self.pos = 0, 0
        self.trigger_update(True)

    def set_zoom_at(self, zoom, x, y, scale=None):
        """Sets the zoom level, leaving the (x, y) at the exact same point
        in the view.
        """
        zoom = clamp(zoom,
                     self.map_source.get_min_zoom(),
                     self.map_source.get_max_zoom())
        if int(zoom) == int(self._zoom):
            return
        scale = scale or 1.

        # first, rescale the scatter
        scale = clamp(scale, self.scale_min, self.scale_max)
        rescale = scale * 1.0 / self.scale
        self.apply_transform(Matrix().scale(rescale, rescale, rescale),
                             post_multiply=True,
                             anchor=self.to_local(x, y))

        # adjust position if the zoom changed
        c1 = self.map_source.get_col_count(self._zoom)
        c2 = self.map_source.get_col_count(zoom)
        if c1 != c2:
            f = float(c2) / float(c1)
            self.delta_x = self.x + self.delta_x * f
            self.delta_y = self.y + self.delta_y * f
            # back to 0 every time
            self.apply_transform(Matrix().translate(
                -self.x, -self.y, 0
            ), post_multiply=True)

        # avoid triggering zoom changes.
        self._zoom = zoom
        self.zoom = self._zoom

    def on_zoom(self, instance, zoom):
        if zoom == self._zoom:
            return
        x = self.map_source.get_x(zoom, self.lon) - self.delta_x
        y = self.map_source.get_y(zoom, self.lat) - self.delta_y
        self.set_zoom_at(zoom, x, y)
        self.center_on(self.lon, self.lat)

    def get_latlon_at(self, x, y, zoom=None):
        """Return the current (lat, lon) within the (x, y) widget coordinate
        """
        if zoom is None:
            zoom = self._zoom
        vx, vy = self.viewport_pos
        return (
            self.map_source.get_lat(zoom, y + vx),
            self.map_source.get_lon(zoom, x + vy))

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
        if self._zoom != other._zoom:
            self.set_zoom_at(other._zoom, *self.center)
        self.center_on(*other.get_latlon_at(*self.center))


    # Private API

    def __init__(self, **kwargs):
        from kivy.base import EventLoop
        EventLoop.ensure_window()
        self.canvas = Canvas()
        with self.canvas:
            self.canvas_map = Canvas()
            self.canvas_layers = Canvas()
        self._tiles = []
        self._tiles_bg = []
        self._tilemap = {}
        self._layers = []
        self._default_marker_layer = None
        self._need_redraw_all = False
        self.trigger_update(True)
        Clock.schedule_interval(self._animate_color, 1 / 60.)
        super(MapView, self).__init__(**kwargs)

    def _animate_color(self, dt):
        for tile in self._tiles:
            if tile.state != "need-animation":
                continue
            tile.g_color.a += dt * 10.  # 100ms
            if tile.g_color.a >= 1:
                tile.state = "animated"
        for tile in self._tiles_bg:
            if tile.state != "need-animation":
                continue
            tile.g_color.a += dt * 10.  # 100ms
            if tile.g_color.a >= 1:
                tile.state = "animated"

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

    def _to_local(self, x, y, **kw):
        x, y = super(MapView, self).to_local(x, y, **kw)
        x += self.delta_x
        y += self.delta_y
        return x, y

    def _get_x_y_for_zoom_level(self, zoom, x, y):
        deltazoom = pow(2, zoom - self._zoom)
        vx, vy = self.viewport_pos
        nx = (vx + x) * deltazoom - x
        ny = (vy + y) * deltazoom - y
        return nx, ny

    def on_map_relocated(self, zoom, lat, lon):
        pass

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return
        if "button" in touch.profile and touch.button in ("scrolldown", "scrollup"):
            d = 1 if touch.button == "scrollup" else -1
            self.set_zoom_at(self._zoom + d, *touch.pos)
            return True
        elif touch.is_double_tap:
            """
            from kivy.animation import Animation
            scale = self.scale
            next_scale = 2 ** (self._zoom + 1)
            d = next_scale - scale
            def _on_progress(_, widget, progression):
                self.set_zoo_at(scale + progression * d, touch.x, touch.y)
                print _, widget, progression
            anim = Animation(d=.1, t="out_quad")
            anim.bind(on_progress=_on_progress)
            anim.start(self)
            """
            self.set_zoom_at(self._zoom + 1, *touch.pos)
            return True
        return super(MapView, self).on_touch_down(touch)

    def collide_point(self, x, y):
        #print "collide_point", x, y
        return True

    def on_transform(self, *args):
        ret = super(MapView, self).on_transform(*args)
        if not hasattr(self, "_blk"):
            self._blk = False
        if self._blk:
            return
        self._blk = True
        # recalculate viewport
        zoom = self._zoom
        scale = self.scale
        if self.scale > 2.:
            zoom += 1
            scale /= 2.
        elif self.scale < 1:
            zoom -= 1
            scale *= 2.
        zoom = clamp(zoom, self.map_source.min_zoom, self.map_source.max_zoom)
        if zoom != self._zoom:
            self.set_zoom_at(zoom, self.x, self.y, scale=scale)
            self.trigger_update(True)
        else:
            self.trigger_update(False)
        self._blk = False
        return ret

    def trigger_update(self, full):
        self._need_redraw_full = full or self._need_redraw_full
        Clock.unschedule(self.do_update)
        Clock.schedule_once(self.do_update, -1)

    def do_update(self, dt):
        zoom = self._zoom
        self.lon = self.map_source.get_lon(zoom, self.width / 2. - self.x - self.delta_x)
        self.lat = self.map_source.get_lat(zoom, self.height / 2. - self.y - self.delta_y)
        for layer in self._layers:
            layer.reposition()
        self.dispatch("on_map_relocated", zoom, self.lon, self.lat)

        if self._need_redraw_full:
            self._need_redraw_full = False
            self.remove_all_tiles()
            self.load_visible_tiles(False)
        else:
            self.load_visible_tiles(True)

    def load_visible_tiles(self, relocate=False):
        map_source = self.map_source
        vx, vy = self.viewport_pos
        zoom = self._zoom
        dirs = [0, 1, 0, -1, 0]

        size = map_source.dp_tile_size

        def bbox_for_zoom(vx, vy, w, h, zoom):
            max_x_end = map_source.get_col_count(zoom)
            max_y_end = map_source.get_row_count(zoom)

            x_count = int(ceil(w / self.scale / float(size))) + 1
            y_count = int(ceil(h / self.scale / float(size))) + 1

            tile_x_first = int(clamp(vx / float(size), 0, max_x_end))
            tile_y_first = int(clamp(vy / float(size), 0, max_y_end))
            tile_x_last = tile_x_first + x_count
            tile_y_last = tile_y_first + y_count
            tile_x_last = int(clamp(tile_x_last, tile_x_first, max_x_end))
            tile_y_last = int(clamp(tile_y_last, tile_y_first, max_y_end))

            x_count = tile_x_last - tile_x_first
            y_count = tile_y_last - tile_y_first
            return (tile_x_first, tile_y_first, tile_x_last, tile_y_last,
                    x_count, y_count)

        tile_x_first, tile_y_first, tile_x_last, tile_y_last, \
            x_count, y_count = bbox_for_zoom(vx, vy, self.width, self.height, zoom)

        #print "Range {},{} to {},{}".format(
        #    tile_x_first, tile_y_first,
        #    tile_x_last, tile_y_last)

        # Adjust tiles behind us
        for tile in self._tiles_bg[:]:
            tile_x = tile.tile_x
            tile_y = tile.tile_y

            f = 2 ** (zoom - tile.zoom)
            w = self.width / f
            h = self.height / f
            btile_x_first, btile_y_first, btile_x_last, btile_y_last, \
                _, _ = bbox_for_zoom(vx / f, vy / f, w, h, tile.zoom)

            if tile_x < btile_x_first or tile_x >= btile_x_last or \
               tile_y < btile_y_first or tile_y >= btile_y_last:
               tile.state = "done"
               self._tiles_bg.remove(tile)
               self.canvas_map.before.remove(tile.g_color)
               self.canvas_map.before.remove(tile)
               continue

            tsize = size * f
            tile.size = tsize, tsize
            tile.pos = (
                tile_x * tsize + self.delta_x,
                tile_y * tsize + self.delta_y)

        # Get rid of old tiles first
        for tile in self._tiles[:]:
            tile_x = tile.tile_x
            tile_y = tile.tile_y

            if tile_x < tile_x_first or tile_x >= tile_x_last or \
               tile_y < tile_y_first or tile_y >= tile_y_last:
                tile.state = "done"
                self.tile_map_set(tile_x, tile_y, False)
                self._tiles.remove(tile)
                self.canvas_map.remove(tile)
                self.canvas_map.remove(tile.g_color)
            elif relocate:
                tile.pos = (tile_x * size + self.delta_x, tile_y * size + self.delta_y)

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
        if self.tile_in_tile_map(x, y) or zoom != self._zoom:
            return
        self.load_tile_for_source(self.map_source, 1., size, x, y, zoom)
        # XXX do overlay support
        self.tile_map_set(x, y, True)

    def load_tile_for_source(self, map_source, opacity, size, x, y, zoom):
        tile = Tile(size=(size, size))
        tile.g_color = Color(1, 1, 1, 0)
        tile.tile_x = x
        tile.tile_y = y
        tile.zoom = zoom
        tile.pos = (x * size + self.delta_x, y * size + self.delta_y)
        tile.map_source = map_source
        tile.state = "loading"
        map_source.fill_tile(tile)
        self.canvas_map.add(tile.g_color)
        self.canvas_map.add(tile)
        self._tiles.append(tile)

    def remove_all_tiles(self):
        # remove all the tiles of the main map into the background map
        # only the one who are already loaded
        zoom = self._zoom
        tiles = self._tiles
        btiles = self._tiles_bg
        canvas_map = self.canvas_map
        while tiles:
            tile = tiles.pop()
            if tile.state == "loading":
                tile.state == "done"
                continue
            btiles.append(tile)

        self.canvas_map.clear()
        self.canvas_map.before.clear()
        for tile in btiles[:]:
            if tile.zoom == zoom:
                btiles.remove(tile)
                continue
            canvas_map.before.add(tile.g_color)
            canvas_map.before.add(tile)
        self._tilemap = {}
        print "btiles", len(btiles)

    def tile_map_set(self, tile_x, tile_y, value):
        key = tile_y * self.map_source.get_col_count(self._zoom) + tile_x
        if value:
            self._tilemap[key] = value
        else:
            self._tilemap.pop(key, None)

    def tile_in_tile_map(self, tile_x, tile_y):
        key = tile_y * self.map_source.get_col_count(self._zoom) + tile_x
        return key in self._tilemap

    def on_size(self, instance, size):
        for layer in self._layers:
            layer.size = size
        print "!!! size changed", size
        self.center_on(self.lon, self.lat)
        self.trigger_update(True)

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
        self.trigger_update(True)


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
        auto_bring_to_front: False
        do_rotation: False
        scale_min: 0.1
        lon: 50.6394
        lat: 3.057
        zoom: 8

        #on_map_relocated: mapview2.sync_to(self)
        #on_map_relocated: mapview3.sync_to(self)

        MapMarker:
            lon: 50.6394
            lat: 3.057

#     MapView:
#         id: mapview2
#         size_hint: None, None
#         size: 256, 256
#         map_source: "osm-hot"
#         center_y: root.center_y
#         center_x: root.width / 4.
#
#         ShadedLabel:
#             text: "OSM Hot"
#             pos: mapview2.pos
#
#     MapView:
#         id: mapview3
#         size_hint: None, None
#         size: 256, 256
#         map_source: "thunderforest-transport"
#         center_y: root.center_y
#         center_x: (root.width / 4.) * 3
#
#         ShadedLabel:
#             text: "Thunderforest Transport"
#             pos: mapview3.pos

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
