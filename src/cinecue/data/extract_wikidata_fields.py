"""Extract the agreed catalog fields from preserved Wikidata entity responses."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_INPUT_PATH = Path("data/raw/wiki_sample/wikidata_entities.json")
DEFAULT_OUTPUT_PATH = Path("data/processed/wiki_sample/wikidata_fields.json")

MOVIE_CLASS_QIDS = {"Q11424", "Q20650540"}
TV_SERIES_CLASS_QIDS = {"Q5398426"}
MINUTE_QID = "Q7727"


# Helper: numeric amounts in quantity-valued claims.
def _parse_amount(amount: str) -> int | float:
    number = float(amount)
    return int(number) if number.is_integer() else number


# Helper: Wikidata entity URLs used as quantity units.
def _normalize_unit(unit: str) -> str:
    prefix = "http://www.wikidata.org/entity/"
    return unit.removeprefix(prefix) if unit.startswith(prefix) else unit


# Helper: values inside claims, qualifiers, and references.
def _normalize_datavalue(datavalue: dict[str, Any]) -> Any:
    value_type = datavalue.get("type")
    value = datavalue.get("value")

    if value_type == "wikibase-entityid" and isinstance(value, dict):
        return value.get("id")
    if value_type == "monolingualtext" and isinstance(value, dict):
        return {"text": value.get("text"), "language": value.get("language")}
    if value_type == "time" and isinstance(value, dict):
        return {
            "time": value.get("time"),
            "precision": value.get("precision"),
            "calendar_model": value.get("calendarmodel"),
        }
    if value_type == "quantity" and isinstance(value, dict):
        amount = value.get("amount")
        return {
            "amount": _parse_amount(amount) if isinstance(amount, str) else amount,
            "unit": _normalize_unit(str(value.get("unit", "1"))),
        }
    return value


# Helper: one mainsnak, qualifier snak, or reference snak.
def _normalize_snak(snak: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "snaktype": snak.get("snaktype"),
        "datatype": snak.get("datatype"),
        "value": None,
    }
    datavalue = snak.get("datavalue")
    if snak.get("snaktype") == "value" and isinstance(datavalue, dict):
        normalized["value"] = _normalize_datavalue(datavalue)
    return normalized


# Helper: qualifier and reference properties attached to a statement.
def _normalize_snak_group(
    snaks: dict[str, list[dict[str, Any]]] | None,
) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(snaks, dict):
        return {}
    return {
        property_id: [_normalize_snak(snak) for snak in property_snaks]
        for property_id, property_snaks in snaks.items()
    }


# Helper: source references attached to a statement.
def _normalize_references(
    references: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if not isinstance(references, list):
        return []
    return [
        {
            "hash": reference.get("hash"),
            "properties": _normalize_snak_group(reference.get("snaks")),
        }
        for reference in references
    ]


# Helper: one selected Wikidata claim with provenance preserved.
def _normalize_statement(
    property_id: str,
    statement: dict[str, Any],
) -> dict[str, Any]:
    mainsnak = statement.get("mainsnak", {})
    normalized_snak = _normalize_snak(mainsnak)
    return {
        "source_property": property_id,
        "statement_id": statement.get("id"),
        "rank": statement.get("rank"),
        "snaktype": normalized_snak["snaktype"],
        "datatype": normalized_snak["datatype"],
        "value": normalized_snak["value"],
        "qualifiers": _normalize_snak_group(statement.get("qualifiers")),
        "references": _normalize_references(statement.get("references")),
    }


# Helper: all statements for one selected Property.
def _extract_claims(
    entity: dict[str, Any],
    property_id: str,
) -> list[dict[str, Any]]:
    claims = entity.get("claims", {})
    if not isinstance(claims, dict):
        return []
    statements = claims.get(property_id, [])
    if not isinstance(statements, list):
        return []
    return [_normalize_statement(property_id, statement) for statement in statements]


# Helper: claim values used for derived fields such as content_type.
def _claim_values(entity: dict[str, Any], property_id: str) -> list[Any]:
    return [
        statement["value"]
        for statement in _extract_claims(entity, property_id)
        if statement["snaktype"] == "value"
    ]


# Fields: wikidata_id, title, aliases, description, Wikipedia link, revision.
def extract_identity_fields(entity: dict[str, Any]) -> dict[str, Any]:
    labels = entity.get("labels", {})
    descriptions = entity.get("descriptions", {})
    aliases = entity.get("aliases", {})
    enwiki = entity.get("sitelinks", {}).get("enwiki", {})

    title = labels.get("en", {}).get("value")
    if not title:
        title_claims = _claim_values(entity, "P1476")
        if title_claims and isinstance(title_claims[0], dict):
            title = title_claims[0].get("text")

    return {
        "wikidata_id": entity.get("id"),
        "title": title,
        "title_statements": _extract_claims(entity, "P1476"),
        "aliases": [alias.get("value") for alias in aliases.get("en", [])],
        "description": descriptions.get("en", {}).get("value"),
        "wikipedia_title": enwiki.get("title"),
        "wikipedia_url": enwiki.get("url"),
        "wikidata_revision_id": entity.get("lastrevid"),
        "wikidata_modified_at": entity.get("modified"),
    }


# Field: content_type from instance of (P31).
def extract_content_type_fields(entity: dict[str, Any]) -> dict[str, Any]:
    statements = _extract_claims(entity, "P31")
    qids = {
        statement["value"]
        for statement in statements
        if isinstance(statement["value"], str)
    }
    if qids & MOVIE_CLASS_QIDS:
        content_type = "movie"
    elif qids & TV_SERIES_CLASS_QIDS:
        content_type = "series"
    else:
        content_type = None
    return {"content_type": content_type, "content_type_statements": statements}


# Field: genres from genre (P136).
def extract_genre_fields(entity: dict[str, Any]) -> dict[str, Any]:
    return {"genres": _extract_claims(entity, "P136")}


# Fields: cast, directors, creators from P161, P57, and P170.
def extract_people_fields(entity: dict[str, Any]) -> dict[str, Any]:
    return {
        "cast": _extract_claims(entity, "P161"),
        "directors": _extract_claims(entity, "P57"),
        "creators": _extract_claims(entity, "P170"),
    }


# Fields: production companies, countries, languages from P272, P495, P364.
def extract_production_fields(entity: dict[str, Any]) -> dict[str, Any]:
    return {
        "production_companies": _extract_claims(entity, "P272"),
        "countries_of_origin": _extract_claims(entity, "P495"),
        "original_languages": _extract_claims(entity, "P364"),
    }


# Field: adapted_from from based on (P144).
def extract_adaptation_fields(entity: dict[str, Any]) -> dict[str, Any]:
    return {"adapted_from": _extract_claims(entity, "P144")}


# Fields: release_dates, series_start_date, series_end_date from P577/P580/P582.
def extract_date_fields(
    entity: dict[str, Any],
    content_type: str | None,
) -> dict[str, Any]:
    return {
        "release_dates": _extract_claims(entity, "P577")
        if content_type == "movie"
        else [],
        "series_start_date": _extract_claims(entity, "P580")
        if content_type == "series"
        else [],
        "series_end_date": _extract_claims(entity, "P582")
        if content_type == "series"
        else [],
    }


# Fields: movie runtime or episode runtime from duration (P2047).
def extract_runtime_fields(
    entity: dict[str, Any],
    content_type: str | None,
) -> dict[str, Any]:
    duration_statements = _extract_claims(entity, "P2047")
    for statement in duration_statements:
        value = statement["value"]
        if isinstance(value, dict) and value.get("unit") == MINUTE_QID:
            value["unit"] = "minute"

    return {
        "runtime_minutes": duration_statements if content_type == "movie" else [],
        "episode_runtime_minutes": duration_statements
        if content_type == "series"
        else [],
    }


# Fields: previous_work and next_work from follows/followed by (P155/P156).
def extract_sequence_fields(entity: dict[str, Any]) -> dict[str, Any]:
    return {
        "previous_work": _extract_claims(entity, "P155"),
        "next_work": _extract_claims(entity, "P156"),
    }


# Fields: season count, episode count, and seasons from P2437/P1113/P527.
def extract_series_structure_fields(
    entity: dict[str, Any],
    content_type: str | None,
) -> dict[str, Any]:
    if content_type != "series":
        return {"number_of_seasons": [], "number_of_episodes": [], "seasons": []}
    return {
        "number_of_seasons": _extract_claims(entity, "P2437"),
        "number_of_episodes": _extract_claims(entity, "P1113"),
        "seasons": _extract_claims(entity, "P527"),
    }


# Fields: setting_periods and characteristics from P2408 and P1552.
def extract_enrichment_fields(entity: dict[str, Any]) -> dict[str, Any]:
    return {
        "setting_periods": _extract_claims(entity, "P2408"),
        "characteristics": _extract_claims(entity, "P1552"),
    }


# Field: UK BBFC ratings from BBFC rating (P2629).
def extract_rating_fields(entity: dict[str, Any]) -> dict[str, Any]:
    return {"bbfc_ratings": _extract_claims(entity, "P2629")}


# Fields: all Wikidata-backed desired fields for one content item.
def extract_wikidata_entity(entity: dict[str, Any]) -> dict[str, Any]:
    record = extract_identity_fields(entity)
    content_type_fields = extract_content_type_fields(entity)
    record.update(content_type_fields)
    content_type = content_type_fields["content_type"]
    record.update(extract_genre_fields(entity))
    record.update(extract_people_fields(entity))
    record.update(extract_production_fields(entity))
    record.update(extract_adaptation_fields(entity))
    record.update(extract_date_fields(entity, content_type))
    record.update(extract_runtime_fields(entity, content_type))
    record.update(extract_sequence_fields(entity))
    record.update(extract_series_structure_fields(entity, content_type))
    record.update(extract_enrichment_fields(entity))
    record.update(extract_rating_fields(entity))
    return record


# Fields: all Wikidata-backed desired fields for every returned entity.
def extract_wikidata_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    entities = response.get("entities")
    if not isinstance(entities, dict):
        raise ValueError("Wikidata response must contain an entities object")
    return [
        extract_wikidata_entity(entity)
        for entity in entities.values()
        if isinstance(entity, dict) and "missing" not in entity
    ]


# Input: preserved Wikidata raw response JSON.
def load_raw_response(input_path: Path) -> dict[str, Any]:
    response = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(response, dict):
        raise ValueError("Wikidata response must be a JSON object")
    return response


# Output: extracted records plus reproducibility metadata.
def save_extracted_records(
    records: list[dict[str, Any]],
    input_path: Path,
    output_path: Path,
) -> None:
    output = {
        "schema_version": 1,
        "source_file": str(input_path),
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "items": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


# CLI: input and output paths for the extraction checkpoint.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract desired fields from a preserved Wikidata response."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


# CLI: load raw data, extract fields, and save processed records.
def main() -> None:
    args = parse_args()
    response = load_raw_response(args.input)
    records = extract_wikidata_response(response)
    save_extracted_records(records, args.input, args.output)
    print(f"Saved {len(records)} extracted Wikidata records to {args.output}")


if __name__ == "__main__":
    main()
