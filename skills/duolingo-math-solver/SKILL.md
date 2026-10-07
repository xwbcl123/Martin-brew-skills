---
name: duolingo-math-solver
description: Auto-solve Duolingo Math (多邻国数学) lessons in a dedicated, logged-in agent-browser session. Handles the observed question types (select-the-answer / select-all-that-match / follow-the-pattern, number-line drag, tile drag-and-drop equations, typed answers, timed Match the pairs / Match Madness), verifies every answer by reading the page back before submitting, and stops instead of guessing on anything unrecognised. Use whenever Martin asks to do, finish, run, test or debug Duolingo math questions or lessons, to control Duolingo in a browser, or to extend this solver to a new Duolingo question type, even if he only says "帮我做多邻国的题" or "再跑一关".
aspg:
  requirements:
    tools: [agent-browser, python3, perl, curl]
---

# Duolingo Math Solver

Drive a Duolingo Math lesson to completion with `agent-browser`. The scripts in `scripts/` do the
work; your job is to set up the session, run them, watch the log and handle stops.

Duolingo's Terms of Service prohibit automation and the account belongs to Martin. He has
accepted that trade-off; mention it once if he has not heard it, then do not repeat it.

## How it works

```
scripts/run.sh            driver loop: detect → solve → read back → submit → advance
scripts/js/lib.js         shared parsing: KaTeX annotations, safe arithmetic, solve-for-the-blank
scripts/js/state.js       classify the screen: MATCH | CHOICE | LINE | TILES | TYPED | OTHER
scripts/js/choice.js      equation or follow-the-pattern prompt, select every matching option
scripts/js/line-plan.js   fit the number-line axis, compute the target x, read the thumb back
scripts/js/tiles-plan.js  DFS over the token bank for an expression that equals the target
scripts/js/typed-plan.js  evaluate the prompt for the typed answer
scripts/js/match.js       Match the pairs / Match Madness: in-page loop that pairs cards by value
scripts/selftest.sh       offline regression test against tests/fixtures (no account access)
```

The prompt is always read from KaTeX `<annotation>` source (`\mathbf{90 - 80 + 32 =
\duoblank{1}}`), never from the rendered text, which shows a misleading placeholder digit. The
blank can be a whole side (`51 = _`) or an operand (`_ - 2 = 54`, `58 - _ = 28`); `lib.js`
solves for it and substitutes the answer back before trusting it. The number line and the tile
board live in a same-origin iframe.

**Match the pairs / Match Madness** (the `Match madness, N of 3 stars` node; seen as unit 4 level 4) is
timed (2 min 15 s, three star stages separated by `You earned N star(s). Keep it up!` CONTINUE
screens) and has no CHECK button: the second click of a pair grades it. A CLI round trip per click
loses the clock, so `match.js` runs the whole board inside the page for up to 15 s per call
(`agent-browser eval` times out at 25 s) and `run.sh` re-enters it until the board is gone. Each
pair is read back twice: the clicks must select and then consume the pair (selection class
appears, then clears), and within 2.5 s both cards must fade or turn `aria-disabled`; anything else
stops the run. Card values go through `lib.js` `texValue` (whitelisted arithmetic, `\frac`,
`\times`, `\div`); a card it cannot read stops the run once no readable pair is left.

**Safety invariant.** `run.sh` clicks `player-next` only when its label says what the click will
do: `CHECK` after a solve whose result was read back from the page, `CONTINUE` on a verdict
screen. Any other label, any solver error and any readback mismatch stops the loop. Match boards
are the one screen without `player-next`; `match.js` never touches it. Clicking the
button to "advance" over an unanswered question submits a blank answer and costs a heart, which is
exactly how hearts were lost while this was being built. Keep that invariant if you change the
driver.

## Running a lesson

1. **Session.** Check for a live session: `agent-browser --session duo get url`. If there is
   none, start one headed and let Martin log in once; `--restore` persists the login for later
   runs:

   ```bash
   agent-browser --session duo --restore --headed open https://www.duolingo.com/
   ```

   Do not try to attach to Martin's everyday Chrome profile. Chrome refuses DevTools on the
   default profile directory, and agent-browser's launch flags would put that profile's saved
   logins at risk. See `references/pitfalls.md`.

2. **Open a lesson.** Either Martin opens one, or open the lesson route directly
   (`https://www.duolingo.com/lesson/unit/<u>/level/<n>`). To find the route, open `/learn`,
   `snapshot -i`, click the current node (`button "Lesson 1 of 1"`) and read the popover's
   `link "START …"` href. A route past the end of a unit silently redirects to `/learn`; a
   finished unit shows an `UP NEXT … CONTINUE` card instead. Its button's accessible name differs
   from its upper-cased text, so tag it (`setAttribute('data-duo-next','1')`) and
   `agent-browser click "[data-duo-next]"`; raw mouse down/up on it does nothing.

3. **Dry run first.** `scripts/run.sh --plan` prints the detected type and the solver's plan
   without clicking. Check the arithmetic yourself on the first question of a new unit.

4. **Run in the background** and wait for the completion notification instead of polling:

   ```bash
   scripts/run.sh 80          # max loop steps; one question takes two steps
   ```

   Each line of the log is one step: the solver plan, the readback, then `PASS (Ns) <verdict
   text>`; screens that are not a verdict for a submitted question log as `NEXT`. The final
   lines report challenges, graded pass/wrong, elapsed time and the average seconds per type.
   Measured on live lessons: choice ~0.6 s, typed ~1.1 s, number line ~3.7 s, tiles ~2.3–3.6 s
   per tile; a 15-question lesson takes 70–100 s including the end-of-lesson screens. Match
   Madness logs one `MATCH ok pairs=N stop=board-gone` line per star stage; the first live run
   took 3 of 3 stars with 75 pairs in 47 s (about 12–14 s per stage, 0 unconfirmed pairs).

5. **Close the session** when Martin is done (`agent-browser --session duo close`). The login
   survives in the restore state.

Env: `DUO_SESSION` (default `duo`), `DUO_STOP_ON_WRONG` (default `1`; stop after a verdict that
looks wrong so a systematic solver bug cannot drain hearts).

## When it stops

A stop is the driver refusing to guess. Read the last log lines, then:

| Stop line | Meaning | Next step |
|---|---|---|
| `player-next label='CONTINUE'…` never appears; `label='I CAN DO IT!'`, `'none'`, etc. | Lesson finished; streak, quest or league screen | Normal end. Report the result. |
| `unknown challenge state (OTHER)` with label `CHECK` | A question type the solver does not know | Screenshot it, probe the iframe (below), extend the solver |
| `ERR …` from a planner | Prompt shape not understood, or no option/arrangement matches | Run `--plan`, read the annotation text, fix the parser |
| `line readback mismatch` / `tile readback mismatch` / `typed readback mismatch` | The widget did not end up holding the computed answer | Nothing was submitted. Inspect with `--plan`; see the drag notes in pitfalls |
| `WRONG …` then stop | Duolingo graded an answer wrong | A solver bug; find it before running again |
| `MATCH ERR card-preselected` | A card was already selected when the run started | Click it once by hand to deselect, then rerun |
| `MATCH ERR no-pair …` | No readable pair on a board with nothing pending (`unparsed=N`: cards `texValue` cannot read) | Read the listed TeX, extend `texValue`, add a fixture |
| `MATCH ERR select-not-registered` / `pair-not-consumed` / `match-not-confirmed` | The game did not react to a pair the way it did when this was built | The board's DOM changed; re-probe with `references/pitfalls.md` (Match section) before rerunning |

Never "fix" a stop by clicking `player-next` by hand. If a question must be skipped, tell Martin.

Probing an unfamiliar screen:

```bash
agent-browser --session duo screenshot /tmp/q.png      # what it looks like
agent-browser --session duo eval "JSON.stringify([...document.querySelectorAll('annotation')].map(a=>a.textContent))"
agent-browser --session duo eval "(()=>{const d=document.querySelectorAll('iframe')[0]?.contentDocument;const s=new Set();d&&d.querySelectorAll('[class]').forEach(e=>String(e.className.baseVal??e.className).split(/\s+/).forEach(c=>c&&s.add(c)));return JSON.stringify([...s])})()"
```

Screenshots are 2× the CSS viewport (1200×1456 CSS → 2400×2912 px). Convert before using any
coordinate from an image, or better, take coordinates from `getBoundingClientRect()` and add the
iframe's own rect.

## Extending the solver

1. Add a fixture page in `tests/fixtures/` that reproduces the new DOM (use `_kit.js` helpers for
   iframe widgets) and a `check` line in `scripts/selftest.sh`.
2. Teach `state.js` to recognise it and add a planner in `scripts/js/` that returns `ERR …` rather
   than guessing when anything is off.
3. Add a branch to `run.sh` that acts, **reads the result back**, and stops on mismatch.
4. `scripts/selftest.sh` must pass, then confirm with `--plan` on the live question before a run.

Read `references/pitfalls.md` before touching drag code or coordinates: the agent-browser `mouse
move` command rejects non-integer coordinates while still exiting 0, which turns a drag into a
silent no-op.

## Reporting

Report in Martin's default technical format: result first (lesson complete or where it stopped,
questions, pass/wrong, hearts lost), then anything new learned about question types, then timing.
Quote the stop line verbatim when the run did not finish.
