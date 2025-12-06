import sys
import math
import random

# ============================================================
# Fast, reliable solver for CodinGame "Search Race"
# - Short plans (4–6 moves)
# - Tight evaluation caps (<= 180 per turn)
# - Simplified physics & scoring
# - HC + SA hybrid with safe fallbacks
# ============================================================

# ----------------------------
# Core game state definitions
# ----------------------------

class Car:
    def __init__(self, x=0, y=0, vx=0, vy=0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy

class Track:
    def __init__(self, checkpoints):
        self.checkpoints = checkpoints  # list of (x, y)

class State:
    def __init__(self, car, track, checkpoint_index=0, turn=0):
        self.car = car
        self.track = track
        self.checkpoint_index = checkpoint_index
        self.turn = turn
        self.crashed = False

    def copy(self):
        return State(Car(self.car.x, self.car.y, self.car.vx, self.car.vy),
                     self.track, self.checkpoint_index, self.turn)

# ----------------------------
# Utility functions
# ----------------------------

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def dist(x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    return math.sqrt(dx*dx + dy*dy)

def norm(dx, dy):
    d = math.sqrt(dx*dx + dy*dy)
    if d <= 1e-6:
        return 0.0, 0.0
    return dx/d, dy/d

# ----------------------------
# Fast simulation (simplified)
# ----------------------------

# Tuned constants for speed and stability
ARENA_W, ARENA_H = 16000, 9000
CP_RADIUS = 600
ACC_COEFF = 0.018  # slightly stronger to speed convergence
FRICTION = 0.86
MAX_SPEED = 1200

def apply_move(state, tx, ty, thrust):
    s = state.copy()

    # Clamp inputs
    tx = clamp(tx, 0, ARENA_W)
    ty = clamp(ty, 0, ARENA_H)
    thrust = clamp(thrust, 0, 100)

    # Direction to target
    dx = tx - s.car.x
    dy = ty - s.car.y
    ux, uy = norm(dx, dy)

    # Acceleration from thrust
    ax = ux * thrust * ACC_COEFF
    ay = uy * thrust * ACC_COEFF

    # Update velocity
    vx = s.car.vx + ax
    vy = s.car.vy + ay

    # Friction
    vx *= FRICTION
    vy *= FRICTION

    # Cap speed (cheap)
    sp2 = vx*vx + vy*vy
    if sp2 > MAX_SPEED*MAX_SPEED:
        sp = math.sqrt(sp2)
        scale = MAX_SPEED / sp
        vx *= scale
        vy *= scale

    # Update position
    s.car.x = int(s.car.x + vx)
    s.car.y = int(s.car.y + vy)
    s.car.vx = vx
    s.car.vy = vy

    # Bounds crash
    if s.car.x < 0 or s.car.x > ARENA_W or s.car.y < 0 or s.car.y > ARENA_H:
        s.crashed = True

    # Checkpoint pass
    if s.checkpoint_index < len(s.track.checkpoints):
        cx, cy = s.track.checkpoints[s.checkpoint_index]
        if dist(s.car.x, s.car.y, cx, cy) < CP_RADIUS:
            s.checkpoint_index += 1

    s.turn += 1
    return s

# ----------------------------
# Scoring (cheap, effective)
# ----------------------------

def estimate_state(state):
    score = 0.0

    # Primary objective
    score += state.checkpoint_index * 200000.0

    # Distance to next CP penalty
    if state.checkpoint_index < len(state.track.checkpoints):
        cx, cy = state.track.checkpoints[state.checkpoint_index]
        d = dist(state.car.x, state.car.y, cx, cy)
        score -= d * 1.6
        # Velocity alignment bonus (cheap)
        dx = cx - state.car.x
        dy = cy - state.car.y
        ux, uy = norm(dx, dy)
        align = ux * state.car.vx + uy * state.car.vy
        score += align * 60.0
    else:
        # Finished (if applicable)
        score += 300000.0

    # Time penalty (small)
    score -= state.turn * 30.0

    if state.crashed:
        score -= 300000.0

    return score

# ----------------------------
# Solution representation
# ----------------------------

class Solution:
    def __init__(self, length, track):
        self.moves = [(0, 0, 100)] * length
        self.track = track

    def copy(self):
        s = Solution(0, self.track)
        s.moves = self.moves[:]
        return s

# Smart initial targeting with simple leading and apexing
def build_initial_solution(length, state):
    sol = Solution(length, state.track)
    x, y = state.car.x, state.car.y
    vx, vy = state.car.vx, state.car.vy

    # Next CP and lookahead
    idx = state.checkpoint_index
    cps = state.track.checkpoints
    cp_now = cps[idx] if idx < len(cps) else cps[-1]
    cp_next = cps[idx+1] if idx+1 < len(cps) else cp_now

    # Apex vector: point slightly toward the next CP from current CP
    ax = cp_next[0] - cp_now[0]
    ay = cp_next[1] - cp_now[1]
    aux, auy = norm(ax, ay)
    apex_offset = 400  # small apex to smooth turns

    # Lead based on velocity to avoid over-steer
    lead_x = int(cp_now[0] - vx * 0.6 + aux * apex_offset)
    lead_y = int(cp_now[1] - vy * 0.6 + auy * apex_offset)

    # Fill plan with small jitter around lead to allow HC/SA refinement
    for i in range(length):
        jx = lead_x + random.randint(-300, 300)
        jy = lead_y + random.randint(-300, 300)
        # Thrust heuristic: higher when far, lower when close
        d = dist(x, y, cp_now[0], cp_now[1])
        if d > 6000: th = random.randint(85, 100)
        elif d > 2500: th = random.randint(70, 95)
        else: th = random.randint(55, 85)
        sol.moves[i] = (clamp(jx, 0, ARENA_W), clamp(jy, 0, ARENA_H), th)

    return sol

# ----------------------------
# Evaluation
# ----------------------------

def evaluate_solution(initial_state, solution):
    s = initial_state.copy()
    for tx, ty, th in solution.moves:
        s = apply_move(s, tx, ty, th)
        if s.crashed:
            break
        if s.checkpoint_index >= len(s.track.checkpoints):
            break
    return estimate_state(s)

# ----------------------------
# Mutations (lightweight)
# ----------------------------

def mutate_single(solution):
    ns = solution.copy()
    i = random.randint(0, len(ns.moves) - 1)
    tx, ty, th = ns.moves[i]
    ns.moves[i] = (
        clamp(tx + random.randint(-250, 250), 0, ARENA_W),
        clamp(ty + random.randint(-250, 250), 0, ARENA_H),
        clamp(th + random.randint(-12, 12), 0, 100)
    )
    return ns

def mutate_window(solution, size=3):
    ns = solution.copy()
    start = random.randint(0, max(0, len(ns.moves) - size))
    for i in range(start, min(start + size, len(ns.moves))):
        tx, ty, th = ns.moves[i]
        ns.moves[i] = (
            clamp(tx + random.randint(-180, 180), 0, ARENA_W),
            clamp(ty + random.randint(-180, 180), 0, ARENA_H),
            clamp(th + random.randint(-10, 10), 0, 100)
        )
    return ns

def mutate_retarget(solution, cx, cy):
    ns = solution.copy()
    i = random.randint(0, len(ns.moves) - 1)
    # Retarget toward current CP with jitter
    ns.moves[i] = (
        clamp(cx + random.randint(-450, 450), 0, ARENA_W),
        clamp(cy + random.randint(-450, 450), 0, ARENA_H),
        random.randint(65, 100)
    )
    return ns

# ----------------------------
# Hill Climbing (capped evaluations)
# ----------------------------

def hill_climbing(initial_state, initial_solution, max_evals=120):
    best = initial_solution.copy()
    best_score = evaluate_solution(initial_state, best)

    evals = 0
    while evals < max_evals:
        r = random.random()
        if r < 0.70:
            cand = mutate_single(best)
        elif r < 0.90:
            # Small window mutation
            cand = mutate_window(best, size=3)
        else:
            # Occasional retarget toward current CP
            idx = initial_state.checkpoint_index
            cx, cy = initial_state.track.checkpoints[idx] if idx < len(initial_state.track.checkpoints) else initial_state.track.checkpoints[-1]
            cand = mutate_retarget(best, cx, cy)

        cand_score = evaluate_solution(initial_state, cand)
        evals += 1
        if cand_score > best_score:
            best = cand
            best_score = cand_score

    return best, best_score

# ----------------------------
# Simulated Annealing (capped)
# ----------------------------

def simulated_annealing(initial_state, initial_solution, max_evals=60, T0=2.5, alpha=0.985):
    cur = initial_solution.copy()
    cur_score = evaluate_solution(initial_state, cur)
    best = cur.copy()
    best_score = cur_score

    T = T0
    evals = 0
    while evals < max_evals and T > 0.08:
        r = random.random()
        if r < 0.75:
            cand = mutate_single(cur)
        elif r < 0.93:
            cand = mutate_window(cur, size=2)
        else:
            idx = initial_state.checkpoint_index
            cx, cy = initial_state.track.checkpoints[idx] if idx < len(initial_state.track.checkpoints) else initial_state.track.checkpoints[-1]
            cand = mutate_retarget(cur, cx, cy)

        cand_score = evaluate_solution(initial_state, cand)
        evals += 1
        delta = cand_score - cur_score

        if delta > 0 or (T > 0 and math.exp(delta / T) > random.random()):
            cur = cand
            cur_score = cand_score
            if cand_score > best_score:
                best = cand.copy()
                best_score = cand_score

        T *= alpha

    return best, best_score

# ----------------------------
# Hybrid solver per turn
# ----------------------------

def solve_turn(initial_state):
    # Short plan, adaptive to remaining CPs
    remaining = len(initial_state.track.checkpoints) - initial_state.checkpoint_index
    base_len = 5 if remaining > 1 else 4
    plan_len = clamp(base_len, 4, 6)

    init_sol = build_initial_solution(plan_len, initial_state)

    # Tight caps to avoid timeouts
    hc_best, hc_score = hill_climbing(initial_state, init_sol, max_evals=120)
    sa_best, sa_score = simulated_annealing(initial_state, hc_best, max_evals=60, T0=2.0, alpha=0.987)

    if sa_score >= hc_score:
        return sa_best, sa_score
    else:
        return hc_best, hc_score

# ----------------------------
# Safe fallback move (no search)
# ----------------------------

def fallback_move(state):
    idx = state.checkpoint_index
    cps = state.track.checkpoints
    cx, cy = cps[idx] if idx < len(cps) else cps[-1]

    # Aim slightly ahead using velocity
    lead_x = int(cx - state.car.vx * 0.6)
    lead_y = int(cy - state.car.vy * 0.6)

    d = dist(state.car.x, state.car.y, cx, cy)
    # Thrust heuristic based on distance
    if d > 6500: th = 100
    elif d > 3000: th = 90
    elif d > 1500: th = 75
    else: th = 60

    return clamp(lead_x, 0, ARENA_W), clamp(lead_y, 0, ARENA_H), th

# ----------------------------
# Main loop (CodinGame I/O)
# ----------------------------

def main():
    # Read checkpoints
    try:
        checkpoint_count = int(input())
    except:
        return

    checkpoints = []
    for _ in range(checkpoint_count):
        x, y = map(int, input().split())
        checkpoints.append((x, y))

    track = Track(checkpoints)
    turn = 0

    while True:
        try:
            next_check_point_id, x, y, vx, vy, angle = map(int, input().split())
        except:
            break

        car = Car(x, y, vx, vy)
        state = State(car, track, next_check_point_id, turn)

        # Try hybrid solver; on any error, use fallback
        try:
            best_sol, best_score = solve_turn(state)
            if best_sol.moves:
                tx, ty, th = best_sol.moves[0]
            else:
                tx, ty, th = fallback_move(state)
        except:
            tx, ty, th = fallback_move(state)

        print(f"{tx} {ty} {th}")
        turn += 1

if __name__ == "__main__":
    # Keep it non-deterministic in contest; uncomment to debug locally
    # random.seed(42)
    main()
