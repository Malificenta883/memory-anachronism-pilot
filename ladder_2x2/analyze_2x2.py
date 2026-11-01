"""Analyse all results_*.jsonl files in this folder.

For every answer:
  choice     = NEW value / OLD value / BOTH ("she trains at both X and Y") /
               ABSTAIN ("I cannot determine, the memories conflict") / unclear
               (mentions after "no longer", "not", "previously", "used to", "moved from", ...
                are ignored, so "She no longer lives in Vienna, she lives in Budapest" -> NEW;
                if both values are named, the last present-tense "she lives/works/trains in X" decides)
  confidence = the number after "confidence"

Outputs:
  answers_classified.csv  every answer with its choice (check the 'unclear' ones by hand)
  summary_2x2.csv         share of NEW answers per model x dates x order x mass, with 95% interval
  summary_position.csv    dated+shuffled only: share of NEW by position of the new entry
  calibration.csv         dated conditions: mean confidence when the answer follows the date vs not
  ladder_2x2.png          the main figure

Reading the numbers:
  share_new is counted over ALL answers (BOTH / ABSTAIN / unclear count as not-new).
  share_new in dated+shuffled   = how often the model follows the DATE when the order says nothing
  share_new in undated+chrono   = how often it follows the POSITION (last = new) without dates
  share_new in undated+shuffled = no time cue at all; shows its pure preference (mass / position)
  If dated+shuffled is close to undated+shuffled, the dates are almost not used.

The interval is a Wilson 95% interval over items (each cell has 9 items x reps).
Answers to the same item are not independent, so with reps > 1 the interval is too narrow;
read it as rough.

Run:  python analyze_2x2.py
"""
import csv, glob, json, math, re
from collections import defaultdict

P = {p["id"]: p for p in map(json.loads, open("prompts.jsonl", encoding="utf-8"))}
NEG = (r"(?:\b(?:no longer|not|never|previously|formerly|used to|moved (?:away )?from|left|instead of|"
       r"rather than|before|earlier)\b|n't\b)")


def strip_negated(text, value):
    """remove mentions of value that come right after a negation / past marker"""
    return re.sub(NEG + r"[^.;:!?]{0,60}?" + re.escape(value), " ", text, flags=re.I)


ASSERT = r"\b(?:lives|is living|works|is working|trains|is training|is based|currently \w+)\s+(?:in|at|for)\s+"
ABSTAIN = (r"\b(?:cannot|can't|can not|unable to|not able to|don't have enough|do not have enough|not enough information|"
           r"insufficient|impossible to|not possible to|cannot determine|unclear|don't have any information|do not have any information|"
           r"don't have information|no information)\b")


def classify(ans, old, new):
    """NEW / OLD / BOTH ('she trains at both X and Y') / ABSTAIN ('I cannot determine') / unclear"""
    text = " ".join(ans.split())
    first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    first_asserted = {v for v in (old, new) if re.search(ASSERT + re.escape(v), strip_negated(first, v), re.I)}
    if re.search(ABSTAIN, first, re.I) and len(first_asserted) != 1:
        return "ABSTAIN"
    if re.search(r"\bboth\b", first, re.I) and re.search(re.escape(old), first, re.I) and re.search(re.escape(new), first, re.I):
        return "BOTH"
    for t in (first, text):                        # first sentence; if unclear, the whole answer
        o = re.search(re.escape(old), strip_negated(t, old), re.I) is not None
        n = re.search(re.escape(new), strip_negated(t, new), re.I) is not None
        if n and not o: return "NEW"
        if o and not n: return "OLD"
    # both values named: take the LAST present-tense statement ("...she lives in X")
    asserted = [(m.start(), v) for v, lab in ((old, "OLD"), (new, "NEW"))
                for m in re.finditer(ASSERT + re.escape(v), strip_negated(text, v), re.I)]
    if asserted:
        last = max(asserted)[1]
        return "NEW" if last == new else "OLD"
    if re.search(ABSTAIN, text, re.I):
        return "ABSTAIN"
    return "unclear"


def confidence(ans):
    m = re.search(r"confidence[^0-9]{0,40}(\d{1,3})", ans, re.I)
    return int(m.group(1)) if m else None


def wilson(k, n, z=1.96):
    if n == 0: return (float("nan"),) * 2
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - h), min(1, c + h)


rows = []
for fn in sorted(glob.glob("results_*.jsonl")):
    for line in open(fn, encoding="utf-8"):
        r = json.loads(line); p = P[r["id"]]
        rows.append(dict(model=r["model"], id=r["id"], rep=r["rep"], dates=p["dates"], order=p["order"],
                         mass=p["mass"], template=p["template"], new_pos=p["new_pos"], old=p["old"], new=p["new"],
                         choice=classify(r["answer"], p["old"], p["new"]), confidence=confidence(r["answer"]),
                         answer=" ".join(r["answer"].split())[:300]))
if not rows:
    raise SystemExit("no results_*.jsonl files yet - run run_ollama.py first")

with open("answers_classified.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
unclear = [r for r in rows if r["choice"] == "unclear"]
print(f"{len(rows)} answers, {len(unclear)} unclear (see answers_classified.csv)")


def summarise(keys, subset):
    g = defaultdict(list)
    for r in subset: g[tuple(r[k] for k in keys)].append(r)
    out = []
    for key, rs in sorted(g.items()):
        n = len(rs); c = {x: sum(r["choice"] == x for r in rs) for x in ("NEW", "OLD", "BOTH", "ABSTAIN", "unclear")}
        k = c["NEW"]; lo, hi = wilson(k, n)        # share of ALL answers that follow the new entry
        out.append(dict(zip(keys, key), n=n, new=k, share_new=round(k / n, 2) if n else "",
                        ci_low=round(lo, 2), ci_high=round(hi, 2), old=c["OLD"], both=c["BOTH"],
                        abstain=c["ABSTAIN"], unclear=c["unclear"]))
    return out


S = summarise(["model", "dates", "order", "mass"], rows)
SP = summarise(["model", "new_pos", "mass"], [r for r in rows if r["dates"] == "dated" and r["order"] == "shuffled"])
for name, tab in (("summary_2x2.csv", S), ("summary_position.csv", SP)):
    with open(name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(tab[0])); w.writeheader(); w.writerows(tab)

cal = []
for model in sorted({r["model"] for r in rows}):
    for follows in ("NEW", "OLD"):
        cs = [r["confidence"] for r in rows if r["model"] == model and r["dates"] == "dated"
              and r["choice"] == follows and r["confidence"] is not None]
        cal.append(dict(model=model, answer_follows=("date (correct)" if follows == "NEW" else "mass/position (wrong)"),
                        n=len(cs), mean_confidence=round(sum(cs) / len(cs), 1) if cs else ""))
with open("calibration.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(cal[0])); w.writeheader(); w.writerows(cal)

# ---- console table: one line per model x condition, share NEW at each mass
masses = sorted({r["mass"] for r in rows})
print("\nshare of answers that follow the NEW (latest) entry   masses:", masses)
for model in sorted({r["model"] for r in rows}):
    print(f"\n{model}")
    for dates in ("dated", "undated"):
        for order in ("chrono", "shuffled"):
            vals = []
            for m in masses:
                s = [x for x in S if x["model"] == model and x["dates"] == dates and x["order"] == order and x["mass"] == m]
                vals.append(f"{s[0]['share_new']:>5}" if s and s[0]["n"] else "    -")
            print(f"  {dates:8s} {order:9s} " + " ".join(vals))
    print("  dated shuffled, by position of the new entry:")
    for pos in ("first", "middle", "last"):
        vals = []
        for m in masses:
            s = [x for x in SP if x["model"] == model and x["new_pos"] == pos and x["mass"] == m]
            vals.append(f"{s[0]['share_new']:>5}" if s and s[0]["n"] else "    -")
        print(f"    {pos:7s}          " + " ".join(vals))
print("\nother answers per condition (OLD / BOTH / ABSTAIN / unclear, all masses together):")
for model in sorted({r["model"] for r in rows}):
    for dates in ("dated", "undated"):
        for order in ("chrono", "shuffled"):
            rs = [r for r in rows if r["model"] == model and r["dates"] == dates and r["order"] == order]
            c = {x: sum(r["choice"] == x for r in rs) for x in ("NEW", "OLD", "BOTH", "ABSTAIN", "unclear")}
            print(f"  {model:14s} {dates:8s} {order:9s} n={len(rs):3d}  NEW {c['NEW']:3d}  OLD {c['OLD']:3d}  "
                  f"BOTH {c['BOTH']:3d}  ABSTAIN {c['ABSTAIN']:3d}  unclear {c['unclear']:3d}")
print("\ncalibration (dated conditions):")
for c in cal: print(f"  {c['model']:20s} {c['answer_follows']:24s} n={c['n']:<4} mean confidence {c['mean_confidence']}")

# ---- figure
try:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
except ImportError:
    raise SystemExit("matplotlib not installed - tables are written, figure skipped")
models = sorted({r["model"] for r in rows})
fig, axes = plt.subplots(len(models), 3, figsize=(13, 3.2 * len(models)), squeeze=False, sharey=True)
style = {("dated", "chrono"): ("#1f4e79", "-", "o", "dated, chronological"),
         ("dated", "shuffled"): ("#1f4e79", "--", "s", "dated, shuffled"),
         ("undated", "chrono"): ("#c55a11", "-", "o", "no dates, chronological"),
         ("undated", "shuffled"): ("#c55a11", "--", "s", "no dates, shuffled")}
xs = list(range(len(masses)))
for i, model in enumerate(models):
    for j, conds in enumerate([[("dated", "chrono"), ("dated", "shuffled")],
                               [("undated", "chrono"), ("undated", "shuffled")]]):
        ax = axes[i][j]
        for c in conds:
            col, ls, mk, lab = style[c]
            pts = [next((x for x in S if x["model"] == model and x["dates"] == c[0] and x["order"] == c[1]
                         and x["mass"] == m and x["n"]), None) for m in masses]
            X = [x for x, p in zip(xs, pts) if p]; Y = [p["share_new"] for p in pts if p]
            lo = [p["share_new"] - p["ci_low"] for p in pts if p]; hi = [p["ci_high"] - p["share_new"] for p in pts if p]
            ax.errorbar(X, Y, yerr=[lo, hi], color=col, ls=ls, marker=mk, capsize=3, label=lab)
        ax.set_title(f"{model}: {'with dates' if j == 0 else 'without dates'}", fontsize=10)
    ax = axes[i][2]
    for pos, col in (("first", "#7f3f98"), ("middle", "#3a7d44"), ("last", "#888888")):
        pts = [next((x for x in SP if x["model"] == model and x["new_pos"] == pos and x["mass"] == m and x["n"]), None)
               for m in masses]
        X = [x for x, p in zip(xs, pts) if p]; Y = [p["share_new"] for p in pts if p]
        ax.plot(X, Y, marker="o", color=col, label=f"new entry {pos}")
    ax.set_title(f"{model}: dated + shuffled, by position", fontsize=10)
    for ax in axes[i]:
        ax.set_xticks(xs); ax.set_xticklabels(masses); ax.set_ylim(-0.05, 1.05); ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="lower left")
    axes[i][0].set_ylabel("share following the NEW entry")
for ax in axes[-1]: ax.set_xlabel("number of older entries (mass)")
fig.suptitle("Ladder 2x2: dates vs order vs mass (9 items per cell; bars = Wilson 95% interval)", fontsize=11)
fig.tight_layout(); fig.savefig("ladder_2x2.png", dpi=180)
print("\nfigure -> ladder_2x2.png")
