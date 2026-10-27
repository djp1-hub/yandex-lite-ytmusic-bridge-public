"""Tests for ADB connection monitoring functionality."""

import unittest
from unittest.mock import patch, MagicMock


class ADBMonitoringTests(unittest.TestCase):
    """Test ADB connection monitoring and reconnection logic."""

    def test_run_voice_bridge_starts_watcher(self):
        """Verify that the launcher starts the watcher without recursion."""
        with open("scripts/run_voice_bridge.sh", "r") as f:
            content = f.read()
        self.assertIn("station_music.watch", content)
        self.assertNotIn('exec "$base_dir/scripts/monitor_adb_connection.sh"', content)

    @patch('subprocess.Popen')
    def test_watch_detects_adb_process_termination(self, mock_popen):
        """Test that watch.py detects when ADB process terminates."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.stdout = iter(["log line 1", "log line 2"])
        mock_process.poll.return_value = 0
        mock_popen.return_value = mock_process

        # Import after patching
        from station_music import watch
        
        # Test that we can read lines normally
        with patch.object(watch, "_adb_ready", side_effect=[True, KeyboardInterrupt]):
            lines = watch._lines_from_adb("test:5555", retry_delay=0)
            self.assertEqual(next(lines), "log line 1")
            self.assertEqual(next(lines), "log line 2")
            self.assertIsNone(next(lines))
            with self.assertRaises(KeyboardInterrupt):
                next(lines)

if __name__ == "__main__":
    unittest.main()
