# Data

Pipeline: `staged/` (values copied from sources, with page and table) → `scripts/` (harmonize to SI and derive) → `model/` (records that validate against `containers/`). `sources/` and `quality/` hold the source and pedigree records the values cite. Rebuild with `python3 data/scripts/build_herd.py`.

## Herd module (2022, US)

One US herd from MetaFarms 2022 benchmarks serves both North Carolina and Iowa. NASS state pigs per litter (2022, Dec-Nov) are a sanity check: NC 10.74 and IA 11.48 against MetaFarms 11.27 pigs weaned per litter (-4.7% and +1.9%). A 5% litter difference moves the sow share of feed per pig by under 1%, so a state-specific herd is not justified yet (parsimony rule 1).

Derived per shipped pig (animal-days): gestation and open 13.45, farrowing-lactation 2.09, gilt development 4.89, nursery 47.42, finishing 126.25. Wean weight 6.14 kg; market weight 131.1 kg (NASS 2022 commercial average, 289 lb); finishing runs 122.8 d to reach it at MetaFarms ADG.

### Known gaps
- Cull sow live weight: not yet sourced (NASS gives sow dressed weight only, 299 lb).
- Boars and AI share: no 2022 source in hand; boar stage omitted.
- Gilt development: mortality not sourced; whether gilts are raised in-house or bought from a multiplier is still open.
- Farrowing room days before farrowing are not counted; lactation = wean age.
- MetaFarms does not state whether feed conversion includes feed eaten by pigs that died.
- Replacement rate is the unweighted mean of 2024 farm-size groups; no overall or 2022 value is printed.
- MetaFarms and NASS hosts block direct download here, so values were transcribed through a web reader. Check them against the PDFs before sign-off.
- Unit ids (animal_day, kg_per_day, ...) await the units vocabulary.
