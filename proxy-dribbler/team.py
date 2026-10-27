"""Proxy attacker (weaker than your best classmates): carries the ball with soft touches, shoots only from close, away from the keeper.
Use as a test opponent: START.cmd new proxy-dribbler, then paste this over proxy-dribbler/team.py."""
import math, os
from soccer import TeamController
hypot = math.hypot
SHOOT_D = float(os.environ.get('SD', '19'))
DRIB = float(os.environ.get('DP', '0.30'))

class MyTeam(TeamController):
    name = "Dribbler"
    version = "1"
    def initial_formation(self, field):
        return [(-48.0, 0.0), (-20.0, -12.0), (-20.0, 12.0), (-11.0, -4.0), (-11.0, 4.0)]
    def act(self, obs):
        bx, by = obs.ball.position
        bvx, bvy = obs.ball.velocity
        mine = obs.my_players
        op = [p.position for p in obs.opponents]
        ky = op[0][1]
        out = {}
        # handler = outfield player nearest the (led) ball
        lx, ly = bx + bvx * 0.3, by + bvy * 0.3
        best = None; bd = 1e9
        for p in mine[1:]:
            x, y = p.position
            d = (x - lx) ** 2 + (y - ly) ** 2
            if d < bd: bd = d; best = p.id
        # keeper
        g = mine[0]; gx, gy = g.position
        if hypot(bx - gx, by - gy) < 3.0 and obs.can_kick(0):
            out[0] = {"movement": (0.0, 0.0), "kick_direction": (0.6, 0.8 if by > 0 else -0.8), "kick_power": 1.0}
        else:
            ty = max(-6.0, min(6.0, by * 0.4)); dx = -47.8 - gx; dy = ty - gy; d = hypot(dx, dy)
            out[0] = {"movement": (dx / d, dy / d) if d > 0.4 else (0.0, 0.0)}
        k = 0
        for p in mine[1:]:
            px, py = p.position
            if p.id == best:
                if obs.can_kick(p.id):
                    gd = hypot(50 - px, py)
                    if gd < SHOOT_D:
                        ty = 3.6 if ky < 0 else -3.6
                        dx = 50 - bx; dy = ty - by; d = hypot(dx, dy)
                        out[p.id] = {"movement": (dx / d, dy / d), "kick_direction": (dx / d, dy / d), "kick_power": 1.0}
                    else:
                        tx, ty = 50.0, py * 0.6
                        for ox, oy in op:
                            if abs(ox - px) < 7 and abs(oy - py) < 4.5 and ox > px - 1:
                                ty = py + (7.0 if py >= oy else -7.0); break
                        dx = tx - px; dy = ty - py; d = hypot(dx, dy)
                        out[p.id] = {"movement": (dx / d, dy / d), "kick_direction": (dx / d, dy / d), "kick_power": DRIB}
                else:
                    dx = lx - px; dy = ly - py; d = hypot(dx, dy) or 1.0
                    out[p.id] = {"movement": (dx / d, dy / d)}
            else:
                k += 1
                if k == 3:
                    tx, ty = max(-30.0, bx - 14.0), 0.0
                else:
                    tx = min(bx + 11.0, 40.0); ty = (13.0 if k == 1 else -13.0)
                dx = tx - px; dy = ty - py; d = hypot(dx, dy)
                out[p.id] = {"movement": (dx / d if d > 0.8 else 0.0, dy / d if d > 0.8 else 0.0)}
        return out
