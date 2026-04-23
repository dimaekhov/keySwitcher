import ctypes
import unittest

from keyswitcher.winapi import INPUT


class WinApiStructureTests(unittest.TestCase):
    def test_input_size_matches_native_windows_layout(self) -> None:
        expected = 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28
        self.assertEqual(ctypes.sizeof(INPUT), expected)


if __name__ == "__main__":
    unittest.main()
