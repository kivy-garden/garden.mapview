# coding=utf-8
"""
MBTiles provider for MapView
============================

This provider is based on .mbfiles from MapBox.
See: http://mbtiles.org/
"""

__all__ = ["MBTilesMapSource"]


from mapview.source import MapSource
from mapview.downloader import Downloader
from kivy.core.image import Image as CoreImage, ImageLoader
import threading
import sqlite3
import io


class MBTilesMapSource(MapSource):
    def __init__(self, filename):
        super(MBTilesMapSource, self).__init__()
        self.filename = filename
        self.db = sqlite3.connect(filename)

        # read metadata
        c = self.db.cursor()
        metadata = dict(c.execute("SELECT * FROM metadata"))
        self.min_zoom = int(metadata["minzoom"])
        self.max_zoom = int(metadata["maxzoom"])
        self.attribution = metadata["attribution"]
        center = metadata["center"].split(",")
        self.default_lat = float(center[0])
        self.default_lon = float(center[1])
        self.default_zoom = int(center[2])

    def fill_tile(self, tile):
        if tile.state == "done":
            return
        Downloader.instance().submit(self._load_tile, tile)

    def _load_tile(self, tile):
        # global db context cannot be shared across threads.
        ctx = threading.local()
        if not hasattr(ctx, "db"):
            ctx.db = sqlite3.connect(self.filename)

        # get the right tile
        c = ctx.db.cursor()
        c.execute(
            ("SELECT tile_data FROM tiles WHERE "
            "zoom_level=? AND tile_column=? AND tile_row=?"),
            (tile.zoom, tile.tile_x, tile.tile_y))
        row = c.fetchone()
        if not row:
            tile.state = "done"
            return

        # no-file loading
        # XXX this must be pushed in kivy somehow.
        # Not all loaders supports buffer-based loading, so it might just fail.
        im = None
        data = io.BytesIO(row[0])
        for loader in ImageLoader.loaders:
            try:
                # try loading raw image
                im = loader(data, nocache=True)
                break
            except:
                import traceback
                traceback.print_exc()

        if im is None:
            tile.state = "done"
            return

        return self._load_tile_done, (tile, im, )

    def _load_tile_done(self, tile, im):
        # XXX internal kivy cache doesn't support ByteIO object yet. >_>
        im.filename = "{}.{}.{}.png".format(tile.zoom, tile.tile_x, tile.tile_y)
        tile.texture = im.texture
        tile.state = "need-animation"
