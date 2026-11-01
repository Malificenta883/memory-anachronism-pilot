"""Turn an Ollama-window log of the staged case (runs marked 'runN:') into the same files run_case.py writes,
so all models sit side by side in this folder.

Usage:  python import_cli_log.py ../LLama/run_llama_P.txt llama3.1:8b
Writes case_<model>.jsonl and reading_<model>.csv (the original log stays where it is and can still be
read by ../analyze_PS.py). If a question was asked twice in a run, the first answer is kept; steps are
put in the standard order S1 S2 S3 R1 R2 R3.
"""
import csv, json, re, sys

src, model = sys.argv[1], sys.argv[2]
tag = re.sub(r"[^A-Za-z0-9._-]+", "_", model)
ORDER = ["S1", "S2", "S3", "R1", "R2", "R3"]
KEYS = [("S1", "Stage 1"), ("S2", "Stage 2"), ("S3", "Stage 3"), ("R1", "charged on 14 March"),
        ("R2", "As of 10 March"), ("R3", "On 12 March")]


def key(p):
    for k, w in KEYS:
        if w in p: return k
    return "?"


def turns(body):
    out, state, p, a = [], None, [], []
    for ln in body.split("\n"):
        s = ln.strip()
        if s in ('>>> """', '... """'):
            if state == "prompt":
                state, a = "ans", []
            else:
                if state == "ans": out.append(("\n".join(p), "\n".join(a).strip()))
                state, p = "prompt", []
            continue
        if state == "prompt": p.append(ln[4:] if ln.startswith("... ") else ln)
        elif state == "ans": a.append(ln)
    if state == "ans": out.append(("\n".join(p), "\n".join(a).strip()))
    return out


text = open(src, encoding="utf-8").read()
parts = re.split(r"(?m)^run(\d+):\s*$", text)
records = []
for i in range(1, len(parts), 2):
    run, seen = int(parts[i]), set()
    for prompt, ans in turns(parts[i + 1]):
        k = key(prompt)
        if k in seen or k == "?": continue
        seen.add(k)
        records.append(dict(run=run, step=k, model=model, temperature=None, prompt=prompt, answer=ans,
                            source=src))
records.sort(key=lambda x: (x["run"], ORDER.index(x["step"])))
with open(f"case_{tag}.jsonl", "w", encoding="utf-8") as f:
    for x in records: f.write(json.dumps(x, ensure_ascii=False) + "\n")
with open(f"reading_{tag}.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["run"] + ORDER)
    for run in sorted({x["run"] for x in records}):
        by = {x["step"]: " ".join(x["answer"].split()) for x in records if x["run"] == run}
        w.writerow([run] + [by.get(k, "") for k in ORDER])
print(f"{len(records)} answers from {len({x['run'] for x in records})} runs -> case_{tag}.jsonl, reading_{tag}.csv")
