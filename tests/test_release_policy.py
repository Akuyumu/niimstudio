import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location(
    "release_policy", Path(__file__).resolve().parents[1] / "scripts/check-release.py"
)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class StableReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "package.json").write_text(json.dumps({"version": "1.2.3"}))
        (self.root / "native/niimstudio").mkdir(parents=True)
        (self.root / "native/niimstudio/__init__.py").write_text('__version__ = "1.2.3"\n')

    def test_main_commit_with_matching_stable_tag_is_eligible(self):
        with patch.object(policy.subprocess, "run", return_value=Mock(returncode=0)) as git:
            policy.check_release(self.root, "v1.2.3")
        self.assertEqual(git.call_args.args[0], ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"])

    def test_development_commit_cannot_be_published_as_stable(self):
        with patch.object(policy.subprocess, "run", return_value=Mock(returncode=1)):
            with self.assertRaisesRegex(ValueError, "already on main"):
                policy.check_release(self.root, "v1.2.3")

    def test_development_and_prerelease_tags_are_rejected(self):
        for tag in ("dev", "v1.2.3-dev", "v1.2.3-rc1", "v1.2", "v1.2.3+test"):
            with self.subTest(tag=tag), self.assertRaisesRegex(ValueError, "Stable releases require"):
                policy.check_release(self.root, tag)

    def test_mismatched_web_or_native_versions_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "package.json"):
            policy.check_release(self.root, "v1.2.4")
        (self.root / "native/niimstudio/__init__.py").write_text('__version__ = "1.2.4"\n')
        with self.assertRaisesRegex(ValueError, "native version"):
            policy.check_release(self.root, "v1.2.3")

    def test_candidate_requires_explicit_channel_and_dev_ancestry(self):
        (self.root / "package.json").write_text(json.dumps({"version": "1.2.3-rc.1"}))
        (self.root / "native/niimstudio/__init__.py").write_text('__version__ = "1.2.3-rc.1"\n')
        with patch.object(policy.subprocess, "run", return_value=Mock(returncode=0)) as git:
            policy.check_release(self.root, "v1.2.3-rc.1", candidate=True)
            self.assertEqual(git.call_args.args[0][-1], "origin/dev")
        with self.assertRaisesRegex(ValueError, "Stable releases require"):
            policy.check_release(self.root, "v1.2.3-rc.1")
        with patch.object(policy.subprocess, "run", return_value=Mock(returncode=1)):
            with self.assertRaisesRegex(ValueError, "already on dev"):
                policy.check_release(self.root, "v1.2.3-rc.1", candidate=True)

    def test_candidate_gate_never_accepts_stable_or_malformed_tags(self):
        for tag in ("v1.2.3", "dev", "v1.2.3-beta.1", "v1.2.3-rc.0", "v1.2.3-rc.01", "v1.2.3-rc.1/test"):
            with self.subTest(tag=tag), self.assertRaisesRegex(ValueError, "Release candidates require"):
                policy.check_release(self.root, tag, candidate=True)
