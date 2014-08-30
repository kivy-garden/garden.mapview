from mapview import MapView
from mapview.geojson import GeoJsonMapLayer
from kivy.base import runTouchApp
import sys

if len(sys.argv) > 1:
    source = sys.argv[1]
else:
    source = "https://storage.googleapis.com/maps-devrel/google.json"

view = MapView()
layer = GeoJsonMapLayer(source=source)
view.add_layer(layer)

runTouchApp(view)
