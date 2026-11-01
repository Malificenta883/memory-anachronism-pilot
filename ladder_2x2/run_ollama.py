"""Send every prompt from prompts.jsonl to a local Ollama model, one fresh chat per prompt
(same as /clear before each prompt in the Ollama window).

Usage (Ollama must be running; see `ollama list` for model names):
    python run_ollama.py --model qwen2.5:7b
    python run_ollama.py --model llama3.1:8b --reps 2
    python run_ollama.py --model gemma3:4b --temperature 0

Writes results_<model>.jsonl. If the run stops, start it again with the same command:
prompts that already have an answer are skipped.
Only the standard library is used.
"""
import argparse, json, os, re, time, urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True, help="Ollama model name, e.g. qwen2.5:7b")
ap.add_argument("--prompts", default="prompts.jsonl")
ap.add_argument("--out", default=None, help="default: results_<model>.jsonl")
ap.add_argument("--reps", type=int, default=1, help="answers per prompt (default 1; variety comes from the items)")
ap.add_argument("--temperature", type=float, default=None, help="default: the model's own setting")
ap.add_argument("--host", default="http://localhost:11434")
args = ap.parse_args()

out = args.out or "results_" + re.sub(r"[^A-Za-z0-9._-]+", "_", args.model) + ".jsonl"
done = set()
if os.path.exists(out):
    with open(out, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line); done.add((r["id"], r["rep"]))

prompts = [json.loads(l) for l in open(args.prompts, encoding="utf-8")]
todo = [(p, rep) for p in prompts for rep in range(args.reps) if (p["id"], rep) not in done]
print(f"{len(todo)} answers to get ({len(done)} already in {out})")


def ask(text):
    body = {"model": args.model, "messages": [{"role": "user", "content": text}], "stream": False}
    if args.temperature is not None:
        body["options"] = {"temperature": args.temperature}
    req = urllib.request.Request(args.host + "/api/chat", data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode("utf-8"))["message"]["content"]


t0 = time.time()
with open(out, "a", encoding="utf-8") as f:
    for i, (p, rep) in enumerate(todo, 1):
        for attempt in range(3):
            try:
                ans = ask(p["prompt"]); break
            except Exception as e:
                print("  error:", e, "- retrying"); time.sleep(3)
        else:
            raise SystemExit("Ollama does not answer. Is it running? Is the model name right (ollama list)?")
        f.write(json.dumps({"id": p["id"], "rep": rep, "model": args.model, "temperature": args.temperature,
                            "answer": ans}, ensure_ascii=False) + "\n")
        f.flush()
        if i % 10 == 0 or i == len(todo):
            print(f"  {i}/{len(todo)}  ({time.time() - t0:.0f} s)")
print("done ->", out)
