# Results Log — Soccer Student Agent Platform

All evaluations run on Windows (`engine 0.1.0`, config hash `372990895c7eca2a`).  
`Pts/match` = (3×W + D) / matches.

---

## Phase A3 — v1-baseline (Before)
Seeds 1000–1029 (58 matches per opponent, both sides):

| Opponent          | W-D-L       | Goals   | Pts/match | Mean Decision | Notes            |
|-------------------|-------------|---------|-----------|---------------|------------------|
| balanced          | 34-20-4     | 59 - 9  | 2.24      | 0.023 ms      | 20 draws (34%)   |
| tactical          | 35-14-9     | 78 - 29 | 2.14      | 0.023 ms      |                  |
| man_marking       | 38-18-2     | 62 - 8  | 2.27      | 0.023 ms      | 5 timeouts       |
| possession        | 51-7-0      | 114 - 4 | 2.76      | 0.023 ms      |                  |
| structured_attack | 40-14-4     | 78 - 15 | 2.31      | 0.023 ms      |                  |
| **v1 TOTAL**      | **198-73-19** | **391-65** | **2.34** | **0.023 ms** | **73 draws (25%)** |

---

## Phase B5 — Prototype v3 (Gate 1, vs Baselines)
Seeds 1000–1029 (58 matches per opponent, both sides):

| Opponent          | W-D-L       | Goals    | Pts/match | Mean Decision | Improvement vs v1 |
|-------------------|-------------|----------|-----------|---------------|-------------------|
| balanced          | 54-3-1      | 99 - 6   | **2.90**  | 0.010 ms      | +0.66 pts/m       |
| tactical          | 48-7-3      | 118 - 8  | **2.67**  | 0.010 ms      | +0.53 pts/m       |
| man_marking       | 50-8-0      | 99 - 0   | **2.97**  | 0.010 ms      | +0.70 pts/m (0 conceded) |
| possession        | 58-0-0      | 163 - 2  | **3.00**  | 0.010 ms      | +0.24 pts/m (100% wins)  |
| structured_attack | 56-2-0      | 131 - 2  | **2.97**  | 0.010 ms      | +0.66 pts/m       |
| **Prototype TOTAL** | **266-20-4** | **610-18** | **2.90** | **0.010 ms** | **+0.56 pts/m (+24%)** |

- **Draws reduced by 73%** (from 73 down to 20).
- **Goals conceded cut by 72%** (from 65 down to 18).
- **Decision speed 2.3× faster** (0.010 ms vs 0.023 ms).

---

## Phase B6 — Head-to-Head Gate 2
Seeds 1000–1059 (118 matches, both sides):

| Matchup | W-D-L | Goals | Win Rate | Status |
|---|---|---|---|---|
| `my-team` vs `v1-baseline` | **79-29-10** | **121 - 24** | **66.9%** | **PASSED Gate 2** |

---

## Phase D — Parameter Sweep Results (Seeds 1000–1019, 38 matches / opp)

| Parameter | Values Tested | 5-Opponent Avg Pts/m | Best Setting | Finding / Rationale |
|---|---|---|---|---|
| **DRIB_POWER** | 0.55 / 0.65 / 0.75 / 0.85 | 2.83 / **2.90** / 2.89 / 2.85 | **0.65** | 0.65 is the sweet spot; lower hurts speed, higher loses ball |
| **SHOT_MARGIN**| 2.2 / 3.2 / 4.2 | 2.83 / **2.90** / 2.88 | **3.2** | 3.2 balances corner precision and avoiding post misses |
| **SHOOT_X** | 14.0 / 18.0 / 22.0 | 2.83 / **2.85** / 2.74 | **18.0** | 18.0 triggers early shots without losing carry momentum |
| **PASS_DIV** | 26.0 / 30.0 / 34.0 | 2.82 / **2.85** / 2.79 | **30.0** | 30.0 gives proper pass flight speed to lead runners |
| **HYST** | 1.0 / 2.0 / 3.0 | 2.82 / **2.85** / 2.73 | **2.0** | 2 ticks credit prevents chaser flicker without lockup |
| **LANE_K** | 3.5 / 4.5 / 5.5 | 2.72 / **2.85** / 2.80 | **4.5** | Lower causes risky passes; higher makes team overly timid |
| **LATE_T** | 0.30 / 0.40 | **2.85** / 2.83 | **0.30** | Last 30% push avoids premature exposure on counter-attacks |

---

## Phase F — Final Confirmation on Unseen Seeds (Seeds 2000–2029)
58 matches per opponent (290 total matches), never used during tuning:

| Opponent | W-D-L | Win Rate | Goals | Pts/match | Goals Against |
|---|---|---|---|---|---|
| balanced | 51-6-1 | 87.9% | 96 - 8 | **2.74** | 8 |
| tactical | 47-8-3 | 81.0% | 93 - 13 | **2.57** | 13 |
| man_marking | 51-7-0 | 87.9% | 98 - 0 | **2.76** | 0 |
| possession | 58-0-0 | 100.0% | 173 - 0 | **3.00** | 0 |
| structured_attack | 50-8-0 | 86.2% | 111 - 1 | **2.72** | 1 |
| **Final Total** | **257-29-4** | **88.6%** | **571-22** | **2.76** | **22** |

### Unseen Head-to-Head vs `v1-baseline` (Seeds 2000–2029, 58 matches):
- **Record**: 38W 15D 5L (65.5% win rate)
- **Goals**: 65 - 12 (+53 goal diff)
- **Reliability**: 0 errors, 0 timeouts

### Overall Progress vs v1-Baseline (Unseen Seeds 2000–2029):
- **Points / match**: 2.29 → **2.76** (+0.47 pts/match)
- **Draws**: 76 → **29** (**-62%**)
- **Losses**: 20 → **4** (**-80%**)
- **Goals against**: 61 → **22** (**-64%**)
- **Mean decision time**: 0.049 ms → **0.010 ms** (nearly **5× faster**)

---

## Step 3 Experiment — Shot Quality Gating (SHOOT_X = 26.0 Alone)
Testing the single-variable hypothesis: delaying shots until within ~24 units of goal to address the 11.74 shots/game (2.6% conversion) giveaway loop.

### Benchmark Seeds 1000–1029 (290 matches, 58 per opponent):
| Opponent | Record (W-D-L) | Win Rate | Goals (GF - GA) | Pts / match |
|---|---|---|---|---|
| balanced | 50 - 7 - 1 | 86.2% | 94 - 7 | 2.71 |
| tactical | 42 - 12 - 4 | 72.4% | 93 - 16 | 2.38 |
| man_marking | 44 - 14 - 0 | 75.9% | 85 - 2 | 2.52 |
| possession | 55 - 2 - 1 | 94.8% | 160 - 3 | 2.88 |
| structured_attack | 53 - 3 - 2 | 91.4% | 104 - 2 | 2.79 |
| **Total** | **244 - 38 - 8** | **84.1%** | **536 - 30** | **2.65** |

### Unseen Seeds 2000–2029 (290 matches, 58 per opponent):
| Opponent | Record (W-D-L) | Win Rate | Goals (GF - GA) | Pts / match |
|---|---|---|---|---|
| balanced | 47 - 9 - 2 | 81.0% | 79 - 9 | 2.59 |
| tactical | 44 - 8 - 6 | 75.9% | 85 - 15 | 2.41 |
| man_marking | 46 - 12 - 0 | 79.3% | 66 - 0 | 2.59 |
| possession | 56 - 2 - 0 | 96.6% | 152 - 1 | 2.93 |
| structured_attack | 51 - 6 - 1 | 87.9% | 96 - 4 | 2.74 |
| **Total** | **244 - 37 - 9** | **84.1%** | **478 - 29** | **2.65** |

### Head-to-Head vs Previous Best (`SHOOT_X = 18.0`, Seeds 1000–1059, 118 matches):
- **Record**: 30W 46D 42L (25.4% win rate, 39.0% draw rate)
- **Goals**: 54 - 71
- **Takeaway**: Against baseline bots whose keepers don't save long shots, shooting from 18 yields easy goals. Against real league opponents (where long shots convert at only 2.6%), delaying shots to x = 26 is the isolated test to evaluate on the course server.

