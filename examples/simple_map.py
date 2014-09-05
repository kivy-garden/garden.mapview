import sys
from mapview import MapView, MapSource
from kivy.base import runTouchApp

kwargs = {}
if len(sys.argv) > 1:
    import hashlib
    url = sys.argv[1]
    key = hashlib.sha224(url).hexdigest()[:10]
    kwargs["map_source"] = MapSource(url=url, cache_key=key, attribution="")

runTouchApp(MapView(**kwargs))
