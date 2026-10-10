import unittest

import task
from task import Task


class TaskConfigTests(unittest.TestCase):
    def test_task_can_be_loaded(self):
        self.assertIsInstance(task.TASK, Task)
        self.assertEqual(task.TASK.name, task.TASK_NAME)
        self.assertTrue(task.TASK.name.strip())

    def test_instructions_present(self):
        self.assertTrue(task.TASK.instructions.strip())

    def test_output_schema_present(self):
        self.assertIsInstance(task.TASK.output_schema, dict)
        self.assertTrue(task.TASK.output_schema)

    def test_default_task_keeps_m0_schema(self):
        self.assertEqual(list(task.TASK.output_schema), ["summary", "steps", "confidence"])

    def test_bad_configs_are_rejected(self):
        schema = {"a": "string"}
        with self.assertRaises(ValueError):
            Task(name=" ", instructions="x", output_schema=schema)
        with self.assertRaises(ValueError):
            Task(name="n", instructions="", output_schema=schema)
        with self.assertRaises(ValueError):
            Task(name="n", instructions="x", output_schema={})
        with self.assertRaises(ValueError):
            Task(name="n", instructions="x", output_schema=schema, example={"input": "only"})


if __name__ == "__main__":
    unittest.main()
