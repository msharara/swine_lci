# Data

Pipeline: `staged/` (values copied from sources, with page and table) → `scripts/` (harmonize to SI and derive) → `model/` (records that validate against `containers/`). `sources/` and `quality/` hold the source and pedigree records the values cite. Rebuild with `python3 data/scripts/build_herd.py` and `python3 data/scripts/build_feed.py`.

## Herd module (2022, US)

One US herd from MetaFarms 2022 benchmarks serves both North Carolina and Iowa. NASS state pigs per litter (2022, Dec-Nov) are a sanity check: NC 10.74 and IA 11.48 against MetaFarms 11.27 pigs weaned per litter (-4.7% and +1.9%). A 5% litter difference moves the sow share of feed per pig by under 1%, so a state-specific herd is not justified yet (parsimony rule 1).

Derived per shipped pig (animal-days): gestation and open 13.45, farrowing-lactation 2.09, gilt development 4.89, nursery 47.42, finishing 126.25. Wean weight 6.14 kg; market weight 131.1 kg (NASS 2022 commercial average, 289 lb); finishing runs 122.8 d to reach it at MetaFarms ADG.

### Feed intake (as-fed, per head per day)
Gestation 1.81 kg/d: PIC base energy level of 5.9 Mcal ME/d (used when gilt breeding weight is under 160 kg; ours is 147.5) divided by the gestation diet's ME (KSU Swine Day 2024 control, 3.27 Mcal/kg), also applied to open days. Lactation 5.24 kg/d: PIC's published daily intake curves for parity 1 and parity 2+ averaged over the 21.3-day lactation, weighted by a parity-1 share of 0.26 (replacement rate / litters per year). Gilts 2.11 kg/d: finishing feed conversion times gilt ADG (0.74 kg/d), because no open gilt intake source exists. Nursery and finishing come from MetaFarms feed conversion times ADG.

Feed per shipped pig is 391 kg: gestation 24.3, lactation 10.9, gilts 10.3, nursery 28.9, finishing 316.6. As a rough check, IFEEDER's 2023 US hog feed (55.2 Mt) over about 125 M hogs slaughtered gives about 440 kg per head, which also feeds inventory carried over and exported pigs. Chiba (2023, NRC 2012 based) sow intakes (gestation 2.1 to 2.3, lactation 5.9 to 6.6 kg/d) are kept as a sanity check only, since the book is not open.

### Known gaps
- Cull sow live weight: not yet sourced (NASS gives sow dressed weight only, 299 lb).
- Boars and AI share: no 2022 source in hand; boar stage omitted.
- Gilt feed intake is derived (finishing feed conversion x gilt ADG), not sourced.
- Gilt development: mortality not sourced; whether gilts are raised in-house or bought from a multiplier is still open.
- Farrowing room days before farrowing are not counted; lactation = wean age.
- MetaFarms does not state whether feed conversion includes feed eaten by pigs that died.
- Replacement rate is the unweighted mean of 2024 farm-size groups; no overall or 2022 value is printed.
- MetaFarms and NASS hosts block direct download here, so values were transcribed through a web reader. Check them against the PDFs before sign-off.
- Unit ids (animal_day, kg_per_day, ...) await the units vocabulary.

## Feeding programs (NC and Iowa)

Recipes are published extension and public diets (Mahmoud's choice), picked per phase in `staged/feed/phase_selection.csv` from `staged/feed/extension_diets_raw.csv`. NC uses corn-soybean meal diets throughout. Iowa uses DDGS diets where a public one exists (nursery phases 2 and 3 at 10%, finishing at 30% from 34 to 59 kg and 15% from 79 kg to market) and corn-SBM elsewhere. Lab markers (titanium dioxide) are dropped and recipes renormalized. Where a diet prints no total P, the matching KSU MF-2301 (2007) band is used and labeled as a fallback.

### Sanity check against IFEEDER 2023 (grow-out feed only)
| Ingredient share | NC model | NC IFEEDER | IA model | IA IFEEDER |
|---|---|---|---|---|
| Corn | 0.768 | 0.705 | 0.697 | 0.654 |
| Soybean meal | 0.201 | 0.086 | 0.132 | 0.108 |
| DDGS | 0.000 | 0.065 | 0.138 | 0.116 |

Iowa is close. NC soybean meal is more than twice IFEEDER's share: the public KSU corn-SBM diets use more SBM than NC's actual mix, which leans on wheat, byproducts and synthetic amino acids.

### NC State 2005 program (staged, not used)
`staged/feed/ncsu_2005_program.csv` holds the NC State 2005 nursery-to-finish program (7 phases, with CP, total P, feed budget per pig and in-feed antibiotics), transcribed from the extension page's Table 2; every phase sums to 100%. It is the only NC-specific public diet found, but it predates the 2019-2025 window by 14 years, carries about 7% lard, and its soybean meal (12-34%) is as high as the KSU diets, so it does not fix the NC soybean meal gap. Role: sanity check.

### Known gaps
- No public gilt development diet: market-pig grow-finish diets stand in (PIC says gilt Lys:energy follows market gilts).
- No public early-gestation diet after 2015: the late-gestation control diet is used for all of gestation.
- No NC or Southeast public diets; all recent diets are from Kansas State. Grow-finish diets are research treatments (the Low SBM arm, closest to practice), not recommendations.
- Nursery diets print no total P and MF-2301 has no nursery band, so nursery total P is empty.
- Sow and gilt daily feed intake are not yet in the herd record.
- Licensing: KSU material is free for educational use, all other rights reserved (not Creative Commons).
