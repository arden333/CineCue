"""Fetch and preserve the Wikidata responses for the fixed sample titles."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
WIKIDATA_ENTITY_PROPS = (
    "info|labels|descriptions|aliases|claims|sitelinks/urls"
)
MAX_TITLES_PER_REQUEST = 50
DEFAULT_SAMPLE_PATH = Path("data/samples/wiki_coverage_titles.json")
DEFAULT_OUTPUT_PATH = Path("data/raw/wiki_sample/wikidata_entities.json")


def load_sample_titles(sample_path: Path) -> list[str]:
    """Load the English Wikipedia titles from the fixed sample definition."""
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    if not isinstance(sample, dict) or not isinstance(sample.get("items"), list):
        raise ValueError("sample file must contain an items list")

    titles: list[str] = []
    for item in sample["items"]:
        if not isinstance(item, dict):
            raise ValueError("each sample item must be an object")
        title = item.get("wikipedia_title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("each sample item must have a wikipedia_title")
        titles.append(title.strip())

    return titles


def build_request(wikipedia_titles: Sequence[str], user_agent: str) -> Request:
    """Build one Wikidata request for multiple English Wikipedia pages."""
    if not user_agent.strip():
        raise ValueError("user_agent must not be empty")

    titles = [title.strip() for title in wikipedia_titles]
    if not titles:
        raise ValueError("wikipedia_titles must not be empty")
    if any(not title for title in titles):
        raise ValueError("wikipedia_titles must not contain blank titles")
    if len(titles) > MAX_TITLES_PER_REQUEST:
        raise ValueError(
            f"wikipedia_titles must contain at most {MAX_TITLES_PER_REQUEST} titles"
        )
    if len(set(titles)) != len(titles):
        raise ValueError("wikipedia_titles must not contain duplicates")

    params = {
        "action": "wbgetentities",
        "sites": "enwiki",
        "titles": "|".join(titles),
        "props": WIKIDATA_ENTITY_PROPS,
        "languages": "en",
        "sitefilter": "enwiki",
        "format": "json",
        "formatversion": "2",
        "maxlag": "5",
    }
    url = f"{WIKIDATA_API_URL}?{urlencode(params)}"
    return Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": user_agent,
        },
        method="GET",
    )


def fetch_raw_response(request: Request, timeout_seconds: float = 30.0) -> bytes:
    """Send the request and return the response body exactly as received."""
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def validate_api_response(raw_response: bytes) -> None:
    """Reject invalid JSON and API-level errors without changing the raw bytes."""
    response = json.loads(raw_response)
    if not isinstance(response, dict):
        raise ValueError("Wikidata response must be a JSON object")
    if "error" in response:
        error = response["error"]
        code = error.get("code", "unknown") if isinstance(error, dict) else "unknown"
        raise RuntimeError(f"Wikidata API returned an error: {code}")


def save_raw_response(raw_response: bytes, output_path: Path) -> None:
    """Write the unmodified response body to the raw-data directory."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(raw_response)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Wikidata entities for the fixed English Wikipedia sample."
    )
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    user_agent = os.environ.get("WIKIMEDIA_USER_AGENT", "")
    if not user_agent.strip():
        raise RuntimeError("WIKIMEDIA_USER_AGENT must be set")

    titles = load_sample_titles(args.sample)
    request = build_request(titles, user_agent)
    raw_response = fetch_raw_response(request)
    validate_api_response(raw_response)
    save_raw_response(raw_response, args.output)
    print(f"Saved {len(titles)} requested Wikidata entities to {args.output}")


if __name__ == "__main__":
    main()
