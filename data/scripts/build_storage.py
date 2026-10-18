"""Build manure storage unit processes (IPCC Tier 2 method; v1 stand-in factors).

Each storage step gets one unit process per tracked constituent, so the engine can
chain steps linearly (the output of one step is the input of the next):
  *_vs : per kg VS in  -> CH4, biogenic CO2, VS out (digester: recovered CH4)
  *_n  : per kg N in   -> direct N2O, NH3, indirect N2O, N leached, N unaccounted, N out
  lagoon P and K       -> share to effluent and to sludge
plus lagoon water balance (per m2 of surface per year), infrastructure (per m3 of
capacity per year) and handling energy (per m3 removed, per t separated).

Method: CH4 = VS x B0 x MCF x 0.67; CO2 = CH4 x (0.4/0.6) by volume (biogas share);
VS degraded in pits and tanks = 0.9 x (CH4 + CO2) mass (Buswell); lagoon and digester
VS destruction = expert 62.5%. N2O = EF3 + Frac_GasMS x EF4 + Frac_LeachMS x EF5;
Frac_GasMS counted as all NH3. Lagoon N not explained by NH3 and N2O closes as
"unaccounted" against the AWMFH retained share; checked against the Smithfield
Agreement Phase 2 B1b mass balance (NC lagoon and sprayfield).

IPCC 2019 Ch. 10 tables could not be read; IPCC 2006 values (via EPA) and secondary
IPCC 2019 values stand in, each flagged by source and quality record.
"""
import csv, json, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "model" / "unit_processes"
REGIONS = ["NC", "IA"]
N2O_N, NH3_N, CO2_CH4 = 44 / 28, 17 / 14, 44 / 16

F = collections.defaultdict(dict)
for r in csv.DictReader(open(ROOT / "staged" / "storage" / "storage_factors.csv")):
    F[(r["parameter"], r["system"])][r["region"]] = r
def f(par, system="all", region="all"):
    d = F[(par, system)]
    return d[region] if region in d else d["all"]
val = lambda *a: float(f(*a)["value"])

def amt(value, unit, basis, rows, note="", origin="derived"):
    rows = rows if isinstance(rows, list) else [rows]
    worst = max(rows, key=lambda r: QSCORE.get(r["quality_id"], 0))
    a = {"value": round(value, 6), "unit_id": unit, "basis": basis,
         "source_id": worst["source_id"], "quality_id": worst["quality_id"], "origin": origin}
    srcs = sorted({r["source_id"] for r in rows})
    a["note"] = "; ".join(x for x in [note, "sources: " + ", ".join(srcs) if len(srcs) > 1 else ""] if x)
    return a

QSCORE = {q["quality_id"]: sum(q["pedigree"].values()) for q in json.load(open(ROOT / "quality" / "quality.json"))}

def ex(flow, direction, a, method=None, tier=None):
    e = {"flow_id": flow, "direction": direction, "amount": a}
    if method:
        e["estimation_method"] = {"method": method, **({"ipcc_tier": tier} if tier else {})}
    return e

def process(pid, name, region, ref_flow, ref_unit, ref_basis, exchanges, layer="foreground"):
    return {"process_id": pid, "name": name, "region_id": region,
            "reference": {"flow_id": ref_flow, "amount": {"value": 1, "unit_id": ref_unit, "basis": ref_basis,
                                                          "source_id": "stoichiometry", "quality_id": "q_derived", "origin": "entered"}},
            "exchanges": exchanges, "system_layer": layer}

# P/N of excreted manure per region, from the finishing-stage excretion process (dominant manure source)
def _excr(reg):
    prog = {"NC": "nc_corn_sbm_2022", "IA": "ia_corn_sbm_ddgs_2022"}[reg]
    d = json.load(open(OUT / f"excretion_d384_{prog}_finishing.json"))
    return {e["flow_id"]: e["amount"]["value"] for e in d["exchanges"]}
P_PER_N = {r: _excr(r)["manure_phosphorus_as_excreted"] / _excr(r)["manure_nitrogen_as_excreted"] for r in REGIONS}

docs = []
ANAEROBIC = ["deep_pit", "shallow_pit", "slurry_tank_above_ground", "anaerobic_lagoon"]
LABEL = {"deep_pit": "deep pit", "shallow_pit": "shallow pit (<1 month)", "slurry_tank_above_ground": "above-ground slurry tank",
         "anaerobic_lagoon": "anaerobic lagoon (single or multi-stage)", "anaerobic_digester": "anaerobic digester (enclosed)",
         "solid_storage": "solid storage", "composting": "composting (static pile)"}
summary = {}

for reg in REGIONS:
    B0, D = f("B0"), f("ch4_density")
    share, buswell = f("ch4_share_biogas"), f("vs_per_biogas_mass")
    co2_per_ch4 = (1 - float(share["value"])) / float(share["value"]) * CO2_CH4

    # --- VS / carbon ---
    for sy in ANAEROBIC + ["solid_storage", "composting"]:
        mcf = f("MCF", sy, reg)
        ch4 = float(B0["value"]) * float(mcf["value"]) * float(D["value"])
        exs = [ex("methane_biogenic_air", "output", amt(ch4, "kg", "absolute", [B0, mcf, D], f"VS x B0 x MCF ({mcf['value']}) x 0.67"),
                  "IPCC 2006/2019 Vol.4 Ch.10 Eq.10.23", 2)]
        if sy in ANAEROBIC:
            co2 = ch4 * co2_per_ch4
            exs.append(ex("carbon_dioxide_biogenic_air", "output", amt(co2, "kg", "absolute", [share, B0, mcf], "CH4 x (0.4/0.6) x 44/16; biogas CH4 share 0.6"),
                          "biogas stoichiometry"))
            if sy == "anaerobic_lagoon":
                vd = f("vs_destroyed", sy)
                exs.append(ex("manure_volatile_solids_out", "output", amt(1 - float(vd["value"]), "kg", "absolute", vd, "1 - VS destroyed (50-75%, midpoint)")))
                summary[(reg, "lagoon_vs_stoich")] = float(buswell["value"]) * (ch4 + co2)
            else:
                exs.append(ex("manure_volatile_solids_out", "output", amt(1 - float(buswell["value"]) * (ch4 + co2), "kg", "absolute", [buswell, B0, mcf],
                                                                           "1 - 0.9 x (CH4 + CO2) mass (Buswell)")))
        summary[(reg, sy, "ch4")] = ch4
        note = "" if sy in ANAEROBIC else " CO2 and VS out not estimated (gap: no open aerobic carbon-loss factor read)."
        docs.append(process(f"storage_{sy}_{reg.lower()}_vs", f"Manure storage, {LABEL[sy]}, {reg}, per kg VS in.{note}", reg,
                            "manure_volatile_solids_in", "kg", "absolute", exs))

    # digester: CH4 produced from destroyed VS, leaked or combusted
    vd, lk, sl = f("vs_destroyed", "anaerobic_digester"), f("leakage", "anaerobic_digester"), f("combustion_slip", "anaerobic_digester")
    prod = float(B0["value"]) * float(vd["value"]) * float(D["value"])
    leak, burnt = prod * float(lk["value"]), prod * (1 - float(lk["value"]))
    slip = burnt * float(sl["value"])
    co2 = prod * co2_per_ch4 + (burnt - slip) * CO2_CH4
    docs.append(process(f"storage_anaerobic_digester_{reg.lower()}_vs", f"Manure storage, {LABEL['anaerobic_digester']}, {reg}, per kg VS in; biogas flared or burned for energy", reg,
        "manure_volatile_solids_in", "kg", "absolute", [
        ex("methane_biogenic_air", "output", amt(leak + slip, "kg", "absolute", [B0, vd, lk, sl], f"leakage {lk['value']} of produced + combustion slip {sl['value']} of burned"), "UNFCCC CDM TOOL14 leakage; EPA destruction efficiency"),
        ex("carbon_dioxide_biogenic_air", "output", amt(co2, "kg", "absolute", [share, vd, B0], "biogas CO2 + CO2 from burned CH4")),
        ex("biogas_methane_recovered", "output", amt(burnt, "kg", "absolute", [B0, vd, lk], "CH4 delivered to flare or engine; reported, not allocated (v1)")),
        ex("manure_volatile_solids_out", "output", amt(1 - float(vd["value"]), "kg", "absolute", vd, "1 - VS destroyed"))]))
    summary[(reg, "anaerobic_digester", "ch4")] = leak + slip

    # --- nitrogen ---
    ef4, ef5, fl = f("EF4"), f("EF5"), f("frac_leach")
    for sy in ANAEROBIC + ["anaerobic_digester", "solid_storage", "composting"]:
        ef3, fg = f("EF3", sy), f("frac_gas", sy)
        e3, g, l = float(ef3["value"]), float(fg["value"]), float(fl["value"])
        exs = [ex("dinitrogen_monoxide_air", "output", amt(e3 * N2O_N, "kg", "absolute", ef3, f"direct: EF3 {e3} x 44/28"), "IPCC Vol.4 Ch.10 Eq.10.25", 2),
               ex("ammonia_air", "output", amt(g * NH3_N, "kg", "absolute", fg, f"Frac_GasMS {g} counted as all NH3, x 17/14"), "IPCC Vol.4 Ch.10 Eq.10.26", 2),
               ex("dinitrogen_monoxide_air", "output", amt((g * float(ef4["value"]) + l * float(ef5["value"])) * N2O_N, "kg", "absolute", [fg, ef4, fl, ef5],
                  "indirect: (Frac_GasMS x EF4 + Frac_LeachMS x EF5) x 44/28"), "IPCC Vol.4 Ch.10 Eq.10.28-10.29", 2),
               ex("nitrogen_leached_water", "output", amt(l, "kg", "absolute", fl, "lined or contained storage"))]
        lost = e3 + g + l
        if sy == "anaerobic_lagoon":
            ret, snp, pr = f("n_retained", sy), f("sludge_n_to_p", sy), f("p_retained_liquid", sy)
            unacc = 1 - float(ret["value"]) - lost
            n_sludge = float(snp["value"]) * (1 - float(pr["value"])) * P_PER_N[reg]
            exs += [ex("nitrogen_unaccounted", "output", amt(unacc, "kg", "absolute", [ret, fg, ef3], "1 - retained (AWMFH 20-30%) - NH3-N - N2O-N; mostly N2 (denitrification)"), "mass balance closure"),
                    ex("manure_nitrogen_to_sludge", "output", amt(n_sludge, "kg", "absolute", [snp, pr, ret], f"sludge N:P 1.04 x P to sludge x P/N excreted ({P_PER_N[reg]:.3f})")),
                    ex("manure_nitrogen_to_effluent", "output", amt(float(ret["value"]) - n_sludge, "kg", "absolute", [ret, snp], "retained N minus sludge N"))]
            summary[(reg, "lagoon_n")] = dict(nh3=g, n2o=e3, unacc=unacc, sludge=n_sludge, effluent=float(ret["value"]) - n_sludge)
        else:
            exs.append(ex("manure_nitrogen_out", "output", amt(1 - lost, "kg", "absolute", [fg, ef3, fl], "1 - NH3-N - N2O-N - leached N")))
        summary[(reg, sy, "nloss")] = lost
        docs.append(process(f"storage_{sy}_{reg.lower()}_n", f"Manure storage, {LABEL[sy]}, {reg}, per kg N in", reg, "manure_nitrogen_in", "kg", "absolute", exs))

    # --- lagoon water balance, per m2 surface per year ---
    pr_, ev = f("precipitation", "anaerobic_lagoon", reg), f("evaporation", "anaerobic_lagoon", reg)
    docs.append(process(f"lagoon_water_balance_{reg.lower()}", f"Anaerobic lagoon water balance, {reg}, per m2 of surface per year; net (precipitation - evaporation) adds to effluent volume sent to land application", reg,
        "lagoon_surface_area_year", "m2_year", "absolute", [
        ex("precipitation_on_lagoon", "input", amt(float(pr_["value"]), "m3", "absolute", pr_, "1991-2020 mean", "entered")),
        ex("evaporation_from_lagoon", "output", amt(float(ev["value"]), "m3", "absolute", ev, "lake (free water surface) evaporation", "entered")),
        ex("lagoon_net_water_to_effluent", "output", amt(float(pr_["value"]) - float(ev["value"]), "m3", "absolute", [pr_, ev], "shared term with land application"))]))

# --- lagoon P and K (region independent) ---
pr, kr = f("p_retained_liquid", "anaerobic_lagoon"), f("k_retained_liquid", "anaerobic_lagoon")
for el, r in (("phosphorus", pr), ("potassium", kr)):
    docs.append(process(f"storage_anaerobic_lagoon_us_{el[0]}", f"Anaerobic lagoon, split of {el} between effluent and sludge, per kg in", "US", f"manure_{el}_in", "kg", "absolute", [
        ex(f"manure_{el}_to_effluent", "output", amt(float(r["value"]), "kg", "absolute", r, "AWMFH retained in liquid (midpoint)")),
        ex(f"manure_{el}_to_sludge", "output", amt(1 - float(r["value"]), "kg", "absolute", r, "rest settles to sludge; not lost"))]))

# --- infrastructure, per m3 capacity per year ---
dens, th = f("hdpe_density"), f("hdpe_thickness", "anaerobic_lagoon")
def infra(pid, name, life, items):
    """items: (flow, amount per m3 capacity, unit, rows, note[, own life row])"""
    exs = []
    for it in items:
        flow, v, u, rows, n = it[:5]
        lf = it[5] if len(it) > 5 else life
        exs.append(ex(flow, "input", amt(v / float(lf["value"]), u, "absolute", rows + [lf], f"{n}{'; ' if n else ''}spread over {lf['value']} yr")))
    docs.append(process(pid, f"{name}; per m3 of capacity per year", "US", "storage_capacity_year", "m3_year", "absolute", exs, "direct_supply"))
for sy, lab in (("deep_pit", "Deep pit, concrete"), ("shallow_pit", "Shallow pit, concrete")):
    c, r = f("concrete", sy), f("rebar", sy)
    infra(f"infrastructure_{sy}", lab, f("life", sy), [("concrete_ready_mix", float(c["value"]), "m3", [c], "walls, floor, footing"),
                                                       ("reinforcing_steel", float(r["value"]), "kg", [r], "")])
st = f("steel", "slurry_tank_above_ground")
infra("infrastructure_slurry_tank_above_ground", "Above-ground glass-fused steel slurry tank", f("life", "slurry_tank_above_ground"),
      [("steel_glass_fused_plate", float(st["value"]), "kg", [st], "floor slab not included (gap)")])
exc, cl, ha = f("excavation", "anaerobic_lagoon"), f("clay_liner", "anaerobic_lagoon"), f("hdpe_liner_area", "anaerobic_lagoon")
infra("infrastructure_anaerobic_lagoon_clay", "Earthen anaerobic lagoon with compacted clay liner", f("life", "anaerobic_lagoon"),
      [("earthwork_excavation", float(exc["value"]), "m3", [exc], ""), ("compacted_clay_liner", float(cl["value"]), "m3", [cl], "")])
hdpe = float(ha["value"]) * float(th["value"]) * float(dens["value"])
infra("infrastructure_anaerobic_lagoon_hdpe", "Earthen anaerobic lagoon with HDPE geomembrane liner", f("life", "hdpe_liner"),
      [("earthwork_excavation", float(exc["value"]), "m3", [exc], "", f("life", "anaerobic_lagoon")),
       ("hdpe_geomembrane", hdpe, "kg", [ha, th, dens], "0.348 m2/m3 x 60 mil x 940 kg/m3")])

# --- handling energy ---
ag, ee = f("agitation_shaft"), f("engine_efficiency")
docs.append(process("handling_agitation_pumpout", "Agitation and pump-out of liquid manure or lagoon sludge by tractor PTO pump, per m3 removed", "US", "manure_removed", "m3", "absolute", [
    ex("diesel_energy", "input", amt(float(ag["value"]) * 3.6 / float(ee["value"]), "MJ", "absolute", [ag, ee], "shaft 0.1 kWh/m3 / engine efficiency 0.375"))]))
for typ in ("screw_press", "decanter_centrifuge"):
    s = f("separator_electricity", typ)
    docs.append(process(f"separation_{typ}", f"Solid-liquid separation, {typ.replace('_', ' ')}, per t manure in", "US", "manure_to_separator", "t", "absolute", [
        ex("electricity", "input", amt(float(s["value"]), "kWh", "absolute", s, "range " + s["as_printed"]))]))

if __name__ == "__main__":
    import jsonschema
    schema = json.load(open(ROOT.parent / "containers" / "unit_processes.schema.json"))
    OUT.mkdir(parents=True, exist_ok=True)
    for d in docs:
        jsonschema.validate(d, schema)
        (OUT / f"{d['process_id']}.json").write_text(json.dumps(d, indent=2) + "\n")
    print(f"wrote {len(docs)} storage unit processes")
    for reg in REGIONS:
        print(f"\n{reg}: kg CH4 per kg VS in: " + ", ".join(f"{s} {summary[(reg, s, 'ch4')]:.4f}" for s in ANAEROBIC + ["anaerobic_digester", "solid_storage", "composting"]))
        print(f"{reg}: N lost per kg N in (NH3 + N2O + leach): " + ", ".join(f"{s} {summary[(reg, s, 'nloss')]:.3f}" for s in ANAEROBIC + ["anaerobic_digester", "solid_storage", "composting"]))
        print(f"{reg}: check lagoon VS destroyed, Buswell from CH4+CO2 {summary[(reg, 'lagoon_vs_stoich')]:.3f} vs expert 0.625 (50-75%)")
        n = summary[(reg, "lagoon_n")]
        print(f"{reg}: lagoon N per kg N in: NH3-N {n['nh3']:.3f}, N2O-N {n['n2o']:.3f}, unaccounted {n['unacc']:.3f}, sludge {n['sludge']:.3f}, effluent {n['effluent']:.3f}")
    # Smithfield Agreement Phase 2 B1b Table AL.5 (4,320-head feeder-finish, flush, NC), lb/yr
    gen, eff, sl = 87436.80, 19299.96, 10196.67
    n = summary[("NC", "lagoon_n")]
    print(f"\nCheck vs Smithfield B1b Table AL.5 (NC lagoon + sprayfield, N): effluent {eff/gen:.3f} (model {n['effluent']:.3f}), "
          f"sludge {sl/gen:.3f} (model {n['sludge']:.3f}), lost or unaccounted {1-(eff+sl)/gen:.3f} (model NH3+N2O+unaccounted {n['nh3']+n['n2o']+n['unacc']:.3f})")
    print("Check vs EPA 2015 state MCF (Annex 3.11 Table A-186): NC lagoon 0.78, liquid/deep pit 0.41; IA lagoon 0.70, liquid/deep pit 0.26")
