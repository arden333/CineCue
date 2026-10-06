"""Fetch and preserve English Wikipedia pages linked from Wikidata entities."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_PAGE_PROPS = "pageprops|revisions"
WIKIPEDIA_REVISION_PROPS = "ids|timestamp|content"
MAX_TITLES_PER_REQUEST = 50
DEFAULT_WIKIDATA_INPUT_PATH = Path(
    "data/raw/wiki_sample/wikidata_entities.json"
)
DEFAULT_OUTPUT_PATH = Path("data/raw/wiki_sample/wikipedia_entities.json")


def build_wikipedia_request_manifest(
    wikidata_response: dict[str, Any],
) -> list[dict[str, str | None]]:
    """Keep the QID-to-English-Wikipedia mapping needed for later requests."""
    entities = wikidata_response.get("entities")
    if not isinstance(entities, dict):
        raise ValueError("Wikidata response must contain an entities object")

    manifest: list[dict[str, str | None]] = []
    for entity in entities.values():
        if not isinstance(entity, dict) or "missing" in entity:
            continue
        enwiki = entity.get("sitelinks", {}).get("enwiki", {})
        manifest.append(
            {
                "wikidata_id": entity.get("id"),
                "wikipedia_title": enwiki.get("title"),
                "wikipedia_url": enwiki.get("url"),
            }
        )
    return manifest


def requestable_titles(
    manifest: Sequence[dict[str, str | None]],
) -> list[str]:
    """Return non-empty Wikipedia titles while retaining missing links in the manifest."""
    titles = [
        title.strip()
        for item in manifest
        if isinstance((title := item.get("wikipedia_title")), str)
        and title.strip()
    ]
    if len(set(titles)) != len(titles):
        raise ValueError("Wikipedia request manifest must not contain duplicate titles")
    return titles


def build_request(
    manifest: Sequence[dict[str, str | None]],
    user_agent: str,
) -> Request:
    """Build one batch request for the requestable English Wikipedia pages."""
    if not user_agent.strip():
        raise ValueError("user_agent must not be empty")

    titles = requestable_titles(manifest)
    if not titles:
        raise ValueError("manifest must contain at least one Wikipedia title")
    if len(titles) > MAX_TITLES_PER_REQUEST:
        raise ValueError(
            f"manifest must contain at most {MAX_TITLES_PER_REQUEST} requestable titles"
        )

    params = {
        "action": "query",
        "prop": WIKIPEDIA_PAGE_PROPS,
        "ppprop": "wikibase_item",
        "titles": "|".join(titles),
        "redirects": "1",
        "rvprop": WIKIPEDIA_REVISION_PROPS,
        "rvslots": "main",
        "curtimestamp": "1",
        "format": "json",
        "formatversion": "2",
        "maxlag": "5",
    }
    url = f"{WIKIPEDIA_API_URL}?{urlencode(params)}"
    return Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": user_agent,
        },
        method="GET",
    )


def fetch_raw_response(request: Request, timeout_seconds: float = 60.0) -> bytes:
    """Send the request and return the response body exactly as received."""
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def validate_api_response(raw_response: bytes) -> None:
    """Reject invalid JSON, API errors, and responses without a query result."""
    response = json.loads(raw_response)
    if not isinstance(response, dict):
        raise ValueError("Wikipedia response must be a JSON object")
    if "error" in response:
        error = response["error"]
        code = error.get("code", "unknown") if isinstance(error, dict) else "unknown"
        raise RuntimeError(f"Wikipedia API returned an error: {code}")
    if not isinstance(response.get("query"), dict):
        raise ValueError("Wikipedia response must contain a query object")


def save_raw_response(raw_response: bytes, output_path: Path) -> None:
    """Write the unmodified response body to the raw-data directory."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(raw_response)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Wikipedia pages linked from preserved Wikidata entities."
    )
    parser.add_argument(
        "--wikidata-input",
        type=Path,
        default=DEFAULT_WIKIDATA_INPUT_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    user_agent = os.environ.get("WIKIMEDIA_USER_AGENT", "")
    if not user_agent.strip():
        raise RuntimeError("WIKIMEDIA_USER_AGENT must be set")

    wikidata_response = json.loads(
        args.wikidata_input.read_text(encoding="utf-8")
    )
    manifest = build_wikipedia_request_manifest(wikidata_response)
    request = build_request(manifest, user_agent)
    raw_response = fetch_raw_response(request)
    validate_api_response(raw_response)
    save_raw_response(raw_response, args.output)
    print(
        f"Saved {len(requestable_titles(manifest))} requested Wikipedia pages "
        f"to {args.output}"
    )


if __name__ == "__main__":
    main()
