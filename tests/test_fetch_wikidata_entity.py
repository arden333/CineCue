import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cinecue.data.fetch_wikidata_entity import (
    WIKIDATA_ENTITY_PROPS,
    build_request,
    load_sample_titles,
    validate_api_response,
)


class BuildWikidataRequestTests(unittest.TestCase):
    def test_builds_one_request_for_multiple_titles(self) -> None:
        request = build_request(
            ["Before Sunset", "Bridgerton"],
            "CineCue/0.1 (contact@example.com)",
        )
        parsed_url = urlparse(request.full_url)
        params = parse_qs(parsed_url.query)

        self.assertEqual(parsed_url.scheme, "https")
        self.assertEqual(parsed_url.netloc, "www.wikidata.org")
        self.assertEqual(parsed_url.path, "/w/api.php")
        self.assertEqual(params["action"], ["wbgetentities"])
        self.assertEqual(params["sites"], ["enwiki"])
        self.assertEqual(params["titles"], ["Before Sunset|Bridgerton"])
        self.assertEqual(params["props"], [WIKIDATA_ENTITY_PROPS])
        self.assertEqual(params["languages"], ["en"])
        self.assertEqual(params["sitefilter"], ["enwiki"])
        self.assertEqual(params["format"], ["json"])
        self.assertEqual(params["formatversion"], ["2"])
        self.assertEqual(params["maxlag"], ["5"])
        self.assertEqual(
            request.get_header("User-agent"),
            "CineCue/0.1 (contact@example.com)",
        )

    def test_rejects_empty_title_list(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            build_request([], "CineCue/0.1 (contact@example.com)")

    def test_rejects_duplicate_titles(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicates"):
            build_request(
                ["Bridgerton", "Bridgerton"],
                "CineCue/0.1 (contact@example.com)",
            )

    def test_rejects_blank_user_agent(self) -> None:
        with self.assertRaisesRegex(ValueError, "user_agent"):
            build_request(["Bridgerton"], "  ")


class LoadSampleTitlesTests(unittest.TestCase):
    def test_loads_the_fixed_twenty_title_sample(self) -> None:
        titles = load_sample_titles(Path("data/samples/wiki_coverage_titles.json"))

        self.assertEqual(len(titles), 20)
        self.assertEqual(len(set(titles)), 20)
        self.assertIn("Before Sunset", titles)
        self.assertIn("Bridgerton", titles)


class ValidateWikidataResponseTests(unittest.TestCase):
    def test_accepts_successful_json_object(self) -> None:
        validate_api_response(b'{"entities": {"Q1": {"id": "Q1"}}}')

    def test_rejects_api_error(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "maxlag"):
            validate_api_response(b'{"error": {"code": "maxlag"}}')


if __name__ == "__main__":
    unittest.main()
