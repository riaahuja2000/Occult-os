import os
import sys
from unittest import TestCase
from unittest.mock import patch
import importlib

class TestServerStartup(TestCase):
    def setUp(self):
        # We need to make sure backend is in the path
        self.root_dir = os.path.dirname(os.path.dirname(__file__))
        if self.root_dir not in sys.path:
            sys.path.insert(0, self.root_dir)

        # Add backend dir to sys path so we can import things inside backend like oracle
        self.backend_dir = os.path.join(self.root_dir, "backend")
        if self.backend_dir not in sys.path:
            sys.path.insert(0, self.backend_dir)

        # Mock load_dotenv so it doesn't read the real .env file and overwrite our env vars
        self.patcher = patch('dotenv.load_dotenv')
        self.mock_load_dotenv = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_missing_jwt_secret_raises_keyerror(self):
        env_vars = {
            "MONGO_URL": "mongodb://localhost:27017",
            "DB_NAME": "testdb",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            # Ensure the module is not already loaded
            if "backend.server" in sys.modules:
                del sys.modules["backend.server"]
            if "server" in sys.modules:
                del sys.modules["server"]

            with self.assertRaises(KeyError) as cm:
                import server

            self.assertEqual(cm.exception.args[0], "JWT_SECRET")

    def test_present_jwt_secret_loads_successfully(self):
        env_vars = {
            "MONGO_URL": "mongodb://localhost:27017",
            "DB_NAME": "testdb",
            "JWT_SECRET": "my-secret-key",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            # Ensure the module is not already loaded
            if "backend.server" in sys.modules:
                del sys.modules["backend.server"]
            if "server" in sys.modules:
                del sys.modules["server"]

            try:
                import server
            except KeyError as e:
                if e.args[0] == "JWT_SECRET":
                    self.fail("JWT_SECRET caused KeyError even though it was present")
                else:
                    # Let other missing keys pass or handle them
                    pass
