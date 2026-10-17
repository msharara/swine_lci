"""Harmonize staged herd tables into a model-ready herd_systems record.

Reads data/staged/herd/*.csv, converts to SI, derives animal-days per shipped
pig (decision C), and writes data/model/herd_systems/swine_market_pig_2022.json
plus its pedigree records in data/quality/quality.json (merged by id). Every derived value carries origin
"derived" and a note with its formula.
"""
import csv, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
LB = 0.45359237

def table(name, key):
    with open(ROOT / "staged" / "herd" / name) as f:
        return {key(r): r for r in csv.DictReader(f)}

mf = table("metafarms_2022.csv", lambda r: (r["metric"], r["phase"]))
nass = table("nass_2022.csv", lambda r: (r["metric"], r["region"]))
pic = table("pic_2025.csv", lambda r: r["metric"])
v = lambda t, k: float(t[k]["value"])

def amt(value, unit, basis, source, quality, note=None, origin="entered"):
    a = {"value": round(value, 4), "unit_id": unit, "basis": basis, "source_id": source,
         "quality_id": quality, "origin": origin}
    if note:
        a["note"] = note
    return a

MF, NS, PIC, DER = "metafarms_2024_npb", "nass_lsan0423", "pic_nutrition_2025", "derived_build_herd"

# sow farm (US-wide, 2022)
pwmfy = v(mf, ("pigs_weaned_per_mated_female_year", "sow"))
weaned_per_litter = v(mf, ("pigs_weaned_per_sow_farrowed", "sow"))
wean_age = v(mf, ("average_wean_age", "sow"))
sow_death = v(mf, ("sow_death_loss", "sow")) / 100
repl_groups = [v(mf, (k, "sow")) for k in ("replacement_rate_farm_lt1000", "replacement_rate_farm_1000_2000",
               "replacement_rate_farm_2000_3000", "replacement_rate_farm_3000_4000", "replacement_rate_farm_ge4000")]
replacement = sum(repl_groups) / len(repl_groups) / 100
gestation = v(pic, "gestation_length")
litters = pwmfy / weaned_per_litter

# grow-out
n_mort = v(mf, ("mortality", "nursery")) / 100
n_out = v(mf, ("weight_out", "nursery"))
n_days = v(mf, ("days_on_feed", "nursery"))
n_adg = v(mf, ("average_daily_gain", "nursery"))
n_fcr = v(mf, ("feed_conversion", "nursery"))
n_in = n_out - n_adg * n_days
f_mort = v(mf, ("mortality", "finishing")) / 100
f_adg = v(mf, ("average_daily_gain", "finishing"))
f_fcr = v(mf, ("feed_conversion", "finishing"))
market = v(nass, ("commercial_avg_live_weight", "US"))
f_days = (market - n_out) / f_adg

# animal-days per shipped pig; deaths at mid-stage (uniform timing default)
placed_nursery = 1 / ((1 - n_mort) * (1 - f_mort))
placed_finish = placed_nursery * (1 - n_mort)
ad_nursery = n_days * (placed_nursery - 0.5 * placed_nursery * n_mort)
ad_finish = f_days * (placed_finish - 0.5 * placed_finish * f_mort)
female_years = placed_nursery / pwmfy
lact_days_yr = litters * wean_age
gest_days_yr = litters * gestation
open_days_yr = 365 - lact_days_yr - gest_days_yr
ad_lact = female_years * lact_days_yr
ad_gest = female_years * (gest_days_yr + open_days_yr)
gilt_days = (float(pic["gilt_first_breeding_age_low"]["value"]) + float(pic["gilt_first_breeding_age_high"]["value"])) / 2 - wean_age
gilt_wt = (float(pic["gilt_first_breeding_weight_low"]["value"]) + float(pic["gilt_first_breeding_weight_high"]["value"])) / 2
gilts = female_years * replacement
culls = female_years * (replacement - sow_death)

Q = {"q_mf_2022": dict(reliability=2, completeness=2, temporal=1, geographic=3, technological=1),
     "q_mf_2024": dict(reliability=2, completeness=3, temporal=2, geographic=3, technological=1),
     "q_nass_2022": dict(reliability=1, completeness=1, temporal=1, geographic=3, technological=1),
     "q_pic_2025": dict(reliability=3, completeness=3, temporal=2, geographic=3, technological=1),
     "q_derived": dict(reliability=3, completeness=2, temporal=1, geographic=3, technological=1)}
quality = [{"quality_id": k, "pedigree": p, "distribution": "none"} for k, p in Q.items()]

d = lambda x, u, b, n: amt(x, u, b, DER, "q_derived", n, "derived")
herd = {
  "herd_id": "swine_market_pig_2022_us",
  "species": "swine",
  "functional_unit": "1 shipped market pig at 2022 US commercial average live weight (131.1 kg), incl. its share of sows, gilts and boars",
  "reference_year": 2022,
  "genetics": "US commercial average (MetaFarms benchmark population)",
  "breeding": {
    "litters_per_sow_year": d(litters, "litter_per_female_year", "absolute", "PWMFY / pigs weaned per sow farrowed"),
    "pigs_weaned_per_litter": amt(weaned_per_litter, "head_per_litter", "absolute", MF, "q_mf_2022", "Pigs Weaned/Sow Farrowed, p.4"),
    "replacement_rate": d(replacement, "fraction_per_year", "absolute", "unweighted mean of 2024 farm-size groups (p.8); no overall or 2022 value printed"),
  },
  "stages": [
    {"stage": "gestation",
     "animal_days_per_unit": d(ad_gest, "animal_day", "per_functional_unit", f"female-years per pig x (litters x {gestation:g} d gestation + open days); open days = 365 - gestation - lactation"),
     "mortality_rate": amt(sow_death, "fraction_per_year", "absolute", MF, "q_mf_2022", "Sow Death Loss, p.4; annual rate for the breeding herd")},
    {"stage": "farrowing_lactation",
     "animal_days_per_unit": d(ad_lact, "animal_day", "per_functional_unit", "female-years per pig x litters x wean age (21.3 d)")},
    {"stage": "gilt_development",
     "animal_days_per_unit": d(gilts * gilt_days, "animal_day", "per_functional_unit", "gilts per pig (female-years x replacement) x days from weaning to first breeding (PIC 200-225 d age midpoint minus wean age)"),
     "body_weight_out": amt(gilt_wt, "kg", "per_head", PIC, "q_pic_2025", "midpoint of 135-160 kg first-breeding target")},
    {"stage": "nursery",
     "animal_days_per_unit": d(ad_nursery, "animal_day", "per_functional_unit", "pigs placed per shipped pig x days on feed, deaths at mid-stage"),
     "body_weight_in": d(n_in * LB, "kg", "per_head", "weight out - ADG x days on feed"),
     "body_weight_out": amt(n_out * LB, "kg", "per_head", MF, "q_mf_2022", "50.86 lb, p.16"),
     "mortality_rate": amt(n_mort, "fraction", "per_stage", MF, "q_mf_2022", "p.16"),
     "average_daily_gain": amt(n_adg * LB, "kg_per_day", "per_head_day", MF, "q_mf_2022", "0.85 lb/d, p.16"),
     "feed_intake": d(n_fcr * n_adg * LB, "kg_per_day", "per_head_day", "feed conversion 1.58 x ADG; as-fed"),
     "mortality_timing": {"distribution": "uniform"}},
    {"stage": "finishing",
     "animal_days_per_unit": d(ad_finish, "animal_day", "per_functional_unit", "pigs placed per shipped pig x days to market weight, deaths at mid-stage"),
     "body_weight_in": amt(n_out * LB, "kg", "per_head", MF, "q_mf_2022", "= nursery weight out"),
     "body_weight_out": amt(market * LB, "kg", "per_head", NS, "q_nass_2022", "2022 US commercial average live weight 289 lb; MetaFarms closeout 284.06 lb"),
     "mortality_rate": amt(f_mort, "fraction", "per_stage", MF, "q_mf_2022", "p.17"),
     "average_daily_gain": amt(f_adg * LB, "kg_per_day", "per_head_day", MF, "q_mf_2022", "1.94 lb/d, p.17"),
     "feed_intake": d(f_fcr * f_adg * LB, "kg_per_day", "per_head_day", "feed conversion 2.85 x ADG; as-fed"),
     "mortality_timing": {"distribution": "uniform"}},
  ],
  "co_products": [
    {"animal": "cull_sow", "head_per_unit": d(culls, "head", "per_functional_unit", "female-years per pig x (replacement - sow death loss)"),
     "live_weight_per_unit": {"value": 0, "unit_id": "kg", "basis": "per_functional_unit", "source_id": "TBD", "note": "cull sow live weight not yet sourced", "origin": "entered"}}],
}
out = ROOT / "model" / "herd_systems" / "swine_market_pig_2022_us.json"
out.write_text(json.dumps(herd, indent=2) + "\n")
qf = ROOT / "quality" / "quality.json"
kept = [q for q in json.loads(qf.read_text()) if q["quality_id"] not in Q] if qf.exists() else []
qf.write_text(json.dumps(quality + kept, indent=2) + "\n")
print(json.dumps({"litters": litters, "female_days_per_pig": female_years * 365, "gestation": ad_gest, "lactation": ad_lact,
                  "gilt": gilts * gilt_days, "nursery": ad_nursery, "finishing": ad_finish, "finish_days": f_days,
                  "wean_kg": n_in * LB, "culls_per_pig": culls, "gilts_per_pig": gilts}, indent=1))
