import json
import unittest
from pathlib import Path


QUERY_FILE = (
    Path(__file__).resolve().parents[1] / "data" / "evaluation" / "queries.json"
)


class EvaluationQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(QUERY_FILE.read_text(encoding="utf-8"))
        cls.queries = cls.payload["queries"]

    def test_file_has_expected_version_and_query_count(self) -> None:
        self.assertEqual(self.payload["version"], 1)
        self.assertEqual(len(self.queries), 10)

    def test_query_ids_are_unique_and_sequential(self) -> None:
        query_ids = [query["query_id"] for query in self.queries]

        self.assertEqual(len(query_ids), len(set(query_ids)))
        self.assertEqual(query_ids, [f"Q{number:03d}" for number in range(1, 11)])

    def test_each_query_has_the_required_structure(self) -> None:
        expected_query_keys = {
            "query_id",
            "raw_query",
            "hard_constraints",
            "expected_preferences",
        }
        expected_constraint_keys = {
            "content_type",
            "max_runtime_minutes",
            "providers",
        }
        expected_preference_keys = {
            "genres",
            "themes",
            "tones",
            "preferred_aspects",
            "must_avoid",
        }

        for query in self.queries:
            with self.subTest(query_id=query["query_id"]):
                self.assertEqual(set(query), expected_query_keys)
                self.assertEqual(
                    set(query["hard_constraints"]), expected_constraint_keys
                )
                self.assertEqual(
                    set(query["expected_preferences"]), expected_preference_keys
                )
                self.assertTrue(query["raw_query"].strip())

    def test_hard_constraint_values_are_valid(self) -> None:
        for query in self.queries:
            constraints = query["hard_constraints"]
            runtime = constraints["max_runtime_minutes"]

            with self.subTest(query_id=query["query_id"]):
                self.assertIn(constraints["content_type"], {"movie", "tv", None})
                self.assertTrue(
                    runtime is None
                    or (isinstance(runtime, int) and not isinstance(runtime, bool) and runtime > 0)
                )
                self._assert_string_list(constraints["providers"])

    def test_expected_preferences_are_string_lists(self) -> None:
        for query in self.queries:
            for field_name, values in query["expected_preferences"].items():
                with self.subTest(
                    query_id=query["query_id"], field_name=field_name
                ):
                    self._assert_string_list(values)

    def test_relevance_labels_are_absent_before_catalog_exists(self) -> None:
        for query in self.queries:
            with self.subTest(query_id=query["query_id"]):
                self.assertNotIn("relevance_labels", query)

    def _assert_string_list(self, values: object) -> None:
        self.assertIsInstance(values, list)
        self.assertTrue(
            all(isinstance(value, str) and value.strip() for value in values)
        )


if __name__ == "__main__":
    unittest.main()

