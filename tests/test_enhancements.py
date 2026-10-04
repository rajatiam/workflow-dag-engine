import unittest, json, csv, io
from workflow_dag_engine.core import plan


class FeatureTests(unittest.TestCase):
    def test_dependency_layers(self):
        spec = {
            "tasks": [
                {"id": "z", "operation": "sum", "depends_on": ["a", "b"]},
                {"id": "b", "operation": "constant", "value": 1},
                {"id": "a", "operation": "constant", "value": 2},
            ]
        }
        result = plan(spec)
        self.assertEqual(result["layers"], [["a", "b"], ["z"]])
        self.assertEqual(result["depth"], 2)
        self.assertTrue(result["dry_run"])

    def test_plan_does_not_execute_failing_operation(self):
        self.assertEqual(
            plan({"tasks": [{"id": "a", "operation": "fail"}]})["tasks"], 1
        )

    def test_invalid_plan_rejected(self):
        with self.assertRaises(ValueError):
            plan({"tasks": [{"id": "a", "operation": "sum", "depends_on": ["a"]}]})
