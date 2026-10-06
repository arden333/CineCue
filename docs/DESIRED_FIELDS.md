# Desired Catalog Fields

This document records the current field hypotheses for the CineCue catalog. It
is a reference for the extraction work that will follow collection of the fixed
20-title sample. The fields are not final until sample coverage and value
quality have been measured.

"Required extraction" means that the pipeline must always check the source for
the field. It does not mean that every item must have a value. Missing source
values remain `null` or an empty collection and must not be inferred.

## Common required fields

| Catalog field | Wikidata or Wikimedia source | Purpose |
| --- | --- | --- |
| `wikidata_id` | Entity QID | Stable identifier and join key |
| `title` | English label and title (P1476) | Display and search title |
| `aliases` | English aliases | Alternative title matching |
| `content_type` | instance of (P31) | Distinguish movies and TV series |
| `genres` | genre (P136) | Primary structured retrieval signal |
| `cast` | cast member (P161) | People-based preferences |
| `directors` | director (P57) | Creator-based preferences for movies and available TV records |
| `creators` | creator (P170) | Series or work creator |
| `production_companies` | production company (P272) | Production metadata |
| `countries_of_origin` | country of origin (P495) | Country and regional preferences |
| `original_languages` | original language of film or TV show (P364) | Language preferences and display |
| `adapted_from` | based on (P144) | Book and other adaptation preferences |
| `description` | English Wikidata description | Short description and fallback text |
| `plot` | English Wikipedia article sections | Rich retrieval text |
| `bbfc_ratings` | BBFC rating (P2629) | Nullable UK rating proxy for the initial release |
| `wikipedia_title` | English Wikipedia sitelink title | Wikipedia request key |
| `wikipedia_url` | English Wikipedia sitelink URL | Attribution and traceability |

## Date fields

| Catalog field | Applies to | Wikidata source | Handling |
| --- | --- | --- | --- |
| `release_dates` | Movie | publication date (P577) | Preserve all values and qualifiers before choosing a representative date |
| `series_start_date` | TV | start time (P580) | Preserve source precision |
| `series_end_date` | TV | end time (P582) | Nullable; absence does not prove that a series is ongoing |

## Movie-specific fields

| Catalog field | Wikidata source | Handling |
| --- | --- | --- |
| `runtime_minutes` | duration (P2047) | Normalize supported units to minutes |
| `previous_work` | follows (P155) | Preserve the related work QID |
| `next_work` | followed by (P156) | Preserve the related work QID |

## TV-specific fields

| Catalog field | Wikidata or Wikimedia source | Handling |
| --- | --- | --- |
| `number_of_seasons` | number of seasons (P2437) | Nullable quantity |
| `number_of_episodes` | number of episodes (P1113) | Preserve criterion and point-in-time qualifiers |
| `seasons` | has part(s) (P527) and series ordinal (P1545) | Preserve season QID and order |
| `episode_runtime_minutes` | duration (P2047) or English Wikipedia | Keep separate from movie runtime |

## Retrieval enrichment candidates

| Catalog field | Source | Current status |
| --- | --- | --- |
| `setting_periods` | set in period (P2408) | Include in extraction and measure coverage |
| `characteristics` | has characteristic (P1552) | Experimental because values are broad and inconsistently used |
| `themes` | Wikipedia text and categories | Extraction rule not yet decided |
| `keywords` | Wikipedia text and categories | Extraction rule not yet decided |
| `tropes` | Possible later content annotation | Add only if V1 failure analysis shows a metadata gap |

## Qualifiers to preserve

Qualifiers must stay attached to the statement that they describe. They must
not be flattened into unrelated item-level fields.

| Wikidata property | Meaning and use |
| --- | --- |
| character role (P453) | Role associated with a cast member |
| author (P50) | Author associated with an adapted work |
| start time (P580) | Start of a cast, creator, distributor, or rating statement |
| end time (P582) | End of a statement's validity |
| point in time (P585) | Observation date for a changing value |
| criterion used (P1013) | Basis for a quantity such as episode or season count |
| series ordinal (P1545) | Order of a season or other part |
| applies to part (P518) | Season, episode, or release to which a rating applies |
| distribution format (P437) | Release format to which a rating applies |
| rating certificate ID (P2676) | BBFC classification record identifier |
| content descriptor (P7367) | Content reason associated with a rating |

## Provenance fields

References explain where a statement came from and should not be inserted into
the retrieval document as content metadata.

- source property and source value
- statement rank
- statement qualifiers
- statement references
- reference URL
- Wikidata revision ID and modified timestamp
- Wikipedia revision ID, article URL, and language
- collection timestamp

## Excluded or deferred fields

- MPA film rating (P1657): excluded after selecting BBFC as the initial rating proxy
- Netflix maturity rating (P8652): platform-specific and not a general rating
- watch-provider availability: deferred until recommendation quality is validated
- ratings, votes, and popularity: no consistent source has been selected
- manually authored themes and tropes: conditional on V1 failure analysis

## Known limitations to test with the sample

- Item-valued claims return QIDs and require a separate label-resolution step.
- BBFC rating (P2629) has very low coverage at the whole-TV-series level.
- Director and runtime may exist at episode level rather than series level.
- A missing property can mean either missing source data or a legitimate absence.
- Wikipedia plot and section structures vary between articles.
