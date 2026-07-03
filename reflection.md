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

My scheduler considers several constraints when building a plan:

- **Available time (the budget).** `build_plan()` takes `available_minutes` and packs tasks
  back-to-back from a `start_hour`, skipping anything that no longer fits. This is the hard
  limit — the plan can never exceed the time the owner actually has.
- **Priority.** Each task is `low`, `medium`, or `high`, and the scheduler places
  higher-priority tasks first via `sort_tasks()`.
- **Duration (as a tie-breaker).** When two tasks share a priority, the shorter one goes first,
  so a tight day fills with more quick wins.
- **Completion status.** Completed tasks are ignored so the owner isn't re-scheduled for things
  already done.
- **Recurrence / day.** Tasks are `daily`, `weekly`, or one-off, and passing a `day` filters out
  tasks that aren't due that weekday.

I decided time and priority mattered most because they map directly to the owner's real problem:
they have a *fixed amount of time* and *some tasks matter more than others* (a walk or medication
outranks an optional enrichment puzzle). Everything else — duration tie-breaking, recurrence,
completion — refines that core "fit the important things into the time I have" decision rather
than replacing it. I deliberately kept "preferences" light (just a `day_start_hour` on the owner
and an optional per-task `time`) so the scheduler stayed simple and predictable.

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

I used an AI coding assistant throughout, but for different jobs at each stage:

- **Design brainstorming.** I started by asking it to help brainstorm a UML class diagram from
  the scenario, then to critique it. That conversation is what led to the three-layer idea and,
  later, the decision to simplify from eight classes to four.
- **Writing code from the design.** Once the classes were settled, I had it turn the UML into
  Python dataclasses and implement the scheduling algorithms in small increments (sorting,
  filtering, recurrence, conflict detection) rather than all at once.
- **Refactoring.** I asked "how could this be simplified for readability or performance?" and it
  suggested reusing `filter_by_status()` inside `find_conflicts()` and swapping a manual counting
  loop for `collections.Counter`.
- **Explaining concepts.** When I hit Streamlit's stateless rerun model, I asked it to explain
  why an object created at the top of the script gets "reborn" on every click, which is how I
  landed on storing the `Owner` in `st.session_state`.

The most helpful prompts were **specific and grounded in my actual code** — e.g. "based on my
skeletons, how should the Scheduler retrieve all tasks from the Owner's pets?" and "what updates
should I make to my UML to match the final implementation?" Open-ended "write me a scheduler"
prompts were far less useful than pointed questions about a decision I was already facing.

**b. Judgment and verification**

One clear moment: the assignment prompts assumed a `Scheduler.sort_by_time()` that sorts tasks by
a `time` attribute, and even suggested a `mark_complete()` method. I did **not** accept those
names/shapes blindly. My `Task` didn't originally have a `time` attribute at all — start times
were *computed by the scheduler*, not stored on tasks — so I questioned whether the method even
made sense for my design before adding an optional `time` field. Similarly, when the assistant
started to rename `mark_done()` to `mark_complete()`, I stopped it because it would have rippled
through code I was happy with, and kept my own method name instead.

I verified AI suggestions in three main ways: (1) **running the test suite** after every change —
it grew to 34 tests, so a bad suggestion showed up immediately as a failure; (2) **running
`main.py` and the Streamlit app** to watch the real behavior, which is how I confirmed things like
completed tasks being skipped and the conflict warning actually firing; and (3) **reading the
code myself** and asking follow-up questions when something looked off, rather than pasting it in
and moving on. The refactor suggestions, for example, I only kept after confirming all 34 tests
still passed.

**c. AI strategy**

*Which features were most effective.* The most useful capability was being able to **point the
assistant at my actual files** (e.g. `@pawpal_system.py`) and ask grounded questions, so its
answers matched my real code instead of a generic template. Close behind were **incremental code
generation** (turning one agreed-on design into small, reviewable changes rather than a wall of
code), **refactoring on request** ("how could this be simplified?"), and its ability to **explain
concepts and tradeoffs** — the Streamlit stateless-rerun explanation and the exact-match vs.
interval-overlap discussion both changed decisions I made. Having it keep the UML diagram and
tests in sync with each change was also a real time-saver.

*One suggestion I rejected/modified.* When an assignment step referred to a `mark_complete()`
method, the assistant started to rename my existing `mark_done()` to match. I stopped it — the
rename would have rippled through code and tests I was happy with for no real benefit — and kept
`mark_done()`, writing the test against the method that actually existed. I made a similar call on
`sort_by_time()`: rather than accept the assumption that tasks already had a `time` attribute, I
first decided whether that field belonged in my design at all before adding it. In both cases I
kept the design on my terms instead of bending it to a prompt's wording.

*How separate chat sessions per phase helped.* I worked in distinct phases — design/UML, class
skeletons, scheduling logic, smart features, UI, and reflection — and keeping them in separate
conversations kept each one **focused and uncluttered**. The design chat stayed about
responsibilities and relationships; the implementation chats stayed about code. This stopped the
assistant from dragging stale assumptions from one phase into another, made it easy to revisit a
single phase without scrolling through unrelated context, and mirrored the project's natural
milestones so I always knew "where" I was.

*What I learned about being the "lead architect."* The powerful lesson is that the AI is a fast,
capable **implementer, but not the decision-maker** — I have to own the architecture. The project
went best when I set the structure (the four classes and their responsibilities), used AI to
brainstorm options and draft code quickly, and then **made the final call and verified it myself**
with tests and by running the app. When I let a prompt's wording nudge the design (the rename, the
assumed attribute), that's exactly when I had to step in. Being lead architect meant treating AI
output as a strong proposal to review, not an answer to accept — the direction, the tradeoffs, and
the "does this fit my design?" judgment stayed mine.

---

## 4. Testing and Verification

**a. What you tested**

My suite (`tests/test_pawpal.py`, 34 tests) focuses on behavior, not implementation details:

- **Task validation** — rejecting non-positive durations, unknown priorities/recurrences, and
  out-of-range times; normalizing priority case and zero-padding times.
- **Sorting** — priority ordering with the shorter-duration tie-breaker, and chronological
  `sort_by_time()` including untimed tasks falling to the end.
- **Filtering** — `filter_by_status()` splitting pending vs. done, and `tasks_for_pet()`.
- **Scheduling** — high-priority-first placement, back-to-back times with no overlap, skipping
  tasks that don't fit, ignoring completed tasks, and day-based recurrence filtering.
- **Conflict detection** — over-budget, duplicate titles, and same-time clashes (and *not*
  flagging untimed tasks).
- **Recurrence** — `next_occurrence()` for daily/weekly/one-off, and `complete_task()`
  auto-adding the next occurrence.

These mattered because the scheduling and conflict logic is where the real decisions happen —
a bug there produces a plausible-looking but wrong plan, which is exactly the kind of error that's
easy to miss by eyeballing the UI. Testing the sort/skip/conflict rules directly meant I could
refactor confidently later.

**b. Confidence**

I'm fairly confident the scheduler works correctly for the cases it's designed for: the 34 tests
cover the core rules, and I also verified behavior by hand through `main.py` and the Streamlit app.
The logic is simple and deterministic (no randomness, no clock dependence), which makes it easy to
reason about.

Where I'm less certain is the edges I knowingly didn't handle. With more time I'd test:
**partial time overlaps** (an 08:00 task lasting 40 minutes vs. an 08:30 task — currently not
flagged); **tasks that run past midnight**; **very large task lists** to confirm performance holds;
**a day with zero available minutes**; and **weekly tasks with no `weekday` set** to pin down the
intended behavior. These are the scenarios most likely to surprise a real user.

---

## 5. Reflection

**a. What went well**

I'm most satisfied with the clean separation between data and behavior. `Owner`, `Pet`, and
`Task` are simple dataclasses that just hold state, while `Scheduler` holds all the algorithms.
That paid off repeatedly: I could add sorting, filtering, recurrence, and conflict detection as
new methods without ever touching the data classes, and I could swap the terminal demo and the
Streamlit UI on top of the exact same logic layer. Keeping the UML in sync with the code the
whole way through also meant the diagram is genuinely useful documentation, not an afterthought.

**b. What you would improve**

If I had another iteration, I'd upgrade conflict detection from exact-time matching to true
**interval-overlap** detection (using each task's `time` + `duration_minutes`), since that's the
most realistic gap in the current behavior. I'd also introduce real **calendar dates** so
"next occurrence" of a recurring task could advance by +1 day or +7 days instead of just producing
a reset copy. On the code side, if `find_conflicts()` grew any further I'd split its three checks
into separate helper methods to keep each concern isolated.

**c. Key takeaway**

The biggest thing I learned is that designing the structure first — and keeping it honest —
makes everything downstream easier, and that AI is most valuable when I drive it with specific,
grounded questions rather than letting it make decisions for me. Deciding the four classes and
their responsibilities up front is what let me bolt on feature after feature cleanly, and the
moments where the project went best were when I used AI to brainstorm options and explain
tradeoffs, then made the actual call myself and verified it with tests.
