.. Mapview documentation master file, created by
   sphinx-quickstart on Mon Aug 25 00:36:08 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Mapview's documentation!
===================================

:class:`MapView` is a Kivy widget specialized into tiles-based map rendering.

Requirements
------------

MapView is based on:

- `concurrent.futures <https://docs.python.org/3.4/library/concurrent.futures.html>`_:
  they are natives in Python 3.2. On previous Python
  version, you need to use `futures <https://pypi.python.org/pypi/futures>`_.
- `requests <https://pypi.python.org/pypi/requests>`_


Current limitations
-------------------

- :class:`MapMarker` are not yet selectable, it should come soon in a commit
- :class:`MarkerMapLayer` doesn't hide :class:`MapMarker` that are outside the
  map bounding box.
- The API is still moving, it may contain errors.
- Some providers can be slow or timeout. This is not an issue from MapView.
- If a tile is not correctly downloaded or missing from the provider, the error
  will be showed on the console, but nothing happen on the map itself. This can
  lead to a defect user experience.
- When leaving, `concurrent.futures` are joining all the threads created. It can
  stuck the application at a maximum time of 5 seconds (requests timeout). More
  if the network is unstable. There is no way to force it yet.
- The cache is not controlable, if the user move the map a lot, it can fill the
  disk easily. More control will be given later.

Usage
-----

If you use Kivy garden, you can import the widget like this::

    from kivy.garden.mapview import MapView, MarkerMap
    map = MapView()

You can customize the default zoom and center the view on Lille by::

    map = MapView(zoom=9, lon=50.6394, lat=3.057)

Then, you can create marker and place them on the map. Normally, anything that
goes on a map should go on a :class:`MapLayer`. Hopefully, the :class:`MapView`
give an API for adding marker directly, and creates a :class:`MarkerMapLayer`
if you did'nt created one yet::

    m1 = MapMarker(lon=50.6394, lat=3.057)  # Lille
    m2 = MapMarker(lon=-33.867, lat=151.206)  # Sydney
    map.add_marker(m1)
    map.add_marker(m2)

You can also change the providers by:

1. using a provider key::

    map.map_source = "mapquest-osm"

2. using a new MapSource object::

    source = MapSource(url="http://my-custom-map.source.com/{z}/{x}/{y}.png",
                       cache_key="my-custom-map", tile_size=512,
                       image_ext="png", attribution="@ Myself")
    map.map_source = source

API
---

.. py:class:: Coordinate(lon, lat)

    Named tuple that represent a geographic coordinate with latitude/longitude

    :param float lon: Longitude
    :param float lat: Latitude


.. py:class:: MapSource(url, cache_key, min_zoom, max_zoom, tile_size, image_ext, attribution, subdomains)

    Class that represent a map source. All the transformations from X/Y/Z to
    longitude, latitude, zoom, and limitations of the providers goes are stored
    here.

    :param str url: Tile's url of the providers.
        Defaults to `http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`
    :param str cache_key: Key for storing the tiles. Must be unique and not
        colliding with another providers, otherwise tiles will not be
        downloaded again.
        Defaults to "osm"
    :param int min_zoom: Minimum zoom value acceptable for this provider.
        Defaults to 0.
    :param int max_zoom: Maximum zoom value acceptable for this provider.
        Defaults to 19.
    :param int tile_size: Size of a image tile returned by the provider.
        Defaults to 256.
    :param str attribution: Attribution for this provider.
        Defaults to empty string
    :param str subdomains: Domains substitutions for the {s} in the url.
        Defaults to "abc"

    .. py:method:: get_x(zoom, lon)

        Get the x position to the longitude in the map source's projection

        :param int zoom: Zoom level to look at
        :param float lon: Longitude
        :return: X position
        :rtype: float

    .. py:method:: get_y(zoom, lat)

        Get the y position to the latitude in the map source's projection

        :param int zoom: Zoom level to look at
        :param float lat: Latitude
        :return: Y position
        :rtype: float

    .. py:method:: get_lon(zoom, x)

        Get the longitude to the x position in the map source's projection

        :param int zoom: Zoom level to look at
        :param float x: X position in the map
        :return: Longitude
        :rtype: float

    .. py:method:: get_lat(zoom, y)

        Get the latitude to the y position in the map source's projection

        :param int zoom: Zoom level to look at
        :param float y: Y position in the map
        :return: Latitude
        :rtype: float

    .. py:method:: get_col_count(zoom)

        Return the number of column for this provider at this zoom level.

        :param int zoom: Zoom level to look at
        :return: Number of column
        :rtype: int

    .. py:method:: get_row_count(zoom)

        Return the number of row for this provider at this zoom level.

        :param int zoom: Zoom level to look at
        :return: Number of rows
        :rtype: int

    .. py:method:: get_max_zoom()

        Return the maximum zoom of this source

        :return: Maximum zoom
        :rtype: int

    .. py:method:: get_min_zoom()

        Return the minimum zoom of this source

        :return: Minimum zoom
        :rtype: int


.. py:class:: MapMarker

    A marker on the map, that must be used on a :class:`MapMarker`, or with
    :meth:`MapView.add_marker` or with :meth:`MapView.add_widget`

    .. py:data:: anchor_x

        Anchor of the Marker on the X axis. Defaults to 0.5, means the anchor
        will be at the X center of the image

    .. py:data:: anchor_y

        Anchor of the marker on the Y axis. Defaults to 0, means the anchor
        will be at the Y bottom of the image

    .. py:data:: lat

        Latitude of the marker

    .. py:data:: lon

        Longitude of the marker


.. py:class:: MapView

    MapView is a widget that control the map displaying, navigation and layers
    management.

    .. py:method:: add_layer(layer)

        Add a new layer to update at the same time than the base tile layer

        :param MapLayer layer: Map layer to add

    .. py:method:: add_marker(marker, layer=None)

        Add a marker into a `layer`. If `layer` is None, it will be added in
        the default marker layer. If there is no default marker layer, a new
        one will be automatically created.

        :param MapMarker marker: The marker to add
        :param MarkerMapLayer layer: The layer to use

    .. py:method:: center_on(lat, lon)

        Center the map on the coordinate (lat, lon)

        :param float lat: Latitude
        :param float lon: Longitude

    .. py:method:: get_latlon_at(x, y, zoom=None):

        Return the current coordinate (lat, lon) at the (x, y) widget coordinate

        :param float x: X widget coordinate
        :param float y: Y widget coordinate
        :return: lat/lon Coordinate
        :rtype: :class:`Coordinate`

    .. py:method:: remove_layer(layer)

        Remove a previously added :class:`MapLayer`

        :param MapLayer layer: A map layer

    .. py:method:: remove_marker(marker)

        Remove a previously added :class:`MarkerMap`

        :param MarkerMap marker: The marker

    .. py:method:: set_zoom_at(zoom, x, y, scale=None)

        Sets the zoom level, leaving the (x, y) at the exact same point in the
        view.

        :param float zoom: New zoom
        :param float x: X coordinate to zoom at
        :param float y: Y coordinate to zoom at
        :param float scale: (internal) Scale to set on the scatter

    .. py:method:: unload()

        Unload the view and all the layers. It also cancel all the remaining
        downloads. The map should not be used after this.


.. py:class:: MapLayer

    A map layer. It is repositionned everytime the :class:`MapView` is moved.

    .. py:method:: reposition()

        Function called when the :class:`MapView` is moved. You must recalculate
        the position of your children, and handle the visibility.


.. py:class:: MarkerMapLayer(MapLayer)

    A map layer speciallized for handling :class:`MapMarker`.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
