# What was known, and when: memory anachronism in LLM agents (pilot)

*Marharyta Shvets · Eötvös Loránd University (ELTE), Budapest · October 2026 · first phase*

Errors in investigations cost innocent people years of their lives. The National Registry of Exonerations
lists over 3,000 wrongful convictions in the USA, and mistaken identification is among the most common
causes. AI agents are starting to draft police reports and summarise case files. If an agent's memory
cannot keep **what was known, and when**, it can repeat the oldest error of investigations: a story that
becomes more certain than its evidence.

This repository is a small first test of that risk. It asks two questions:

1. **Does a model use the dates of memory entries, or only their order and number ("mass")?**
2. **When a case arrives stage by stage, does the model keep what was known at each date, and does its
   own summary keep the uncertainty of the evidence?**

I call the two failures **memory anachronism**:
*parachronism* — an outdated state keeps being used after the world has changed;
*prochronism* — later knowledge is projected onto an earlier moment, and the record of what was known
then is lost.

---

## Findings in short

1. **Two of three small open models follow the order of memory entries, not their dates.** When the
   newest entry is listed first, they mostly answer with the old value.
2. **Small models put later knowledge on an earlier date.** Asked what was known on 10 March, they
   include a doubt first recorded on 20 March.
3. **Frontier models keep the dates, but two of three store an inference as a fact in their
   summaries.** Asked directly, the same model says that the fact is not established.

### 1. Dates or order? (`ladder_2x2/`)

The model gets a list of "saved memories" about a person. One entry, with the latest date, gives a new
city, employer or gym; 3 to 20 older entries give the old one. The list is shuffled, so only the dates
show which entry is new. How often does the answer follow the newest entry?

| model | newest entry listed last | newest entry listed first |
|---|---|---|
| Llama 3.1 8B | 12 / 12 | 12 / 12 |
| Qwen 2.5 7B | 12 / 12 | 5 / 12 |
| Gemma 3 4B | 11 / 12 | 3 / 12 |

Llama reads the dates. Qwen and Gemma read the position: listed first, the newest entry loses to the
older ones. Their confidence does not show the error (about 95/100 for wrong answers, 96–97 for right
ones). The full design, the conditions without dates and the figures are in [`ladder_2x2/`](ladder_2x2/).

### 2. What was known on 10 March? (`staged_case/`)

A fictional burglary case arrives in three stages (notes dated 2 March – 15 April). Witness B picks the
suspect from a line-up on 9 March and says he was not certain on 20 March. After all stages the model is
asked: *"As of 10 March, how certain was Witness B's identification?"*

| model | runs | doubt put on 10 March | doubt dated later (correct) |
|---|---|---|---|
| Gemma 3 4B (local) | 10 | 10 | 0 |
| Llama 3.1 8B (local) | 10 | 10 | 0 |
| Qwen 2.5 7B (local) | 10 | 6 | 4 |
| Claude Opus 5.5 (web) | 5 | 0 | 5 |
| Gemini 3.1 Pro (web) | 10 | 0 | 10 |
| Qwen 3.8 Max (web) | 3 | 0 | 3 |

Other later-date leaks, the figure and all answers are in [`staged_case/`](staged_case/).

### 3. The summary stores an inference as a fact

At stage 3 the notes say: *"A second CCTV camera shows a person leaving Linden Street at 22:15 on a
bicycle; the face is not visible."* The notes do not say that this person is the burglar, nor what was
stolen. Linking the two is a plausible inference from the setting (a bicycle shop: steal a bicycle,
ride away on it), and a human reader makes it too. The question is whether the summary keeps it as an
inference or writes it as a fact.

| model | stage-3 summaries: "the suspect fled on a bicycle" | asked "Is it established that the burglar left on a bicycle?" |
|---|---|---|
| Gemini 3.1 Pro | 10 / 10 | "No", 5 / 5 * |
| Qwen 3.8 Max | 3 / 3 | not asked |
| Claude Opus 5.5 | 0 / 5 ("unidentified cyclist") | not asked |
| small local models | 0 / 30 | not asked |

\* asked in the 5 runs without a word limit on the summary.

Gemini knows that the link is not established, but writes it into the story. In one run the summary
says the suspect "likely fled": of the possible readings the model keeps the most probable one, and in
the other runs even the "likely" is gone. The summary keeps the top hypothesis and drops its probability.

**Why it matters.** Agent memory over long cases is built from summaries. A summary that turns an
inference into a fact becomes, at the next stage, a premise — the mechanism of *tunnel vision* in
investigations. Direct-question tests do not catch it: the same model answers correctly when asked.

---

## What this suggests for agent memory

- Keep **dated layers with their sources**; never overwrite what was known at t1.
- At each stage **re-read the sources, not the agent's own previous summary**.
- Mark **inferred vs. established** in every summary that will be stored.
- Test memory with **summaries and decisions**, not only with direct questions.

These are the design rules of the planned *multilayer chronological memory* (see research statement);
the next experiment tests them directly (summary chains: the agent sees only its own previous summary).

---

## Repository

```
ladder_2x2/          dates vs order vs mass: prompt generator, Ollama runner, analysis, results, figure
staged_case/         the burglary case: runner (Ollama), web-chat prompts, all answers, coding, summary, figure
memory_error_types.md  error types seen in an AI-written profile built from chat memory (fictional examples)
```

### Reproduce (local models, free)

Requires Python 3 and [Ollama](https://ollama.com) with the models pulled (`ollama list`).

```
cd ladder_2x2
python make_prompts.py              # 180 prompts, fixed seed
python run_ollama.py --model qwen2.5:7b
python analyze_2x2.py               # tables, calibration, figure

cd ../staged_case
python run_case.py --model qwen2.5:7b      # 10 runs, one conversation per run
python summarize_case.py                   # table + figure for all models in the folder
```

Web models (Claude, Gemini, Qwen Max) were run by hand in temporary chats with the prompts in
`staged_case/prompts_for_web.txt` (default settings, thinking mode, 31 Oct – 1 Nov 2026); the answers are kept
verbatim in `staged_case/*_crime_web.txt`.

### How answers were scored

- Ladder: an answer is NEW / OLD / BOTH / ABSTAIN; mentions after "no longer", "not", "previously" etc.
  are ignored; if both values are named, the last present-tense statement decides. All 540 answers are
  in `ladder_2x2/answers_classified.csv`.
- Staged case: the date questions (R2) were coded by hand into three classes
  (`staged_case/R2_coding_by_claude.csv`, checked by the author); "later notes in the 14 March
  evidence" (R1) is a keyword count for local models and hand-coded for web models
  (`R1_manual.csv`), because web models name later notes explicitly as later.

---

## Limitations

- **Pilot scale.** Small open models (4–8B); 3–5 runs per frontier model; one case; 9 item variants
  per ladder cell (about 3 per position in the shuffled condition).
- **One fictional case.** The frontier summary error needs more cases with other "cyclists" before it
  can be called systematic.
- **The case itself suggests the link.** In stage 3 the lawyer says Daniel cannot ride a bicycle and the
  police answer that he can; this dispute only matters if the burglar rode away. The notes never state
  the link, and the direct question shows that Gemini knows it, but the summary may follow the frame of
  the people in the case. A variant without these two notes is the next control.
- **Web runs** depend on the product version and settings of the day.
- **Coder overlap.** The hand-coding was drafted by Claude (an Anthropic model, same family as one
  of the tested models) and checked by the author; the R2 answers are unambiguous, the cyclist
  phrases can be checked in `reading_*.csv`.

## Next

1. Summary chains with frontier models: does "the burglar fled on a bicycle" survive when only the
   summary is kept, and does it change the estimate?
2. The same case without the lawyer and police notes on the bicycle (does the link appear without
   the frame?); more cases and variants; probabilities instead of text answers on open models, to see
   whether a summary is the top hypothesis with its probability dropped.
3. A prototype of multilayer chronological memory against summary-only memory.

## Related

- Kwon, A. (2026). *Manufactured Confidence: How Memory Consolidation Turns Hearsay into Confident
  Facts.* arXiv:2606.29279 — memory tools drop hedges, and agents act on the confident phrasing. Here
  the inference is the model's own, and the question is when and from where it entered memory.
- Shvets, M. (2026). *Boundaries Agree, Labels Do Not: Intra-Annotator Dynamics as a Kind of Training
  Data.* arXiv:2610.04370 — the human "corridor" of revision that the memory design builds on.
  Code: [intra-annotator-dynamics](https://github.com/Malificenta883/intra-annotator-dynamics)

## Use of AI assistants

Claude (Anthropic) was used to write the analysis code and this text and to draft the hand-coding.
The research question, the case and the experimental design, the runs on local and web models, the
reading of the answers and the interpretation are the author's.

License: MIT.
