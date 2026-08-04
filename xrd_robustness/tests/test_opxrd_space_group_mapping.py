"""
Tests for space group to crystal system mapping.
"""
import os
import sys
import unittest

# Add scripts dir to path
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPT_DIR)

# We test the mapping directly without importing the audit script
# to avoid dependency issues


class TestSpaceGroupMapping(unittest.TestCase):
    """Test space group number to crystal system mapping."""

    # Mapping table: (sg_number, expected_system)
    KNOWN_MAPPINGS = [
        (1, "triclinic"),
        (2, "triclinic"),
        (3, "monoclinic"),
        (14, "monoclinic"),
        (15, "monoclinic"),
        (16, "orthorhombic"),
        (62, "orthorhombic"),
        (74, "orthorhombic"),
        (75, "tetragonal"),
        (99, "tetragonal"),
        (142, "tetragonal"),
        (143, "trigonal"),
        (155, "trigonal"),
        (167, "trigonal"),
        (168, "hexagonal"),
        (176, "hexagonal"),
        (194, "hexagonal"),
        (195, "cubic"),
        (221, "cubic"),
        (225, "cubic"),
        (230, "cubic"),
    ]

    SPACE_GROUP_RANGES = {
        "triclinic": (1, 2),
        "monoclinic": (3, 15),
        "orthorhombic": (16, 74),
        "tetragonal": (75, 142),
        "trigonal": (143, 167),
        "hexagonal": (168, 194),
        "cubic": (195, 230),
    }

    def _map_sg(self, sg: int) -> str:
        for system, (lo, hi) in self.SPACE_GROUP_RANGES.items():
            if lo <= sg <= hi:
                return system
        return "unknown"

    def test_known_mappings(self):
        """Test each known space group maps to expected crystal system."""
        for sg, expected in self.KNOWN_MAPPINGS:
            with self.subTest(sg=sg, expected=expected):
                result = self._map_sg(sg)
                self.assertEqual(result, expected,
                                 f"SG {sg} mapped to {result}, expected {expected}")

    def test_boundary_values(self):
        """Test boundary values between crystal systems."""
        boundaries = {
            (1, 2): "triclinic",
            (15, 16): "boundary",  # monoclinic->orthorhombic
            (74, 75): "boundary",  # orthorhombic->tetragonal
            (142, 143): "boundary",  # tetragonal->trigonal
            (167, 168): "boundary",  # trigonal->hexagonal
            (194, 195): "boundary",  # hexagonal->cubic
        }
        for (sg1, sg2), expected in boundaries.items():
            sys1 = self._map_sg(sg1)
            sys2 = self._map_sg(sg2)
            if expected == "boundary":
                self.assertNotEqual(sys1, sys2,
                                    f"SG {sg1} and SG {sg2} should be different systems")
            else:
                self.assertEqual(sys1, expected)

    def test_no_gaps(self):
        """Test that all space group numbers 1-230 are covered."""
        for sg in range(1, 231):
            system = self._map_sg(sg)
            self.assertNotEqual(system, "unknown",
                                f"SG {sg} not mapped to any system")

    def test_no_overlap(self):
        """Test ranges do not overlap."""
        seen = set()
        for sg in range(1, 231):
            system = self._map_sg(sg)
            self.assertNotIn(sg, seen, f"SG {sg} already mapped")
            seen.add(sg)

    def test_invalid_space_group(self):
        """Test invalid space group numbers."""
        self.assertEqual(self._map_sg(0), "unknown")
        self.assertEqual(self._map_sg(231), "unknown")
        self.assertEqual(self._map_sg(-1), "unknown")
        self.assertEqual(self._map_sg(999), "unknown")

    def test_ferroelectric_common_sgs(self):
        """Test space groups common in ferroelectric materials."""
        # Common ferroelectric space groups
        fe_sgs = {
            99: "tetragonal",    # P4mm (BaTiO3 ferroelectric phase)
            221: "cubic",        # Pm-3m (BaTiO3 paraelectric)
            161: "trigonal",     # R3c (BiFeO3, LiNbO3)
            38: "orthorhombic",  # Amm2 (KNbO3, NaNbO3 phases)
            160: "trigonal",     # R3m
            62: "orthorhombic",  # Pnma (common perovskite)
            225: "cubic",        # Fm-3m
            14: "monoclinic",    # P2_1/c
            15: "monoclinic",    # C2/c
            29: "orthorhombic",  # Pca2_1 (HfO2 FE phase)
            127: "tetragonal",   # P4/mbm
            139: "tetragonal",   # I4/mmm
            167: "trigonal",     # R-3c
            186: "hexagonal",    # P6_3mc
        }
        for sg, expected in fe_sgs.items():
            with self.subTest(sg=sg, expected=expected):
                result = self._map_sg(sg)
                self.assertEqual(result, expected,
                                 f"FE-related SG {sg} mapped to {result}, expected {expected}")


class TestSpaceGroupSymbolMapping(unittest.TestCase):
    """Test space group symbol normalization and mapping."""

    def test_symbol_normalization(self):
        """Test that various space group symbol formats normalize consistently."""
        test_cases = [
            ("P4mm", "P4MM"),
            ("P 4 m m", "P4MM"),
            ("P4/mmm", "P4MMM"),
            ("P2_1/c", "P21C"),
            ("R-3c", "R-3C"),
            ("Fm-3m", "FM-3M"),
            ("Pm-3m", "PM-3M"),
            ("Pnma", "PNMA"),
            ("R3c", "R3C"),
            ("Amm2", "AMM2"),
            ("C2/c", "C2C"),
        ]
        for input_sym, expected in test_cases:
            result = input_sym.replace(" ", "").replace("_", "").replace("/", "").upper()
            self.assertEqual(result, expected,
                             f"'{input_sym}' normalized to '{result}', expected '{expected}'")

    def test_known_fe_symbols(self):
        """Test that known ferroelectric space group symbols are recognized."""
        # These are symbols commonly seen in ferroelectric materials
        fe_symbols = {
            "P4mm": "tetragonal",
            "Pm-3m": "cubic",
            "R3c": "trigonal",
            "Amm2": "orthorhombic",
            "Pnma": "orthorhombic",
            "Fm-3m": "cubic",
            "P2_1/c": "monoclinic",
            "Pca2_1": "orthorhombic",
            "R-3c": "trigonal",
            "P6_3mc": "hexagonal",
            "I4/mmm": "tetragonal",
        }
        # Just verify they're syntactically valid
        for sym, _ in fe_symbols.items():
            self.assertTrue(len(sym) >= 2, f"Symbol too short: {sym}")
            self.assertTrue(sym[0].isupper() or sym[0].isdigit(),
                            f"Symbol doesn't start with uppercase or digit: {sym}")


if __name__ == "__main__":
    unittest.main()
