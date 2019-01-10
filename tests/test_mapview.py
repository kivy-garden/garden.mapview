import unittest
from mapview import MapView


class TextInputTest(unittest.TestCase):

    def test_init_simple_map(self):
        """
        Makes sure we can initialize a simple MapView object.
        """
        kwargs = {}
        mapview = MapView(**kwargs)
        self.assertEqual(len(mapview.children), 2)


if __name__ == '__main__':
    import unittest
    unittest.main()
