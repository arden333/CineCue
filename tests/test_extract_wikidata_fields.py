import unittest

from cinecue.data.extract_wikidata_fields import (
    extract_wikidata_entity,
    extract_wikidata_response,
)


def entity_claim(
    property_id: str,
    value: object,
    value_type: str = "wikibase-entityid",
    datatype: str = "wikibase-item",
    qualifiers: dict | None = None,
) -> dict:
    return {
        "mainsnak": {
            "snaktype": "value",
            "property": property_id,
            "datavalue": {"value": value, "type": value_type},
            "datatype": datatype,
        },
        "type": "statement",
        "id": f"Q1${property_id}",
        "rank": "normal",
        "qualifiers": qualifiers or {},
        "references": [
            {
                "hash": "reference-hash",
                "snaks": {
                    "P854": [
                        {
                            "snaktype": "value",
                            "property": "P854",
                            "datavalue": {
                                "value": "https://example.com/source",
                                "type": "string",
                            },
                            "datatype": "url",
                        }
                    ]
                },
            }
        ],
    }


def sample_series_entity() -> dict:
    return {
        "id": "Q1",
        "lastrevid": 123,
        "modified": "2026-01-01T00:00:00Z",
        "labels": {"en": {"language": "en", "value": "Example Series"}},
        "descriptions": {
            "en": {"language": "en", "value": "example television series"}
        },
        "aliases": {"en": [{"language": "en", "value": "Example"}]},
        "claims": {
            "P31": [
                entity_claim(
                    "P31", {"entity-type": "item", "numeric-id": 5398426, "id": "Q5398426"}
                )
            ],
            "P136": [
                entity_claim(
                    "P136", {"entity-type": "item", "numeric-id": 130232, "id": "Q130232"}
                )
            ],
            "P2437": [
                entity_claim(
                    "P2437",
                    {"amount": "+4", "unit": "1"},
                    value_type="quantity",
                    datatype="quantity",
                )
            ],
            "P527": [
                entity_claim(
                    "P527",
                    {"entity-type": "item", "numeric-id": 2, "id": "Q2"},
                    qualifiers={
                        "P1545": [
                            {
                                "snaktype": "value",
                                "property": "P1545",
                                "datavalue": {"value": "1", "type": "string"},
                                "datatype": "string",
                            }
                        ]
                    },
                )
            ],
        },
        "sitelinks": {
            "enwiki": {
                "site": "enwiki",
                "title": "Example Series",
                "url": "https://en.wikipedia.org/wiki/Example_Series",
            }
        },
    }


class ExtractWikidataEntityTests(unittest.TestCase):
    def test_extracts_identity_type_and_selected_claim_values(self) -> None:
        record = extract_wikidata_entity(sample_series_entity())

        self.assertEqual(record["wikidata_id"], "Q1")
        self.assertEqual(record["title"], "Example Series")
        self.assertEqual(record["content_type"], "series")
        self.assertEqual(record["genres"][0]["value"], "Q130232")
        self.assertEqual(record["number_of_seasons"][0]["value"]["amount"], 4)
        self.assertEqual(record["wikipedia_title"], "Example Series")

    def test_preserves_qualifiers_and_references_with_their_statement(self) -> None:
        record = extract_wikidata_entity(sample_series_entity())
        season = record["seasons"][0]

        self.assertEqual(season["value"], "Q2")
        self.assertEqual(season["qualifiers"]["P1545"][0]["value"], "1")
        self.assertEqual(
            season["references"][0]["properties"]["P854"][0]["value"],
            "https://example.com/source",
        )

    def test_keeps_missing_desired_fields_as_empty_collections(self) -> None:
        record = extract_wikidata_entity(sample_series_entity())

        self.assertEqual(record["cast"], [])
        self.assertEqual(record["bbfc_ratings"], [])
        self.assertEqual(record["release_dates"], [])


class ExtractWikidataResponseTests(unittest.TestCase):
    def test_extracts_non_missing_entities(self) -> None:
        records = extract_wikidata_response(
            {
                "entities": {
                    "Q1": sample_series_entity(),
                    "-1": {"id": "-1", "missing": ""},
                }
            }
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["wikidata_id"], "Q1")

    def test_rejects_response_without_entities_object(self) -> None:
        with self.assertRaisesRegex(ValueError, "entities"):
            extract_wikidata_response({"success": 1})


if __name__ == "__main__":
    unittest.main()
