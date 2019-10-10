import sys
from kivy.base import runTouchApp

if __name__ == '__main__' and __package__ is None:
    from os import path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from mapview import MapView, MapSource

kwargs = {}
if len(sys.argv) > 1:
    kwargs["map_source"] = MapSource(url=sys.argv[1], attribution="")

runTouchApp(MapView(**kwargs))
