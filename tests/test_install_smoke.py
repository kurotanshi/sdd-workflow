from __future__ import annotations

import platform
import unittest

from tests.install_smoke import run_smoke


class InstallSmokeTests(unittest.TestCase):
    @unittest.skipUnless(platform.system() in {"Darwin", "Linux"}, "supported POSIX only")
    def test_current_supported_platform(self) -> None:
        expected = "macos" if platform.system() == "Darwin" else "linux"
        run_smoke(expected)


if __name__ == "__main__":
    unittest.main()
