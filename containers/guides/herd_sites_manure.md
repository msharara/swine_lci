# Herd, sites, manure systems and production systems: field guide

Plain-language reading of four containers that are kept deliberately separate:

| Container | Schema | What it is | What it never holds |
|---|---|---|---|
| Herd | [`herd_systems`](../herd_systems.schema.json) | The animals: a group fed and maintained | Sites, buildings, manure handling |
| Site | [`sites`](../sites.schema.json) | A place with buildings | Animals, manure chain |
| Manure system | [`manure_systems`](../manure_systems.schema.json) | Custody of manure from barn floor to leaving farm storage, optionally split into solid and liquid chains | Animals, land application |
| Feeding program | [`feeding_programs`](../feeding_programs.schema.json) | The diets fed per stage and phase: nutrient spec plus ingredient recipe | Animals, requirements |
| Mortality system | [`mortality_systems`](../mortality_systems.schema.json) | Custody of dead animals at a site: equipment, resources, outputs | Animals, mortality rates |
| Production system | [`production_systems`](../production_systems.schema.json) | The assembly that puts the others together | Any numbers of its own |

**The boundary between herd and manure is excretion.** The herd produces as-excreted manure (D384.2 engine). Custody starts at the pit. Land application is handled by land pools.

Because they are separate, one herd record can run under a one-, two- or three-site layout, and under any manure chain, without being copied.

```
Production system
├── herd_id ───────────► Herd (stages, animal-days, intake, requirements, excretion, breeding)
├── site_configuration   (1, 2 or 3 sites)
├── placements[]         stage ──► site
├── site_manure[]        site ───► manure system
├── site_mortality[]     site ───► mortality system
├── feeding_program_id ──► Feeding program (phase diets: nutrient spec + recipe)
├── feed_mill_process_id ► Feed mill (located unit process; ingredients in, complete feed out)
└── transport links      derived wherever pigs move between sites
```

## Herd

| Field | Required | Meaning |
|---|---|---|
| `herd_id` | yes | Unique name |
| `species` | yes | swine, broiler, layer, dairy, beef |
| `functional_unit` | yes | "1 shipped market pig at 2022-typical slaughter weight" |
| `reference_year` | yes | 2022 |
| `stages[]` | yes | One per stage: gestation, farrowing_lactation, gilt_development, boar, nursery, finishing |
| `stages[].animal_days_per_unit` | yes | Animal-days of the stage per shipped pig |
| `stages[].body_weight_in` / `body_weight_out` | no | Weights entering and leaving the stage (D384.2 inputs) |
| `stages[].mortality_rate` | no | Share lost in the stage |
| `stages[].feed_intake` / `average_daily_gain` | no | Performance of this genetics in this stage |
| `stages[].requirements` | no | Nutrient requirement (net energy, SID lysine, digestible P, CP), used to check diets |
| `stages[].excretion_process_id` | no | As-excreted manure model for the stage |
| `genetics` | no | Genetic line or lean-growth class |
| `breeding` | no | AI share, litters per sow per year, pigs weaned per litter, semen supply |

## Site

| Field | Required | Meaning |
|---|---|---|
| `site_id` | yes | Unique name |
| `region_id` | yes | Where it is (state or region) |
| `housing_type` | yes | confinement_curtain_sided, confinement_tunnel_ventilated, hoop_barn, outdoor |
| `stages_supported` | yes | Which stages the buildings can house |
| `capacity` | no | Head spaces |
| `infrastructure_process_ids` | no | Buildings and equipment |
| `energy_process_ids` | no | Heating, ventilation, lighting |
| `downtime_days_per_turn` | no | Empty days between groups; sets turns and pigs per year, which divide yearly site energy and materials |

## Manure system

| Field | Required | Meaning |
|---|---|---|
| `manure_system_id` | yes | Unique name |
| `in_house.type` | yes | deep_pit or shallow_pit |
| `external_steps[]` | depends | Ordered steps: slurry_tank_above_ground, anaerobic_digester, anaerobic_lagoon_single_stage, anaerobic_lagoon_multi_stage |
| each step's `process_id` | no | Its losses and infrastructure |

| `external_steps[].type` = `solid_liquid_separator` | optional | Splits manure into a solid and a liquid fraction; must be the last external step |
| `partition` | separator | Share of mass, total solids, VS, N, P and K sent to the solid fraction |
| `solid_fraction` / `liquid_fraction` | separator | Each has its own `steps[]` (solid: solid_storage, composting; liquid: the tank, digester and lagoon types) and one or more `exits[]` with shares summing to 1 |
| `exits[].share` | separator | Share of the stream taking this exit, so part can leave and part stay |
| `exits[].fate` | separator | `land_applied` (goes on to land pools), `kept_on_site` (other on-farm use, reported) or `exported_off_site` |
| `exits[].use` | if exported | fuel_pyrolysis, fuel_gasification, composting_feedstock |
| `exits[].removal_interval_days` | no | Days between removals, e.g. 7 for weekly hauling; sets on-site holding time |
| `exits[].transport_link_id` | if exported | Farm to off-site processor |

Rules the schema enforces: a deep pit has no external steps; a shallow pit has at least one; only a separator carries a partition and two fractions; an exported stream names its use and transport link. A digester followed by a lagoon is simply two ordered external steps. Lagoon steps' unit processes also carry the lagoon water balance (rain, evaporation, flush water); its effluent volume is the term handed to land application.

## Mortality system

Custody of dead animals at a site. Carcass mass per shipped pig comes from the herd (deaths times weight at death), so it is not entered here.

| Field | Required | Meaning |
|---|---|---|
| `mortality_system_id` | yes | Unique name |
| `type` | yes | composting_in_vessel, composting_aerated_static_bin, rendering_refrigerated_storage, incineration_onsite |
| `fuel` | incineration | propane or natural_gas |
| `design_capacity` | yes | Sizing: carcass kg per day, or refrigerated box volume for rendering |
| `service_life_years` | yes | Spreads the unit's materials over the carcasses it handles |
| `capital_cost` / `operating_cost` | no | USD; kept for later economic allocation, not summed into the inventory |
| `infrastructure_process_id` | no | Materials of the unit itself |
| `resources[]` | yes | Per kg carcass: fuel, electricity, labor, carbon-rich amendment (composting) |
| `outputs[]` | no | Compost or ash `used_on_site`; refrigerated carcass `shipped_to_renderer` with a transport link |

## Feeding program

Requirement belongs to the animal; the diet is a management choice. The program lists phases per stage, each with a diet spec (CP, total P, DM, net energy, SID lysine, DM digestibility, which feed the D384.2 inputs) and a recipe of ingredients with inclusion rates. Each ingredient can name its origin region, transport link and production process, which is how feed acres and rail or truck legs get attached.

| Field | Required | Meaning |
|---|---|---|
| `feeding_program_id` | yes | Unique name |
| `region_id` | yes | Region whose diets these are |
| `phases[]` | yes | stage, phase_id, weight range, `diet_spec`, `recipe[]` |
| `recipe[].flow_id` | yes | Ingredient |
| `recipe[].inclusion` | yes | As-fed fraction of the diet |
| `recipe[].origin_region_id` | no | Where it was grown or made |

## Production system

| Field | Required | Meaning |
|---|---|---|
| `production_system_id` | yes | Unique name |
| `herd_id` | yes | Which herd |
| `site_configuration` | yes | single_site_sow_to_finish, two_site_sow_nursery__finishing, three_site_sow__nursery__finishing |
| `placements[]` | yes | Which site each herd stage is on |
| `site_manure[]` | yes | Which manure system serves each site |
| `site_mortality[]` | yes | Which mortality system serves each site |
| `feeding_program_id` | yes | Which feeding program is fed |
| `feed_mill_process_id` | no | Which mill makes the feed; omit for on-farm mixing |
| `transport_link_ids` | no | Pig movements between sites, derived from placements |

## Every number is an "amount"

| Part | Required | Meaning |
|---|---|---|
| `value` | yes | The number |
| `unit_id` | yes | Its unit |
| `basis` | yes | as_fed, dry_matter, per_head, per_head_day, per_stage, per_functional_unit, per_area, absolute |
| `source_id` | yes | Where it came from |
| `quality_id` | no | Quality score and uncertainty |
| `origin` | no | entered (default), derived (engine recomputes each run) or overridden (user value kept and flagged in results) |
| `note` | no | Free text |

## Illustrative records

Structure is real; **every number is a placeholder (0)**. One herd, run as a three-site North Carolina system.

```json
{
  "herd": {
    "herd_id": "swine_market_pig_2022",
    "species": "swine",
    "functional_unit": "1 shipped market pig at 2022-typical slaughter weight",
    "reference_year": 2022,
    "stages": [
      {"stage": "finishing",
       "animal_days_per_unit": {"value": 0, "unit_id": "animal_day", "basis": "per_functional_unit", "source_id": "TBD"},
       "excretion_process_id": "d384_swine_grow_finish"}
    ],
    "breeding": {"ai_share": {"value": 0, "unit_id": "fraction", "basis": "absolute", "source_id": "TBD"},
                 "semen_supply_process_id": "boar_stud_semen"}
  },
  "sites": [
    {"site_id": "nc_sow_farm", "region_id": "NC", "housing_type": "confinement_curtain_sided",
     "stages_supported": ["gestation", "farrowing_lactation", "gilt_development"]},
    {"site_id": "nc_nursery", "region_id": "NC", "housing_type": "confinement_tunnel_ventilated",
     "stages_supported": ["nursery"]},
    {"site_id": "nc_finisher", "region_id": "NC", "housing_type": "confinement_curtain_sided",
     "stages_supported": ["finishing"]}
  ],
  "manure_systems": [
    {"manure_system_id": "shallow_pit_to_lagoon",
     "in_house": {"type": "shallow_pit"},
     "external_steps": [{"type": "anaerobic_lagoon_single_stage"}]},
    {"manure_system_id": "deep_pit_only",
     "in_house": {"type": "deep_pit"}, "external_steps": []}
  ],
  "feeding_program": {
    "feeding_program_id": "nc_corn_sbm_2022",
    "region_id": "NC",
    "phases": [
      {"phase_id": "finisher_1", "stage": "finishing",
       "diet_spec": {"crude_protein": {"value": 0, "unit_id": "percent", "basis": "as_fed", "source_id": "TBD"}},
       "recipe": [
         {"flow_id": "corn_grain", "inclusion": {"value": 0, "unit_id": "fraction", "basis": "as_fed", "source_id": "TBD"},
          "origin_region_id": "IA"},
         {"flow_id": "soybean_meal", "inclusion": {"value": 0, "unit_id": "fraction", "basis": "as_fed", "source_id": "TBD"}}
       ]}
    ]
  },
  "production_system": {
    "production_system_id": "nc_3site_example",
    "herd_id": "swine_market_pig_2022",
    "feeding_program_id": "nc_corn_sbm_2022",
    "site_configuration": "three_site_sow__nursery__finishing",
    "placements": [
      {"stage": "gestation", "site_id": "nc_sow_farm"},
      {"stage": "farrowing_lactation", "site_id": "nc_sow_farm"},
      {"stage": "gilt_development", "site_id": "nc_sow_farm"},
      {"stage": "nursery", "site_id": "nc_nursery"},
      {"stage": "finishing", "site_id": "nc_finisher"}
    ],
    "site_manure": [
      {"site_id": "nc_sow_farm", "manure_system_id": "shallow_pit_to_lagoon"},
      {"site_id": "nc_nursery", "manure_system_id": "shallow_pit_to_lagoon"},
      {"site_id": "nc_finisher", "manure_system_id": "deep_pit_only"}
    ]
  }
}
```

Switching this to a two-site layout changes only the production system record: new placements and site_manure. Feeding the same herd an Iowa DDGS diet means a new feeding program and one changed id. The herd, site and manure records stay as they are.

## Co-products (fix #3)

Cull sows and cull boars leave the farm alive. The engine sets `herd.co_products[]` (head and kg live weight per shipped pig) from `breeding.replacement_rate`, breeding-herd deaths and `breeding.cull_weight`. They are reported, not allocated: in v1 every burden stays on the market pig, and the record is ready for mass allocation later.

## Phase intake split (fix #4)

The engine sets each feeding phase's `intake_share` of its stage's intake. Method: read the herd stage's cumulative intake curve at the phase's `body_weight_from` and `body_weight_to`. Fallback: the phase's share of the stage's weight gain. `intake_share_method` records which was used. D384.2 then runs forward per phase on that intake and the phase diet; diets are never inferred from manure.

## Manure pooled by site (fix #6)

The engine sums the as-excreted manure of every stage placed on a site and runs that site's manure system once on the pooled stream. Each stage keeps its share of the result in proportion to what it contributed. Two barns with different pit types on one farm are entered as two site records.

## Manure application (fix #8)

`production_systems.manure_application[]` sends each site's stored manure to manure-receiving land pools: share, method (broadcast_surface, broadcast_incorporated, injection, spray_irrigation, subsurface_drip_irrigation, banded_drop_in_canopy such as a 360 RAIN hose-reel), timing (pre_planting, post_harvest, in_season), rate basis (nitrogen or phosphorus), storage-to-field transport link and equipment process. Land pools carry the rotation as `crops[]` with shares, plus an optional `cover_crop` that is incorporated (plowed in) or harvested.
