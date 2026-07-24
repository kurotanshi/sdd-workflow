from __future__ import annotations

import unittest

import app


class AppTests(unittest.TestCase):
    def test_health_is_ok(self) -> None:
        status, headers, body = app.handle("/health")
        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/json")
        self.assertEqual(body["status"], "ok")

    def test_unknown_path_remains_json_404(self) -> None:
        status, headers, body = app.handle("/missing")
        self.assertEqual(status, 404)
        self.assertEqual(headers["content-type"], "application/json")
        self.assertEqual(body, {"error": "not found"})


if __name__ == "__main__":
    unittest.main()
