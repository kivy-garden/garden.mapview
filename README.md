# Mapview

Mapview is a Kivy widget for displaying interactive maps. It has been
designed with lot of inspirations of
[Libchamplain](https://wiki.gnome.org/Projects/libchamplain) and
[Leaflet](http://leafletjs.com/).

The goal of this widget is to be a replacement of Google Maps widget,
even if this one works very well, it just works on Android with Kivy.
I wanted a map widget that can support custom map, and designed with
the latests state-of-the-art Kivy's methods.

![ScreenShot](https://cloud.githubusercontent.com/assets/37904/22764226/925c93ce-ee69-11e6-90ed-88123bfa731f.png)

![Marker clustering](https://cloud.githubusercontent.com/assets/37904/22764225/92516f12-ee69-11e6-99d5-6346e302766d.png)

# Features

* native multitouch (one for translate, many for translate and zoom)
* asynchronous downloading
* avoided GPU limitation / float precisions issues on tiles coordinates
* marker support
* blazing fast!
* supports Z/X/Y providers by default with `MapSource`
* supports [.mbtiles](http://mbtiles.org) via `MBTilesMapSource`
* supports marker clustering, via `ClusteredMarkerLayer`

# Requirements

It requires the `concurrent.futures` and `requests`. If you are on python 2.7,
you can use `futures`:

```
pip install futures requests
```

If you use it on Android / iOS, don't forget to add `openssl` as a requirements,
otherwise you'll have an issue when importing `urllib3` from `requests`.

# Install

Install the mapview garden module using the `garden` tool:

```
garden install mapview
```

# Usage

This widget can be either used within Python or Kv. That's said, not
everything can be done in Kv, to prevent too much computing.

```python
from kivy.garden.mapview import MapView
from kivy.app import App

class MapViewApp(App):
    def build(self):
        mapview = MapView(zoom=11, lat=50.6394, lon=3.057)
        return mapview

MapViewApp().run()
```

More extensive documentation will come soon.
