# LCI data containers

Sixteen containers hold every value the model uses. Each file here is a JSON Schema
template (draft 2020-12) for one container; the records themselves will live under
`../data/model/` once sources are harmonized.

| Container | Layer | Holds |
|---|---|---|
| `herd_systems` | Building block | The animals only: stages, animal-days, weights, intake, requirements, mortality, excretion, breeding per functional unit |
| `sites` | Building block | A place with buildings: region, housing type, stages supported, capacity, infrastructure and energy |
| `manure_systems` | Building block | Manure custody from barn floor to land application: deep or shallow pit, ordered external steps, optional solid-liquid separation |
| `feeding_programs` | Building block | Phase diets per stage: nutrient spec plus ingredient recipe with origin regions |
| `mortality_systems` | Building block | Dead-animal custody per site: composting (in-vessel or aerated static bin), refrigerated storage for rendering, or on-site incineration; sizing, costs, resources, outputs |
| `production_systems` | Building block | The assembly: herd stages placed on sites, a manure system and a mortality system per site, the feeding program, derived transport links |
| `unit_processes` | Building block | Inputs and outputs per reference amount (farm, direct input production, background) |
| `land_pools` | Building block | Feed acres (origin region) and manure acres (near farm); overlap only when declared |
| `transport_links` | Building block | Every movement between two locations, with mode, distance, load and empty return |
| `flows` | Vocabulary | One name per input/output, with crosswalks from source terms |
| `units` | Vocabulary | Conversion factors to SI, including flow-specific ones (bushel of corn to kg) |
| `regions` | Vocabulary | States (FIPS) and named groups of states; region definitions still to set |
| `sources` | Vocabulary | Citation, year, region, kind, license, raw file path |
| `quality` | Overlay | Pedigree scores (1 to 5) and uncertainty range |
| `scenarios` | Overlay | Named overrides, such as farm presets |
| `results` | Output | Written by the engine per run: inventory rows per shipped pig (traceable to step, site, stage, process), co-products, sanity checks, overrides, quality |

Field guide for herd, sites, manure and production systems: [guides/herd_sites_manure.md](guides/herd_sites_manure.md).

Rules every container follows:
- Building blocks never store a raw name, unit or place; they store ids from the vocabularies.
- Every quantity is an `amount`: value, unit_id, basis (as-fed, dry matter, per head-day, ...), source_id, optional quality_id.

## Data layers (`../data/`)
- `raw/` as received, never edited
- `staged/` tidy tables, original units and names
- `harmonized/` mapped to the vocabularies, SI units, region codes, quality scored
- `model/` filled containers, versioned

Plan and rationale: the "Data containers" tab of the plan doc
(https://claude.ai/code/artifact/a3cbbad0-78a7-4491-9b5e-f151e017bfa2).
