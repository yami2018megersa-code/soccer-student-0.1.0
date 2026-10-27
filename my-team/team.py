"""Fast, direct football: one chaser, early corner shots, led passes, lean per-tick cost.

Design rules (see IMPLEMENTATION_PLAN.md):
  * score first: shoot early at the corner, dribble hard, pass forward when it is open
  * think cheap: read the observation once, plain floats, closed-form ball physics,
    plain-dict actions (no TeamAction / PlayerAction construction in the hot path)
  * robust: no reliance on reset(), no reliance on engine fields the build may lack
"""

import math

hypot = math.hypot
sqrt = math.sqrt

from soccer import TeamController, TeamAction, PlayerAction

# ---- tunables (each one was swept on 30-60 matches per opponent) -----------
SHOOT_X = 26.0       # shoot as soon as the carrier is beyond this x  [Step 3: 26.0]
SHOT_MARGIN = 3.2    # aim this far inside each post (target y = +/-(goal_half - margin))
DRIB_POWER = 0.65    # soft-touch power when carrying the ball
PASS_DIV = 30.0      # pass power = distance / PASS_DIV (clamped 0.35 .. 1.0)
LANE_K = 4.5         # speed (u/s) an opponent is assumed to close on a lane
LANE_BASE = 2.3      # opponent reach at t = 0 (body + kick range)
HYST = 2.0           # ticks of credit for the incumbent chaser (stops flip-flopping)
GK_X = 2.2           # keeper stands this far off our goal line
LATE_T = 0.30        # last 30% of the match ...
LATE_X = 8.0         # ... when tied or behind: shoot from here and commit forward
USE_DICT = True      # False -> wrap in TeamAction/PlayerAction (fallback, ~6 us slower)


class MyTeam(TeamController):
    name = "MyTeam"
    version = "5"

    # state is class-level so a missing reset() call can never crash act()
    _ready = False
    chaser = -1
    shoot_x = SHOOT_X
    _cand = None

    # ------------------------------------------------------------------
    def initial_formation(self, field):
        gx = field.my_goal[0]
        # forwards sit just outside the centre circle (radius 9, jitter up to 1.5)
        return [(gx + 1.5, 0.0), (-22.0, -12.0), (-22.0, 12.0),
                (-11.2, -4.0), (-11.2, 4.0)]

    def reset(self, seed):
        self._ready = False
        self.chaser = -1

    def _setup(self, obs):
        f = obs.field
        self.W = f.width / 2.0
        self.H = f.height / 2.0
        self.GW = f.goal_width / 2.0
        self.R = f.centre_circle_radius
        self.dt = 1.0 / obs.simulation_hz()          # method exists on every build
        fr = getattr(f, "ball_friction", 0.985)      # field attribute is missing on some builds
        # S[n] = sum of fr**k for k < n : ball displacement after n ticks = v * dt * S[n]
        self.S = [(1.0 - fr ** n) / (1.0 - fr) for n in range(121)]
        self._ready = True

    # ------------------------------------------------------------------
    def act(self, obs):
        if not self._ready or obs.tick == 0:
            self._setup(obs)
            self.chaser = -1
        W = self.W; H = self.H; dt = self.dt; S = self.S

        ball = obs.ball
        bx, by = ball.position
        bvx, bvy = ball.velocity
        ctrl = ball.controlling_team
        bsp2 = bvx * bvx + bvy * bvy

        mine = obs.my_players
        mp = [(p.id,) + tuple(p.position) + (p.kick_cooldown_ticks,) for p in mine]
        op = [tuple(p.position) for p in obs.opponents]

        out = {}
        self._cand = None

        # opponent kickoff in progress: the centre circle is theirs, stay out of it
        at_centre = abs(bx) < 0.7 and abs(by) < 0.7 and bsp2 < 0.05
        opp_kick = at_centre and ctrl != 0

        # ---- who chases: full intercept scan for the 2 likeliest players ----
        moving = bsp2 > 2.0
        s10 = S[10] * dt
        fx = bx + bvx * s10 if moving else bx
        fy = by + bvy * s10 if moving else by
        d2 = []
        for i in range(1, 5):
            _, px, py, _cd = mp[i]
            d2.append(((px - fx) ** 2 + (py - fy) ** 2, i))
        d2.sort()
        best = d2[0][1]; best_eta = 1e9
        chase_pt = (bx, by)
        for k in (0, 1):
            i = d2[k][1]
            _, px, py, _cd = mp[i]
            if moving:
                eta = 1e9; ip = (bx, by)
                for n in (3, 7, 12, 18, 26, 38, 55):
                    s_ = S[n] * dt
                    tx = bx + bvx * s_; ty = by + bvy * s_
                    if tx > W: tx = W
                    elif tx < -W: tx = -W
                    if ty > H: ty = H
                    elif ty < -H: ty = -H
                    need = hypot(tx - px, ty - py) * 2.9     # ticks at ~6.9 u/s
                    if need <= n + 2:
                        eta = need; ip = (tx, ty); break
                else:
                    eta = need + 20; ip = (tx, ty)
            else:
                eta = hypot(bx - px, by - py) * 2.9
                ip = (bx, by)
            if i == self.chaser:
                eta -= HYST
            if eta < best_eta:
                best_eta = eta; best = i; chase_pt = ip
        chaser = best
        self.chaser = chaser

        # ---- mode ------------------------------------------------------
        we_attack = (ctrl == 0)
        sc = obs.score
        push = (obs.time_remaining < LATE_T) and (sc[0] <= sc[1])
        self.shoot_x = LATE_X if push else SHOOT_X
        if push:
            we_attack = True

        # ---- goalkeeper ------------------------------------------------
        _, gx_, gy_, _gcd = mp[0]
        kx = -W + GK_X
        if hypot(bx - gx_, by - gy_) < 3.4 and obs.can_kick(0):
            ty = 22.0 if by > 0 else -22.0            # clear to the side the ball is on
            dx = 10.0 - gx_; dy = ty - gy_
            d = hypot(dx, dy) or 1.0
            out[0] = {"movement": (0.0, 0.0), "kick_direction": (dx / d, dy / d), "kick_power": 1.0}
        else:
            sweep = False
            if bx < -32.0 and abs(by) < 16.0 and bsp2 < 30.0:
                gkd2 = (bx - gx_) ** 2 + (by - gy_) ** 2
                closer = False
                for j in range(1, 5):
                    _, px, py, _ = mp[j]
                    if (bx - px) ** 2 + (by - py) ** 2 < gkd2:
                        closer = True
                        break
                if not closer:
                    sweep = True

            if sweep:
                dx = bx - gx_; dy = by - gy_
                d = hypot(dx, dy) or 1.0
                out[0] = {"movement": (dx / d, dy / d)}
            else:
                ty = by * 0.42
                if bvx < -1.0:
                    t = (kx - bx) / bvx
                    if 0.0 < t < 3.0:
                        ty = by + bvy * t
                lim = self.GW - 0.6
                ty = lim if ty > lim else (-lim if ty < -lim else ty)
                dx = kx - gx_; dy = ty - gy_
                d = hypot(dx, dy)
                out[0] = {"movement": (0.0, 0.0)} if d < 0.35 else {"movement": (dx / d, dy / d)}

        # ---- outfield --------------------------------------------------
        for i in range(1, 5):
            pid, px, py, _cd = mp[i]
            if opp_kick:
                dc = hypot(px, py)
                if dc < self.R + 2.0:
                    out[pid] = {"movement": (px / (dc or 1.0), py / (dc or 1.0))}
                else:
                    out[pid] = {"movement": (0.0, 0.0)}
                continue
            if i == chaser:
                if obs.can_kick(pid):
                    out[pid] = self._carry(i, mp, mine, op, bx, by)
                else:
                    tx, ty = chase_pt
                    dx = tx - px; dy = ty - py
                    d = hypot(dx, dy) or 1.0
                    out[pid] = {"movement": (dx / d, dy / d)}
                continue
            if we_attack:
                tx, ty = self._support(i, bx, by)
            else:
                tx, ty = self._defend(i, op, bx, by)
            dx = tx - px; dy = ty - py
            d = hypot(dx, dy)
            if d < 0.6:
                out[pid] = {"movement": (0.0, 0.0)}
            else:
                k = 1.0 if d > 3.0 else d / 3.0
                out[pid] = {"movement": (dx / d * k, dy / d * k)}

        if USE_DICT:
            return out
        ta = TeamAction()
        for pid, a in out.items():
            ta.set(pid, PlayerAction(a["movement"], a.get("kick_direction"), a.get("kick_power", 0.0)))
        return ta

    # ------------------------------------------------------------------
    def _room(self, ax, ay, tx, ty, op, v0):
        """How much clear space a ball struck at v0 along a->t has, after letting
        each opponent run towards the lane while the ball is in flight."""
        dx = tx - ax; dy = ty - ay
        L2 = dx * dx + dy * dy
        if L2 < 1e-6:
            return -9.0
        L = sqrt(L2)
        best = 1e9
        spd = v0 * 0.8
        for ox, oy in op:
            t = ((ox - ax) * dx + (oy - ay) * dy) / L2
            if t < 0.0: t = 0.0
            elif t > 1.0: t = 1.0
            d = hypot(ox - (ax + dx * t), oy - (ay + dy * t))
            r = d - (LANE_BASE + LANE_K * (t * L / spd))
            if r < best:
                best = r
        return best

    def _carry(self, i, mp, mine, op, bx, by):
        """The chaser has the ball in range: shoot, pass, or drive."""
        _, px, py, _cd = mp[i]
        W = self.W
        # 1. shoot at the better corner (or the middle) once past shoot_x
        if px > self.shoot_x:
            lim = self.GW - SHOT_MARGIN
            best_room = -99.0; best_t = 0.0
            for ty in (-lim, lim, 0.0):
                r = self._room(bx, by, W, ty, op, 22.0)
                if r > best_room:
                    best_room = r; best_t = ty
            dx = W - bx; dy = best_t - by
            d = hypot(dx, dy) or 1.0
            return {"movement": (dx / d, dy / d), "kick_direction": (dx / d, dy / d), "kick_power": 1.0}
        # 2. forward pass to the best open team-mate, led by their velocity
        bestp = None; bscore = 0.0
        for j in range(1, 5):
            if j == i:
                continue
            _, mx, my, _c = mp[j]
            gain = mx - px
            if gain < 3.0:
                continue
            L = hypot(mx - bx, my - by)
            if L < 5.0 or L > 42.0:
                continue
            power = L / PASS_DIV
            power = 1.0 if power > 1.0 else (0.35 if power < 0.35 else power)
            v0 = 22.0 * power
            tb = L / (v0 * 0.8)
            vx, vy = mine[j].velocity
            tx = mx + vx * tb * 0.6; ty = my + vy * tb * 0.6
            if tx > W - 2: tx = W - 2
            r = self._room(bx, by, tx, ty, op, v0)
            if r <= 0.3:
                continue
            press = 99.0
            for ox, oy in op:
                dd = hypot(ox - tx, oy - ty)
                if dd < press: press = dd
            if press < 3.5:
                continue
            sc = gain + (r if r < 6.0 else 6.0) + (press if press < 8.0 else 8.0)
            if sc > bscore:
                bscore = sc; bestp = (tx, ty, power)
        if bestp is not None:
            tx, ty, power = bestp
            dx = tx - bx; dy = ty - by
            d = hypot(dx, dy) or 1.0
            return {"movement": (dx / d, dy / d), "kick_direction": (dx / d, dy / d), "kick_power": power}
        # 3. drive at goal with a firm touch, bending away from the nearest opponent
        tx = W; ty = py * 0.5
        near = None; nd = 6.0
        for ox, oy in op:
            dd = hypot(ox - px, oy - py)
            if dd < nd and ox > px - 1.0:
                nd = dd; near = (ox, oy)
        if near is not None:
            ty = py + (6.0 if py >= near[1] else -6.0)
            ty = max(-self.H + 3.0, min(self.H - 3.0, ty))
        dx = tx - px; dy = ty - py
        d = hypot(dx, dy) or 1.0
        return {"movement": (dx / d, dy / d), "kick_direction": (dx / d, dy / d), "kick_power": DRIB_POWER}

    def _support(self, i, bx, by):
        """Attacking shape: two wide support players behind, two forwards ahead."""
        W = self.W
        if i == 1:
            return (max(-26.0, min(bx - 9.0, 10.0)), -15.0 if by > -5 else -6.0)
        if i == 2:
            return (max(-26.0, min(bx - 9.0, 10.0)), 15.0 if by < 5 else 6.0)
        fx = max(-5.0, min(bx + 13.0, W - 10.0))
        if i == 3:
            return (fx, -11.0 if by > -3 else -4.0)
        return (fx, 11.0 if by < 3 else 4.0)

    def _defend(self, i, op, bx, by):
        """Defensive shape: two goalside markers, two screening players."""
        gx = -self.W
        if i == 1 or i == 2:
            cand = self._cand
            if cand is None:
                cand = self._cand = sorted(op, key=lambda o: (o[0] - gx) ** 2 + o[1] ** 2 * 0.5)
            idx = 0 if i == 1 else 1
            if hypot(cand[idx][0] - bx, cand[idx][1] - by) < 2.5:
                ox, oy = cand[min(idx + 1, len(cand) - 1)]   # skip the player the chaser is on
            else:
                ox, oy = cand[idx]
            return (max(gx + 6.0, ox - 3.5), oy * 0.9)
        ty = by * 0.55 + (-8.0 if i == 3 else 8.0)
        tx = max(-32.0, min(bx - 10.0, 0.0))
        return (tx, max(-self.H + 3.0, min(self.H - 3.0, ty)))
