# search-race

Hill Climbing + Simulated Annealing solver for CodinGame Search Race.

---

## What I Did

### Step 1 - Initial Implementation with ChatGPT

* I asked ChatGPT to generate a Hill Climbing + Simulated Annealing (HC/SA) solver for Search Race using the lecture PDF as guidance.
* **Result:** Received a basic HC/SA framework with `State`, `Car`, and mutation logic.
* **Issue:** The code didn’t run on CodinGame due to incorrect input parsing and performance issues (timed out frequently).

### Step 2 - Iterative Debugging with Claude

* I carefully analyzed the errors and provided them to Claude for guidance.
* With Claude’s suggestions, I **adapted the code myself**, including:

  * Fixing input parsing (`checkpoint_index` order)
  * Optimizing performance to prevent timeouts (shorter solution path, faster cooling schedule)
  * Applying capped evaluations to avoid excessive computation

**My contribution:**

* Actively tested the code 5–6 times on different inputs, tracked all errors, and incorporated fixes.
* Made key decisions about which fixes to implement and verified the behavior of the algorithm.
* Ensured the final version worked reliably on CodinGame.

---

## What the Code Does

* **State:** Tracks car position, velocity, and current checkpoint.
* **apply_move:** Simulates physics (updates velocity and position).
* **estimate:** Evaluates score based on checkpoint completion and distance.
* **Search:** Hill Climbing tries 120 mutations, then Simulated Annealing tries 60 more to explore suboptimal moves, keeping the best solution.
