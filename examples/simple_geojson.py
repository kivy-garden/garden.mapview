from kivy.base import runTouchApp
import sys

if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from mapview import MapView
from mapview.geojson import GeoJsonMapLayer

if len(sys.argv) > 1:
    source = sys.argv[1]
else:
    source = "https://storage.googleapis.com/maps-devrel/google.json"

view = MapView()
layer = GeoJsonMapLayer(source=source)
view.add_layer(layer)

runTouchApp(view)
