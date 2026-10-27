# Revised plan: secure at least a draw, keep the wins

Revision of `DEFENSE_FIRST_IMPLEMENTATION_PLAN.md`. Your league data (#182 of 272, 496 points from 1048 matches, 132W 100D 816L, 0.30 scored and 3.19 conceded per match) is the best information we have had so far. It changes the plan in three ways: it exposes a step zero that the original plan skipped, it shows that two of the plan's defensive components fail when tested, and it shows that scoring matters as much as defending.

Sandbox results below come from the Linux engine in your zip, which differs from your Windows engine in API details. Treat every sandbox number as direction, not as a promise.

---

## 1. Summary of changes

| Original plan item | Verdict | Reason |
|---|---|---|
| Diagnosis from league stats | **Keep, with corrections** (§3) | Core numbers are right; two causal claims are unsupported |
| A. Keeper angle-cutting | **Remove** | Tested worse: goals against 0.34 vs 0.26 per match |
| A. Sweeper-keeper rush | **Keep as an A/B candidate** | 0.20 vs 0.26, but only about 1.2 standard errors |
| B. All four players drop to x = −42 | **Remove** | This is "park the bus", tested worse, including against a stronger team |
| B. Third goalside marker | **Remove** | Tested worse: 0.35 vs 0.26 |
| C. Shot gating | **Keep, as the top-priority league experiment** | League conversion is 2.6% vs 32% league-wide; thresholds changed (§5) |
| D. Preserve counter-attack | **Keep** | Already how the code works |
| Four gates | **Rebuilt** (§6) | Reference bots cannot see your problem; the head-to-head gate was too noisy |
| Expected outcomes table | **Replaced** (§7) | The numbers had no basis |
| Phase order | **Reordered** (§4) | Confirm what is live first |

---

## 2. Step zero: find out which version produced these statistics

The plan assumes the 1,048 matches were played by the prototype (`SHOOT_X = 18.0`). The data does not settle that:

- **Decision time 0.055 ms** matches your original v1 (0.049–0.056 ms in my sandbox) far better than the prototype (0.012–0.020 ms in my sandbox, 0.020 ms on your machine). It is possible the course server is about 2.7× slower than your PC, which would make 0.055 ms the prototype, but that is a guess.
- **Passes completed 6.14 per match** sits closer to the prototype (about 5.7 against reference bots) than to v1 (about 3).

This matters because the two versions defend very differently. Against my proxy attacker (§8), your **original v1 concedes 1.03 goals per match; the prototype concedes 0.13.** Against the prototype itself, v1 conceded 61 goals in 60 matches. If v1 is what is live, the cheapest improvement available is to submit the prototype, and the plan below would be tested on top of that.

**How to check (any one is enough):**
1. Read the version label on your submission page, or the one in the leaderboard row, and compare it with `version` in your `team.toml` and the class `version` attribute.
2. Check the submission date in the portal against when you installed the prototype.
3. Weak hint only: v1 completes about 3 passes per match against the reference bots and the prototype about 6, and your league figure is 6.14. Other teams differ from the bots, so do not rely on this.

If you cannot tell, resubmit `team_v4_speed.py` and see whether decision time drops sharply. That alone answers the question.

---

## 3. What the league data does and does not show

| Claim in the original plan | Check |
|---|---|
| 11.74 shots, 0.30 goals, 2.5% conversion | **Correct.** 0.30 ÷ 11.74 = 2.6% |
| Shots are the main cause of lost possession and 1.8% control | **Partly.** "Ball control" is a share of ticks you actually hold the ball, and dribbles are 5.3 per match against a league mean of 52.7. You seldom carry the ball at all, regardless of shots |
| "97.5% of long shots are scooped up by keepers" | **Unsupported.** Your blocked-shot count is average (2.10 vs 2.08). The split between saved, wide and blocked is unknown |
| Only players 1 and 2 mark; players 3 and 4 are "stranded" | **Overstated.** Players 3 and 4 screen about 10 units behind the ball, within x = −32 to 0. They are not goalside of runners, which is a fair concern, but it is untested |
| Keeper is passive | **True of the code**, but the fix proposed (angle-cutting) tested worse |
| "+408 points if half the losses become draws" | **Arithmetic is right (904)**, but it assumes half of 816 losses are fixable. Against the top teams you lose by 8–9 goals |

### The one number that should drive the plan
League-wide, teams score 1.50 goals from 4.67 shots, a **32% conversion**. You score 0.30 from 11.74, a **2.6% conversion**. Other teams shoot rarely and from good positions; you shoot constantly from range. In my sandbox the same shots convert at 13% against the reference bots, so the reference keepers are far easier than your classmates'.

### Scoring is worth as much as defending
In a simple scoring model (Poisson goals, which understates your real points because it ignores that some opponents are weak):

| Scenario (goals for / against per match) | Win | Draw | Loss | Points/match |
|---|---|---|---|---|
| Today (0.30 / 3.19) | 0.02 | 0.07 | 0.92 | 0.12 |
| Cut conceded to 1.20, scoring unchanged (0.30 / 1.20) | 0.09 | 0.31 | 0.60 | 0.59 |
| Cut conceded to 0.60 (0.30 / 0.60) | 0.15 | 0.48 | 0.36 | 0.95 |
| Conceded 1.20 and scoring 0.80 (0.80 / 1.20) | 0.25 | 0.30 | 0.45 | 1.04 |
| League-average team (1.50 / 1.38) | 0.40 | 0.25 | 0.35 | 1.46 |

At your current scoring rate, **an extra 0.5 goals scored per match is worth about the same as 2 fewer conceded.** Drawing needs you to score as well, unless you shut the match out completely. So "defence first, ignore scoring" is not the best route to draws.

---

## 4. Revised execution order

Each step is one league submission, so the effect can be read from the league statistics. Do not bundle changes.

**Step 0.** Establish which version is live (§2).

**Step 1. If v1 is live, submit `team_v4_speed.py` now.** It is the best-supported change and needs no new code. Read the new league statistics after the run (§6.2).

**Step 2. Pull diagnostics on real losses.** For six pairings, two near the top of the "worst result" list, two mid-table and two near the bottom, open the pairing statistics (`stats ▸`) and record: your shots and their shots, ball control for each side, territory, and goals. Ask: do they concede from long range or from a carry into your area? Are they holding the ball (control above 25%) or hitting quickly? If the match viewer can open a replay for any pairing, watch two losses and write down where each goal came from. **This tells us which defensive change is worth making; the sandbox cannot.**

**Step 3. First behaviour experiment: shot quality.** Change only `SHOOT_X` from 18 to **26** (shoot from within about 24 units of goal). Everything else stays identical. Judge it on league conversion (goals per shot), goals per match, and goals conceded per match, not on points alone.

**Step 4. Second experiment: carry rather than boot.** If Step 3 raises conversion but your ball control stays near 2%, change `DRIB_POWER` from 0.65 to **0.35**. It keeps the ball nearer your feet. The sandbox showed harder carries (0.55 and above) beat soft ones against the reference bots, so this is a real trade-off that only the league can settle.

**Step 5. Third experiment: sweeper keeper.** Add the sweeper rush only (§5), unchanged otherwise.

**Step 6. Defensive shape.** Only after Step 2's diagnosis suggests a specific fix. Use the diagnosis, not the original plan's shapes.

---

## 5. Component specifications (what to build, if anything)

### Shot gating (Step 3)
In `_carry`, the shot branch is `if px > self.shoot_x:`. Set `SHOOT_X = 26.0` at the top of `team.py`. Nothing else changes: the late push (`LATE_X`) stays, and shots still aim at the better corner. Do **not** add a lane condition: in the sandbox, lane gates between −4 and −0.5 made no difference and a stricter one reduced points.

Expected sandbox cost: against the reference bots, shooting only from further in scored about 0.05–0.1 points per match lower (2.43 vs 2.48 for `SHOOT_X` 26 vs 18 in an early sweep, 2.60 vs 2.71 in a later one). That is the cost of testing it, and it is why this change needs the league to judge it.

### Sweeper keeper (Step 5)
In the keeper block, add: if the ball is in `bx < -32` and `|by| < 16`, its speed squared is under 30, and no outfield player is closer to the ball than the keeper, move toward the ball instead of holding the line. The existing clear (strike at power 1.0 towards the touchline when within 3.4 units and able to kick) stays.

### Components removed, with evidence
Defensive variants vs four attackers (my proxy attacker, the prototype itself, `tactical`, `balanced`; 240 matches each):

| Variant | Goals against / match | Points / match |
|---|---|---|
| Current prototype | 0.26 (62 goals) | 2.34 |
| Keeper angle-cutting and advance (up to 4.5 off line) | 0.34 (82) | 2.38 |
| **Sweeper rush** | **0.20 (49)** | 2.40 |
| Third goalside marker, fourth player 6 units behind ball | 0.35 (83) | 2.33 |
| All three together | 0.34 (82) | 2.32 |

Separately, a full "park the bus" line (all four outfield players holding x = −34 or −40 while defending) scored 2.30 and 1.96 points per match against the reference bots against 2.71 normally. Head-to-head against the prototype it scored 0.99 and 0.88 against 1.23 for an identical copy, and it conceded more (82 and 92 goals vs 67). The original plan's "all four drop to x = −42" is this same idea, so it is removed.

---

## 6. Verification, rebuilt

### 6.1 Sandbox checks before any submission
1. `START.cmd validate my-team`: `PASSED`, 0 exceptions, 0 missing actions, 0 non-finite values, mean decision under 0.03 ms.
2. `START.cmd check`: `PASSED`.
3. **Regression against reference bots** (`balanced`, `tactical`, `man_marking`, `possession`, `structured_attack`, seeds 1000..1029): points per match must stay within 0.15 of the previous best. This is the guard for your existing wins, not a measure of progress; reference bots concede about 0.07 goals per match and cannot show a defensive leak.
4. **Proxy attacker test** (§8): goals conceded per match must not rise by more than 25% over 240 matches. Use the aggregate, not single matches.
5. **Pure refactors only:** compare the full result record on fixed seeds before and after. It must be identical.

Dropped from the original gates:
- "Head-to-head win rate ≥ 50% over 120 matches." An identical team went 18W 22D 20L against itself over 60 matches, so this fails for no reason about half the time.
- "Goals conceded against tactical or balanced must not increase." They are about 0.07–0.2 per match; a change of one goal is noise.

### 6.2 League readout after each submission
Compare these before and after, averaged over the whole run, and write them down:

| Measure | Before (from your page) |
|---|---|
| Goals scored / conceded per match | 0.30 / 3.19 |
| Shots and conversion (goals ÷ shots) | 11.74 / 2.6% |
| Ball control share and dribbles | 1.8% / 5.30 |
| Draws and wins | 100 draws, 132 wins |
| Decision time | 0.055 ms |

Judge a change by whether goals per match and conceded per match move in the right direction. Per-pairing results are only four matches each, so use them for diagnosis, not for deciding.

**Rule for keeping a change:** keep it if goals conceded per match fall without goals scored falling by more than about 0.1, or if goals scored rise without conceded rising by more than about 0.3. Revert anything else.

---

## 7. What to expect

The original table (goals against below 1.20, conversion above 12%, 250–350 draws, divisions 5–7) is replaced because nothing supported it. What the evidence does support:

- A **real step-change is only likely if the live version is v1.** In that case the prototype should reduce conceding and increase scoring sharply, but I cannot put a number on it from sandbox data. Do not plan around a division.
- If the prototype is already live, the remaining gains come from **shot quality** (the largest gap in your league data) and then from diagnosed defensive fixes. Expect small, incremental movement per submission, not +400 points in one step.
- Against the very best teams, which beat you by 8–9 goals, a draw is not realistic soon. Points are available in the middle of the table, against teams that score 1–2 goals per match.
- Keep fouls at zero and decision time low. Both are already in your favour, and neither should be traded for anything above.

---

## 8. Files

- `REVISED_DEFENSE_FIRST_PLAN.md`: this plan.
- `proxy_dribbler.py`: a test opponent that carries the ball with soft touches and shoots from close, away from the keeper. It is **weaker than your best classmates**: it loses to `tactical` in my sandbox, and my prototype beats it 53–5–2. Use it as one extra opponent to catch regressions, not as a model of the top of the league. To use it: `START.cmd new proxy-dribbler`, paste the file over `proxy-dribbler/team.py`, then `START.cmd tournament my-team --against proxy-dribbler --seeds 1000..1029`.
- `team_v4_speed.py` (from earlier): the prototype with the speed pass, for Step 1.
