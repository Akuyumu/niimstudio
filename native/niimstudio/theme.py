"""Read Omarchy palettes without changing desktop configuration."""

import os
import re
import tomllib
from pathlib import Path

DEFAULT_PALETTE = {
    "mode": "dark",
    "background": "#2e3440",
    "foreground": "#d8dee9",
    "accent": "#81a1c1",
    "selection": "#434c5e",
    "muted": "#4c566a",
    "red": "#bf616a",
    "green": "#a3be8c",
    "yellow": "#ebcb8b",
}


def theme_paths():
    state = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    paths = [state / "omarchy/current/theme/colors.toml", config / "omarchy/current/theme/colors.toml"]
    if os.environ.get("FLATPAK_ID") == "io.github.niimstudio.App":
        # Flatpak redirects XDG paths to app data. Only explicitly granted,
        # read-only host Omarchy directories are considered as extra sources.
        paths.extend(
            [
                Path.home() / ".local/state/omarchy/current/theme/colors.toml",
                Path.home() / ".config/omarchy/current/theme/colors.toml",
            ]
        )
    return paths


def read_palette(paths=None, *, fallback=True):
    """Only permit color literals: theme files never become arbitrary CSS/JS."""
    result = DEFAULT_PALETTE.copy()
    for path in paths if paths is not None else theme_paths():
        try:
            data = tomllib.loads(path.read_text())
        except (OSError, tomllib.TOMLDecodeError):
            continue
        result["mode"] = "light" if data.get("mode") == "light" else "dark"
        for key, value in data.items():
            if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                result[key] = value
        return result
    return result if fallback else None


def gtk_palette(lookup, dark):
    """Mirror the actual native GTK colors, not a hardcoded Omarchy theme.

    `lookup` returns (found, Gdk.RGBA). Accepting it as a callable keeps color
    conversion/compositing testable without starting a graphical application.
    """
    defaults = {
        "background": "#222226" if dark else "#fafafb",
        "foreground": "#ffffff" if dark else "#2e2e32",
        "accent": "#3584e4",
        "accent_foreground": "#ffffff",
        "selection": "#3a3a3e" if dark else "#e6e6e8",
        "muted": "#88888c",
        "red": "#e01b24",
        "green": "#2ec27e",
        "yellow": "#e5a50a",
    }
    result = {"mode": "dark" if dark else "light", **defaults}
    names = {
        "background": "window_bg_color",
        "foreground": "window_fg_color",
        "accent": "accent_bg_color",
        "accent_foreground": "accent_fg_color",
        "selection": "card_bg_color",
        "muted": "insensitive_fg_color",
        "red": "error_color",
        "green": "success_color",
        "yellow": "warning_color",
    }
    for key, name in names.items():
        found, color = lookup(name)
        if not found:
            continue
        background = tuple(int(result["background"][start : start + 2], 16) for start in (1, 3, 5))
        rgb = (color.red, color.green, color.blue)
        channels = [
            round(channel * 255 * color.alpha + base * (1 - color.alpha)) for channel, base in zip(rgb, background)
        ]
        result[key] = "#" + "".join(f"{max(0, min(255, channel)):02x}" for channel in channels)
    return result


def gtk_css(palette):
    p = palette
    return f"""
    @define-color window_bg_color {p["background"]};
    @define-color window_fg_color {p["foreground"]};
    @define-color view_bg_color {p["background"]};
    @define-color view_fg_color {p["foreground"]};
    @define-color headerbar_bg_color {p["background"]};
    @define-color headerbar_fg_color {p["foreground"]};
    @define-color dialog_bg_color {p["background"]};
    @define-color dialog_fg_color {p["foreground"]};
    @define-color popover_bg_color {p["background"]};
    @define-color popover_fg_color {p["foreground"]};
    @define-color card_bg_color {p.get("lighter_background", p["selection"])};
    @define-color accent_color {p["accent"]};
    @define-color accent_bg_color {p["accent"]};
    @define-color accent_fg_color {p["background"]};
    .studio-status {{ font-size: 12px; opacity: 0.75; }}
    """
