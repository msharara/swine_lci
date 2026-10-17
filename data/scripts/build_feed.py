"""Build feeding_programs records from staged extension diets.

Reads data/staged/feed/extension_diets_raw.csv and phase_selection.csv and
writes one record per program to data/model/feeding_programs/. Recipes are
renormalized to 1 after dropping lab markers (titanium dioxide). Where a diet
prints no total P, the matching KSU MF-2301 band is used as a labeled fallback;
where neither exists (nursery phases), total P is computed from the recipe and the
open ingredient P table in ingredient_phosphorus.csv (origin "derived"). The same
calculation is checked against every diet that prints total P.
"""
import csv, json, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parents[1]
FEED = ROOT / "staged" / "feed"
ANALYSIS = {"cp", "cp_analyzed", "total_p", "sttd_p", "avail_p", "avail_p_equiv", "ca", "ne_kcal_lb", "me_kcal_lb",
            "sid_lys", "tid_lys", "total_lys", "dm", "na", "fat"}
DROP = {"titanium_dioxide"}
FLOW = lambda i: "soybean_meal" if i.startswith("soybean_meal_4") else i
REGION = {"nc_corn_sbm_2022": "NC", "ia_corn_sbm_ddgs_2022": "IA"}
SRC_ID = {"KSU_NURS_2019": "ksu_nursery_diets_2019", "KSU_SD2024_SOW": "ksu_swineday_2024_sow",
          "KSU_SD2024_GF": "ksu_swineday_2024_gf", "KSU_SD2025_DDGS": "ksu_swineday_2025_ddgs",
          "KSU_MF2301_2007": "ksu_mf2301_2007"}

P = {r["flow_id"]: (float(r["total_p_pct_as_fed"]), r["source_id"]) for r in csv.DictReader(open(FEED / "ingredient_phosphorus.csv"))}

def computed_p(recipe):
    missing = [k for k in recipe if k not in P]
    assert not missing, f"no P value for {missing}"
    return sum(v * P[k][0] for k, v in recipe.items())

diets = collections.defaultdict(list)
for r in csv.DictReader(open(FEED / "extension_diets_raw.csv")):
    diets[(r["source_id"], r["phase_label"])].append(r)

def amt(v, unit, basis, src, q, note=None, origin="entered"):
    a = {"value": round(v, 5), "unit_id": unit, "basis": basis, "source_id": src, "quality_id": q, "origin": origin}
    if note: a["note"] = note
    return a

def items(key):
    rows = diets[key]
    assert rows, key
    return {r["item"]: (float(r["value"]), r["unit"]) for r in rows}

programs = collections.defaultdict(list)
check = {}
for s in csv.DictReader(open(FEED / "phase_selection.csv")):
    it = items((s["source_id"], s["phase_label"]))
    src, q = SRC_ID[s["source_id"]], "q_ext_research" if "SD20" in s["source_id"] else "q_ext_guide"
    ing = {k: v for k, (v, u) in it.items() if k not in ANALYSIS | DROP}
    unit = next(u for k, (v, u) in it.items() if k not in ANALYSIS)
    scale = 2000 if unit == "lb_per_ton" else 100
    total = sum(ing.values())
    recipe = collections.defaultdict(float)
    for k, v in ing.items():
        recipe[FLOW(k)] += v / total  # renormalize after dropping markers
    spec = {}
    if "cp" in it: spec["crude_protein"] = amt(it["cp"][0], "percent", "as_fed", src, q, "calculated, as printed")
    if "total_p" in it:
        spec["total_phosphorus"] = amt(it["total_p"][0], "percent", "as_fed", src, q, "calculated, as printed")
        check[(s["program"], s["phase_id"])] = (computed_p(recipe), it["total_p"][0])
    elif s["total_p_fallback_label"]:
        fb = items(("KSU_MF2301_2007", s["total_p_fallback_label"]))
        spec["total_phosphorus"] = amt(fb["total_p"][0], "percent", "as_fed", SRC_ID["KSU_MF2301_2007"], "q_ext_old",
                                       f"fallback: MF-2301 band '{s['total_p_fallback_label']}'; source diet prints no total P")
    else:
        srcs = sorted({P[k][1] for k in recipe if P[k][0]})
        spec["total_phosphorus"] = amt(computed_p(recipe), "percent", "as_fed", "ingredient_phosphorus", "q_comp_derived_p",
                                       "computed: sum of inclusion x ingredient total P (" + ", ".join(srcs) + "); source diet prints no total P",
                                       origin="derived")
    if "ne_kcal_lb" in it: spec["net_energy"] = amt(it["ne_kcal_lb"][0] * 2.20462, "kcal_per_kg", "as_fed", src, q, "converted from kcal/lb")
    if "sid_lys" in it: spec["sid_lysine"] = amt(it["sid_lys"][0], "percent", "as_fed", src, q)
    if "dm" in it: spec["dry_matter"] = amt(it["dm"][0], "percent", "as_fed", src, q)
    ph = {"phase_id": s["phase_id"], "stage": s["stage"], "diet_spec": spec,
          "recipe": [{"flow_id": k, "inclusion": amt(v, "fraction", "as_fed", src, q)} for k, v in sorted(recipe.items(), key=lambda x: -x[1])]}
    if s["bw_from_kg"]: ph["body_weight_from"] = amt(float(s["bw_from_kg"]), "kg", "per_head", src, q, s["note"] or None)
    if s["bw_to_kg"]: ph["body_weight_to"] = amt(float(s["bw_to_kg"]), "kg", "per_head", src, q)
    programs[s["program"]].append(ph)

out = ROOT / "model" / "feeding_programs"
out.mkdir(parents=True, exist_ok=True)
for pid, phases in programs.items():
    rec = {"feeding_program_id": pid, "region_id": REGION[pid], "phases": phases}
    (out / f"{pid}.json").write_text(json.dumps(rec, indent=2) + "\n")
    print(pid, len(phases), "phases")

print("\ncheck: computed vs printed total P (% as-fed)")
for (pid, ph), (c, pr) in check.items():
    print(f"  {pid:24s} {ph:12s} computed {c:.3f}  printed {pr:.2f}  {100 * (c - pr) / pr:+.0f}%")
