"""Ladder 2x2: does a model use the DATES of memory entries, or only their ORDER and MASS?

Builds prompts.jsonl (one prompt per line) and prompts_preview.txt (readable).

Design (4 conditions x 5 masses x 9 items = 180 prompts):
  dates   : "dated"   - every entry starts with a date; the new entry has the latest date
            "undated" - no dates at all
  order   : "chrono"   - entries in true time order, new entry LAST
            "shuffled" - entries in random order; the new entry is placed first / middle / last
                         (balanced across items, so position can be analysed separately)
  mass    : number of older entries that support the OLD value: 1, 3, 5, 10, 20
  items   : 3 fact types (city, employer, gym) x 3 value pairs (old -> new)

What each cell tells you:
  dated+chrono     date and order agree            -> baseline, should be easy
  dated+shuffled   order is uninformative, date is the only time cue
                   -> share of NEW answers = how much the model reads dates
  undated+chrono   order is the only time cue      -> how much the model reads position
  undated+shuffled no time cue at all              -> pure mass / position preference (control)

No entry contains a time word ("now", "moved", "no longer", "corrected", ...),
so the only time information is the date (and, in chrono, the order).

Run:  python make_prompts.py            (seed fixed, so the file is reproducible)
"""
import json, random

SEED = 2026
MASSES = [1, 3, 5, 10, 20]

TEMPLATES = {
    "city": {
        "pairs": [("Vienna", "Budapest"), ("Prague", "Warsaw"), ("Lisbon", "Madrid")],
        "new": "She lives in {v}.",
        "old": [
            "She lives in {v}.",
            "She mentioned her flat in {v}.",
            "She talked about her neighbours in {v}.",
            "She said she loves the cafés near her home in {v}.",
            "She asked how to renew her public transport pass in {v}.",
            "She invited friends for dinner at her place in {v}.",
            "She complained about the noise from the street outside her flat in {v}.",
            "She said the rent for her flat in {v} went up.",
            "She described her walk to the park near her home in {v}.",
            "She mentioned the market close to her flat in {v}.",
            "She said her landlord in {v} fixed the heating.",
            "She talked about cycling to the shops near her home in {v}.",
        ],
        "question": "Where does she live now?",
    },
    "employer": {
        "pairs": [("Northwind Analytics", "Bluefield Labs"), ("Corvel Systems", "Ardent Data"),
                  ("Maple Ridge Studio", "Quillstone Media")],
        "new": "She works at {v}.",
        "old": [
            "She works at {v}.",
            "She mentioned a meeting with her team at {v}.",
            "She complained about the coffee machine at {v}.",
            "She said her manager at {v} liked her report.",
            "She talked about a deadline at {v}.",
            "She described the office of {v}.",
            "She said she had lunch with colleagues from {v}.",
            "She mentioned a training course organised by {v}.",
            "She asked how to write an email to HR at {v}.",
            "She said {v} gave her a new laptop.",
            "She talked about the commute to {v}.",
            "She mentioned a team party at {v}.",
        ],
        "question": "Where does she work now?",
    },
    "gym": {
        "pairs": [("Ironleaf Gym", "Harbour Fitness"), ("Peak Motion Club", "Riverside Sports Hall"),
                  ("Copperfield Gym", "Lantern Climbing Centre")],
        "new": "She trains at {v}.",
        "old": [
            "She trains at {v}.",
            "She mentioned her trainer at {v}.",
            "She said the showers at {v} were cold.",
            "She talked about a yoga class at {v}.",
            "She described the weights area at {v}.",
            "She asked how to pause her membership at {v}.",
            "She said {v} was crowded on Monday.",
            "She mentioned a friend she met at {v}.",
            "She talked about the opening hours of {v}.",
            "She said she ran 5 km on a treadmill at {v}.",
            "She mentioned the music played at {v}.",
            "She said she forgot her towel at {v}.",
        ],
        "question": "Where does she train now?",
    },
}

HEADER = "These are your saved memories about the user from previous conversations:"
ASK = "Answer in one sentence, then give your confidence from 0 to 100."
NEW_DATE = "2026-07-15"


def old_dates(rng, n):
    """n distinct dates between 2026-01-05 and 2026-06-30, sorted."""
    days = rng.sample(range(0, 177), n)          # 177 days from 5 Jan to 30 Jun
    import datetime as dt
    start = dt.date(2026, 1, 5)
    return sorted((start + dt.timedelta(d)).isoformat() for d in days)


def build():
    rng = random.Random(SEED)
    prompts = []
    for mass in MASSES:
        for t_i, (tname, T) in enumerate(TEMPLATES.items()):
            for p_i, (old, new) in enumerate(T["pairs"]):
                # one shared set of older entries + dates per item, reused in all 4 conditions,
                # so the conditions differ ONLY in dates/order
                olds = [T["old"][k % len(T["old"])].format(v=old) for k in range(mass)]
                rng.shuffle(olds)
                dates = old_dates(rng, mass)
                old_entries = list(zip(dates, olds))           # chronological
                new_entry = (NEW_DATE, T["new"].format(v=new))
                # balanced position of the new entry in the shuffled order
                positions = ["first", "middle", "last"] if mass >= 2 else ["first", "last"]
                new_pos = positions[(p_i + t_i + mass) % len(positions)]
                others = old_entries[:]
                rng.shuffle(others)
                if new_pos == "first":
                    shuffled = [new_entry] + others
                elif new_pos == "last":
                    shuffled = others + [new_entry]
                else:
                    k = rng.randint(1, len(others) - 1)
                    shuffled = others[:k] + [new_entry] + others[k:]
                chrono = old_entries + [new_entry]
                for dated in (True, False):
                    for order, seq, pos in (("chrono", chrono, "last"), ("shuffled", shuffled, new_pos)):
                        lines = [f"{d}: {s}" if dated else f"- {s}" for d, s in seq]
                        text = "\n".join([HEADER, *lines, "", f"Question: {T['question']} {ASK}"])
                        pid = f"{'D' if dated else 'N'}{order[0].upper()}_m{mass:02d}_{tname}_{p_i}"
                        prompts.append(dict(id=pid, dates="dated" if dated else "undated", order=order,
                                            mass=mass, template=tname, pair=p_i, old=old, new=new,
                                            new_pos=pos, prompt=text))
    return prompts


if __name__ == "__main__":
    P = build()
    with open("prompts.jsonl", "w", encoding="utf-8") as f:
        for p in P:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    with open("prompts_preview.txt", "w", encoding="utf-8") as f:
        for p in P:
            f.write(f"===== {p['id']}  ({p['dates']}, {p['order']}, mass {p['mass']}, new entry {p['new_pos']}; "
                    f"old={p['old']} new={p['new']})\n{p['prompt']}\n\n")
    from collections import Counter
    c = Counter((p["dates"], p["order"]) for p in P)
    print(len(P), "prompts written to prompts.jsonl;", dict(c))
    print("shuffled new-entry positions:", Counter(p["new_pos"] for p in P if p["order"] == "shuffled"))
