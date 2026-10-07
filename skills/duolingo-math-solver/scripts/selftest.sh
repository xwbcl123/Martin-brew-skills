#!/bin/bash
# Offline regression test for the solvers. Serves tests/fixtures (pages that mirror Duolingo's
# real DOM) on localhost and runs every planner in an isolated agent-browser session, so it never
# touches the logged-in Duolingo account. Run it after any change to scripts/js/*.js.
#
# It tests detection and planning only. Drag mechanics depend on Duolingo's own widget and can
# only be verified live (run.sh reads the result back before every submit for that reason).

DIR="$(cd "$(dirname "$0")" && pwd)"
JS="$DIR/js"
FX="$(cd "$DIR/../tests/fixtures" && pwd)"
S=duo-selftest
PASS=0; FAIL=0

command -v agent-browser >/dev/null 2>&1 || { echo "agent-browser CLI not found"; exit 2; }

PORT=$(python3 -I -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')
python3 -I -m http.server "$PORT" --bind 127.0.0.1 --directory "$FX" >/dev/null 2>&1 &
SRV=$!
cleanup() { kill "$SRV" 2>/dev/null; wait "$SRV" 2>/dev/null; agent-browser --session "$S" close >/dev/null 2>&1; }
trap cleanup EXIT
for _ in $(seq 1 50); do curl -s -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.1; done

ev() { agent-browser --session "$S" eval "$1" 2>/dev/null | tail -1 | sed 's/\\//g; s/^"//; s/"$//'; }

check() {  # $1=name $2=actual $3=expected substring
  case "$2" in
    *"$3"*) PASS=$((PASS+1)); printf '  PASS  %-26s %s\n' "$1" "$3" ;;
    *)      FAIL=$((FAIL+1)); printf '  FAIL  %-26s want [%s] got [%s]\n' "$1" "$3" "$2" ;;
  esac
}

# tiles: any arrangement is fine as long as it uses bank tokens and evaluates to the target
check_tiles() {  # $1=name $2=plan $3=target $4=bank(csv)
  local ok
  ok=$(python3 -I - "$2" "$3" "$4" <<'PY'
import sys, re, collections
plan, target, bank = sys.argv[1], int(sys.argv[2]), sys.argv[3].split(',')
m = re.search(r'seq=(\S+)', plan)
if not m: print('no-seq'); sys.exit()
seq = m.group(1).split(',')
if collections.Counter(seq) - collections.Counter(bank): print('uses-missing-token'); sys.exit()
acc = int(seq[0])
for op, n in zip(seq[1::2], seq[2::2]):
    acc = acc - int(n) if op == '-' else acc + int(n)
print('valid' if acc == target else 'evaluates-to-%d' % acc)
PY
)
  check "$1" "$ok :: $2" "valid"
}

plan() { ev "$(printf '%s\n%s' "$(cat "$JS/lib.js")" "$(cat "$JS/$1")")"; }

load() { agent-browser --session "$S" open "http://127.0.0.1:$PORT/$1" >/dev/null 2>&1; sleep 0.4; }

echo "== detection + planning (fixtures on :$PORT) =="

load choice-target-given.html
check choice-target-given/state "$(ev "$(cat "$JS/state.js")")" "CHOICE"
ev "window.__duoDryRun=true" >/dev/null
check choice-target-given/plan  "$(plan choice.js)" "target=51 matched=0,2,3"

load choice-evaluate.html
ev "window.__duoDryRun=true" >/dev/null
check choice-evaluate/plan "$(plan choice.js)" "target=42 matched=1"

load choice-no-match.html
ev "window.__duoDryRun=true" >/dev/null
check choice-no-match/stops "$(plan choice.js)" "ERR no-match"

load line-tick.html
check line-tick/state "$(ev "$(cat "$JS/state.js")")" "LINE"
P=$(plan line-plan.js)
check line-tick/target   "$P" '"target":29'
check line-tick/targetX  "$P" '"targetX":480'
check line-tick/residual "$P" '"maxResidual":0'
check line-tick/thumb    "$P" '"thumb":{"x":420,"y":794,"value":0}'

load line-interp.html
P=$(plan line-plan.js)
check line-interp/target  "$P" '"target":43'
check line-interp/targetX "$P" '"targetX":510'

load tiles-minus.html
check tiles-minus/state "$(ev "$(cat "$JS/state.js")")" "TILES"
check_tiles tiles-minus/plan "$(plan tiles-plan.js)" 9 "-,5,50,-,-,11,70"

load tiles-plus.html
check_tiles tiles-plus/plan "$(plan tiles-plan.js)" 63 "13,+,50,-,20"

load tiles-impossible.html
check tiles-impossible/stops "$(plan tiles-plan.js)" "ERR no-solution"

load typed.html
check typed/state "$(ev "$(cat "$JS/state.js")")" "TYPED"
check typed/plan  "$(plan typed-plan.js)" "answer=64"

echo "== follow the pattern (unit 4 regression) =="

load choice-pattern.html
check choice-pattern/state "$(ev "$(cat "$JS/state.js")")" "CHOICE"
ev "window.__duoDryRun=true" >/dev/null
check choice-pattern/plan "$(plan choice.js)" "pattern target=300 matched=0"

load choice-pattern-inconsistent.html
ev "window.__duoDryRun=true" >/dev/null
check choice-pattern-inconsistent/stops "$(plan choice.js)" "ERR pattern-row-not-equal"

echo "== blank as an operand / on the left (level 16 regression) =="

load choice-blank-operand.html
ev "window.__duoDryRun=true" >/dev/null
check choice-blank-operand/plan "$(plan choice.js)" "target=46 matched=0"

load line-blank-operand.html
P=$(plan line-plan.js)
check line-blank-operand/target  "$P" '"target":56'
check line-blank-operand/targetX "$P" '"targetX":660'

load typed-blank-left.html
check typed-blank-left/plan "$(plan typed-plan.js)" "answer=3"

load typed-unsolvable.html
check typed-unsolvable/stops "$(plan typed-plan.js)" "ERR no-answer"

echo "== match the pairs / match madness (unit 4 level 4) =="

# match.js really clicks here: the fixture grades pairs, fades and refills cards in place like the
# live board, so this exercises the whole in-page loop, not only the plan.
load match.html
check match/state "$(ev "$(cat "$JS/state.js")")" "MATCH"
ev "window.__duoDryRun=true" >/dev/null
check match/dry-run "$(plan match.js)" "pairs=4 :: 6+3=9 2+1=3 6+1=7 4+3=7"
ev "window.__duoDryRun=false;window.__duoMatchBudgetMs=12000" >/dev/null
check match/run   "$(plan match.js)" "MATCH ok pairs=8 stop=board-gone"
check match/graded "$(ev "'matched='+window.__fxMatched+' wrong='+window.__fxWrong")" "matched=8 wrong=0"

load "match.html?grey=1"
ev "window.__duoMatchBudgetMs=14000" >/dev/null
check match-grey/run    "$(plan match.js)" "MATCH ok pairs=8 stop=board-gone"
check match-grey/graded "$(ev "'matched='+window.__fxMatched+' wrong='+window.__fxWrong")" "matched=8 wrong=0"

load "match.html?ignore=1"
ev "window.__duoMatchBudgetMs=8000" >/dev/null
check match-unconfirmed/stops "$(plan match.js)" "ERR match-not-confirmed"
check match-unconfirmed/graded "$(ev "'wrong='+window.__fxWrong")" "wrong=0"

load "match.html?unparsed=1"
ev "window.__duoMatchBudgetMs=8000" >/dev/null
check match-unparsed/stops "$(plan match.js)" "ERR no-pair after 3 pairs"
check match-unparsed/graded "$(ev "'wrong='+window.__fxWrong")" "wrong=0"

load "match.html?preselect=1"
check match-preselected/stops "$(plan match.js)" "ERR card-preselected :: 9"
check match-preselected/graded "$(ev "'matched='+window.__fxMatched+' wrong='+window.__fxWrong")" "matched=0 wrong=0"

load other.html
check other/state "$(ev "$(cat "$JS/state.js")")" "OTHER"

echo "== $PASS passed, $FAIL failed =="
[ "$FAIL" = 0 ]
