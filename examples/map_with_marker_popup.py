import sys
from kivy.base import runTouchApp
from kivy.lang import Builder

if __name__ == '__main__' and __package__ is None:
    from os import path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import mapview

root = Builder.load_string("""
#:import sys sys
#:import MapSource mapview.MapSource
MapView:
    lat: 50.6394
    lon: 3.057
    zoom: 13
    map_source: MapSource(sys.argv[1], attribution="") if len(sys.argv) > 1 else "osm"

    MapMarkerPopup:
        lat: 50.6394
        lon: 3.057
        popup_size: dp(230), dp(130)

        Bubble:
            BoxLayout:
                orientation: "horizontal"
                padding: "5dp"
                AsyncImage:
                    source: "http://upload.wikimedia.org/wikipedia/commons/9/9d/France-Lille-VieilleBourse-FacadeGrandPlace.jpg"
                    mipmap: True
                Label:
                    text: "[b]Lille[/b]\\n1 154 861 hab\\n5 759 hab./km2"
                    markup: True
                    halign: "center"

""")

runTouchApp(root)
