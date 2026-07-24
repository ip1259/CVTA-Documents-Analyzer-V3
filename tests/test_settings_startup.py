import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import settings


class SettingsStartupTests(unittest.TestCase):
    def test_missing_config_is_created_and_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            with patch.object(settings, "CONFIG_DIR", config_dir):
                created = settings._ensure_default_config()

            config_path = config_dir / "settings.cfg"
            self.assertTrue(created)
            self.assertTrue(config_path.is_file())
            content = config_path.read_text(encoding="utf-8")
            self.assertIn("[Ollama]", content)
            self.assertIn("[Google]", content)
            self.assertIn(
                "ollama_host = http://127.0.0.1:11434",
                content
            )

    def test_existing_config_is_not_reported_as_new(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            with patch.object(settings, "CONFIG_DIR", config_dir):
                self.assertTrue(settings._ensure_default_config())
                self.assertFalse(settings._ensure_default_config())


if __name__ == "__main__":
    unittest.main()
