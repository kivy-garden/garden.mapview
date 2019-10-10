# coding=utf-8

__all__ = ["Downloader"]

from kivy.clock import Clock
from os.path import join, exists
from os import makedirs, environ
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from random import choice
import requests
import traceback
from time import time
from mapview import CACHE_DIR


DEBUG = "MAPVIEW_DEBUG_DOWNLOADER" in environ
# user agent is needed because since may 2019 OSM gives me a 429 or 403 server error
# I tried it with a simpler one (just Mozilla/5.0) this also gets rejected
USER_AGENT = 'Kivy-garden.mapview'


class Downloader(object):
    _instance = None
    MAX_WORKERS = 5
    CAP_TIME = 0.064  # 15 FPS

    @staticmethod
    def instance(cache_dir):
        if Downloader._instance is None:
            if not cache_dir:
                cache_dir = CACHE_DIR
            Downloader._instance = Downloader(cache_dir=cache_dir)
        return Downloader._instance

    def __init__(self, max_workers=None, cap_time=None, **kwargs):
        self.cache_dir = kwargs.get('cache_dir', CACHE_DIR)
        if max_workers is None:
            max_workers = Downloader.MAX_WORKERS
        if cap_time is None:
            cap_time = Downloader.CAP_TIME
        super(Downloader, self).__init__()
        self.is_paused = False
        self.cap_time = cap_time
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._futures = []
        Clock.schedule_interval(self._check_executor, 1 / 60.)
        if not exists(self.cache_dir):
            makedirs(self.cache_dir)

    def submit(self, f, *args, **kwargs):
        future = self.executor.submit(f, *args, **kwargs)
        self._futures.append(future)

    def download_tile(self, tile):
        if DEBUG:
            print("Downloader: queue(tile) zoom={} x={} y={}".format(
                tile.zoom, tile.tile_x, tile.tile_y))
        future = self.executor.submit(self._load_tile, tile)
        self._futures.append(future)

    def download(self, url, callback, **kwargs):
        if DEBUG:
            print("Downloader: queue(url) {}".format(url))
        future = self.executor.submit(
            self._download_url, url, callback, kwargs)
        self._futures.append(future)

    def _download_url(self, url, callback, kwargs):
        if DEBUG:
            print("Downloader: download(url) {}".format(url))
        r = requests.get(url, **kwargs)
        return callback, (url, r, )

    def _load_tile(self, tile):
        if tile.state == "done":
            return
        cache_fn = tile.cache_fn
        if exists(cache_fn):
            if DEBUG:
                print("Downloader: use cache {}".format(cache_fn))
            return tile.set_source, (cache_fn, )
        tile_y = tile.map_source.get_row_count(tile.zoom) - tile.tile_y - 1
        uri = tile.map_source.url.format(z=tile.zoom, x=tile.tile_x, y=tile_y,
                                         s=choice(tile.map_source.subdomains))
        if DEBUG:
            print("Downloader: download(tile) {}".format(uri))
        req = requests.get(uri, headers={'User-agent': USER_AGENT}, timeout=5)
        try:
            req.raise_for_status()
            data = req.content
            with open(cache_fn, "wb") as fd:
                fd.write(data)
            if DEBUG:
                print("Downloaded {} bytes: {}".format(len(data), uri))
            return tile.set_source, (cache_fn, )
        except Exception as e:
            print("Downloader error: {!r}".format(e))

    def _check_executor(self, dt):
        start = time()
        try:
            for future in as_completed(self._futures[:], 0):
                self._futures.remove(future)
                try:
                    result = future.result()
                except Exception:
                    traceback.print_exc()
                    # make an error tile?
                    continue
                if result is None:
                    continue
                callback, args = result
                callback(*args)

                # capped executor in time, in order to prevent too much
                # slowiness.
                # seems to works quite great with big zoom-in/out
                if time() - start > self.cap_time:
                    break
        except TimeoutError:
            pass
