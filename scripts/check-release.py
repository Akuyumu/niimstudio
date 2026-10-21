#!/usr/bin/env python3
"""Gate stable tags on main; explicit release candidates on dev, with matching versions."""

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path


def check_release(root, tag, stable_ref="origin/main", candidate=False):
    if candidate and not re.fullmatch(r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)-rc\.[1-9][0-9]*", tag):
        raise ValueError("Release candidates require vMAJOR.MINOR.PATCH-rc.N with a positive candidate number")
    if not candidate and not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
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
    source_ref = "origin/dev" if candidate else stable_ref
    result = subprocess.run(["git", "merge-base", "--is-ancestor", "HEAD", source_ref], cwd=root, check=False)
    if result.returncode != 0:
        if candidate:
            raise ValueError("Only commits already on dev may be published as release candidates")
        raise ValueError("Only commits already on main may be published as stable; dev remains opt-in")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument(
        "--candidate", action="store_true", help="Explicit prerelease-only channel; never grants stable publication"
    )
    arguments = parser.parse_args()
    try:
        check_release(Path(__file__).resolve().parents[1], arguments.tag, candidate=arguments.candidate)
    except ValueError as error:
        parser.exit(1, f"Release blocked: {error}\n")
