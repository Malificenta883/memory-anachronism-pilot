# Memory error types: a profile written from chat memory

A chat assistant with long-term memory was asked to write a CV of its user from what it remembered.
A document assembled from AI memory cannot be checked: it does not show where each claim came from
or which moment it describes. The error types below were seen in that document; the examples here are
**fictional** ("Lena", a historian now studying computational social science) and only reproduce the
*form* of each error. They serve as templates for test items.

| error type | fictional example | concept |
|---|---|---|
| **The outdated state holds** | Lena's previous surname is used, although she now publishes under a new one | parachronism; *mass* — the old name appeared many times |
| **Periods glued together** | a preparatory year at one university and a BA at another become one entry | loss of chronology: two times and places as one |
| **Hallucination about a real document** | a wrong title for her paper and a "result" the paper does not contain | information without origin |
| **Inflation by a coherent story** | "data scientist", "engineered", "deep learning", "strong quantitative background" | the story fills in elements that were never stated |
| **New information without its time and status** | she *started learning* PyTorch this month → "developed classification models" | the new wins, but loses its date and status: a process becomes a result |
| **A trivial detail with mass** | a passing remark about an old side project becomes an "achievement" | mass without relevance; no filter for what matters in this document |
| **Own concept → fashionable term** | her own method is renamed with a generic buzzword | appropriation and simplification |
| **Correct** | the degree is given correctly | not everything is false, which makes the false harder to see |

## Observation about dates

The newest information (what she began learning this month) did enter the profile, so "the new" did
not lose. But it entered **without its time**: an early stage of learning became a finished skill.
This is a separate kind of anachronism — **erasing the time stamp**: "is learning" (a process) turns
into "can do" (a result). For a historian it is a classic error: a state at one date presented as a
permanent property.

**For test items:** add pairs where the new entry carries a process status ("started learning X",
"is preparing for…", "applied for…") and ask about the skill or the result.

## A live example: "day off" → "Saturday"

On a Tuesday during a university break, a user wrote "a day off, morning". The assistant replied
"A perfect Saturday morning…" and added "at 9 a.m.".

- **Schema instead of calendar:** "day off" was read by a learned schema as Saturday; the real date lost.
- The same mechanism as order restored from meaning instead of dates.
- An invented detail ("9 a.m.") to make the scene coherent.
- In an investigation, "at the weekend" in a witness statement can easily become "on Saturday" — a
  wrong date that nobody said.
