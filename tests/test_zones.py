from __future__ import annotations

import unittest

from passfinder.known_zones import KNOWN_ZONES


class ZoneTests(unittest.TestCase):
    def test_expanded_grand_teton_zone_list_includes_representative_areas(self):
        self.assertEqual(KNOWN_ZONES["Death Canyon Shelf"], "4675342030")
        self.assertEqual(KNOWN_ZONES["Granite Lower"], "4675342032")
        self.assertEqual(KNOWN_ZONES["Leigh Lake 12B"], "4675342014")
        self.assertEqual(KNOWN_ZONES["Waterfalls Canyon"], "4675342125")


if __name__ == "__main__":
    unittest.main()
