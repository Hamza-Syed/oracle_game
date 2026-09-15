"""Packaged paths are isolated from real user data and the bundle directory."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import memories
from memories import Memory, default_memory_path


class PackagedPathTests(unittest.TestCase):
    def test_source_path_remains_beside_module(self):
        with patch.object(memories.sys, "frozen", False, create=True):
            self.assertEqual(default_memory_path(), Path(memories.__file__).with_name("memory.json"))

    def test_frozen_save_creates_user_directory_and_survives_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with patch.object(memories.sys, "frozen", True, create=True), \
                    patch.object(memories.sys, "_MEIPASS", str(base / "extraction"), create=True), \
                    patch.dict("os.environ", {"LOCALAPPDATA": str(base / "user-data")}):
                memory = Memory()
                self.assertEqual(memory.path, base / "user-data" / "TheOracle" / "memory.json")
                self.assertTrue(memory.path.parent.is_dir())
                memory.remember_question("Will tomorrow be sunny?")
                memory.track_repeat("Will tomorrow be sunny?")
                memory.save_memory()
                self.assertEqual(Memory().questions_asked, 1)
                self.assertFalse((base / "extraction").exists())

    def test_missing_or_empty_localappdata_uses_home(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(memories.sys, "frozen", True, create=True), \
                    patch.object(Path, "home", return_value=Path(directory)):
                for environment in ({}, {"LOCALAPPDATA": "  "}):
                    with patch.dict("os.environ", environment, clear=True):
                        memory = Memory()
                        self.assertEqual(memory.path, Path(directory) / "AppData" / "Local" / "TheOracle" / "memory.json")
                        self.assertTrue(memory.path.parent.is_dir())

    def test_explicit_path_overrides_frozen_default_without_creating_user_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with patch.object(memories.sys, "frozen", True, create=True), \
                    patch.dict("os.environ", {"LOCALAPPDATA": str(base / "unused")}):
                memory = Memory(base / "test.json")
                memory.save_memory()
                self.assertTrue((base / "test.json").exists())
                self.assertFalse((base / "unused").exists())

    def test_user_directory_failure_propagates_to_existing_startup_handler(self):
        with patch.object(memories.sys, "frozen", True, create=True), \
                patch.dict("os.environ", {"LOCALAPPDATA": "unused-test-location"}), \
                patch.object(Path, "mkdir", side_effect=PermissionError("Cannot create user storage")):
            with self.assertRaises(PermissionError):
                Memory()
