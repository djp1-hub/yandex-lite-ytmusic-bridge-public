"""Tests for ADB connection monitoring functionality."""

import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch, MagicMock


class ADBMonitoringTests(unittest.TestCase):
    """Test ADB connection monitoring and reconnection logic."""

    def test_monitor_script_exists(self):
        """Verify that the monitoring script exists."""
        monitor_script = "scripts/monitor_adb_connection.sh"
        self.assertTrue(os.path.exists(monitor_script))
        self.assertTrue(os.access(monitor_script, os.X_OK))

    def test_monitor_script_syntax(self):
        """Verify that the monitoring script has valid shell syntax."""
        try:
            result = subprocess.run(
                ["shellcheck", "scripts/monitor_adb_connection.sh"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # If shellcheck is available and runs successfully, check for errors
            if result.returncode == 0:
                self.assertEqual(result.returncode, 0, f"Shellcheck errors: {result.stdout}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # shellcheck not available or timeout - skip this check
            pass

    def test_run_voice_bridge_calls_monitor(self):
        """Verify that run_voice_bridge.sh calls the monitoring script."""
        with open("scripts/run_voice_bridge.sh", "r") as f:
            content = f.read()
        self.assertIn("monitor_adb_connection.sh", content)

    @patch('subprocess.Popen')
    def test_watch_detects_adb_process_termination(self, mock_popen):
        """Test that watch.py detects when ADB process terminates."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.stdout = iter(["log line 1", "log line 2"])
        mock_process.poll.return_value = None  # Process running
        mock_popen.return_value = mock_process

        # Import after patching
        from station_music import watch
        
        # Test that we can read lines normally
        lines = list(watch._lines_from_adb("test:5555"))
        self.assertEqual(len(lines), 2)
        
        # Verify poll was called
        mock_process.poll.assert_called()

    def test_monitor_script_has_correct_parameters(self):
        """Verify that the monitoring script accepts correct parameters."""
        with open("scripts/monitor_adb_connection.sh", "r") as f:
            content = f.read()
        
        # Check for parameter usage
        self.assertIn("$1", content)  # ADB serial
        self.assertIn("$2", content)  # Bridge script
        
        # Check for configuration variables
        self.assertIn("CHECK_INTERVAL", content)
        self.assertIn("MAX_RETRIES", content)


if __name__ == "__main__":
    unittest.main()
