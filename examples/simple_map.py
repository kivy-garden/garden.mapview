import sys
from mapview import MapView, MapSource
from kivy.base import runTouchApp

kwargs = {}
if len(sys.argv) > 1:
    kwargs["map_source"] = MapSource(url=sys.argv[1], attribution="")

runTouchApp(MapView(**kwargs))
