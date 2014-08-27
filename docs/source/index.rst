.. Mapview documentation master file, created by
   sphinx-quickstart on Mon Aug 25 00:36:08 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Mapview's documentation!
===================================

MapView is a Kivy widget that display maps.

.. note::

    Documentation in progress.

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

    .. py:method:: get_x(self, zoom, lon)

        Get the x position to the longitude in the map source's projection

        :param int zoom: Zoom level to look at
        :param float lon: Longitude
        :return: X position
        :rtype: float

    .. py:method:: get_y(self, zoom, lat)

        Get the y position to the latitude in the map source's projection

        :param int zoom: Zoom level to look at
        :param float lat: Latitude
        :return: Y position
        :rtype: float

    .. py:method:: get_lon(self, zoom, x)

        Get the longitude to the x position in the map source's projection

        :param int zoom: Zoom level to look at
        :param float x: X position in the map
        :return: Longitude
        :rtype: float

    .. py:method:: get_lat(self, zoom, y)

        Get the latitude to the y position in the map source's projection

        :param int zoom: Zoom level to look at
        :param float y: Y position in the map
        :return: Latitude
        :rtype: float

    .. py:method:: get_col_count(self, zoom)

        Return the number of column for this provider at this zoom level.

        :param int zoom: Zoom level to look at
        :return: Number of column
        :rtype: int

    .. py:method:: get_row_count(self, zoom)

        Return the number of row for this provider at this zoom level.

        :param int zoom: Zoom level to look at
        :return: Number of rows
        :rtype: int

    .. py:method:: get_max_zoom(self)

        Return the maximum zoom of this source

        :return: Maximum zoom
        :rtype: int

    .. py:method:: get_min_zoom(self)

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

    .. py:method:: add_layer(self, layer)

        Add a new layer to update at the same time than the base tile layer

        :param MapLayer layer: Map layer to add


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
