#!/bin/bash
# Duolingo Math auto-solver driver: CHOICE / LINE / TILES / TYPED / MATCH.
#
# Usage:
#   run.sh [MAX_STEPS]     solve the lesson that is currently open (default 60 steps)
#   run.sh --plan          print the detected type and solver plan for the current question; no clicks
#
# Env:
#   DUO_SESSION=duo        agent-browser session holding the logged-in Duolingo page
#   DUO_STOP_ON_WRONG=1    stop after the first verdict that looks wrong (protects hearts)
#
# SAFETY INVARIANT: player-next is only clicked when its label says what the click will do.
#   label == CHECK    -> we just solved and verified the challenge, submit it
#   label == CONTINUE -> we are on a verdict screen, advance
# Any other label stops the loop, so an unanswered question can never be submitted.
# (Clicking it blindly to "advance" is exactly how two hearts were lost during development.)
# MATCH boards have no player-next at all: each pair is graded on its second click, so match.js
# never touches player-next and does its own per-pair read-back inside the page.
#
# SPEED: drags run a fast profile first and fall back to the slower, originally verified profile
# when the readback disagrees. Waits poll the page instead of sleeping for a fixed time. Neither
# changes what gets submitted: every answer is still read back from the page first.

S=${DUO_SESSION:-duo}
STOP_ON_WRONG=${DUO_STOP_ON_WRONG:-1}
DIR="$(cd "$(dirname "$0")" && pwd)"
JS="$DIR/js"

command -v agent-browser >/dev/null 2>&1 || { echo "agent-browser CLI not found"; exit 2; }

ab() { agent-browser --session "$S" "$@" >/dev/null 2>&1; }
ev() { agent-browser --session "$S" eval "$1" 2>/dev/null | tail -1 | tr -d '"'; }
# every planner needs lib.js evaluated in front of it; the last statement's value is returned
withlib() { printf '%s\n%s' "$(cat "$JS/lib.js")" "$(cat "$JS/$1")"; }
evfile() { ev "$(withlib "$1")"; }
now() { perl -MTime::HiRes=time -e 'printf "%.2f\n", time'; }
lerp() { awk -v a="$1" -v b="$2" -v f="$3" 'BEGIN{printf "%.0f", a+(b-a)*f}'; }  # integers only

btnlabel() { ev "document.querySelector('button[data-test=player-next]')?.innerText.trim()||'none'"; }
state() { evfile state.js; }
# A match board renders a moment after the intro / star-break CONTINUE screen and has no
# player-next, so a missing label alone must not end the run. Prints the last state seen.
wait_match() {
  local st k
  for k in $(seq 1 15); do st=$(state); [ "$st" = MATCH ] && break; sleep 0.2; done
  echo "$st"
}
feedback() { ev "document.body.innerText.replace(/\n/g,' ').slice(-150)"; }

# Poll until the player-next label differs from $1; prints the new label ("" on timeout).
wait_label_leaves() {  # $1=label $2=timeout seconds
  local deadline l; deadline=$(awk -v t="$(now)" -v d="$2" 'BEGIN{print t+d}')
  while awk -v t="$(now)" -v d="$deadline" 'BEGIN{exit !(t<d)}'; do
    l=$(btnlabel); [ "$l" != "$1" ] && { echo "$l"; return; }
    sleep 0.2
  done
}

# After advancing, wait until the screen actually changed: either the label moved off CONTINUE,
# or (end-of-lesson screens chain several CONTINUE pages) the page content changed. When a
# challenge appears, also wait for its widget to be recognised and laid out.
screen_sig() { ev "document.body.innerText.slice(0,240)"; }
wait_next_screen() {  # $1=signature of the screen we just left
  local l st i
  for i in $(seq 1 50); do
    l=$(btnlabel)
    [ "$l" != "CONTINUE" ] && break
    if [ "$(screen_sig)" != "$1" ]; then
      # content moved first. Wait until the page stops changing, so a mid-transition read of the
      # old verdict is not taken for a new screen (observed: one verdict logged twice).
      local a b k
      a=$(screen_sig)
      for k in 1 2 3 4 5 6 7 8 9 10; do
        sleep 0.3; b=$(screen_sig); [ "$a" = "$b" ] && break; a=$b
      done
      l=$(btnlabel)
      [ "$l" != "CONTINUE" ] && break
      return   # genuinely another CONTINUE page (end-of-lesson chain)
    fi
    sleep 0.2
  done
  [ "$l" != "CHECK" ] && return
  for i in $(seq 1 20); do
    st=$(state); [ "$st" != "OTHER" ] && break
    sleep 0.2
  done
  sleep 0.6
}

# Planner with one retry, for widgets that were still rendering on the first read.
plan_retry() {  # $1=planner file -> plan line
  local out; out=$(evfile "$1")
  case "$out" in ERR*) sleep 1; out=$(evfile "$1") ;; esac
  echo "$out"
}

thumbx() {
  ev "(()=>{const f=document.querySelectorAll('iframe')[0];if(!f||!f.contentDocument)return 'none';const t=f.contentDocument.querySelector('.slider1d-thumb');if(!t)return 'none';const fr=f.getBoundingClientRect(),r=t.getBoundingClientRect();return Math.round((fr.left+r.left+r.width/2)*10)/10;})()"
}

lineplan() { agent-browser --session "$S" eval "$(withlib line-plan.js)" 2>/dev/null | tail -1 | sed 's/\\//g'; }
jnum() { echo "$1" | grep -o "\"$2\":[-0-9.]*" | head -1 | cut -d: -f2; }

# Number line: the widget only tracks the pointer if the DOM is read between moves, so thumbx()
# after every step is load-bearing (it also proves the thumb is actually moving).
# agent-browser `mouse move` accepts INTEGERS only; a float is rejected yet still exits 0.
line_drag() {  # $1=from $2=y $3=to (integers) $4=fast|slow -> "tracked" | "stuck"
  local from=$1 y=$2 to=$3 prev cur tracked=0 steps hover down step up f
  if [ "$4" = fast ]; then steps="0.25 0.5 0.75 0.92 1.00"; hover=0.15; down=0.2; step=0.1; up=0.5
  else steps="0.10 0.22 0.35 0.48 0.60 0.72 0.83 0.92 0.97 1.00"; hover=0.45; down=0.45; step=0.3; up=1.2; fi
  ab mouse move "$((from - 40))" "$y"; sleep "$hover"
  ab mouse move "$from" "$y"; sleep "$hover"
  ab mouse down; sleep "$down"
  prev=$(thumbx)
  for f in $steps; do
    ab mouse move "$(lerp "$from" "$to" "$f")" "$y"; sleep "$step"
    cur=$(thumbx); [ "$cur" != "$prev" ] && tracked=1; prev=$cur
  done
  ab mouse up; sleep "$up"
  [ "$tracked" = 1 ] && echo tracked || echo stuck
}

tile_xy() {  # $1=token text -> "x,y". The bank re-flows after every drop, so always re-read.
  ev "(()=>{const f=document.querySelectorAll('iframe')[0],d=f.contentDocument,fr=f.getBoundingClientRect();const e=[...d.querySelectorAll('.token-slot')].find(n=>(n.textContent||'').trim()==='$1');if(!e)return 'none';const r=e.getBoundingClientRect();return Math.round(fr.left+r.left+r.width/2)+','+Math.round(fr.top+r.top+r.height/2);})()"
}

empty_slot_xy() {
  ev "(()=>{const f=document.querySelectorAll('iframe')[0],d=f.contentDocument,fr=f.getBoundingClientRect();const e=[...d.querySelectorAll('.slot')].find(n=>n.className.includes('empty-cell'));if(!e)return 'none';const r=e.getBoundingClientRect();return Math.round(fr.left+r.left+r.width/2)+','+Math.round(fr.top+r.top+r.height/2);})()"
}

# ev() strips double quotes, so this reads back as [70,-,50,-,11]
slot_texts() {
  ev "(()=>{const d=document.querySelectorAll('iframe')[0].contentDocument;return JSON.stringify([...d.querySelectorAll('.slot')].map(e=>(e.textContent||'').trim()));})()" | sed 's/\\//g'
}

tile_drag() {  # $1="x1,y1" $2="x2,y2" $3=fast|slow
  local x1=${1%,*} y1=${1#*,} x2=${2%,*} y2=${2#*,} steps press step up f
  if [ "$3" = fast ]; then steps="0.33 0.66 0.9 1.0"; press=0.15; step=0.08; up=0.4
  else steps="0.2 0.4 0.6 0.8 0.95 1.0"; press=0.5; step=0.45; up=1.2; fi
  ab mouse move "$x1" "$y1"; sleep "$press"
  ab mouse down; sleep "$press"
  for f in $steps; do
    ab mouse move "$(lerp "$x1" "$x2" "$f")" "$(lerp "$y1" "$y2" "$f")"; sleep "$step"
  done
  ab mouse up; sleep "$up"
}

# ---- read-only plan mode -------------------------------------------------------------------
if [ "$1" = "--plan" ]; then
  ST=$(state)
  echo "label=$(btnlabel) state=$ST"
  case "$ST" in
    CHOICE) ev "window.__duoDryRun=true" >/dev/null; evfile choice.js; ev "window.__duoDryRun=false" >/dev/null ;;
    LINE)   lineplan ;;
    TILES)  evfile tiles-plan.js ;;
    TYPED)  evfile typed-plan.js ;;
    MATCH)  ev "window.__duoDryRun=true" >/dev/null; evfile match.js; ev "window.__duoDryRun=false" >/dev/null ;;
    *)      echo "no solver for this screen" ;;
  esac
  exit 0
fi

MAX=${1:-60}
PASS=0; WRONG=0; N=0; MP=0
STATS=$(mktemp -t duo-stats)
trap 'rm -f "$STATS"' EXIT
T_RUN=$(now); T_Q=""; Q_TYPE=""

for i in $(seq 1 "$MAX"); do
  LBL=$(btnlabel)

  if [ "$LBL" = "CONTINUE" ] && [ -z "$T_Q" ]; then
    # not the verdict for a question we submitted: end-of-lesson, quest or league screens
    echo "[$i] NEXT  $(feedback | cut -c1-90)"
    SIG=$(screen_sig)
    ab click "button[data-test=player-next]"
    wait_next_screen "$SIG"
    continue
  fi

  if [ "$LBL" = "CONTINUE" ]; then
    FB=$(feedback)
    VERDICT=PASS
    case "$FB" in
      *"Correct solution"*|*Incorrect*|*"Not quite"*|*Oops*|*"correct answer"*|*"Try again"*) VERDICT=WRONG ;;
    esac
    DT=$(awk -v a="$T_Q" -v b="$(now)" 'BEGIN{printf "%.1f", b-a}')
    echo "$Q_TYPE $DT" >> "$STATS"; T_Q=""
    FB="(${DT}s) $FB"
    if [ "$VERDICT" = WRONG ]; then
      WRONG=$((WRONG+1)); echo "[$i] WRONG $FB"
      if [ "$STOP_ON_WRONG" = 1 ]; then echo "[$i] STOP: wrong answer, inspect before continuing"; break; fi
    else
      PASS=$((PASS+1)); echo "[$i] PASS  $FB"
    fi
    SIG=$(screen_sig)
    ab click "button[data-test=player-next]"
    wait_next_screen "$SIG"
    continue
  fi

  # Match the pairs: one call runs up to ~15 s of matching in the page, then the loop comes back
  # here until the board is gone (star break or end screen, both CONTINUE pages).
  if [ "$LBL" = "CHECK" ]; then ST=$(state); else ST=$(wait_match); fi
  if [ "$ST" = MATCH ]; then
    R=$(evfile match.js)
    echo "[$i] MATCH $R"
    case "$R" in "MATCH ok"*) ;; *) echo "[$i] STOP on match error"; break ;; esac
    MP=$((MP + $(echo "$R" | grep -o 'pairs=[0-9]*' | cut -d= -f2)))
    continue
  fi

  if [ "$LBL" != "CHECK" ]; then
    echo "[$i] STOP: player-next label='$LBL', state=$ST"
    break
  fi

  N=$((N+1)); T_Q=$(now); Q_TYPE=$ST
  case "$ST" in
    CHOICE)
      R=$(plan_retry choice.js)
      echo "[$i] CHOICE $R"
      case "$R" in ERR*) echo "[$i] STOP on choice error"; break ;; esac
      ;;

    LINE)
      got=""; tgt=""
      for prof in fast slow; do
        P=$(lineplan)   # re-plan each attempt: the widget may still have been settling
        tgt=$(jnum "$P" target); to=$(jnum "$P" targetX | awk '{printf "%d", $1+0.5}')
        from=$(echo "$P" | grep -o '"thumb":{"x":[-0-9.]*' | grep -o '[-0-9.]*$' | awk '{printf "%d", $1+0.5}')
        y=$(jnum "$P" y | awk '{printf "%d", $1+0.5}')
        if [ -z "$tgt" ] || [ -z "$from" ] || [ -z "$to" ] || [ -z "$y" ]; then
          sleep 1; continue
        fi
        if [ "$(jnum "$P" value)" = "$tgt" ]; then st=already
        else st=$(line_drag "$from" "$y" "$to" "$prof"); fi
        got=$(lineplan | grep -o '"value":[-0-9.]*' | head -1 | cut -d: -f2)
        [ "$got" = "$tgt" ] && { echo "[$i] LINE target=$tgt $from->$to [$prof/$st] readback=$got OK"; break; }
        echo "[$i] LINE $prof [$st] readback=$got want=$tgt"
        sleep 0.5
      done
      if [ -z "$tgt" ] || [ "$got" != "$tgt" ]; then echo "[$i] STOP: line readback mismatch :: $P"; break; fi
      ;;

    TILES)
      TP=$(plan_retry tiles-plan.js)
      echo "[$i] TILES $TP"
      case "$TP" in ERR*) echo "[$i] STOP on tile plan error"; break ;; esac
      SEQP=$(echo "$TP" | grep -o 'seq=[^ ]*' | cut -d= -f2)
      IFS=',' read -ra WANT <<< "$SEQP"
      OK=1; DONE=""; SLOWED=0
      for w in "${WANT[@]}"; do
        DONE="${DONE:+$DONE,}$w"
        for prof in fast slow; do
          src=$(tile_xy "$w"); dst=$(empty_slot_xy)
          if [ "$src" = "none" ] || [ "$dst" = "none" ]; then echo "[$i] STOP: tile '$w' src=$src dst=$dst"; OK=0; break 2; fi
          tile_drag "$src" "$dst" "$prof"
          # the filled slots must read exactly the prefix placed so far
          case "$(slot_texts)" in "[$DONE,"*|"[$DONE]") break ;; esac
          [ "$prof" = slow ] && { echo "[$i] STOP: tile '$w' did not land :: $(slot_texts)"; OK=0; break 2; }
          SLOWED=$((SLOWED+1))
        done
      done
      [ "$OK" = 0 ] && break
      PLACED=$(slot_texts)
      echo "[$i] TILES slots -> $PLACED (slow retries: $SLOWED)"
      if [ "$PLACED" != "[$SEQP]" ]; then echo "[$i] STOP: tile readback mismatch (want $SEQP)"; break; fi
      ;;

    TYPED)
      TP=$(plan_retry typed-plan.js)
      echo "[$i] TYPED $TP"
      case "$TP" in ERR*) echo "[$i] STOP on typed plan error"; break ;; esac
      ANS=$(echo "$TP" | grep -o 'answer=[-0-9.]*' | cut -d= -f2)
      ab fill "input[data-test=challenge-text-input]" "$ANS"
      sleep 0.3
      V=$(ev "document.querySelector('input[data-test=challenge-text-input]').value")
      echo "[$i] TYPED filled='$V' want='$ANS'"
      if [ "$V" != "$ANS" ]; then echo "[$i] STOP: typed readback mismatch"; break; fi
      ;;

    *)
      echo "[$i] STOP: unknown challenge state ($ST)"
      break ;;
  esac

  # submit only if the label still says CHECK, then require the verdict screen to appear.
  # A submit that does not register must stop the loop: re-solving a "select all" question
  # would click the same options again and DEselect them.
  if [ "$(btnlabel)" = "CHECK" ]; then
    ab click "button[data-test=player-next]"
    NL=$(wait_label_leaves CHECK 8)
    if [ -z "$NL" ]; then echo "[$i] STOP: submit did not register (label still CHECK)"; break; fi
  else
    echo "[$i] note: label changed before submit -> $(btnlabel)"
  fi
done

TOTAL=$(awk -v a="$T_RUN" -v b="$(now)" 'BEGIN{printf "%.0f", b-a}')
echo "=== challenges=$N graded_pass=$PASS wrong=$WRONG match_pairs=$MP elapsed=${TOTAL}s ==="
if [ -s "$STATS" ]; then
  awk '{n[$1]++; s[$1]+=$2; N++; S+=$2} END{
    printf "timing (solve -> verdict, s): all n=%d avg=%.1f", N, S/N
    for (t in n) printf " | %s n=%d avg=%.1f", t, n[t], s[t]/n[t]
    printf "\n" }' "$STATS"
fi
