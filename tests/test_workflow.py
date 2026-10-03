import asyncio, unittest
from unittest.mock import patch
from workflow_dag_engine.core import execute, validate


class WorkflowTests(unittest.TestCase):
    def test_worker_limit_bounds_real_concurrency(self):
        active = peak = 0

        async def operation(task, inputs):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return task["value"]

        spec = {
            "tasks": [
                {"id": str(i), "operation": "constant", "value": i} for i in range(8)
            ]
        }
        with patch("workflow_dag_engine.core.operate", operation):
            result = asyncio.run(execute(spec, workers=3))
        self.assertTrue(result["success"])
        self.assertEqual(peak, 3)

    def test_dependency_results(self):
        spec = {
            "tasks": [
                {"id": "total", "operation": "sum", "depends_on": ["a", "b"]},
                {"id": "a", "operation": "constant", "value": 3},
                {"id": "b", "operation": "constant", "value": 4},
            ]
        }
        result = asyncio.run(execute(spec))
        self.assertEqual(result["tasks"]["total"]["value"], 7)

    def test_cycles_rejected(self):
        with self.assertRaises(ValueError):
            validate({"tasks": [{"id": "a", "operation": "sum", "depends_on": ["a"]}]})

    def test_unknown_dependencies_rejected(self):
        with self.assertRaises(ValueError):
            validate(
                {"tasks": [{"id": "a", "operation": "sum", "depends_on": ["missing"]}]}
            )

    def test_retry_and_failure_propagation(self):
        result = asyncio.run(
            execute(
                {
                    "tasks": [
                        {"id": "a", "operation": "fail", "retries": 2},
                        {"id": "b", "operation": "sum", "depends_on": ["a"]},
                    ]
                }
            )
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["tasks"]["a"]["attempts"], 3)
        self.assertEqual(result["tasks"]["b"]["status"], "skipped")

    def test_timeout(self):
        result = asyncio.run(
            execute(
                {
                    "tasks": [
                        {
                            "id": "a",
                            "operation": "sleep",
                            "value": 0.05,
                            "timeout": 0.001,
                        }
                    ]
                }
            )
        )
        self.assertEqual(result["tasks"]["a"]["status"], "failed")

    def test_independent_branch_survives(self):
        result = asyncio.run(
            execute(
                {
                    "tasks": [
                        {"id": "a", "operation": "fail"},
                        {"id": "b", "operation": "constant", "value": "safe"},
                    ]
                }
            )
        )
        self.assertEqual(result["tasks"]["b"]["value"], "safe")

    def test_invalid_configuration(self):
        with self.assertRaises(ValueError):
            asyncio.run(execute({"tasks": [{"id": "a", "operation": "shell"}]}))
        with self.assertRaises(ValueError):
            asyncio.run(execute({"tasks": [{"id": "a", "operation": "sum"}]}, 0))

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            validate(
                {
                    "tasks": [
                        {"id": "a", "operation": "sum"},
                        {"id": "a", "operation": "sum"},
                    ]
                }
            )
