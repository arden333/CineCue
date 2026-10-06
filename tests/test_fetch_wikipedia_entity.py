import unittest
from urllib.parse import parse_qs, urlparse

from cinecue.data.fetch_wikipedia_entity import (
    WIKIPEDIA_PAGE_PROPS,
    WIKIPEDIA_REVISION_PROPS,
    build_request,
    build_wikipedia_request_manifest,
    requestable_titles,
    validate_api_response,
)


def wikidata_response_fixture() -> dict:
    return {
        "entities": {
            "Q1": {
                "id": "Q1",
                "sitelinks": {
                    "enwiki": {
                        "title": "Example Film",
                        "url": "https://en.wikipedia.org/wiki/Example_Film",
                    }
                },
            },
            "Q2": {"id": "Q2", "sitelinks": {}},
        }
    }


class BuildWikipediaManifestTests(unittest.TestCase):
    def test_keeps_qids_and_missing_wikipedia_links(self) -> None:
        manifest = build_wikipedia_request_manifest(wikidata_response_fixture())

        self.assertEqual(
            manifest,
            [
                {
                    "wikidata_id": "Q1",
                    "wikipedia_title": "Example Film",
                    "wikipedia_url": "https://en.wikipedia.org/wiki/Example_Film",
                },
                {
                    "wikidata_id": "Q2",
                    "wikipedia_title": None,
                    "wikipedia_url": None,
                },
            ],
        )

    def test_rejects_response_without_entities_object(self) -> None:
        with self.assertRaisesRegex(ValueError, "entities"):
            build_wikipedia_request_manifest({"success": 1})


class BuildWikipediaRequestTests(unittest.TestCase):
    def test_builds_request_only_for_titles_present_in_manifest(self) -> None:
        manifest = build_wikipedia_request_manifest(wikidata_response_fixture())
        request = build_request(
            manifest,
            "CineCue/0.1 (contact@example.com)",
        )
        parsed_url = urlparse(request.full_url)
        params = parse_qs(parsed_url.query)

        self.assertEqual(parsed_url.scheme, "https")
        self.assertEqual(parsed_url.netloc, "en.wikipedia.org")
        self.assertEqual(parsed_url.path, "/w/api.php")
        self.assertEqual(params["action"], ["query"])
        self.assertEqual(params["prop"], [WIKIPEDIA_PAGE_PROPS])
        self.assertEqual(params["ppprop"], ["wikibase_item"])
        self.assertEqual(params["titles"], ["Example Film"])
        self.assertEqual(params["redirects"], ["1"])
        self.assertEqual(params["rvprop"], [WIKIPEDIA_REVISION_PROPS])
        self.assertEqual(params["rvslots"], ["main"])
        self.assertEqual(params["curtimestamp"], ["1"])
        self.assertEqual(params["format"], ["json"])
        self.assertEqual(params["formatversion"], ["2"])
        self.assertEqual(params["maxlag"], ["5"])
        self.assertEqual(
            request.get_header("User-agent"),
            "CineCue/0.1 (contact@example.com)",
        )

    def test_rejects_manifest_without_requestable_title(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one"):
            build_request(
                [
                    {
                        "wikidata_id": "Q2",
                        "wikipedia_title": None,
                        "wikipedia_url": None,
                    }
                ],
                "CineCue/0.1 (contact@example.com)",
            )

    def test_rejects_duplicate_request_titles(self) -> None:
        duplicate_manifest = [
            {
                "wikidata_id": "Q1",
                "wikipedia_title": "Example Film",
                "wikipedia_url": None,
            },
            {
                "wikidata_id": "Q2",
                "wikipedia_title": "Example Film",
                "wikipedia_url": None,
            },
        ]

        with self.assertRaisesRegex(ValueError, "duplicate"):
            requestable_titles(duplicate_manifest)

    def test_rejects_blank_user_agent(self) -> None:
        manifest = build_wikipedia_request_manifest(wikidata_response_fixture())

        with self.assertRaisesRegex(ValueError, "user_agent"):
            build_request(manifest, "  ")


class ValidateWikipediaResponseTests(unittest.TestCase):
    def test_accepts_response_with_query_object(self) -> None:
        validate_api_response(b'{"batchcomplete": true, "query": {"pages": []}}')

    def test_rejects_api_error(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "maxlag"):
            validate_api_response(b'{"error": {"code": "maxlag"}}')


if __name__ == "__main__":
    unittest.main()
