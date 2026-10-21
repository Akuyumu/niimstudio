#!/usr/bin/env python3
"""Stable publication requires a stable tag/version and a commit on main."""

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path


def check_release(root, tag, stable_ref="origin/main"):
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        raise ValueError("Stable releases require vMAJOR.MINOR.PATCH; development/prerelease tags cannot publish here")
    version = tag[1:]
    if json.loads((root / "package.json").read_text())["version"] != version:
        raise ValueError("Release tag does not match package.json")
    native_version = None
    for statement in ast.parse((root / "native/niimstudio/__init__.py").read_text()).body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__version__" for target in statement.targets
        ):
            native_version = ast.literal_eval(statement.value)
    if native_version != version:
        raise ValueError("Release tag does not match the native version")
    result = subprocess.run(["git", "merge-base", "--is-ancestor", "HEAD", stable_ref], cwd=root, check=False)
    if result.returncode != 0:
        raise ValueError("Only commits already on main may be published as stable; dev remains opt-in")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    arguments = parser.parse_args()
    try:
        check_release(Path(__file__).resolve().parents[1], arguments.tag)
    except ValueError as error:
        parser.exit(1, f"Release blocked: {error}\n")
