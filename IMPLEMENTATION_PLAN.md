# Climbing the divisions: implementation plan

Project: `soccer-student-0.1.0` (student soccer agent platform, 5-a-side, 2400 ticks at 20 Hz)
Goal: more points per match first, lower mean decision time second.

---

## 0. Summary

- **Division is decided by points alone.** Decision time only orders teams *inside* a division (guide §10). So the plan is: win more matches first, then make each decision cheaper. Speed cannot rescue a division, but once points are equal it decides your rank.
- **Your current team's problem is draws, not losses.** On 300 matches against the five main reference opponents it drew **76 (25%)** and lost 20. Every draw turned into a win is +2 points.
- **The cause is too few, too slow attacks.** In the matches I inspected: 71–96% possession, but only 4–5 shots per match and a territory share of 33–42% against the opponent's 57–66%. Shots were taken only inside 32 units, and the carry between was a 0.42-power nudge.
- **A tested replacement is included** (`team_prototype.py`). On identical unseen seeds it takes 5 baselines from **2.29 to 2.71 points/match**, draws from **76 to 34**, goals against from 61 to 25, and mean decision time from **0.049 ms to about 0.024 ms**. Head-to-head against your current team: 36W 21D 3L.
- **Caveat that matters:** I measured on the Linux engine in the zip, which differs from the Windows engine you run (see §8). Every gate below must be re-run on your machine before you trust a number.

---

## 1. What I examined

Cloned your repo (the GitHub page itself blocks automated fetching) and read: `README.md`, `docs/student-guide.md` (all 1031 lines), `configs/default.toml`, every file in `student-sdk/soccer/`, `tools/evaluator/` (the marker's checks), `launch.py`, `bootstrap.py`, `my-team/team.py` and `team.toml`. The compiled engine is a binary, so its internals were inferred from behaviour and from the config. I then ran the engine to measure rather than guess.

Key facts that shape the strategy:

| Fact | Source | Consequence |
|---|---|---|
| Match = 120 s (2400 ticks). Goal mouth 14 wide, pitch 100×60, 5 players, no offside | config | Few possessions per match; shot volume matters |
| 3 pts win, 1 draw, then goal difference; **divisions of 20 cut on points only** | guide §10 | Convert draws into wins |
| Inside a division, ranked on **mean decision time, lower is better** | guide §10 | Speed is the tiebreak, worth doing after football is solid |
| Decision timer wraps only `act()` (via `perf_counter`) | `runner.py::_decide` | Engine-side cost is free; only your Python counts |
| 20 ms limit per decision, 20 consecutive failures forfeits | config | You are at about 0.1% of the limit; no risk, only ranking |
| Kickoff-circle intrusion is the only foul (player teleported, ~4 s lost) | guide §2 | Hold shape during opponent kickoffs |
| One `.py` file only; `team.toml` must hold your real name and student number | README, `evaluator` | See Step A1, **your repo still has the example values** |

---

## 2. Diagnosis of the current implementation (measured)

Your `my-team/team.py` on 300 matches (5 opponents × 30 seeds × both sides, seeds 2000–2029):

| Opponent | W–D–L | Goals | Pts/match |
|---|---|---|---|
| balanced | 35–19–6 | 56–12 | 2.07 |
| tactical | 39–13–8 | 85–29 | 2.17 |
| man_marking | 35–21–4 | 57–12 | 2.10 |
| possession | 54–6–0 | 113–0 | 2.80 |
| structured_attack | 41–17–2 | 72–8 | 2.33 |
| **Total** | **204–76–20** | **383–61** | **2.29** |

Mean decision time **0.049 ms**.

Why it draws:

1. **Shooting is late.** `_handle_kick` shoots only at `dist_to_goal < 32` and otherwise passes or nudges at power 0.42. Typical stats against `balanced`: 4–5 shots per match, territory 33–42%.
2. **Passing is weak.** 2–5 completed passes per match against `balanced`/`tactical`; lane test is binary and ignores that defenders move while the ball travels.
3. **Wasted compute.** `predict_ball` loops 20 ticks every tick; `direction()`, `distance()`, `closest_point_on_segment()` and `TeamAction`/`PlayerAction` objects are slow wrappers (§6).
4. **Fragile API use.** `obs.field.simulation_hz` and `obs.field.ball_friction` are read every tick. On the Linux engine in your zip these attributes do not exist, so the team **raises on every tick and forfeits** (the marker's own `check` reports it). On your Windows engine they exist, which is why it works for you.

---

## 3. The strategy

Seven decisions. Each was either measured or follows from a measured cost.

**3.1 Shoot early, at a corner, every time past x = 18.** Gating shots on "is the lane open?" made things *worse* (2.20 vs 2.48 pts/match) because it suppressed shots; lane-gate thresholds from −4 to −0.5 were all within noise of "always shoot". So: past x = 18, strike at power 1.0 at whichever of three aim points (left corner, right corner, centre) has the most room. This is also the cheapest option to compute.

**3.2 Aim well inside the posts.** Target y = ±(goal half-width − 3.2) = ±3.8. Margins 0.8 / 1.4 / 2.2 / 3.2 / 4.2 gave 2.51 / 2.48 / 2.62 / 2.71 / 2.72. Hugging the post loses shots to small errors and the keeper's reach.

**3.3 Drive the ball hard.** Carry at kick power 0.65 while running at goal. Power 0.30 / 0.40 / 0.55 gave 2.38 / 2.48 / 2.71. The old 0.42 nudge was slow enough to be tackled and kept the ball in your half.

**3.4 Pass forward only when it is clearly open, and lead the receiver.** Passing on vs off: 2.48 vs 2.36. A pass is accepted only if the receiver is ≥3 units further forward, the pass is 5–42 units, the lane has positive *room* (opponents are assumed to close on the lane at 4.5 u/s while the ball is in flight), and no opponent is within 3.5 of the aim point. Power = distance / 30; aim point = receiver position + 0.6 × receiver velocity × flight time.

**3.5 One chaser, chosen by arrival time, with hysteresis.** Roll the ball forward with a closed-form table (`S[n]`) instead of a loop, find the earliest tick each of the two nearest outfield players can reach it, and give the incumbent 2 ticks of credit so the chaser does not flip-flop.

**3.6 Hold shape at opponent kickoffs.** If the ball is on the centre spot and not ours, outfield players stay outside the 9-unit circle plus margin. Fouls per match: 0.0.

**3.7 Late push when tied or behind.** In the last 30% of the match, shoot from x = 8 and send everyone forward. Small but consistent: points 2.52 → 2.58/2.59, draws 42 → 35/32 (180 matches). Keep only if goals-against does not rise on your machine.

**What I tested and rejected:** lane-gated shooting (worse), a two-step "fixed-point" intercept (cheaper but weaker head-to-head than the scan), and shoot thresholds of 10 or 26 instead of 18 (no better).

---

## 4. Evidence

All numbers are points per match, 3/1/0, on the Linux engine. Sweeps 1–3 used 120 matches (4 opponents × 15 seeds × 2 sides), so the noise is about **±0.07**; differences smaller than 0.1 are not real. Sweeps used slightly different baselines, so read each row as "direction and size", not as a leaderboard.

| Sweep | Setting → points/match |
|---|---|
| Shot gating | lane-gated 2.20 · always shoot past x=18 **2.48** · x=10 2.42 · x=26 2.43 |
| Passing | off 2.36 · on **2.48** |
| Carry power | 0.30 → 2.38 · 0.40 → 2.48 · 0.55 → **2.71** |
| Corner margin | 0.8 → 2.51 · 1.4 → 2.48 · 2.2 → 2.62 · 3.2 → **2.71** · 4.2 → 2.72 |
| Lane-gate threshold (180 matches) | −99 → 2.52 · −4 → 2.42 · −2 → 2.54 · −0.5 → 2.48 (no effect) |
| Late push (180 matches) | off 2.52 · last 25% 2.58 · last 40% **2.59** |

**Final team versus your current team, same 300 matches** (seeds 2000–2029, never used for tuning):

| | W–D–L | Goals | Pts/match | Mean decision |
|---|---|---|---|---|
| Your current team | 204–76–20 | 383–61 | 2.29 | 0.049 ms |
| Prototype | 260–34–6 | 567–25 | **2.71** | **0.024 ms** (0.017 ms in `validate`) |
| Head-to-head, prototype vs yours (60 matches) | 36–21–3 | 61–12 | | |

Prototype per opponent: balanced 49–10–1, tactical 48–8–4, man_marking 48–11–1, possession 58–2–0, structured_attack 57–3–0.

**A warning from the data:** an earlier, cheaper variant of the intercept code beat all baselines but went 17W–18D–25L against a heavier variant of itself. Beating baselines does not prove you beat a good classmate's team. That is why the plan gates every change on head-to-head against your previous best (Phase D).

---

## 5. Execution steps

Commands are written for Windows (`START.cmd`). On macOS/Linux replace `START.cmd` with `./start.sh`; arguments are identical. Run everything from the repo root.

### Phase A: prepare (about 10 minutes)

**A1. Fix `my-team/team.toml`.** It still contains `Your Name` / `2412345`. The marker's `check` warns about this, and the README says a submission without your details is not marked. Put your registered name and student number in the `[[members]]` block, and set a real team `name`.

**A2. Snapshot your current team as the opponent to beat.**
```
xcopy my-team v1-baseline /E /I          (Windows)
cp -r my-team v1-baseline                (macOS / Linux)
```
Edit `v1-baseline/team.toml` and give it a valid name such as `V1 Baseline`. This folder is your regression opponent for the rest of the plan.

**A3. Record baseline numbers for your current team.**
```
START.cmd doctor
START.cmd validate my-team
```
Write down the **mean decision (ms)**. Then, in PowerShell:
```
foreach ($o in "balanced","tactical","man_marking","possession","structured_attack") {
  START.cmd tournament my-team --against $o --seeds 1000..1029 }
```
(bash: `for o in balanced tactical man_marking possession structured_attack; do ./start.sh tournament my-team --against $o --seeds 1000..1029; done`)

Points per match = (3×W + D) / matches. Enter them in the log (Appendix B). This is your "before".

### Phase B: install the prototype and verify it on your machine

**B1.** Copy `team_prototype.py` over `my-team/team.py`.

**B2. Legality gate.**
```
START.cmd validate my-team
```
Required: `PASSED`, `exceptions 0`, `missing player actions 0`, `non-finite values 0`, `over deadline 0`, no moved-formation-spot warning. Mean decision should be roughly 0.02–0.03 ms.

**B3. Verify plain-dict actions on your engine.** The prototype returns `{player_id: {"movement":…, "kick_direction":…, "kick_power":…}}` instead of `TeamAction`/`PlayerAction` objects. The SDK documents this form, and it gave **identical** match results on the Linux engine, but it is the one thing I could not test on Windows.
```
START.cmd play my-team --against balanced --seed 2001
```
Note the score and the `decision mean`. Then set `USE_DICT = False` at the top of `team.py`, rerun the same command. The scores must be **identical**. If the dict version errors or differs, leave `USE_DICT = False` (it costs about 14 µs more per decision, measured 0.031 vs 0.017 ms). Otherwise set it back to `True`.

**B4.** `START.cmd check` must report `PASSED` for `my-team`.

**B5. Gate 1, versus baselines.** Repeat the A3 loop. Expected from my measurements: about 2.5–2.9 points/match on each, with draws under about 15% of matches. If any opponent is worse than your "before" number by more than 0.15, stop and investigate before continuing (most likely cause: the Windows engine behaves differently from the Linux one).

**B6. Gate 2, head-to-head.**
```
START.cmd tournament my-team --against v1-baseline --seeds 1000..1029
```
Expected: wins clearly exceed losses (I measured 36W 21D 3L). If not, do not proceed.

**B7.** Save this state (git commit, or copy the folder to `best-so-far`). Every later step is compared against it.

### Phase C: watch it (about 30 minutes)

Dashboard: `START.cmd`, pick `my-team` vs `balanced`, **Record and watch**. Click players to see `asked` vs `doing`. Confirm:

1. Exactly one outfield player chases the ball and the choice does not flicker every few ticks.
2. The carrier shoots as soon as it crosses about x = 18, aiming near but not at the corners.
3. At opponent kickoffs your outfield players stay outside the circle (fouls = 0 in the `play` summary).
4. The keeper tracks the ball's y and clears when it arrives.

Then check the numbers that explain goals: `play` should show shots well above your old 4–5 per match (about 14–16 against `balanced`/`tactical` in my runs).

### Phase D: tuning loop (repeat as needed)

Rules that keep you honest:

- **One change per experiment.** Copy the current best to `best-so-far`, change one constant in `my-team`.
- **Tune on seeds 1000–1059; confirm on 2000–2029 only once per accepted batch.** Never tune on the confirm seeds. The public practice seeds 1001–1005 are for debugging only.
- **Accept a change only if both hold:** the 5-baseline average improves by ≥ 0.05 points/match over at least 100 matches, *and* head-to-head against `best-so-far` is not negative (`START.cmd tournament my-team --against best-so-far --seeds 1000..1029`).
- **Calibrate head-to-head noise.** When I played the prototype against an identical copy of itself over 60 matches it went 18W 22D 20L. So a head-to-head margin of a few wins in 60 matches means nothing; use at least 200 matches (`--seeds 1000..1099`) before trusting a head-to-head difference, and use it as a veto against clear regressions rather than as proof of improvement.
- Matches are deterministic, so a rerun with the same seeds repeats exactly. Noise comes from seed choice, which is why the seed count matters more than rerunning.

Constants in order of measured sensitivity (all at the top of `team.py`):

| Constant | Now | Try | What it does |
|---|---|---|---|
| `DRIB_POWER` | 0.65 | 0.55–0.85 | carry speed; biggest single lever |
| `SHOT_MARGIN` | 3.2 | 2.2–4.2 | distance inside the post |
| `SHOOT_X` | 18 | 14–22 | where shooting starts |
| `LATE_T` / `LATE_X` | 0.30 / 8 | 0.25–0.40 / 6–12 | late push window and shot range |
| `PASS_DIV` | 30 | 26–34 | pass power = distance / this |
| `LANE_K` | 4.5 | 3–6 | how fast defenders are assumed to close a lane |
| `HYST` | 2.0 | 1–4 | chaser stickiness |

After the constants stop paying, the next gains are structural. These are **untested ideas**, ordered by my expectation:

1. **Exploit your own kickoff and post-concession restarts.** The guide says the side taking a kickoff cannot be challenged, so a deliberate first pass to a pre-positioned forward is free.
2. ~~**Aim shots away from the keeper.**~~ **Tested, rejected.** Adding a bonus for the corner farther from the opponent keeper (weights 0.3 and 1.0) left the 4-baseline average at 2.65 and 2.60 against 2.71 without it; head-to-head was within noise.
3. **Sticky marking.** Assign each marker an opponent and keep it for a few seconds instead of re-picking every tick.
4. ~~**A second presser** near the ball when defending in your own half.~~ **Tested, rejected.** 4-baseline average 2.63 vs 2.71, head-to-head 20W 24D 16L (noise).
5. **Keeper sweeping** for through balls (risky; test head-to-head carefully).

### Phase E: speed pass (after the football is frozen for a milestone)

Because matches are deterministic, **a pure speed optimisation must give identical scores on fixed seeds.** Use that as your regression test: record the scores on 3 seeds before, optimise, and the scores must match exactly. If they do not, you changed behaviour, not speed.

**E1. Remove all `actions.annotate(...)` calls** (the prototype has none). Building the debug payload costs time inside `act()` even though grading ignores it.

**E2. Profile.**
```python
# profile.py, run from the repo root with:  python profile.py
import sys, cProfile, pstats, io
sys.path.insert(0, "."); import bootstrap; bootstrap.ensure_engine(); sys.path.insert(0, "student-sdk")
import soccer
team = soccer.load_controller("my-team/team.py")
pr = cProfile.Profile(); pr.enable()
soccer.play_match(team, "balanced", seed=1003); soccer.play_match(team, "tactical", seed=1004)
pr.disable(); s = io.StringIO(); pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(14); print(s.getvalue())
```
Look at `act` tottime and the `math.hypot` call count. My first prototype made about 34 `hypot` calls per tick (a 7-point intercept scan for all four outfield players), and that was its hot spot; restricting the scan to the two likeliest players removed most of it.

**E3. Apply the speed playbook (§6), highest saving first.** Re-run the regression seeds after each step.

**E4.** Measure with `START.cmd validate my-team` (mean decision ms) and record it.

### Phase F: submit

1. `team.toml` has your real name and student number, version bumped.
2. The folder contains only `team.py` and `team.toml` (an optional `README.md`/`data/` is allowed; no second `.py`; `__pycache__` is ignored).
3. `START.cmd check` → `PASSED`.
4. Final run on **unseen** seeds: `START.cmd tournament my-team --against balanced --seeds 2000..2029` and head-to-head against `best-so-far`.
5. Hand in, renamed per guide §9 (`<studentnumber>-<name>`).

---

## 6. Speed playbook (measured costs)

Micro-benchmarks on live observation objects (µs per call, sandbox hardware):

| Operation | Cost | Take-away |
|---|---|---|
| `obs.ball`, `obs.my_players`, `p.position`, `p.velocity` | 0.10–0.22 | engine reads are cheap; read once per tick into locals |
| `obs.can_kick(id)`, `obs.closest_*_to(pt)` | 0.16–0.25 | fine to call |
| `math.hypot(dx, dy)` | 0.14 | use this |
| `soccer.distance(a, b)` | 0.70 | 5× slower than hypot |
| `soccer.direction(a, b)` | 1.37 | ~10× hypot; inline `dx/d, dy/d` |
| `soccer.closest_point_on_segment` | 1.40 | write the 6-line projection inline |
| `soccer.closest_to_ball(obs)` | 1.49 | compare squared distances yourself |
| `TeamAction()` + 5 `PlayerAction` | 6.2–6.7 | **biggest single saving**: return plain dicts |
| trivial bot, objects vs dict | 0.010 vs 0.004 ms | confirmed end to end |

Ranked actions:

1. Return a plain dict of dicts (saves about 6–14 µs). Verify as in Step B3.
2. Replace per-tick loops with closed-form physics. Ball displacement after n ticks is `v · dt · (1 − fⁿ)/(1 − f)`; precompute the `(1 − fⁿ)/(1 − f)` table once in `_setup`.
3. Read the observation once into plain floats and tuples; never touch `obs` inside inner loops.
4. Use `hypot` and inline vector arithmetic instead of SDK helpers.
5. Do work lazily and only for who needs it. The prototype runs the full intercept scan for only the two players nearest the ball's predicted position, and computes the opponent sort once per tick and only when defending.
6. No `print`, logging, imports or allocation of large temporaries inside `act`.

What not to do: do not trade football for speed. A 0.01 ms saving is invisible if it costs a draw, because points decide the division first. Also do not cache every attribute individually; the reads are cheap, the wrappers are not.

---

## 7. Realistic expectations

- On the baselines the prototype wins about 87% of matches (260 of 300), up from 68%, and draws only 11%.
- Your division competitors are classmates, not baselines, and some will play well. I cannot test against them, so I cannot promise a number of divisions climbed. What the evidence supports is that the main thing holding you at 8th, a 25% draw rate, should shrink substantially, and that you will rank near the top of whichever division your points place you in thanks to decision time.
- The ceiling against a strong opponent is lower than against baselines. Phase D head-to-head gating exists for exactly this reason.

---

## 8. Risks and caveats

1. **Different engine builds.** The Linux engine in your zip lacks `field.simulation_hz`, `field.ball_friction` and others that the guide documents, and has native helpers (`predict_ball_position`, `is_pass_lane_clear`, …) the Windows engine does not. The Windows engine matches the guide. The physics config is shared (hash `372990895c7eca2a`), so my results are directionally valid, but **re-measure on Windows** (Steps B2–B6). The prototype reads `obs.simulation_hz()` (present on both) and `getattr(field, "ball_friction", 0.985)` so it runs on either. If the marking server uses the Linux build, your current team would forfeit every match; the prototype would not.
2. **Plain-dict actions** are verified on Linux only. Step B3 is mandatory; `USE_DICT = False` is the tested fallback.
3. **Noise.** About ±0.07 points/match at 120 matches. Do not accept changes on smaller samples.
4. **Baselines are a proxy.** See the head-to-head warning in §4.
5. **Late push** exposes you to counter-attacks. It helped on baselines; drop it if goals-against rises on your machine.
6. **Sandbox timing is noisy** (shared single CPU). Compare ratios, not absolute values, and measure on your own machine.
7. **`reset()` is not called by `validate`.** The prototype initialises state lazily and re-initialises on tick 0. Keep that pattern for anything you add.

---

## Appendix A: files delivered

- `IMPLEMENTATION_PLAN.md`: this document.
- `team_prototype.py`: the tested reference implementation (drop-in for `my-team/team.py`). Its tunables sit at the top of the file.

## Appendix B: results log (copy and fill in)

| Version | Opp. | W–D–L | Goals | Pts/match | Mean ms | Seeds | Notes |
|---|---|---|---|---|---|---|---|
| v1 (before) | balanced | | | | | 1000–1029 | |
| v1 (before) | tactical | | | | | 1000–1029 | |
| v1 (before) | man_marking | | | | | 1000–1029 | |
| v1 (before) | possession | | | | | 1000–1029 | |
| v1 (before) | structured_attack | | | | | 1000–1029 | |
| prototype | (repeat five rows) | | | | | 1000–1029 | |
| prototype | v1-baseline | | | | | 1000–1029 | head-to-head |
