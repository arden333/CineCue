"""Core CineCue data models.

These models describe the minimum information currently required by CineCue.
They are provisional and should be reviewed after inspecting real Wikidata and
Wikipedia responses.
"""

from dataclasses import dataclass
from enum import Enum
from math import isfinite


class ContentType(str, Enum):
    """Content types supported by CineCue."""

    MOVIE = "movie"
    TV = "tv"


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


@dataclass(frozen=True)
class WatchOffer:
    """One way a title is available from a provider in a region."""

    region: str
    provider_name: str
    link: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.region, "region")
        _require_text(self.provider_name, "provider_name")


@dataclass(frozen=True)
class ContentItem:
    """A movie or TV title represented in CineCue's internal catalog."""

    content_id: str
    content_type: ContentType
    title: str
    release_year: int | None = None
    vote_average: float | None = None  # Average rating when a source provides one.
    vote_count: int = 0  # Number of votes used to calculate the average rating.
    popularity: float | None = None
    overview: str = ""  # Summary of the story.
    genres: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    cast: tuple[str, ...] = ()
    runtime_minutes: int | None = None
    episode_runtime_minutes: int | None = None
    poster_url: str | None = None
    watch_offers: tuple[WatchOffer, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.content_id, "content_id")
        _require_text(self.title, "title")

        if self.release_year is not None and self.release_year <= 0:
            raise ValueError("release_year must be positive")
        if self.vote_average is not None and not 0 <= self.vote_average <= 10:
            raise ValueError("vote_average must be between 0 and 10")
        if self.vote_count < 0:
            raise ValueError("vote_count must not be negative")
        if self.popularity is not None and self.popularity < 0:
            raise ValueError("popularity must not be negative")
        if self.runtime_minutes is not None and self.runtime_minutes <= 0:
            raise ValueError("runtime_minutes must be positive")
        if (
            self.episode_runtime_minutes is not None
            and self.episode_runtime_minutes <= 0
        ):
            raise ValueError("episode_runtime_minutes must be positive")


@dataclass(frozen=True)
class UserRequest:
    """The user's original query and currently supported hard constraints."""

    raw_query: str
    content_type: ContentType | None = None
    max_runtime_minutes: int | None = None
    providers: tuple[str, ...] = ()
    excluded_keywords: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.raw_query, "raw_query")
        if self.max_runtime_minutes is not None and self.max_runtime_minutes <= 0:
            raise ValueError("max_runtime_minutes must be positive")


@dataclass(frozen=True)
class RecommendationItem:
    """One recommended title with its score and explanation."""

    content: ContentItem
    score: float
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isfinite(self.score):
            raise ValueError("score must be finite")


@dataclass(frozen=True)
class RecommendationResult:
    """The ordered recommendations produced for one user request."""

    request: UserRequest
    recommendations: tuple[RecommendationItem, ...]
