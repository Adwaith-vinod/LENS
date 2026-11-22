import unittest
from fastapi.testclient import TestClient
from backend.api.app import app


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["app"], "LENS")

    def test_stats_endpoint(self):
        response = self.client.get("/api/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_files", data)
        self.assertIn("indexed_files", data)

    def test_index_status_endpoint(self):
        response = self.client.get("/api/index/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)

    def test_config_endpoints(self):
        get_res = self.client.get("/api/config")
        self.assertEqual(get_res.status_code, 200)
        cfg = get_res.json()
        self.assertIn("chunk_size", cfg)

        post_res = self.client.post("/api/config", json={"chunk_size": 450})
        self.assertEqual(post_res.status_code, 200)
        updated_cfg = post_res.json()["config"]
        self.assertEqual(updated_cfg["chunk_size"], 450)

    def test_search_endpoint(self):
        res = self.client.post("/api/search", json={"query": "machine learning system design", "top_k": 3})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("results", data)
        self.assertIn("duration_ms", data)


if __name__ == "__main__":
    unittest.main()
