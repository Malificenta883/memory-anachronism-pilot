"""One summary table and one figure for the staged case, all models in this folder.

Reads case_*.jsonl and R2_coding_by_claude.csv (edit the 'code' column there after checking by hand -
the summary follows your codes).

  likelihood  S1 -> S2 -> S3: "how likely was Daniel K. at the shop" after each stage (number from the answer)
  R1          runs where the list of evidence "on 14 March" contains notes written AFTER 14 March
              (same 7 patterns as ../analyze_PS.py)
  R2          A = correct (doubt marked as later), B = "not certain as of 10 March" because he LATER said so,
              C = doubt put on 10 March with no time marker
  R3          yes because of the bus driver (25 March -> prochronism) / yes because of the anonymous tip / no

Writes case_summary.csv and case_summary.png.   Run:  python summarize_case.py
"""
import csv, glob, json, re, statistics as st
from collections import Counter, defaultdict

LATE = {'B unsure 20.03': r'not certain|most similar|wasn.t certain|uncertain', 'bus driver 25.03': r'bus driver',
        'Ivo passing 27.03': r'passing', '2nd camera 02.04': r'second (CCTV|camera)|22:15|on a bicycle',
        'lawyer 05.04': r'lawyer|cannot ride|own a bicycle', 'neighbour 2025 09.04': r'2025|seen riding',
        'postponed 15.04': r'postpon'}


def bval(a):
    a = re.sub(r'\d{1,2}:\d{2}', '', a); a = re.sub(r'\d{1,2}(st|nd|rd|th)? (March|April)', '', a)
    a = re.sub(r'20\d\d', '', a); a = re.sub(r'(March|April) \d{1,2}', '', a)
    m = re.search(r'\b(\d{1,3})\b', a); return int(m.group(1)) if m else None


def r3(a):
    a = " ".join(a.split())
    if re.match(r'\W*yes', a, re.I):
        return 'yes: bus driver' if re.search(r'bus driver|22:05', a, re.I) else 'yes: tip only'
    return 'no' if re.match(r'\W*no', a, re.I) else 'unclear'


codes, r1man = {}, {}
try:
    with open('R1_manual.csv', encoding='utf-8-sig') as f:
        for r in csv.DictReader(l for l in f if not l.startswith('#')):
            r1man[(r['model'], int(r['run']))] = int(r['late_included'])
except FileNotFoundError:
    pass
CYCLIST = re.compile(r"(burglar|culprit|perpetrator|suspect|hooded (figure|individual|person)|someone)[^.]{0,60}"
                     r"(fled|flee|fleeing|escape)[^.]{0,30}bicycle|(fled|fleeing|escape)[^.]{0,20}on a bicycle", re.I)
try:
    with open('R2_coding_by_claude.csv', encoding='utf-8-sig') as f:
        lines = [l for l in f if not l.startswith('#')]
    for r in csv.DictReader(lines):
        codes[(r['model'], int(r['run']))] = r['code'].strip()
except FileNotFoundError:
    pass

data = defaultdict(dict)                     # model -> run -> step -> answer
for fn in sorted(glob.glob('case_*.jsonl')):
    tag = fn[5:-6]
    for line in open(fn, encoding='utf-8'):
        x = json.loads(line); data[tag].setdefault(x['run'], {})[x['step']] = x['answer']

rows, summary = [], []
for tag, runs in data.items():
    for run, s in sorted(runs.items()):
        b = [bval(" ".join(s.get(k, '').split())) for k in ('S1', 'S2', 'S3')]
        late = [k for k, rx in LATE.items() if re.search(rx, " ".join(s.get('R1', '').split()), re.I)]
        n_late = r1man.get((tag, run), len(late))
        if (tag, run) in r1man: late = ['manual coding']
        cyc = 1 if CYCLIST.search(" ".join(s.get('S3', '').split())) else 0
        rows.append(dict(model=tag, run=run, S1=b[0], S2=b[1], S3=b[2], R1_late=n_late, R1_which="; ".join(late),
                         S3_cyclist_is_burglar=cyc,
                         R2_code=codes.get((tag, run), '?'), R3=r3(s.get('R3', ''))))
    rs = [r for r in rows if r['model'] == tag]
    def mean(k):
        v = [r[k] for r in rs if isinstance(r[k], int)]; return round(st.mean(v)) if v else ''
    c2, c3 = Counter(r['R2_code'] for r in rs), Counter(r['R3'] for r in rs)
    summary.append(dict(model=tag, runs=len(rs), S1_mean=mean('S1'), S2_mean=mean('S2'), S3_mean=mean('S3'),
                        S1_to_S2_up=sum(1 for r in rs if isinstance(r['S1'], int) and isinstance(r['S2'], int) and r['S2'] > r['S1']),
                        S1_to_S2_down=sum(1 for r in rs if isinstance(r['S1'], int) and isinstance(r['S2'], int) and r['S2'] < r['S1']),
                        R1_runs_with_late=sum(r['R1_late'] > 0 for r in rs),
                        R2_A=c2['A'], R2_B=c2['B'], R2_C=c2['C'], R2_unchecked=c2['?'],
                        R3_yes_driver=c3['yes: bus driver'], R3_yes_tip=c3['yes: tip only'], R3_no=c3['no'],
                        S3_cyclist_is_burglar=sum(r['S3_cyclist_is_burglar'] for r in rs)))

with open('case_summary.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
with open('case_per_run.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for s in summary: print(s)

import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
models = [s['model'] for s in summary]
col = dict(zip(models, ['#7f3f98', '#1f4e79', '#c55a11', '#3a7d44', '#b8860b', '#008b8b', '#8b0000', '#555555']))
short = {m: m.replace('_web', ' (web)') for m in models}
fig, ax = plt.subplots(1, 4, figsize=(20, 4.8))
for tag in models:                                                     # 1. likelihood trajectories
    for r in [r for r in rows if r['model'] == tag]:
        y = [r['S1'], r['S2'], r['S3']]
        if all(isinstance(v, int) for v in y): ax[0].plot([1, 2, 3], y, color=col[tag], alpha=0.18, lw=1)
    s = next(x for x in summary if x['model'] == tag)
    ax[0].plot([1, 2, 3], [s['S1_mean'], s['S2_mean'], s['S3_mean']], color=col[tag], lw=3, marker='o', label=short[tag])
ax[0].set_xticks([1, 2, 3]); ax[0].set_xticklabels(['after stage 1\n(to 14 Mar)', 'after stage 2\n(B unsure, Ivo seen)', 'after stage 3\n(bicycle, court)'])
ax[0].set_ylim(0, 100); ax[0].set_ylabel('likelihood Daniel K. was at the shop'); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)
ax[0].set_title('Belief across stages (thin = runs, thick = mean)', fontsize=10)
bottom = [0] * len(models)                                             # 2. R2 codes
for code, c, lab in (('A', '#4caf50', 'A: correct, doubt marked later'), ('B', '#ffb74d', 'B: "later" said, still put on 10 Mar'),
                     ('C', '#e53935', 'C: doubt put on 10 Mar')):
    v = [next(x for x in summary if x['model'] == m)[f'R2_{code}'] for m in models]
    ax[1].bar([short[m] for m in models], v, bottom=bottom, color=c, label=lab); bottom = [b + x for b, x in zip(bottom, v)]
ax[1].set_title('R2: "As of 10 March, how certain was Witness B?"', fontsize=10); ax[1].set_ylabel('runs'); ax[1].set_ylim(0, 14.5); ax[1].set_yticks(range(0, 11, 2)); ax[1].legend(fontsize=7, loc='upper center')
import numpy as np                                                     # 3. R1 and R3
x = np.arange(len(models)); wdt = 0.27
for i, (k, lab, c) in enumerate((('R1_runs_with_late', 'R1: later notes in "evidence on 14 March"', '#90a4ae'),
                                  ('R3_yes_driver', 'R3: yes, citing bus driver (25 Mar)', '#e53935'),
                                  ('R3_yes_tip', 'R3: yes, citing only the tip', '#ffb74d'))):
    ax[2].bar(x + (i - 1) * wdt, [next(s for s in summary if s['model'] == m)[k] for m in models], wdt, color=c, label=lab)
ax[2].set_xticks(x); ax[2].set_xticklabels([short[m] for m in models]); ax[2].set_ylabel('runs'); ax[2].set_ylim(0, 10)
ax[2].legend(fontsize=7); ax[2].set_title('Information from later dates (R1, R3)', fontsize=10)
v = [next(s for s in summary if s['model'] == m)['S3_cyclist_is_burglar'] for m in models]
n = [next(s for s in summary if s['model'] == m)['runs'] for m in models]
ax[3].bar([short[m] for m in models], v, color='#6d4c41'); ax[3].set_ylim(0, 10)
for i, (a, b) in enumerate(zip(v, n)): ax[3].text(i, a + 0.2, f'{a}/{b}', ha='center', fontsize=8)
ax[3].set_title('Stage 3 summary: unidentified cyclist\nbecomes "the burglar fled on a bicycle"', fontsize=10)
for a in ax[1:]:
    for lbl in a.get_xticklabels(): lbl.set_rotation(25); lbl.set_ha('right')
fig.suptitle('Staged case: does the model keep "what was known when"?  (local models: 10 runs; web models: 3-5 runs)', fontsize=11)
fig.tight_layout(); fig.savefig('case_summary.png', dpi=180); print('figure -> case_summary.png')
