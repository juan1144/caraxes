import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "plugins/caraxes/skills/add-principle/scripts/principles.py"


class PrinciplesTests(unittest.TestCase):
    def complete_args(self):
        return (
            "--rationale", "Consistent technical language improves collaboration.",
            "--scope", "Source code and developer-facing technical artifacts; exclude user-facing product content when the project requires another language.",
            "--implications", "Technical contributions use one shared language while product localization remains a project decision.",
            "--verification", "Review the affected artifacts and confirm they use English.",
            "--exceptions", "None unless the project documents a specific legal or product requirement.",
        )

    def run_helper(self, operation, workspace, *args):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), operation, "--workspace", str(workspace), *args],
            capture_output=True, text=True, check=False,
        )
        output = result.stdout or result.stderr
        return result.returncode, json.loads(output)

    def workspace(self):
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "workspace"
        (path / "principles").mkdir(parents=True)
        self.addCleanup(temporary.cleanup)
        return path

    def test_inspect_empty_principles_directory(self):
        workspace = self.workspace()

        code, result = self.run_helper("inspect", workspace)

        self.assertEqual(code, 0)
        self.assertEqual(result["document_count"], 0)
        self.assertEqual(result["principles"], [])

    def test_add_creates_document_and_compact_index(self):
        workspace = self.workspace()

        code, result = self.run_helper(
            "add", workspace,
            "--title", "English for code",
            "--summary", "Write code and technical artifacts in English.",
            "--rule", "Use English for source code, comments, tests, and technical documentation.",
            *self.complete_args(),
            "--slug", "english-for-code",
        )

        self.assertEqual(code, 0)
        self.assertEqual(result["principle"]["id"], "P-001")
        document = workspace / "principles" / "P-001-english-for-code.md"
        index = workspace / "principles" / "index.md"
        self.assertTrue(document.is_file())
        self.assertEqual(index.read_text(encoding="utf-8").count("P-001"), 1)
        self.assertIn("English for code", index.read_text(encoding="utf-8"))

    def test_existing_id_is_not_overwritten(self):
        workspace = self.workspace()
        document = workspace / "principles" / "P-001-existing.md"
        document.write_text(
            "# P-001 — Existing\n\nSummary: Existing summary.\n\n"
            "## Principle\nExisting rule.\n\n"
            "## Rationale\nExisting rationale.\n\n"
            "## Scope\nExisting scope and exclusions.\n\n"
            "## Implications\nExisting implications.\n\n"
            "## Verification\nExisting verification.\n\n"
            "## Exceptions\nNone.\n",
            encoding="utf-8",
        )

        code, result = self.run_helper(
            "add", workspace,
            "--id", "P-001",
            "--title", "Replacement",
            "--summary", "Replacement summary.",
            "--rule", "Replacement rule.",
            *self.complete_args(),
            "--slug", "replacement",
        )

        self.assertNotEqual(code, 0)
        self.assertEqual(result["status"], "error")
        self.assertIn("already exists", result["message"])
        self.assertIn("Existing rule", document.read_text(encoding="utf-8"))

    def test_malformed_document_stops_addition(self):
        workspace = self.workspace()
        malformed = workspace / "principles" / "P-001-broken.md"
        malformed.write_text("not a principle\n", encoding="utf-8")

        code, result = self.run_helper(
            "add", workspace,
            "--title", "New principle",
            "--summary", "New summary.",
            "--rule", "New rule.",
            *self.complete_args(),
            "--slug", "new-principle",
        )

        self.assertNotEqual(code, 0)
        self.assertIn("must start with an ID heading", result["message"])
        self.assertFalse((workspace / "principles" / "P-002-new-principle.md").exists())

    def test_incomplete_document_stops_addition(self):
        workspace = self.workspace()
        incomplete = workspace / "principles" / "P-001-incomplete.md"
        incomplete.write_text(
            "# P-001 — Incomplete\n\nSummary: Missing required sections.\n",
            encoding="utf-8",
        )

        code, result = self.run_helper(
            "add", workspace,
            "--title", "New principle",
            "--summary", "New summary.",
            "--rule", "New rule.",
            *self.complete_args(),
            "--slug", "new-principle",
        )

        self.assertNotEqual(code, 0)
        self.assertIn("required fields missing", result["message"])
        self.assertFalse((workspace / "principles" / "P-002-new-principle.md").exists())

    def test_missing_principles_directory_is_rejected(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        workspace = Path(temporary.name) / "workspace"
        workspace.mkdir()

        code, result = self.run_helper("inspect", workspace)

        self.assertNotEqual(code, 0)
        self.assertIn("missing or invalid", result["message"])


if __name__ == "__main__":
    unittest.main()
