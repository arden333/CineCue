# Evaluation Queries

`queries.json` contains the initial requests used to evaluate CineCue. These
queries describe user intent before a real catalog exists, so they do not yet
contain content IDs or relevance labels.

## File format

```json
{
  "version": 1,
  "queries": [
    {
      "query_id": "Q001",
      "raw_query": "The user's input exactly as written.",
      "hard_constraints": {
        "content_type": "movie",
        "max_runtime_minutes": 120,
        "providers": []
      },
      "expected_preferences": {
        "genres": ["romance"],
        "themes": ["first love"],
        "tones": ["light"],
        "preferred_aspects": ["story"],
        "must_avoid": ["tragedy"]
      }
    }
  ]
}
```

## Field meanings

- `version`: format version for future migrations.
- `query_id`: unique, stable query identifier.
- `raw_query`: original user input without rewriting or translation.
- `hard_constraints`: conditions a result must satisfy.
  - `content_type`: `movie`, `tv`, or `null` when either is acceptable.
  - `max_runtime_minutes`: positive integer or `null` when unrestricted.
  - `providers`: required provider names, or an empty list when unrestricted.
- `expected_preferences`: human-authored interpretation used to inspect whether
  retrieval and ranking respond in the intended direction.
  - `genres`: preferred broad genres.
  - `themes`: preferred subjects or tropes.
  - `tones`: desired emotional qualities.
  - `preferred_aspects`: aspects that should matter most in ranking or reasons.
  - `must_avoid`: unwanted subjects, tones, or plot elements.

The normalized preference values are written in English for consistency while
`raw_query` preserves the user's original language.

## Later catalog-based labeling

After `data/processed/catalog.parquet` exists, candidate titles will be reviewed
and assigned relevance labels from `0` to `3`. Those labels are intentionally
absent from the current file and must not be invented before inspecting real
catalog items.

