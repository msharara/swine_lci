"""Build as-excreted manure unit processes (ASAE D384.2 MAR2005, Section 9, swine).

For each feeding program and herd stage, runs the D384.2 intake-minus-retention
equations once per stage, with the stage diet taken as the intake-weighted mean of
its feeding phases (phase shares by weight gain, fix #4 fallback). Writes one
unit process per program and stage to data/model/unit_processes/, with outputs
per animal-day of the stage, and prints a per-shipped-pig summary with checks.

Equations are implemented from the standard (cited, not reproduced); D384.2 has no
swine K or VS equations, so K and VS/TS come from its typical-value tables (fallback).
Sanity checks: IPCC 2006 Tier 2 N excretion (30% of N intake retained) and the
D384.2 typical values per animal-day. Units: intake g/d -> results in g.
"""
import csv, json, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parents[1]
ST = ROOT / "staged" / "excretion"
LB = 0.45359237
STD, TYP = "asabe_d384_2", "asabe_d384_2_table1"

inp = collections.defaultdict(dict)
for r in csv.DictReader(open(ST / "d384_inputs.csv")):
    inp[r["parameter"]][r["stage"]] = (float(r["value"]), r["source_id"])
def par(name, stage):
    d = inp[name]
    return d[stage] if stage in d else d["all"]

herd = json.loads((ROOT / "model" / "herd_systems" / "swine_market_pig_2022_us.json").read_text())
stg = {s["stage"]: s for s in herd["stages"]}
v = lambda st, k: stg[st][k]["value"]
mf = {(r["metric"], r["phase"]): float(r["value"]) for r in csv.DictReader(open(ROOT / "staged" / "herd" / "metafarms_2022.csv"))}

# sow weights: PIC Table H2, mean of parity categories, at breeding (d0) and d114
h2 = list(csv.DictReader(open(ST / "pic_sow_weight_h2.csv")))
GL = par("GL", "gestation")[0]
wt = lambda d: sum(float(r["intercept"]) + float(r["a"]) * d + float(r["b"]) * d * d for r in h2) / len(h2)
LITTER = mf[("average_born_alive", "sow")]
SW_BREED, SW_LATE = wt(0), wt(GL)
LW_BIRTH = LITTER * par("piglet_birth_weight", "gestation")[0]
SW_PF_LACT = SW_LATE - par("conceptus_mass_per_pig", "gestation")[0] * LITTER
SW_WEAN = SW_PF_LACT + par("sow_weight_change_lactation", "farrowing_lactation")[0]
LW_WEAN = herd["breeding"]["pigs_weaned_per_litter"]["value"] * v("nursery", "body_weight_in")
LL = mf[("average_wean_age", "sow")]


def stage_diet(phases, stage):
    """Intake-weighted CP, P, DM (% as-fed) of a stage's phases; weights = share of weight gain."""
    ph = [p for p in phases if p["stage"] == stage]
    if len(ph) == 1:
        w = [1.0]
    else:
        lo, hi = v(stage, "body_weight_in") if "body_weight_in" in stg[stage] else ph[0]["body_weight_from"]["value"], v(stage, "body_weight_out")
        w = [max(0.0, min(p["body_weight_to"]["value"], hi) - max(p["body_weight_from"]["value"], lo)) for p in ph]
    tot = sum(w)
    g = lambda key, dflt=None: sum(wi * (p["diet_spec"][key]["value"] if key in p["diet_spec"] else dflt) for wi, p in zip(w, ph)) / tot
    return g("crude_protein"), g("total_phosphorus"), g("dry_matter", par("C_DM", "all")[0])


def grow(cp, p, dm, dmd, bwi, bwf, dof, adfi):
    """D384.2 9.3 grow-finish (also used for gilt development). adfi g/d; returns g per head over the stage."""
    fi = adfi * dof
    dpf, ffl = par("DP_F", "finishing")[0], par("FFLP_F", "finishing")[0]
    wbn_f = bwf * dpf * ffl / 159.4
    wbn_i = bwi * (dpf - 0.05 * (bwf - bwi)) * (ffl + 0.07 * (bwf - bwi)) / 159.4
    nr = wbn_f - wbn_i
    pr = 0.2256 * nr - 8.0e-6 * nr * (wbn_i + wbn_f)
    ni, pi = fi * cp / 625, fi * p / 100
    dme = dm * fi * (100 - dmd) / 10000 + 0.025 * dof * (20 * (bwi + bwf) / 2 + 2100)
    return ni, ni - nr, pi - pr, dme


def nursery(cp, p, dm, dmd, bwi, bwf, dof, adfi):
    """D384.2 9.4 weanling pigs; DM is feces only (standard footnote)."""
    ni, pi = adfi * dof * cp / 625, adfi * dof * p / 100
    nr = dof * par("FFLG_G", "nursery")[0] * (1 + 0.137 * (bwf + bwi)) / 125.8
    pr = 4.7494 * (bwf - bwi)
    return ni, ni - nr, pi - pr, dm * adfi * dof * (100 - dmd) / 10000


def gestation(cp, p, dm, dmd, adfi):
    """D384.2 9.5 gestating sow over GL days."""
    ni, pi = adfi * cp * GL / 625, adfi * p * GL / 100
    nr = par("GLTG", "gestation")[0] * 36.8 + LITTER * 39.1
    pr = 93.039 + 3.9717 * ((SW_LATE - SW_BREED) - 2.277 * LITTER) + LW_BIRTH * 5.7 + (2.277 * LITTER - LW_BIRTH) * 0.80
    return ni, ni - nr, pi - pr, dm * adfi * GL * (100 - dmd) / 10000


def lactation(cp, p, dm, dmd, adfi):
    """D384.2 9.6 lactating sow with litter over LL days."""
    ni, pi = adfi * cp * LL / 625, adfi * p * LL / 100
    nr = 36.8 * par("LLTG", "farrowing_lactation")[0] + LW_WEAN * 32 - LW_BIRTH * 36.8
    pr = (SW_WEAN * 4.84 - SW_PF_LACT * 5.28) + (LW_WEAN * 6.4 - LW_BIRTH * 5.7)
    return ni, ni - nr, pi - pr, dm * adfi * LL * (100 - dmd) / 10000


# typical values per animal-day (kg) for K, VS/TS and the check
typ = {}
for r in csv.DictReader(open(ST / "d384_typical_values.csv")):
    d = float(r["days"])
    typ[r["class"]] = {k: float(r[k + "_lb"]) * LB / d for k in ("N", "P", "K", "TS", "VS")}
TYP_CLASS = {"nursery": "nursery", "finishing": "grow_finish", "gilt_development": "grow_finish",
             "gestation": "gestating_sow", "farrowing_lactation": "lactating_sow"}


def amt(x, unit, basis, src, q, note=None, origin="derived"):
    a = {"value": round(x, 6), "unit_id": unit, "basis": basis, "source_id": src, "quality_id": q, "origin": origin}
    if note: a["note"] = note
    return a


out = ROOT / "model" / "unit_processes"
out.mkdir(parents=True, exist_ok=True)
summary = {}
for fpf in sorted((ROOT / "model" / "feeding_programs").glob("*.json")):
    fp = json.loads(fpf.read_text())
    pid, phases = fp["feeding_program_id"], fp["phases"]
    rows = {}
    for st in ("gestation", "farrowing_lactation", "gilt_development", "nursery", "finishing"):
        cp, p, dm = stage_diet(phases, st)
        dmd = par("DMD", st)[0]
        adfi = v(st, "feed_intake") * 1000
        if st == "nursery":
            bwi, bwf = v(st, "body_weight_in"), v(st, "body_weight_out")
            dof = (bwf - bwi) / v(st, "average_daily_gain")
            ni, ne, pe, dme = nursery(cp, p, dm, dmd, bwi, bwf, dof, adfi)
        elif st in ("finishing", "gilt_development"):
            bwi = v(st, "body_weight_in") if st == "finishing" else v("nursery", "body_weight_in")
            bwf = v(st, "body_weight_out")
            dof = (bwf - bwi) / v(st, "average_daily_gain")
            ni, ne, pe, dme = grow(cp, p, dm, dmd, bwi, bwf, dof, adfi)
        elif st == "gestation":
            dof = GL
            ni, ne, pe, dme = gestation(cp, p, dm, dmd, adfi)
        else:
            dof = LL
            ni, ne, pe, dme = lactation(cp, p, dm, dmd, adfi)
        t = typ[TYP_CLASS[st]]
        day = {"N": ne / dof / 1000, "P": pe / dof / 1000, "TS": dme / dof / 1000, "N_intake": ni / dof / 1000}
        day["VS"] = day["TS"] * t["VS"] / t["TS"]
        day["K"] = t["K"]
        rows[st] = (day, t, (cp, p, dm, dmd, adfi, dof))
        pdoc = {"process_id": f"excretion_d384_{pid}_{st}", "name": f"As-excreted manure, {st}, {pid} diets (ASAE D384.2)",
                "region_id": fp["region_id"],
                "reference": {"flow_id": f"swine_{st}_animal_day", "amount": amt(1, "animal_day", "per_head_day", STD, "q_derived", origin="entered")},
                "exchanges": [
                    {"flow_id": "manure_nitrogen_as_excreted", "direction": "output", "amount": amt(day["N"], "kg", "per_head_day", STD, "q_d384",
                        f"D384.2 N intake - N retention; diet CP {cp:.2f}%, intake {adfi/1000:.3f} kg/d, {dof:.1f} d")},
                    {"flow_id": "manure_phosphorus_as_excreted", "direction": "output", "amount": amt(day["P"], "kg", "per_head_day", STD, "q_d384",
                        f"D384.2 P intake - P retention; diet total P {p:.3f}%")},
                    {"flow_id": "manure_dry_matter_as_excreted", "direction": "output", "amount": amt(day["TS"], "kg", "per_head_day", STD, "q_d384",
                        f"D384.2 DM excretion, DMD {dmd:g}%, diet DM {dm:g}%" + ("; feces + urine" if st in ("finishing", "gilt_development") else "; feces only per standard"))},
                    {"flow_id": "manure_volatile_solids_as_excreted", "direction": "output", "amount": amt(day["VS"], "kg", "per_head_day", TYP, "q_d384_typical",
                        f"DM x VS/TS {t['VS']/t['TS']:.3f} from D384.2 typical values ({TYP_CLASS[st]}); standard has no swine VS equation")},
                    {"flow_id": "manure_potassium_as_excreted", "direction": "output", "amount": amt(day["K"], "kg", "per_head_day", TYP, "q_d384_typical",
                        f"D384.2 typical value ({TYP_CLASS[st]}); standard has no swine K equation", origin="entered")}]}
        (out / f"{pdoc['process_id']}.json").write_text(json.dumps(pdoc, indent=2) + "\n")
    summary[pid] = rows

print(f"sow weights (PIC H2 parity mean): breeding {SW_BREED:.1f} kg, d{GL:g} {SW_LATE:.1f} kg, post-farrow {SW_PF_LACT:.1f}, wean {SW_WEAN:.1f}; litter {LITTER} born alive, LW birth {LW_BIRTH:.1f}, LW wean {LW_WEAN:.1f} kg")
for pid, rows in summary.items():
    print(f"\n{pid}: per shipped pig, kg (check columns: IPCC 2006 Tier 2 N = 70% of N intake; D384.2 typical x animal-days)")
    print(f"  {'stage':20s} {'days/pig':>8s} {'N':>7s} {'N_ipcc':>7s} {'N_typ':>7s} {'P':>7s} {'P_typ':>7s} {'TS':>7s} {'TS_typ':>7s} {'VS':>7s} {'K':>7s}")
    tot = collections.Counter()
    for st, (day, t, _) in rows.items():
        ad = v(st, "animal_days_per_unit")
        r = {"N": day["N"] * ad, "N_ipcc": 0.7 * day["N_intake"] * ad, "N_typ": t["N"] * ad, "P": day["P"] * ad, "P_typ": t["P"] * ad,
             "TS": day["TS"] * ad, "TS_typ": t["TS"] * ad, "VS": day["VS"] * ad, "K": day["K"] * ad}
        tot.update(r)
        print(f"  {st:20s} {ad:8.2f} " + " ".join(f"{r[k]:7.3f}" for k in ("N", "N_ipcc", "N_typ", "P", "P_typ", "TS", "TS_typ", "VS", "K")))
    print(f"  {'total':20s} {'':8s} " + " ".join(f"{tot[k]:7.3f}" for k in ("N", "N_ipcc", "N_typ", "P", "P_typ", "TS", "TS_typ", "VS", "K")))
