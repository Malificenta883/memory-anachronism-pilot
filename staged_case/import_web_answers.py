"""Turn answers copied from web chats (layout of answers_web_TEMPLATE.txt: 'model:' line, 'runN:', '[S1]'...)
into case_<tag>.jsonl and reading_<tag>.csv, like run_case.py writes. Empty runs are skipped.

Usage:  python import_web_answers.py claude_crime_web.txt claude-opus-5.5_web
        python import_web_answers.py gemini_crime_web.txt gemini-3.1-pro-nolimit_web _WIde   (only runs named run1_WIde: ...)
"""
import csv, json, re, sys
src, tag = sys.argv[1], sys.argv[2]
suffix = sys.argv[3] if len(sys.argv) > 3 else ""
ORDER = ["S1", "S2", "S3", "R1", "R2", "R3", "R4"]
text = open(src, encoding="utf-8").read()
model = (re.search(r"(?m)^model:\s*(.+)$", text) or [None, tag])[1].strip(" ()")
records = []
for m in re.finditer(r"(?ms)^run(\d+)" + re.escape(suffix) + r":\s*$(.*?)(?=^run\d+\w*:\s*$|\Z)", text):
    run, body = int(m.group(1)), m.group(2)
    parts = re.split(r"\[(S1|S2|S3|R1|R2|R3|R4)\]\s*", body)
    ans = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}
    if not any(ans.values()): continue
    for k in [k for k in ORDER if k in ans]:
        records.append(dict(run=run, step=k, model=model, temperature=None, prompt="(web chat, see prompts_for_web.txt)",
                            answer=ans.get(k, ""), source=src))
with open(f"case_{tag}.jsonl", "w", encoding="utf-8") as f:
    for x in records: f.write(json.dumps(x, ensure_ascii=False) + "\n")
with open(f"reading_{tag}.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["run"] + ORDER)
    for run in sorted({x["run"] for x in records}):
        by = {x["step"]: " ".join(x["answer"].split()) for x in records if x["run"] == run}
        w.writerow([run] + [by.get(k, "") for k in ORDER])
print(f"{model}: {len({x['run'] for x in records})} runs -> case_{tag}.jsonl")
