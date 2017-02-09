"""
Demonstrate the speed of the KD-tree (KDBush) implementation

The green circle will indicate the selection zone, the blue rectangle indicate
the selected red dot.
"""

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Ellipse, Canvas
from mapview.clustered_marker_layer import KDBush, Marker
from random import random

# creating markers
points = []
for i in range(10000):
    points.append(Marker(lon=random() * 360 - 180, lat=random() * 180 - 90))

# test kdbush
kdbush = KDBush(points, 64)


class TestWidget(Widget):
    selection = []
    selection_center = None
    radius = 0.1

    canvas_points = None

    def build(self):
        radius = self.radius

        if not self.canvas_points:
            self.canvas_points = Canvas()
            self.canvas.add(self.canvas_points)
            with self.canvas_points:
                Color(1, 0, 0)
                for marker in points:
                    Rectangle(
                        pos=(marker.x * 600, marker.y * 600), size=(2, 2))

        self.canvas.before.clear()
        with self.canvas.before:
            if self.selection_center:
                Color(0, 1, 0, 0.5)
                x, y = self.selection_center
                r = radius * 600
                r2 = r * 2
                Ellipse(pos=(x - r, y - r), size=(r2, r2))

            if self.selection:
                Color(0, 0, 1)
                for m_id in self.selection:
                    # x = kdbush.coords[m_id * 2]
                    # y = kdbush.coords[m_id * 2 + 1]
                    marker = points[m_id]
                    x = marker.x
                    y = marker.y
                    Rectangle(pos=(x * 600 - 4, y * 600 - 4), size=(8, 8))

    def on_touch_down(self, touch):
        self.select(*touch.pos)

    def on_touch_move(self, touch):
        self.select(*touch.pos)

    def select(self, x, y):
        self.selection_center = (x, y)
        self.selection = kdbush.within(x / 600., y / 600., self.radius)
        self.build()


class TestApp(App):
    def build(self):
        self.root = TestWidget()
        self.root.build()


TestApp().run()
