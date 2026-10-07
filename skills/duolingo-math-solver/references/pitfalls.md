# Pitfalls: how this automation fails silently

Every item below cost real debugging time or real hearts on the live site. Most of them fail
*silently* — no error, no exit code, just a wrong or missing action — which is why `run.sh` reads
every action back before it submits.

## Browser access

| Symptom | Cause | What to do |
|---|---|---|
| `--auto-connect` says "No running Chrome instance found"; port 9222 is bound but every `/json*` endpoint returns 404 | Chrome (136+) refuses DevTools on the **default** user-data-dir, even when that dir is passed explicitly. Chrome logs `DevTools remote debugging requires a non-default data directory`. | Do not try to drive the user's real Chrome profile. Use a dedicated `agent-browser --session duo --restore --headed` session and let the user log in once. |
| `open -a 'Google Chrome' --args …` does nothing | macOS `open` re-activates any running process named "Google Chrome" — including agent-browser's own headless Chrome — and drops the args. | Not needed with the dedicated-session approach. |
| `element.click()` on the lesson START button has no effect | Duolingo is a React SPA; synthetic clicks on that button are ignored. | Open the lesson route directly, e.g. `https://www.duolingo.com/lesson/unit/3/level/16`. |

## agent-browser CLI

- **`mouse move` accepts integers only.** `mouse move 420 794.3` prints
  `Missing arguments for: mouse move` **and exits 0**. Behind `>/dev/null 2>&1` that is completely
  invisible: the move is dropped, `mouse down` lands at the previous position and the drag never
  grabs anything. Round every coordinate, including interpolated intermediate points.
- `eval` returns the JS value JSON-encoded, so a returned JSON string arrives with escaped quotes
  (`{\"value\":29}`). Strip backslashes before grepping. `run.sh`'s `ev()` also strips all double
  quotes, so `slot_texts` reads back as `[70,-,50,-,11]`, not `["70",...]`.
- In shell-built JS, `$e` inside double quotes is expanded by the shell (to nothing). Avoid `$`
  identifiers in inline JS.
- zsh `echo` interprets `\t`, so `\textbf` becomes a tab + `extbf`. Use `printf '%s'` when
  generating anything containing TeX.

## Reading the challenge

- The question lives in KaTeX `<annotation>` elements, e.g. `\mathbf{51 = \duoblank{5}}`. The
  rendered text (`51 = 5`) shows the blank's placeholder digit and is misleading; always parse the
  annotation.
- The number line and the tile board are rendered in a **same-origin iframe**
  (`document.querySelectorAll('iframe')[0].contentDocument`). Main-document queries for `canvas`,
  `svg`, `input` or the tick labels all come back empty. iframe index 1 is reCAPTCHA.
- Choice prompts come in several shapes — `51 = _` (target given), `90 - 80 + 32 = _` (evaluate),
  `275 + _ = 425` (solve) and "Follow the pattern" tables with a `?` cell and no `=` at all — and
  options come as expressions (`80 - 60 + 31`) or plain numbers (`41`). Filtering options by
  "contains an operator" silently empties the list on numeric-option questions; read each option
  from the annotation *inside* its `[data-test=challenge-choice]` element instead.
- **The blank is not always a whole side.** `_ - 2 = 54` means 56, not 54. The first solver took
  the numeric side as the answer. On a number line with ticks every 14 the thumb snapped from 54
  to 56 — the right answer by coincidence — and only the readback mismatch (`56 != 54`) exposed
  the bug. `lib.js` solves for the blank and substitutes the result back; keep that check.

## Judging the number line

The only trustworthy reading is the thumb's position mapped back through the axis:

1. read `.number-line-label` centres inside the iframe, fit `x = a + b·value`, require residual 0;
2. read `.slider1d-thumb`'s `getBoundingClientRect()` centre, invert: `value = (x − a) / b`;
3. submit only if that equals the target.

Two signals that look right and are not:

- `.number-line__label--highlighted` read `"0"` the whole time the thumb sat on 29.
- Screenshots: the thumb is drawn under the cursor, so a screenshot taken with the mouse parked
  on a tick looks "selected" even when nothing was committed.

Scale differs per question (`b` was 2.069, 2.093 and 1.463 px/unit on three consecutive
questions) — never reuse a previous mapping.

The widget only follows the pointer if the DOM is read between moves; `thumbx()` after each step
is load-bearing, not just logging. The same drag at the same coordinates failed without it.

## Tiles

- Slots are `.slot` (`.empty-cell` while empty); draggable tokens are `.token-slot`.
- The token bank re-flows after every drop, so re-read token coordinates before each drag.
- `tiles-plan.js` searches (DFS) for an arrangement `n op n op n …` from the bank; it is not
  hard-coded to subtraction (it has solved `13 + 50 = 63` with 3 slots).

## Match the pairs / Match Madness

- Cards are `button[data-test="-challenge-tap-token"]`: note the **leading dash**, so match with
  `[data-test$=challenge-tap-token]`. There is no `player-next` on the board; `btnlabel` reads
  `none`, which the driver used to treat as the end of the lesson.
- **The clock is the constraint.** A first, hand-driven attempt (eval to read, eval to tag, two
  `click`s per pair) scored 1 of 3 stars; the in-page loop scored 3 of 3 with 75 pairs in 47 s.
  Keep the clicking inside the page.
- Dispatched `MouseEvent`s (`pointerdown … click`, as in `choice.js`) are accepted on these cards.
  A first probe looked like they were ignored, because nothing visible changed within 600 ms.
- A matched card **keeps its text**. Two marking modes appeared in the same session:
  - fade: opacity falls 1 → 0 over ~2 s starting immediately, then the same button is refilled
    in place with a new card (in another row than its partner);
  - grey: `aria-disabled="true"` after **~870 ms**, opacity stays 1, and the card stays until the
    whole board is replaced.
  No class or attribute marks the fade mode, so `match.js` remembers the buttons it matched and
  skips each one until its text changes. A first version waited 800 ms for a fade and stopped on
  the first grey pair after 21 good matches.
- Selection adds one class to the card and the second click of a pair removes it within ~70 ms.
  That is the synchronous read-back; the fade/grey mark is checked asynchronously (2.5 s window)
  so the loop does not wait ~870 ms per pair. The grey state also adds one class, so the
  "already selected" check at start only compares enabled, fully shown cards.
- A replaced board can give a card the exact text it had. Treat a text change on either card of
  a pair as confirmation; never wait for both.
- Card values: never `eval()` card text. The auto-mode permission classifier blocked a quick
  `eval()` version as a code-execution surface; `lib.js` `texValue` runs only whitelisted
  arithmetic after rewriting `\frac`, `\times` and `\div`.

## Advancing safely

- Clicking `player-next` to "advance" while a question is still unanswered submits a blank answer
  and costs a heart. That is how two hearts were lost. Only click when the label is `CHECK`
  (after a verified solve) or `CONTINUE` (verdict screen).
- If a submit does not register, stop. On "select all that match", re-solving clicks the same
  options again and *deselects* them.
- Screen transitions are not atomic: the page text can change while the button still reads
  CONTINUE. Reading too early logged one verdict twice; `wait_next_screen` waits for the text to
  stop changing, and only the first verdict after a submit is graded.
- Duolingo re-queues missed questions later in the lesson, tagged `PREVIOUS MISTAKE`.
- The wrong-answer text markers in `run.sh` ("Incorrect", "Not quite", "Correct solution", …) have
  **not** been observed on a solver-produced wrong answer: none occurred in the 60 graded
  questions of the level 15, level 16 and unit 4 runs. Treat them as a best guess; the readback
  checks are the real protection.

## Speed

- One `agent-browser` call costs ~90 ms; fixed `sleep`s were the real cost (v1: 17 s per
  question, 31 s per tile question). Drags now try a fast profile and fall back to the original,
  slower profile only when the readback disagrees, and waits poll the page instead of sleeping.
  Live result: 2.5–3.3 s per question, with no fallback needed on 15 number-line drags and 3
  tile questions.
- Do not edit `run.sh` while it is running: bash reads the script as it executes, so an edit can
  make the running loop execute garbage. Stage changes in a copy and swap after the run.
