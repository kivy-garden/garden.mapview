from mapview import MapView
from mapview.geojson import GeoJsonMapLayer
from kivy.base import runTouchApp

view = MapView()
layer = GeoJsonMapLayer(source="https://storage.googleapis.com/maps-devrel/google.json")
view.add_layer(layer)

runTouchApp(view)
