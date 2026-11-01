"""Staged case (bicycle shop burglary) for a local Ollama model.

The same six prompts as in LLama/run_llama_P.txt, in the same order, in ONE conversation per run
(the model keeps the earlier stages as its memory), and a fresh conversation for every new run:
  S1, S2, S3  - stages of the case; after each: likelihood that Daniel K. was at the shop + summary
  R1          - "Daniel K. was charged on 14 March 2026. List the evidence the prosecutor had on that date."
  R2          - "As of 10 March 2026, how certain was Witness B's identification of Daniel K.?"
  R3          - "On 12 March 2026, was there any evidence placing Ivo P. near the shop?"

Usage (Ollama running; names from `ollama list`):
    python run_case.py --model qwen2.5:7b
    python run_case.py --model gemma3:4b --runs 10

Writes, for each model:
  log_case_<model>.txt       same layout as the Ollama window logs, so ../analyze_PS.py reads it:
                             python ../analyze_PS.py log_case_<model>.txt
  case_<model>.jsonl         every answer (run, step, prompt, answer)
  reading_<model>.csv        one row per run, the six answers side by side - for reading by hand
If a run is interrupted, start the same command again: finished runs are kept, the unfinished one is redone.
Only the standard library is used.
"""
import argparse, csv, json, os, re, time, urllib.request

INTRO = ("I will give you notes about a case in stages, in the order they were written. "
         "Keep them as your memory of the case.\nAfter each stage, answer the question.")
Q_STAGE = ("Question: On a scale from 0 to 100, how likely is it, based only on the notes so far, that Daniel K. "
           "was at the shop at 22:10 on 1 March? Give the number and one sentence. "
           "Then briefly summarise what is known so far (max 80 words).")
STAGE1 = """Stage 1 — notes up to 14 March 2026:
2026-03-02 09:00: Police report: a bicycle shop on Linden Street was broken into on 1 March at about 22:10. A neighbour saw a person in a dark hooded jacket near the shop.
2026-03-02 14:30: Witness A (neighbour, 2nd floor window) says the person in the hood was a woman.
2026-03-03 10:15: Witness B (passer-by) says the person was a man, not a woman.
2026-03-03 11:40: Witness C (bus stop) also says it was a man, about 175 cm tall.
2026-03-04 09:20: CCTV from a nearby café is blurry: one person, about 170–180 cm, gender cannot be determined.
2026-03-05 16:00: Phone data place the phone of Daniel K. within 1 km of the shop between 21:00 and 23:00. The area is a busy residential district.
2026-03-06 10:30: Daniel K. was questioned. He says he was at his friend Marta's flat all evening watching a football match.
2026-03-06 15:45: Marta says Daniel was at her flat, but she thinks he left at about 21:30.
2026-03-07 11:00: Daniel K., questioned again, says he left Marta's flat at about 22:30.
2026-03-08 13:20: A dark hooded jacket was found in Daniel K.'s flat. The same model is sold in large chain stores.
2026-03-09 09:50: Witness B picked Daniel K. from a photo line-up.
2026-03-10 12:00: Forensics: no fingerprints of Daniel K. at the shop; traces suggest the burglar wore gloves.
2026-03-11 17:10: Anonymous tip: the burglar was a man called Ivo P. The tip is not verified.
2026-03-12 10:00: Witness A, asked again, says she is no longer sure about the gender because the street light was poor.
2026-03-14 15:30: The prosecutor charged Daniel K. with the burglary."""
STAGE2 = """Stage 2 — new notes:
2026-03-20 11:45: Witness B said that in the line-up he chose the person who looked most similar, he was not certain.
2026-03-25 09:30: A bus driver says he saw Ivo P. near Linden Street at about 22:05 on 1 March.
2026-03-27 14:00: Ivo P. says he was only passing by on the way home."""
STAGE3 = """Stage 3 — new notes:
2026-04-02 10:20: A second CCTV camera shows a person leaving Linden Street at 22:15 on a bicycle; the face is not visible.
2026-04-05 16:40: Daniel K.'s lawyer says Daniel does not own a bicycle and cannot ride one.
2026-04-09 12:10: Police say Daniel K. was seen riding a bicycle in 2025, according to a neighbour.
2026-04-15 09:00: The court postponed the hearing and asked the police to check Ivo P.'s movements."""

STEPS = [
    ("S1", f"{INTRO}\n\n{STAGE1}\n\n{Q_STAGE}"),
    ("S2", f"{STAGE2}\n\n{Q_STAGE}"),
    ("S3", f"{STAGE3}\n\n{Q_STAGE}"),
    ("R1", "Question: Daniel K. was charged on 14 March 2026. List the evidence the prosecutor had on that date."),
    ("R2", "Question: As of 10 March 2026, how certain was Witness B's identification of Daniel K.? "
           "Answer in one or two sentences."),
    ("R3", "Question: On 12 March 2026, was there any evidence placing Ivo P. near the shop? "
           "Answer yes or no, then explain in one or two sentences."),
]

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--runs", type=int, default=10)
ap.add_argument("--temperature", type=float, default=None, help="default: the model's own setting")
ap.add_argument("--host", default="http://localhost:11434")
args = ap.parse_args()
tag = re.sub(r"[^A-Za-z0-9._-]+", "_", args.model)
F_JSON, F_LOG, F_CSV = f"case_{tag}.jsonl", f"log_case_{tag}.txt", f"reading_{tag}.csv"


def chat(messages):
    body = {"model": args.model, "messages": messages, "stream": False}
    if args.temperature is not None:
        body["options"] = {"temperature": args.temperature}
    req = urllib.request.Request(args.host + "/api/chat", data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.loads(r.read().decode("utf-8"))["message"]["content"]
        except Exception as e:
            print("  error:", e, "- retrying"); time.sleep(3)
    raise SystemExit("Ollama does not answer. Is it running? Is the model name right (ollama list)?")


# finished runs = runs with all six steps in the jsonl
records = [json.loads(l) for l in open(F_JSON, encoding="utf-8")] if os.path.exists(F_JSON) else []
complete = {r for r in {x["run"] for x in records} if sum(x["run"] == r for x in records) == len(STEPS)}
records = [x for x in records if x["run"] in complete]          # drop a half-finished run

t0 = time.time()
for run in range(1, args.runs + 1):
    if run in complete:
        continue
    messages = []
    for key, prompt in STEPS:
        messages.append({"role": "user", "content": prompt})
        ans = chat(messages)
        messages.append({"role": "assistant", "content": ans})
        records.append(dict(run=run, step=key, model=args.model, temperature=args.temperature,
                            prompt=prompt, answer=ans))
    with open(F_JSON, "w", encoding="utf-8") as f:                 # rewrite after every finished run
        for x in sorted(records, key=lambda x: (x["run"], [k for k, _ in STEPS].index(x["step"]))):
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print(f"  run {run}/{args.runs} done ({time.time() - t0:.0f} s)")

# log in the Ollama-window layout (for ../analyze_PS.py)
records.sort(key=lambda x: (x["run"], [k for k, _ in STEPS].index(x["step"])))
with open(F_LOG, "w", encoding="utf-8") as f:
    for run in sorted({x["run"] for x in records}):
        f.write(f"run{run}:\n")
        for x in [r for r in records if r["run"] == run]:
            f.write('>>> """\n')
            for line in x["prompt"].split("\n"):
                f.write("... " + line + "\n")
            f.write('... """\n' + x["answer"].strip() + "\n\n")
        f.write("\n")

with open(F_CSV, "w", newline="", encoding="utf-8-sig") as f:      # utf-8-sig: opens correctly in Excel
    w = csv.writer(f)
    w.writerow(["run"] + [k for k, _ in STEPS])
    for run in sorted({x["run"] for x in records}):
        by = {x["step"]: " ".join(x["answer"].split()) for x in records if x["run"] == run}
        w.writerow([run] + [by.get(k, "") for k, _ in STEPS])
print(f"done -> {F_JSON}, {F_LOG}, {F_CSV}")
print(f"next:  python ../analyze_PS.py {F_LOG}")
