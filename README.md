# Mapview

Mapview is a Kivy widget for displaying interactive maps. It has been
designed with lot of inspirations of
[Libchamplain](https://wiki.gnome.org/Projects/libchamplain) and
[Leaflet](http://leafletjs.com/). 

The goal of this widget is to be a replacement of Google Maps widget,
even if this one works very well, it just works on Android with Kivy.
I wanted a map widget that can support custom map, and designed with
the latests state-of-the-art Kivy's methods.

![ScreenShot](https://raw.github.com/kivy-garden/garden.mapview/master/screenshot.png)

# Features

* native multitouch handling (one for translate, many for translate and zoom)
* asynchronous downloading
* avoided GPU limitation / float precisions issues on tiles coordinates
* marker support
* blazing fast!

# Requirements

It requires the `concurrent.futures` and `requests`. If you are on python 2.7,
you can use `futures`:

```
pip install futures requests
```

# Usage

This widget can be either used within Python or Kv. That's said, not
everything can be done in Kv, to prevent too much computing.

```python
from kivy.garden.mapview import MapView
from kivy.app import App

class MapViewApp(App):
    def build(self):
        mapview = MapView(zoom=19)
        # center the current view to Lille, France
        mapview.center_on(50.6394, 3.057)
        # or set a zoom at a position on the screen
        mapview.set_zoom_at(18, 50., 50.)
        return mapview

MapViewApp().run()
```

More extensive documentation will come soon.
