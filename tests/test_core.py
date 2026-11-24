import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from openactionproof.cli import demo
from openactionproof.core import ActionSpec, check_receipt, relative_target, verify_action


class CoreTests(unittest.TestCase):
    def test_demo_cases(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            self.assertEqual(demo(out), {
                "A_confirmed": "CONFIRMED",
                "B_false_success": "FALSE_SUCCESS",
                "C_partial_timeout": "INDETERMINATE",
            })
            for file in out.glob("*.json"):
                self.assertTrue(check_receipt(json.loads(file.read_text())))
            self.assertEqual(len(list(out.glob("*.json"))), 3)

    def test_tampering_detected(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            demo(out)
            proof = json.loads((out / "A_confirmed.json").read_text())
            proof["verification"]["verdict"] = "FALSE_SUCCESS"
            self.assertFalse(check_receipt(proof))

    def test_path_traversal_blocked(self):
        with TemporaryDirectory() as tmp:
            for value in ["../secret", "/etc/hosts", "a/../../b"]:
                with self.assertRaises(ValueError):
                    relative_target(Path(tmp), value)

    def test_portable_path_restrictions(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for value in [r"C:\secret", r"\secret", "C:secret", "//host/share/file", "a:stream", "a/./b", "a//b", "NUL.txt", "dir.", "dir ", "a\x00b"]:
                with self.subTest(value=value), self.assertRaises(ValueError):
                    relative_target(root, value)
            self.assertEqual(relative_target(root, "nested/file.txt"), root.resolve() / "nested" / "file.txt")

    def test_exception_details_are_redacted(self):
        with TemporaryDirectory() as tmp:
            def actor(target):
                raise RuntimeError("private-token-example")
            proof = verify_action(Path(tmp), ActionSpec("R", "file", b"x"), actor, operation_name="redaction")
            self.assertEqual(proof["verification"]["verdict"], "INDETERMINATE")
            self.assertNotIn("private-token-example", json.dumps(proof))

    def test_symlink_blocked(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            link = root / "bad"
            try:
                link.symlink_to(Path(tmp).parent, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unsupported")
            with self.assertRaises(ValueError):
                relative_target(root, "bad/secrets")

    def test_timeout_after_full_write_is_still_uncertain(self):
        with TemporaryDirectory() as tmp:
            spec = ActionSpec("C2", "out.txt", b"finished", True)
            def write_then_timeout(target):
                target.write_bytes(b"finished")
                raise TimeoutError("no confirmation")
            proof = verify_action(Path(tmp), spec, write_then_timeout, operation_name="write_then_timeout")
            self.assertTrue(proof["verification"]["matches_expected"])
            self.assertEqual(proof["verification"]["verdict"], "INDETERMINATE")

    def test_no_claim_no_change_not_confirmed(self):
        with TemporaryDirectory() as tmp:
            proof = verify_action(Path(tmp), ActionSpec("N", "a", b"hello", None), lambda _: None, operation_name="no_op")
            self.assertEqual(proof["verification"]["verdict"], "NOT_CONFIRMED")

    def test_preexisting_expected_state_not_attributed_to_agent(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "already.txt").write_bytes(b"same")
            proof = verify_action(root, ActionSpec("P", "already.txt", b"same", True), lambda _: None, operation_name="no_op")
            self.assertEqual(proof["verification"]["verdict"], "STATE_SATISFIED_UNATTRIBUTED")

    def test_empty_file_success(self):
        with TemporaryDirectory() as tmp:
            proof = verify_action(Path(tmp), ActionSpec("E", "file", b"", True), lambda p: p.write_bytes(b""), operation_name="empty_write")
            self.assertEqual(proof["verification"]["verdict"], "CONFIRMED")


if __name__ == "__main__":
    unittest.main()
