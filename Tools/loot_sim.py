#!/usr/bin/env python3
"""No Brainers loot economy simulator.

Mirrors BFL_LootMath + BP_ZombieBase.RollTieredLoot / SpawnPinataBurst.
Standard library only.
Usage: python Tools/loot_sim.py --runs 1000 --nights 10 --ad-level 1 --luck 0
"""
import argparse
import json
import math
import os
import random
import statistics

TIERS = ["Junk", "Common", "Uncommon", "Rare", "Treasure"]


def normalize(w):
    s = sum(w)
    return [x / s for x in w] if s > 0 else w


def apply_tier_shift(weights, shift, cap):
    s = max(0.0, shift)
    w = list(weights)
    for _ in range(int(math.floor(s))):
        n = [0.0] * 5
        for i in range(4):
            n[i + 1] += w[i]
        n[4] += w[4]
        w = n
    frac = s - math.floor(s)
    for i in range(3, -1, -1):
        m = w[i] * frac
        w[i] -= m
        w[i + 1] += m
    w = normalize(w)
    if cap > 0 and w[4] > cap:
        w[3] += w[4] - cap
        w[4] = cap
    return normalize(w)


def roll_tier(w, rng):
    r = rng.random() * sum(w)
    c = 0.0
    for i, x in enumerate(w):
        c += x
        if r < c:
            return i
    return 4


def pity_shift(dropped, expected, elapsed, K):
    if elapsed < K["pity_grace"]:
        return 0.0
    target = expected * min(max(elapsed, 0.0), 1.0)
    if target <= 0:
        return 0.0
    deficit = (target - dropped) / target
    if deficit <= K["pity_threshold"]:
        return 0.0
    return min(max((deficit - K["pity_threshold"]) / K["pity_span"], 0.0), 1.0)


def ad_shift(level, K):
    return min(max(K["ad_per_level"] * (level - 1), 0.0), K["ad_max"])


def curve_row(curve, night):
    n = max(1, night)
    if n <= 10:
        r = curve[str(n)]
        return r["weights"], r["bonus_max_drops"], r["expected_night_value"]
    r = curve["10"]
    return r["weights"], r["bonus_max_drops"], r["expected_night_value"] * 1.2 ** (n - 10)


def build_pools(items):
    pools = {i: [] for i in range(5)}
    for iid, it in items.items():
        if it["in_pool"]:
            pools[TIERS.index(it["tier"])].append(iid)
    return pools


def pick_item(tier, themed, bias, pools, items, rng):
    t = tier
    while t >= 0:
        pool = pools[t]
        if pool:
            ws = [(items[i]["drop_weight"] if items[i]["drop_weight"] > 0 else 1.0)
                  * (bias if i in themed else 1.0) for i in pool]
            return rng.choices(pool, weights=ws)[0]
        t -= 1
    return None


def spawn_counts(night, sp):
    horde = max(1, math.ceil((sp["BaseHordeCount"] + sp["BaseRunDifficulty"] * sp["DifficultyMultiplier"])
                             * sp["horde_size_multiplier"] * sp["player_factor"]))
    boss = night % sp["BossNightInterval"] == 0
    normal = sp["night_length_seconds"] / 4.5 * min(sp["BurstSize"], horde)
    n = sp["SurgesPerNight"]
    budget = max(sp["SurgeMinBudget"], horde) * (sp["BossSurgeBudgetScale"] if boss else 1.0)
    surges = [budget] * n
    if n:
        surges[-1] *= sp["FinaleBudgetScale"]
    return int(round(normal)), [int(round(s)) for s in surges]


def type_table(data, night, ad):
    names, ws = [], []
    for name, z in data["zombie_types"].items():
        if z["unlock_night"] > night:
            continue
        w = z["spawn_weight"] + z["weight_per_night"] * night + z["weight_per_ad_level"] * (ad - 1)
        if w > 0:
            names.append(name)
            ws.append(w)
    return names, ws


def roll_kill(row, elite, weights, bonus, expected, dropped, elapsed, ad, luck, data, pools, rng):
    K = data["constants"]
    items = data["items"]
    shift = (row["TierOffset"] + (K["elite_shift"] if elite else 0) + ad_shift(ad, K)
             + (K["luck"] if luck else 0.0) + pity_shift(dropped, expected, elapsed, K))
    w = apply_tier_shift(weights, shift, K["treasure_cap"])
    g = row["GuaranteedDropCount"]
    if elite:
        g = max(g, rng.randint(*K["elite_guaranteed"]))
    cap = max(row["MaxDrops"] + bonus, g)
    count = g
    for _ in range(g, cap):
        if rng.random() < row["DropChance"]:
            count += 1
    val = 0
    for _ in range(count):
        iid = pick_item(roll_tier(w, rng), row["ThemedItemIDs"], row["ThemedBias"], pools, items, rng)
        if iid:
            val += items[iid]["price"]
    return val


def roll_pinata(row, night, weights, ad, luck, data, pools, rng):
    K, sp = data["constants"], data["spawner"]
    boss_num = max(1, night // sp["BossNightInterval"])
    count = min(row["PinataBaseCount"] + row["PinataPerBossNumber"] * max(0, boss_num - 1),
                row["PinataMaxCount"])
    shift = row["TierOffset"] + ad_shift(ad, K) + (K["luck"] if luck else 0.0)
    w = apply_tier_shift(weights, shift, 0)
    tiers = [roll_tier(w, rng) for _ in range(count)]
    while sum(1 for t in tiers if t == 4) < min(row["MinTreasureCount"], count):
        j = tiers.index(min(tiers))
        tiers[j] = 4
    val = 0
    for t in tiers:
        iid = pick_item(t, row["ThemedItemIDs"], row["ThemedBias"], pools, data["items"], rng)
        if iid:
            val += data["items"][iid]["price"]
    return val


def simulate_night(night, data, pools, args, rng):
    sp = data["spawner"]
    weights, bonus, expected = curve_row(data["night_curve"], night)
    normal, surges = spawn_counts(night, sp)
    total = normal + sum(surges)
    kills = int(round(total * args.kill_fraction))
    names, ws = type_table(data, night, args.ad_level)
    elite_at = set()
    if kills:
        # first kill of each surge is elite; surge kills sit after the normal ones
        pos = normal * args.kill_fraction
        for s in surges:
            elite_at.add(min(kills - 1, int(round(pos))))
            pos += s * args.kill_fraction
    dropped = 0.0
    for k in range(kills):
        zt = rng.choices(names, weights=ws)[0]
        row = data["zombie_loot"].get(data["zombie_types"][zt]["loot_row"], data["zombie_loot"]["Default"])
        dropped += roll_kill(row, k in elite_at, weights, bonus, expected, dropped, k / kills,
                             args.ad_level, args.luck, data, pools, rng)
    pin = 0
    if night % sp["BossNightInterval"] == 0:
        pin = roll_pinata(data["zombie_loot"]["Boss"], night, weights, args.ad_level, args.luck, data, pools, rng)
    return dropped, pin


def pct(v, p):
    v = sorted(v)
    i = (len(v) - 1) * p
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    return v[lo] + (v[hi] - v[lo]) * (i - lo)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1000)
    ap.add_argument("--nights", type=int, default=10)
    ap.add_argument("--kill-fraction", type=float, default=0.85)
    ap.add_argument("--ad-level", type=int, default=1)
    ap.add_argument("--luck", type=int, default=0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--data", default=os.path.join(here, "loot_sim_data.json"))
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()
    data = json.load(open(args.data))
    pools = build_pools(data["items"])
    rng = random.Random(args.seed)
    print(f"runs={args.runs} kill_fraction={args.kill_fraction} ad_level={args.ad_level} "
          f"luck={args.luck} seed={args.seed}")
    hdr = ["night", "target", "mean", "p10", "p90", "min", "max", "pinata_mean", "IN_BAND"]
    fmt = "{:>5} {:>8} {:>8} {:>8} {:>8} {:>7} {:>7} {:>11} {:>8}"
    print(fmt.format(*hdr))
    rows = []
    for n in range(1, args.nights + 1):
        vals, pins = [], []
        for _ in range(args.runs):
            v, p = simulate_night(n, data, pools, args, rng)
            vals.append(v)
            pins.append(p)
        target = 700 * 1.2 ** (n - 1)
        p10, p90 = pct(vals, 0.1), pct(vals, 0.9)
        ok = p10 >= 0.7 * target and p90 <= 1.3 * target
        r = [n, round(target, 1), round(statistics.mean(vals), 1), round(p10, 1), round(p90, 1),
             min(vals), max(vals), round(statistics.mean(pins), 1), "YES" if ok else "NO"]
        rows.append(r)
        print(fmt.format(*r))
    if args.csv:
        with open(args.csv, "w", newline="") as f:
            f.write(",".join(hdr) + "\n")
            for r in rows:
                f.write(",".join(str(x) for x in r) + "\n")


if __name__ == "__main__":
    main()
