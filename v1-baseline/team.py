"""Your team. Edit this file.

Everything you write goes in here. A submission is one file of code — extra
.py files next to it are not importable when the server loads your team, so
they are rejected rather than silently ignored.

This is a working team, so you can play it right now and see numbers come back:

    START.cmd play my-team --against balanced      (Windows)
    ./start.sh play my-team --against balanced     (macOS and Linux)

It is about as simple as a team can be while still playing football. Every
player asks two questions and does one of four things:

    is the ball ours?
        am I the closest of us to it?   ->  shoot at their goal
        otherwise                       ->  push up towards their goal
    otherwise
        am I the closest of us to it?   ->  go and get it
        otherwise                       ->  drop back towards our goal

It will lose to the reference opponents, which is the point — it is something
to improve, not something to hand in as it stands. Things wrong with it, in
roughly the order they cost you goals: nobody keeps goal, the four players who
are not chasing all run to the same place, nobody ever passes, and every shot
is struck at full power from wherever the player is standing.

The other half of your submission is `team.toml` next to this file, which says
who you are. Fill that in too.

You write one method, `act`, and it is called on every tick of the match —
whether the ball is yours or theirs. Deciding which of those it is, and what
your players should be doing about it, is the assignment. There is no engine
call that will do it for you: an observation reports where everybody is and how
the ball behaves, and the football is yours to write.

You are always given the same pitch whichever side you are really playing:
your goal at the left, theirs at the right, forward is +x, your players are
ids 0..n-1. Write one team, not one per side.

The full API is in the student guide that came with this download.
"""

from soccer import (
    PlayerAction,
    TeamAction,
    TeamController,
    clamp,
    closest_point_on_segment,
    closest_to_ball,
    direction,
    distance,
)


def predict_ball(obs, ticks=20):
    """Where the ball will be after `ticks` under the engine's drag."""
    dt = 1.0 / obs.field.simulation_hz
    x, y = obs.ball.position
    vx, vy = obs.ball.velocity
    f = obs.field.ball_friction
    for _ in range(ticks):
        x += vx * dt
        y += vy * dt
        vx *= f
        vy *= f
    return x, y


class MyTeam(TeamController):
    name = "MyTeam"
    version = "1"

    def initial_formation(self, field):
        """Kickoff formation: legal, compact, with keeper on the line."""
        keeper_x = field.my_goal[0] + field.player_radius * 2.0
        # Forwards positioned just outside the centre circle on our own half
        forward_x = -field.centre_circle_radius - 1.0
        return [
            (keeper_x, 0.0),        # 0: Goalkeeper
            (-25.0, -14.0),         # 1: Left defender
            (-25.0, 14.0),          # 2: Right defender
            (forward_x, -7.0),      # 3: Left attacker
            (forward_x, 7.0),       # 4: Right attacker
        ]

    def act(self, obs):
        """Called every tick. Decide actions for all 5 players."""
        actions = TeamAction()
        ball_pos = obs.ball.position
        ball_vel = obs.ball.velocity
        field = obs.field
        mouth = field.goal_width / 2.0 - 0.5
        future_ball = predict_ball(obs, 20)

        # Check if kickoff is live and belongs to opponent: avoid centre circle!
        opp_kickoff = (
            obs.ball.controlling_team != 0
            and distance(ball_pos, (0.0, 0.0)) < 1.0
        )

        # Decide who chases / intercepts the ball among outfield players
        outfield = [p for p in obs.my_players if p.id != 0]
        # Interception point on ball trajectory
        def intercept_dist(p):
            pt = closest_point_on_segment(p.position, ball_pos, future_ball)
            return distance(p.position, pt)

        chaser = min(outfield, key=intercept_dist)

        # Check if ball is very close to keeper
        keeper = obs.my_players[0]
        keeper_dist_to_ball = distance(keeper.position, ball_pos)
        keeper_should_clear = keeper_dist_to_ball < 3.5

        for player in obs.my_players:
            # 1. GOALKEEPER (slot 0)
            if player.id == 0:
                if keeper_should_clear and obs.can_kick(player.id):
                    # Clear firmly upfield towards touchline or forward
                    clear_y = 15.0 if ball_pos[1] > 0 else -15.0
                    actions.kick(
                        player.id,
                        direction(player.position, (0.0, clear_y)),
                        kick_power=1.0,
                    )
                else:
                    target_x = field.my_goal[0] + 2.0
                    # If ball is rolling towards goal, block arrival y
                    if ball_vel[0] < -1.0:
                        arrival_time = (target_x - ball_pos[0]) / (ball_vel[0] - 1e-6)
                        if 0.0 < arrival_time < 3.0:
                            predicted_y = ball_pos[1] + ball_vel[1] * arrival_time
                            target_y = clamp(predicted_y, -mouth, mouth)
                        else:
                            target_y = clamp(ball_pos[1] * 0.45, -mouth, mouth)
                    else:
                        target_y = clamp(ball_pos[1] * 0.45, -mouth, mouth)
                    actions.move(player.id, direction(player.position, (target_x, target_y)))
                continue

            # 2. AVOID FOUL ON OPPONENT KICKOFF
            if opp_kickoff:
                dist_to_center = distance(player.position, (0.0, 0.0))
                if dist_to_center < field.centre_circle_radius + 2.5:
                    retreat = (-field.centre_circle_radius - 3.0, player.position[1])
                    actions.move(player.id, direction(player.position, retreat))
                    continue

            # 3. BALL CHASER / INTERCEPTOR
            if player.id == chaser.id:
                if obs.can_kick(player.id):
                    self._handle_kick(player, obs, actions)
                else:
                    meet_spot = closest_point_on_segment(player.position, ball_pos, future_ball)
                    actions.move(player.id, direction(player.position, meet_spot))
                continue

            # 4. OFF-THE-BALL OUTFIELD PLAYERS
            if obs.ball.controlling_team == 0 or closest_to_ball(obs):
                # We have possession: spread out into attacking support lanes
                self._position_in_attack(player, obs, actions)
            else:
                # Opponent has possession: mark goalside
                self._position_in_defense(player, obs, actions)

        return actions

    def _handle_kick(self, player, obs, actions):
        """Decide whether to shoot, pass, or dribble forward."""
        opp_goal = obs.opponent_goal
        dist_to_goal = distance(player.position, opp_goal)

        # A. Shoot if close or in good range (e.g. within 35 units and reasonable angle)
        if dist_to_goal < 32.0:
            actions.kick(
                player.id,
                direction(player.position, opp_goal),
                kick_power=1.0,
                movement=direction(player.position, opp_goal),
            )
            return

        # B. Look for an open forward pass
        teammates = [p for p in obs.my_players if p.id != 0 and p.id != player.id]
        best_pass = None
        best_gain = -999.0

        for mate in teammates:
            # Only pass forward (advancing the ball)
            forward_gain = mate.position[0] - player.position[0]
            if forward_gain < 5.0:
                continue

            # Check passing lane clearance from opponents
            lane_clear = True
            for opp in obs.opponents:
                pt_on_lane = closest_point_on_segment(
                    opp.position, player.position, mate.position
                )
                if distance(opp.position, pt_on_lane) < 3.2:
                    lane_clear = False
                    break

            if lane_clear and forward_gain > best_gain:
                best_gain = forward_gain
                best_pass = mate

        if best_pass is not None:
            pass_dist = distance(player.position, best_pass.position)
            # Power sized so it arrives firmly: ~ distance / 33.0
            power = clamp(pass_dist / 33.0, 0.45, 0.95)
            # Lead teammate slightly forward
            lead_target = (best_pass.position[0] + 3.0, best_pass.position[1])
            actions.kick(
                player.id,
                direction(player.position, lead_target),
                kick_power=power,
                movement=direction(player.position, lead_target),
            )
            return

        # C. Otherwise: Dribble/push ball towards opponent goal
        dribble_target = (player.position[0] + 12.0, player.position[1] * 0.8)
        actions.kick(
            player.id,
            direction(player.position, dribble_target),
            kick_power=0.42,
            movement=direction(player.position, dribble_target),
        )

    def _position_in_attack(self, player, obs, actions):
        """Attacking structure: provide depth and width without bunching."""
        ball_x = obs.ball.position[0]
        # Assign lanes based on player slot
        # Slot 1: Left wing/mid
        # Slot 2: Right wing/mid
        # Slot 3: Left striker/forward
        # Slot 4: Right striker/forward
        if player.id == 1:
            target = (max(-25.0, ball_x - 8.0), -16.0)
        elif player.id == 2:
            target = (max(-25.0, ball_x - 8.0), 16.0)
        elif player.id == 3:
            target = (min(38.0, ball_x + 12.0), -10.0)
        else:  # id == 4
            target = (min(38.0, ball_x + 12.0), 10.0)

        actions.move(player.id, direction(player.position, target))

    def _position_in_defense(self, player, obs, actions):
        """Defensive structure: goalside marking."""
        # Find closest opponent to mark
        closest_opp = obs.closest_opponent_to(player.position)
        if closest_opp is not None:
            # Stand between opponent and our own goal (at -x)
            mark_x = closest_opp.position[0] - 3.5
            mark_y = closest_opp.position[1] * 0.9
            # Keep within defensive boundaries
            mark_x = clamp(mark_x, obs.field.my_goal[0] + 5.0, 10.0)
            actions.move(player.id, direction(player.position, (mark_x, mark_y)))
        else:
            actions.move(player.id, direction(player.position, obs.field.my_goal))

