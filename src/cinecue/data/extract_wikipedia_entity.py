"""Extract structural fields from preserved English Wikipedia wikitext."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import mwparserfromhell
from mwparserfromhell.nodes import Heading
from mwparserfromhell.wikicode import Wikicode


DEFAULT_INPUT_PATH = Path("data/raw/wiki_sample/wikipedia_entities.json")
DEFAULT_OUTPUT_PATH = Path(
    "data/processed/wiki_sample/wikipedia_fields.json"
)
SECTION_MAPPING_VERSION = "1.0"

SECTION_ALIASES = {
    "plot": {
        "plot",
        "premise",
        "synopsis",
        "story",
        "storyline",
        "plot summary",
    },
    "themes_analysis": {
        "themes",
        "analysis",
        "analysis and themes",
        "major themes and analysis",
        "thematic analysis",
    },
    "reception": {
        "reception",
        "critical response",
        "critical reception",
    },
}


def normalize_heading(heading: str) -> str:
    """Normalize heading text before exact alias matching."""
    normalized = unicodedata.normalize("NFKC", heading)
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def exact_semantic_role(normalized_heading: str) -> str | None:
    """Return the canonical role for an exact heading alias."""
    for role, aliases in SECTION_ALIASES.items():
        if normalized_heading in aliases:
            return role
    return None


def identify_infobox_type(wikicode: Wikicode) -> str | None:
    """Identify the top-level infobox without extracting duplicate metadata."""
    for template in wikicode.filter_templates(recursive=False):
        template_name = normalize_heading(str(template.name))
        if template_name.startswith("infobox "):
            return template_name.removeprefix("infobox ")
    return None


def extract_categories(wikicode: Wikicode) -> list[str]:
    """Extract category names in source order without their optional sort keys."""
    categories: list[str] = []
    seen: set[str] = set()
    for link in wikicode.filter_wikilinks(recursive=True):
        title = str(link.title).strip()
        if not title.casefold().startswith("category:"):
            continue
        category = title.split(":", 1)[1].strip()
        if category and category not in seen:
            categories.append(category)
            seen.add(category)
    return categories


def extract_content_structure(content: str) -> dict[str, Any]:
    """Split wikitext into a lead, section index, and aliased section bodies."""
    wikicode = mwparserfromhell.parse(content)
    lead_nodes: list[Any] = []
    sections: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []
    current_section: dict[str, Any] | None = None

    for node in wikicode.nodes:
        if not isinstance(node, Heading):
            if current_section is None:
                lead_nodes.append(node)
            else:
                current_section["body_nodes"].append(node)
            continue

        if current_section is not None:
            sections.append(current_section)

        level = int(node.level)
        heading = str(node.title.strip_code()).strip()
        normalized_heading = normalize_heading(heading)

        while stack and stack[-1]["level"] >= level:
            stack.pop()

        role = exact_semantic_role(normalized_heading)
        if role is not None:
            mapping_method = "exact_alias"
        elif stack and stack[-1]["semantic_role"] != "unknown":
            role = stack[-1]["semantic_role"]
            mapping_method = "parent_inheritance"
        else:
            role = "unknown"
            mapping_method = "unmapped"

        current_section = {
            "order": len(sections),
            "heading": heading,
            "normalized_heading": normalized_heading,
            "level": level,
            "path": [section["heading"] for section in stack] + [heading],
            "semantic_role": role,
            "mapping_method": mapping_method,
            "body_nodes": [],
        }
        stack.append(current_section)

    if current_section is not None:
        sections.append(current_section)

    section_index = [
        {key: value for key, value in section.items() if key != "body_nodes"}
        for section in sections
    ]
    selected_sections = [
        {
            **{key: value for key, value in section.items() if key != "body_nodes"},
            "raw_wikitext": "".join(str(node) for node in section["body_nodes"]).strip(),
        }
        for section in sections
        if section["semantic_role"] != "unknown"
    ]

    plot_sections = [
        section for section in selected_sections if section["semantic_role"] == "plot"
    ]
    if plot_sections:
        plot_selection = {
            "source_type": "section",
            "source_headings": [section["heading"] for section in plot_sections],
            "section_orders": [section["order"] for section in plot_sections],
            "is_fallback": False,
        }
        warnings: list[str] = []
    else:
        plot_selection = {
            "source_type": "lead",
            "source_headings": [],
            "section_orders": [],
            "is_fallback": True,
        }
        warnings = ["plot_section_missing_used_lead"]

    return {
        "infobox_type": identify_infobox_type(wikicode),
        "lead_raw_wikitext": "".join(str(node) for node in lead_nodes).strip(),
        "plot_selection": plot_selection,
        "section_index": section_index,
        "selected_sections": selected_sections,
        "categories": extract_categories(wikicode),
        "extraction_warnings": warnings,
    }


def wikipedia_url(title: str) -> str:
    """Build the canonical English Wikipedia article URL from its title."""
    return f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"


def extract_wikipedia_page(
    page: dict[str, Any],
    retrieved_at: str | None,
) -> dict[str, Any]:
    """Extract page provenance and structural content from one API page result."""
    revisions = page.get("revisions")
    if not isinstance(revisions, list) or not revisions:
        raise ValueError(f"Wikipedia page {page.get('title')} has no revision")
    revision = revisions[0]
    main_slot = revision.get("slots", {}).get("main", {})
    content = main_slot.get("content")
    if not isinstance(content, str):
        raise ValueError(f"Wikipedia page {page.get('title')} has no main content")

    title = page.get("title")
    if not isinstance(title, str) or not title:
        raise ValueError("Wikipedia page must have a title")

    record = {
        "wikidata_id": page.get("pageprops", {}).get("wikibase_item"),
        "wikipedia_page_id": page.get("pageid"),
        "wikipedia_title": title,
        "wikipedia_url": wikipedia_url(title),
        "revision_id": revision.get("revid"),
        "parent_revision_id": revision.get("parentid"),
        "revision_timestamp": revision.get("timestamp"),
        "retrieved_at": retrieved_at,
        "content_model": main_slot.get("contentmodel"),
        "content_format": main_slot.get("contentformat"),
    }
    record.update(extract_content_structure(content))
    return record


def extract_wikipedia_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract every non-missing page from a formatversion-2 API response."""
    query = response.get("query")
    if not isinstance(query, dict) or not isinstance(query.get("pages"), list):
        raise ValueError("Wikipedia response must contain a query.pages list")
    retrieved_at = response.get("curtimestamp")
    return [
        extract_wikipedia_page(page, retrieved_at)
        for page in query["pages"]
        if isinstance(page, dict) and "missing" not in page
    ]


def load_raw_response(input_path: Path) -> dict[str, Any]:
    """Load a preserved Wikipedia raw response."""
    response = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(response, dict):
        raise ValueError("Wikipedia response must be a JSON object")
    return response


def save_extracted_records(
    records: list[dict[str, Any]],
    input_path: Path,
    output_path: Path,
) -> None:
    """Save structural fields with extraction and mapping version metadata."""
    output = {
        "schema_version": 1,
        "section_mapping_version": SECTION_MAPPING_VERSION,
        "source_file": str(input_path),
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "items": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract structural fields from preserved Wikipedia wikitext."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    response = load_raw_response(args.input)
    records = extract_wikipedia_response(response)
    save_extracted_records(records, args.input, args.output)
    print(f"Saved {len(records)} extracted Wikipedia records to {args.output}")


if __name__ == "__main__":
    main()
