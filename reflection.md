# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

I started by reading the scenario in the README and drafting a UML class diagram before
writing any code. I settled on four core components with clearly separated responsibilities:

- **`Owner`** — holds basic info plus scheduling preferences (like the hour their day starts)
  and owns one or more `Pet`s. It also exposes a helper to gather every task across all of its
  pets so the scheduler has a single list to work from.
- **`Pet`** — the animal being cared for. It owns its own list of `Task`s.
- **`Task`** — a single care activity with a title, duration in minutes, priority, category,
  and recurrence. It knows how to rank its own priority and whether it fits in a given amount
  of remaining time.
- **`Scheduler`** — the engine. It reads a list of tasks plus the day's time budget and start
  hour, sorts and places the tasks into a plan, and can explain that plan in plain language. I
  deliberately kept all the algorithm here, outside the data classes, so the planning logic
  can change without touching the data model.

I then converted this diagram into Python class stubs, implemented the scheduling logic in
small steps, and added tests before wiring everything into the Streamlit UI.

**b. Design changes**

Yes. My first draft had eight classes — it split out a separate `Priority` enum, a
`Constraints` class, a `ScheduledTask`, and a `Plan` on top of the four core components. Once I
started implementing, that felt like over-engineering for the size of this problem, so I
simplified down to just `Owner`, `Pet`, `Task`, and `Scheduler`:

- **Folded `Priority` into `Task`.** Instead of a separate enum, priority is now a simple string
  on the task ("low"/"medium"/"high") that `Task` validates and can rank via a
  `priority_rank()` method. This kept the UI (which passes priority as a string) and the model
  in sync without a conversion layer.
- **Folded `Constraints` into method parameters.** Rather than a dedicated class, the
  scheduler's `build_plan()` simply takes `available_minutes` and `start_hour` directly, which
  is all the constraint information the algorithm actually needs.
- **Folded `Plan` and `ScheduledTask` into the scheduler's output.** `build_plan()` now returns
  a plain dictionary of scheduled items, skipped tasks, and total minutes, and `Scheduler.explain()`
  turns that into a human-readable summary. This avoided two thin wrapper classes that existed
  only to carry data.

I also added a tie-breaker to the sorting rule along the way: sort by priority first, then by
shorter duration, so when time is tight the day fills with more quick wins instead of one long
task crowding others out.

One more change came from a question I asked while reviewing the design: what happens if two
owners have the same name? My original `Owner` was identified only by `name`, so two people both
called "Jordan" would look identical. To fix this I added an auto-generated `owner_id` (a UUID)
to the `Owner` class, so every owner has a unique identity independent of their name, while the
name stays as the human-friendly label.

After settling on this simpler shape, I updated the UML so the diagram matches the final
four-class implementation exactly (including the new `owner_id` field).

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

One clear tradeoff is in my conflict detection. `Scheduler.find_conflicts()` flags two tasks
as clashing only when they share the *exact same* `HH:MM` start time — it does **not** account
for overlapping durations. So a 40-minute task starting at 08:00 and another task starting at
08:30 genuinely overlap in real life, but my scheduler won't warn about them because their start
times differ. To catch that, I would have to treat each task as a time interval
(`start` to `start + duration_minutes`) and check whether any two intervals overlap, which is
more code and more edge cases (tasks with no time set, tasks crossing midnight, etc.).

I chose the simpler exact-match approach on purpose. It is a "lightweight" check: it groups tasks
by their time string in a single pass, is easy to read and test, and returns a plain warning
message instead of trying to resolve the conflict or crashing. For a busy pet owner sketching out
a daily routine, catching "you scheduled two things for 8:00" covers the most common and most
obvious mistake, and the cost of missing a partial overlap is low — the owner still sees both
tasks in the plan and can adjust. If this were a medical or industrial scheduler where overlaps
had real consequences, the full interval-overlap algorithm would be worth the extra complexity,
but for this scenario the exact-match check is a reasonable, readable starting point.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
