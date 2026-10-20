import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from niimstudio.theme import DEFAULT_PALETTE, gtk_css, gtk_palette, read_palette, theme_paths


class ThemeTests(unittest.TestCase):
    def test_flatpak_also_checks_explicitly_exposed_host_theme_paths(self):
        from unittest.mock import patch

        with (
            patch.dict(
                "os.environ",
                {
                    "FLATPAK_ID": "io.github.niimstudio.App",
                    "XDG_CONFIG_HOME": "/sandbox/config",
                    "XDG_STATE_HOME": "/sandbox/state",
                },
            ),
            patch("pathlib.Path.home", return_value=Path("/home/test")),
        ):
            paths = theme_paths()
        self.assertEqual(paths[0], Path("/sandbox/state/omarchy/current/theme/colors.toml"))
        self.assertIn(Path("/home/test/.config/omarchy/current/theme/colors.toml"), paths)

    def test_missing_omarchy_palette_can_defer_to_gtk(self):
        self.assertIsNone(read_palette([], fallback=False))

    def test_gtk_palette_uses_native_colors_and_composites_transparency(self):
        def color(r, g, b, alpha=1):
            return SimpleNamespace(red=r / 255, green=g / 255, blue=b / 255, alpha=alpha)

        colors = {
            "window_bg_color": color(34, 34, 38),
            "window_fg_color": color(255, 255, 255),
            "card_bg_color": color(255, 255, 255, 0.08),
            "accent_bg_color": color(0, 170, 255),
        }
        palette = gtk_palette(lambda name: (name in colors, colors.get(name)), dark=True)
        self.assertEqual(palette["background"], "#222226")
        self.assertEqual(palette["accent"], "#00aaff")
        self.assertEqual(palette["selection"], "#343437")
        self.assertEqual(palette["mode"], "dark")

    def test_gtk_light_mode_does_not_fall_back_to_nord(self):
        palette = gtk_palette(lambda _name: (False, None), dark=False)
        self.assertEqual(palette["mode"], "light")
        self.assertEqual(palette["background"], "#fafafb")

    def test_missing_theme_has_safe_defaults(self):
        self.assertEqual(read_palette([]), DEFAULT_PALETTE)

    def test_theme_switch_can_replace_entire_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "colors.toml"
            path.write_text('mode="light"\naccent="#112233"\nbackground="#ffffff"')
            palette = read_palette([path])
            self.assertEqual(palette["accent"], "#112233")
            self.assertEqual(palette["mode"], "light")
            path.unlink()
            self.assertEqual(read_palette([path]), DEFAULT_PALETTE)
            path.write_text('accent="#aabbcc"')
            self.assertEqual(read_palette([path])["accent"], "#aabbcc")

    def test_theme_cannot_inject_css(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "colors.toml"
            path.write_text('accent="red; } button { opacity: 0"\nforeground=12\nmode="unexpected"')
            palette = read_palette([path])
            self.assertEqual(palette, DEFAULT_PALETTE)
            self.assertNotIn("red; } button", gtk_css(palette))

    def test_malformed_theme_uses_next_location(self):
        with tempfile.TemporaryDirectory() as directory:
            broken, valid = Path(directory) / "bad", Path(directory) / "valid"
            broken.write_text("accent = [")
            valid.write_text('accent="#abcdef"')
            self.assertEqual(read_palette([broken, valid])["accent"], "#abcdef")
