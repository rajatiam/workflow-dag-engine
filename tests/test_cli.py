"""Exercise the shipped examples through the real process entrypoint."""

import json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def test_help_entrypoint(self):
        result = subprocess.run(
            [sys.executable, "-m", "workflow_dag_engine", "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)

    def test_documented_workflow(self):
        with tempfile.TemporaryDirectory() as folder:
            clone = Path(folder)
            shutil.copytree(ROOT / "workflow_dag_engine", clone / "workflow_dag_engine")
            shutil.copytree(ROOT / "examples", clone / "examples")
            for command in [
                "run examples/workflow.json --workers 3 --journal examples/run.json"
            ]:
                result = subprocess.run(
                    [sys.executable, "-m", "workflow_dag_engine", *command.split()],
                    cwd=clone,
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(result.stdout)
            self.assertEqual(payload["tasks"]["scaled"]["value"], 40)
