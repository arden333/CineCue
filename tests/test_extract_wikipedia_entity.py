import unittest

from cinecue.data.extract_wikipedia_entity import (
    extract_content_structure,
    extract_wikipedia_page,
    extract_wikipedia_response,
    normalize_heading,
)


SAMPLE_CONTENT = """{{Short description|Example romance series}}
{{Infobox television
| genre = Romance
}}
'''Example''' is a romance series.

== Premise ==
Two people meet.

=== Season 1 ===
They fall in love.

== Critical reception ==
Critics praised the performances.

== Unmapped section ==
Other material.

[[Category:Romance television series]]
[[Category:Example category|Sort key]]
"""


def page_fixture(content: str = SAMPLE_CONTENT) -> dict:
    return {
        "pageid": 10,
        "ns": 0,
        "title": "Example",
        "pageprops": {"wikibase_item": "Q1"},
        "revisions": [
            {
                "revid": 101,
                "parentid": 100,
                "timestamp": "2026-01-01T00:00:00Z",
                "slots": {
                    "main": {
                        "contentmodel": "wikitext",
                        "contentformat": "text/x-wiki",
                        "content": content,
                    }
                },
            }
        ],
    }


class NormalizeHeadingTests(unittest.TestCase):
    def test_normalizes_case_unicode_and_whitespace(self) -> None:
        self.assertEqual(normalize_heading("  Critical   Response  "), "critical response")


class ExtractContentStructureTests(unittest.TestCase):
    def test_maps_exact_aliases_and_inherits_parent_role(self) -> None:
        structure = extract_content_structure(SAMPLE_CONTENT)
        sections = structure["section_index"]

        self.assertEqual(sections[0]["semantic_role"], "plot")
        self.assertEqual(sections[0]["mapping_method"], "exact_alias")
        self.assertEqual(sections[1]["semantic_role"], "plot")
        self.assertEqual(sections[1]["mapping_method"], "parent_inheritance")
        self.assertEqual(sections[1]["path"], ["Premise", "Season 1"])
        self.assertEqual(sections[2]["semantic_role"], "reception")
        self.assertEqual(sections[3]["semantic_role"], "unknown")

    def test_extracts_lead_infobox_categories_and_selected_bodies(self) -> None:
        structure = extract_content_structure(SAMPLE_CONTENT)

        self.assertEqual(structure["infobox_type"], "television")
        self.assertIn("'''Example''' is a romance series.", structure["lead_raw_wikitext"])
        self.assertEqual(
            structure["categories"],
            ["Romance television series", "Example category"],
        )
        self.assertEqual(len(structure["selected_sections"]), 3)
        self.assertEqual(structure["plot_selection"]["source_type"], "section")
        self.assertFalse(structure["plot_selection"]["is_fallback"])

    def test_uses_lead_when_no_plot_alias_exists(self) -> None:
        structure = extract_content_structure(
            "'''Example''' is a romance.\n\n== Cast ==\n* Person"
        )

        self.assertEqual(structure["plot_selection"]["source_type"], "lead")
        self.assertTrue(structure["plot_selection"]["is_fallback"])
        self.assertEqual(
            structure["extraction_warnings"],
            ["plot_section_missing_used_lead"],
        )


class ExtractWikipediaPageTests(unittest.TestCase):
    def test_extracts_page_revision_and_content_provenance(self) -> None:
        record = extract_wikipedia_page(page_fixture(), "2026-01-02T00:00:00Z")

        self.assertEqual(record["wikidata_id"], "Q1")
        self.assertEqual(record["wikipedia_page_id"], 10)
        self.assertEqual(record["revision_id"], 101)
        self.assertEqual(record["parent_revision_id"], 100)
        self.assertEqual(record["retrieved_at"], "2026-01-02T00:00:00Z")
        self.assertEqual(record["content_model"], "wikitext")

    def test_rejects_page_without_revision(self) -> None:
        page = page_fixture()
        page["revisions"] = []

        with self.assertRaisesRegex(ValueError, "no revision"):
            extract_wikipedia_page(page, None)


class ExtractWikipediaResponseTests(unittest.TestCase):
    def test_skips_missing_pages(self) -> None:
        records = extract_wikipedia_response(
            {
                "curtimestamp": "2026-01-02T00:00:00Z",
                "query": {
                    "pages": [
                        page_fixture(),
                        {"title": "Missing", "missing": True},
                    ]
                },
            }
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["wikidata_id"], "Q1")

    def test_rejects_response_without_page_list(self) -> None:
        with self.assertRaisesRegex(ValueError, "query.pages"):
            extract_wikipedia_response({"query": {}})


if __name__ == "__main__":
    unittest.main()
