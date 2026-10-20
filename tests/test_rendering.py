import unittest
from unittest.mock import Mock, patch

from niimstudio.app import WebKit, configure_rendering


class RenderingTests(unittest.TestCase):
    def test_default_rendering_keeps_platform_acceleration(self):
        settings = Mock()
        with patch.dict("os.environ", {"NIIMSTUDIO_RENDERER": "auto"}):
            self.assertEqual(configure_rendering(settings), "auto")
        settings.set_hardware_acceleration_policy.assert_not_called()

    def test_software_fallback_only_changes_webkit_policy(self):
        settings = Mock()
        with patch.dict("os.environ", {"NIIMSTUDIO_RENDERER": "software"}):
            self.assertEqual(configure_rendering(settings), "software")
        settings.set_hardware_acceleration_policy.assert_called_once_with(WebKit.HardwareAccelerationPolicy.NEVER)

    def test_unknown_renderer_does_not_silently_disable_acceleration(self):
        settings = Mock()
        with patch.dict("os.environ", {"NIIMSTUDIO_RENDERER": "typo"}), self.assertLogs("niimstudio", level="WARNING"):
            self.assertEqual(configure_rendering(settings), "auto")
        settings.set_hardware_acceleration_policy.assert_not_called()
