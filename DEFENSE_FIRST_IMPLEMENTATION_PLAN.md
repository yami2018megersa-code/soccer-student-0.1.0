# Defense-First Implementation Plan: Fortress & Draw Conversion

**Project:** `soccer-student-0.1.0` (5-a-side Autonomous Soccer Simulator)  
**Author:** Yamlack Megersa (2800269) — Team: `Yamlack FC`  
**Current Placement:** #182 of 272 (Division 10) — 496 pts (132W 100D 816L, 313 GF, 3346 GA)  
**Primary Strategic Objective:** Prioritize defense to turn losses into draws at minimum, maintain existing wins, and eliminate defensive blowouts.

---

## 1. Ground-Truth League Diagnostics (1,048 Matches Analyzed)

The course server statistics reveal an extreme strategic imbalance:

| Metric | Your Team | League Avg | League Rank | Diagnosis |
|---|---|---|---|---|
| **Shots** | **11.74 / match** | 4.67 | **#1 of 272 (Gold)** | Excessive trigger-happy shooting from deep |
| **Goals Scored** | **0.30 / match** | 1.50 | #231 of 272 | **2.5% shot conversion** (1 goal per 39 shots) |
| **Goals Conceded** | **3.19 / match** | 1.38 | **#247 of 272 (Critical)**| Bleeding goals: 3,346 conceded in 1,048 matches |
| **Ball Control** | **1.8% of ticks** | 11.6% | #260 of 272 | Involuntary ball donation to opponents |
| **Dribbles** | 5.30 / match | 52.65 | #260 of 272 | No sustained carries; instant hoofs |
| **Fouls** | **0.00 / match** | 0.07 | **#1 of 272 (Gold)** | Excellent discipline (must be preserved) |
| **Decision Time** | 0.055 ms | 0.080 ms | Upper tier | Fast enough for tiebreaks; compute headroom exists |

### The Root Cause of the 816 Losses
1. **The Involuntary Giveaway Loop:** Because `SHOOT_X = 18.0` triggers full-power shots at the goal from 32+ units away whenever the player enters the attacking half, 97.5% of these long-distance shots are scooped up effortlessly by opponent goalkeepers. This immediately awards possession to the opponent and drops our possession share to 1.8%.
2. **Defensive Outnumbering (2 vs 4):** In `_defend()`, only outfield players 1 and 2 mark opponents. Players 3 and 4 stay forward above `x = -32.0` screening the midfield. When organized classmate teams attack with 3 or 4 players, players 1 and 2 are easily bypassed, leading to massive deficits (-9.25 GD against Ahmed Majeed, Daniel Passos, etc.).
3. **Passive Goalkeeping:** The keeper tracks `by * 0.42` along a static line `kx = -47.8` and only clears within 3.4 units. The keeper never cuts shooting angles, never rushes out to smother loose balls in the box, and allows opponents to dribble in for tap-ins.

### The Value of Turning Losses into Draws
- Current record: 132W, 100D, 816L = **496 points**.
- If just half (408) of those losses are turned into 0-0 or 1-1 draws: 132W, 508D, 408L = **904 points** (a **+408 point surge**, moving from Division 10 to Division 5/6).
- If 80% are drawn: 132W, 752D, 164L = **1,148 points** (Upper Division promotion).

---

## 2. Core Pillars of the New Implementation

```
+-------------------------------------------------------------------------------+
|                        FORTRESS ARCHITECTURE                                  |
+-------------------------------------------------------------------------------+
|  1. ACTIVE GOALKEEPER (Sweeper-Keeper + Angle Cutting)                        |
|     - Cuts shooting angles dynamically based on ball trajectory               |
|     - Charges to smother uncontested loose balls inside our penalty area      |
+-------------------------------------------------------------------------------+
|  2. COMPACT 4-MAN DEFENSIVE BLOCK (No Outfield Player Stranded)               |
|     - When opponent attacks, ALL 4 outfield players track back into our third |
|     - 3 tight goalside markers + 1 central lane screener / ball double-team   |
+-------------------------------------------------------------------------------+
|  3. HIGH-PERCENTAGE SHOT GATING (End the Turnover Loop)                       |
|     - Do not hoof from x=18 into the keeper's hands                           |
|     - Only shoot if inside 24 units OR if the lane to post is completely free |
|     - Otherwise: maintain carry, turn away from tackle, or circulate to mate  |
+-------------------------------------------------------------------------------+
|  4. CLINICAL TRANSITION COUNTERS (Preserve Existing 132 Wins)                |
|     - Fast forward pass / led carry on turnover when space is vacated         |
|     - Strict zero-foul discipline maintained                                  |
+-------------------------------------------------------------------------------+
```

---

## 3. Detailed Component Specification: Current vs. Proposed

### Component A: Goalkeeper Overhaul (`GK_X`, Angle-Cutting & Sweeping)

#### Current State
- Stands at fixed `x = -W + 2.2 = -47.8`.
- Only adjusts `y` as `by * 0.42`.
- Clears if ball is within 3.4 units, but never moves forward to claim 50-50 balls.
- Result: Concedes 3.19 goals/match because any shot or carry across the box finds an empty net.

#### Proposed Redesign
1. **Geometric Angle Cutting:**
   - The goal line runs from `(-50, -7)` to `(-50, 7)`.
   - The keeper position should be placed along the bisector of the angle between the ball `(bx, by)` and both goal posts `(-50, -6)` and `(-50, 6)`.
   - When the ball is close (`bx < -25`), the keeper advances up to `x = -45.0` to narrow the shooting cone.
2. **Sweeper-Keeper Rush:**
   - If the ball is loose in the defensive penalty box (`bx < -32.0` and `|by| < 18.0`) and no outfield defender is closer to it than the keeper, the keeper charges directly at the ball at max speed to kick it away into touch or upfield before the opponent striker arrives.
3. **Decisive Clearing:**
   - When clearing, strike at power 1.0 diagonally towards touchlines (`y = ±22.0`) to avoid clearing into the center where opponent midfielders volley it back.

---

### Component B: 4-Player Cohesive Defensive Shape

#### Current State
- Player 1 marks opponent 0.
- Player 2 marks opponent 1.
- Players 3 and 4 stay forward: `tx = max(-32.0, min(bx - 10.0, 0.0))`.
- When opponent attacks with 3 or 4 forwards, players 3 and 4 watch from 20+ units away, leaving our 2 defenders to face 3v2 or 4v2 overloads.

#### Proposed Redesign
1. **Full Team Defensive Transition:**
   - When `ctrl != 0` (opponent controls ball or ball is in our half `bx < 0`), all 4 outfield players drop behind the ball.
   - Defensive line anchor: `tx` can drop to `gx + 8.0 = -42.0` (deep defensive block).
2. **Dynamic 3-Man Goalside Marking:**
   - Rank all opponents by danger score:
     $$\text{Danger} = \text{dist}(\text{opp}, \text{our\_goal}) + 0.5 \times |\text{opp}_y|$$
   - Players 1, 2, and 3 each pick one of the top 3 most dangerous opponents and position themselves **strictly goalside**:
     $$x_{\text{mark}} = \text{opp}_x - 3.2, \quad y_{\text{mark}} = \text{opp}_y \times 0.95$$
3. **The 4th Player (Chaser / Disruptor / Sweeper):**
   - The remaining outfield player (closest to ball) presses the ball carrier aggressively to force rushed passes, tackle, or block passing lanes.

---

### Component C: Shot Gating & Possession Protection

#### Current State
- Carrier executes a shot at `px > 18.0` every single time.
- 11.74 shots per match with only 0.30 goals produced.
- Consequence: Kicking the ball away 12 times a match gives opponent 12 free possessions with our team out of shape.

#### Proposed Redesign
1. **Tiered Shooting Criterion:**
   - **Tier 1 (Prime Shot Zone):** `dist_to_goal < 22.0` or `px > 30.0` with clear sightline (`_room > 1.5`): Shoot firmly at the corner.
   - **Tier 2 (Mid-Range Shot Zone):** `22.0 <= dist_to_goal < 32.0`: Only shoot if `_room > 3.0` (uncontested lane with keeper out of position). If blocked, **DO NOT SHOOT**.
   - **Tier 3 (Contested / Distant):** If `_room <= 3.0`: Look for open forward/lateral pass to teammate. If no pass exists, **protect the ball by dribbling away from nearest defender**.
2. **Possession Value:**
   - Keeping the ball in the attacking third for an extra 10–20 seconds per drive naturally reduces opponent attacking opportunities by 30–50%, directly cutting goals against.

---

### Component D: Preserving the Counter-Attack (Maintaining Existing Wins)

- Do not compromise fast breaks when the ball is won.
- When an opponent attack is broken up, the ball is immediately released into space:
  - If a forward teammate has an open lane (`forward_gain >= 4.0`), execute a led pass with `PASS_DIV = 30.0`.
  - If no pass is open, carry forward at `DRIB_POWER = 0.65`.
- This ensures the 132 existing wins are preserved because our transition speed remains lethal.

---

## 4. Strict Safety & Verification Protocol (No Regressions Allowed)

Every code change must satisfy the **Non-Regression Covenant**: a change is discarded immediately if it increases goals conceded or drops overall points.

```
+---------------------------------------------------------------------------+
|                          FOUR-GATE VERIFICATION                           |
+---------------------------------------------------------------------------+
| Gate 1: Syntax, Engine & Deadline Validation                              |
|         - Command: START.cmd validate my-team                             |
|         - Must report: PASSED, 0 exceptions, 0 timeouts, mean < 0.03 ms.  |
+---------------------------------------------------------------------------+
| Gate 2: Reference Opponents Benchmark (Seeds 1000..1029, 290 matches)     |
|         - Must beat all 5 baseline bots (balanced, tactical, etc.)        |
|         - Goals conceded against tactical/balanced must not increase.     |
+---------------------------------------------------------------------------+
| Gate 3: Head-to-Head vs Previous Best (Seeds 1000..1059, 120 matches)     |
|         - Command: START.cmd tournament my-team --against best-so-far     |
|         - Win rate must be >= 50% and goals conceded must be <= baseline. |
+---------------------------------------------------------------------------+
| Gate 4: Unseen Confirmation (Seeds 2000..2029, 290 matches)               |
|         - Verification on unseen seeds to guard against over-fitting.     |
+---------------------------------------------------------------------------+
```

---

## 5. Execution Steps

### Phase 1: Goalkeeper Active Positioning & Sweeping
1. Implement angle-cutting in `my-team/team.py`:
   - Replace linear `ty = by * 0.42` with goal-mouth bisector positioning.
   - Advance keeper `kx` up to `field.my_goal[0] + 4.5` as ball approaches box.
2. Add sweeper-keeper clearance:
   - When ball is loose in box with no defender near, charge ball at full speed.
3. Validate and verify Gate 1 & Gate 2.

### Phase 2: 4-Player Compact Defensive Marking
1. Modify `_defend()` in `my-team/team.py`:
   - Bring players 3 & 4 back to `x = min(bx - 5.0, -10.0)` instead of leaving them stranded upfield.
   - Assign 3 markers to the 3 most dangerous opponent forwards goalside.
   - Assign the 4th outfield player to aggressively press the ball carrier.
2. Validate and verify Gate 2 & Gate 3.

### Phase 3: Shot Gating & Ball Protection
1. Modify `_carry()` in `my-team/team.py`:
   - Tighten shot conditions from unconditional `px > 18` to requiring either proximity (`px > 28`) or clear lane clearance (`_room > 2.5`).
   - If shot is not clear, prioritize open pass or shield dribble.
2. Validate on tournament suite to ensure shot conversion rate improves and turnovers drop.

### Phase 4: Final Head-to-Head & Unseen Benchmark
1. Run 120 matches head-to-head vs `v1-baseline` and `best-so-far`.
2. Run full 290-match unseen confirmation on seeds 2000..2029.
3. Update `RESULTS_LOG.md`.

---

## 6. Expected Outcomes

| Metric | Current (League Measured) | Expected Target With Fortress Plan |
|---|---|---|
| **Goals Conceded / Match** | **3.19** (#247) | **< 1.20** (Top 30% of league) |
| **Shot Conversion Rate** | **2.5%** (11.74 shots, 0.30 G) | **> 12%** (~5-6 shots, ~0.7-1.0 G) |
| **Ball Control Share** | **1.8%** (#260) | **10% - 15%** (League standard) |
| **Draw Conversion** | 100 draws in 1,048 (9.5%) | **250 - 350 draws** (+150-250 pts) |
| **Projected Placement** | **#182 (Division 10)** | **Division 5 - 7 (Top 40%)** |
