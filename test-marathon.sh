#!/bin/bash
# ============================================
# CTFLab UIT - Marathon Test Suite (7-challenge version)
# Tests multi-challenge scoring, isolation, edge cases
# ============================================
set -uo pipefail
export DOCKER_HOST=unix:///var/run/docker.sock

BASE="http://localhost:8080"
PASS=0; FAIL=0; TOTAL=0
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

check() {
    TOTAL=$((TOTAL + 1))
    local name="$1" expected="$2" actual="$3"
    if echo "$actual" | grep -qE "$expected"; then
        PASS=$((PASS + 1)); echo -e "  ${GREEN}[PASS]${NC} $name"
    else
        FAIL=$((FAIL + 1)); echo -e "  ${RED}[FAIL]${NC} $name"
        echo -e "         Expected pattern: $expected"
        echo -e "         Got: $(echo "$actual" | head -1 | cut -c1-100)"
    fi
}

get_csrf() { curl -s -b "$1" "$BASE/challenges" 2>/dev/null | grep -oP "'csrfNonce': \"\K[^\"]+"; }

api_post() {
    local jar="$1" endpoint="$2" data="$3"
    local csrf; csrf=$(get_csrf "$jar")
    curl -s -b "$jar" -X POST "$BASE$endpoint" \
        -H "Content-Type: application/json" -H "CSRF-Token: $csrf" -d "$data" 2>/dev/null
}

api_delete() {
    local jar="$1" endpoint="$2"
    local csrf; csrf=$(get_csrf "$jar")
    curl -s -b "$jar" -X DELETE "$BASE$endpoint" \
        -H "Content-Type: application/json" -H "CSRF-Token: $csrf" 2>/dev/null
}

login_user() {
    local user="$1" pass="$2" jar="$3"
    rm -f "$jar"
    local nonce; nonce=$(curl -s -c "$jar" "$BASE/login" | grep -oP 'id="nonce".*?value="\K[^"]+')
    curl -s -c "$jar" -b "$jar" -X POST "$BASE/login" \
        -d "name=${user}&password=${pass}&nonce=${nonce}&_submit=Submit" -o /dev/null -L
}

register_user() {
    local user="$1" email="$2" pass="$3" jar="$4"
    rm -f "$jar"
    local nonce; nonce=$(curl -s -c "$jar" "$BASE/register" | grep -oP 'id="nonce".*?value="\K[^"]+')
    curl -s -c "$jar" -b "$jar" -X POST "$BASE/register" \
        -d "name=${user}&email=${email}&password=${pass}&nonce=${nonce}&_submit=Submit" -o /dev/null -L
}

echo ""
echo "============================================"
echo "  CTFLab UIT - Marathon Test (7 Challenges)"
echo "============================================"
echo ""

# ---- Cleanup ----
echo -e "${YELLOW}[0] Cleanup${NC}"
docker rm -f $(docker ps -q --filter "label=ctflab.managed=true") 2>/dev/null || true
docker network rm $(docker network ls -q --filter "label=ctflab.managed=true") 2>/dev/null || true
docker exec trogiang-ctfd-1 python3 -c "
from CTFd import create_app
app = create_app()
with app.app_context():
    from CTFd.plugins.ctflab.models import LabInstance
    from CTFd.models import db, Solves, Fails
    Solves.query.delete(); Fails.query.delete(); LabInstance.query.delete()
    db.session.commit(); print('  DB cleaned')
" 2>&1 | grep -v "Loaded\|alembic\|INFO"

# ---- Test 1: Health ----
echo -e "${YELLOW}[1] Health${NC}"
check "CTFd responds" "200|302" "$(curl -s -o /dev/null -w '%{http_code}' $BASE/)"

# ---- Test 2: User A - Full solve ----
echo -e "${YELLOW}[2] User A: Full solve (7/7 challenges)${NC}"
register_user "userA" "userA@test.com" "passA123" "/tmp/jarA"
login_user "userA" "passA123" "/tmp/jarA"
check "UserA logged in" "userA" "$(curl -s -b /tmp/jarA $BASE/api/v1/users/me)"

# Launch instance
LAUNCH_A=$(api_post "/tmp/jarA" "/api/ctflab/instances" '{"challenge_id": 1}')
check "UserA instance launched" "running" "$LAUNCH_A"
INST_A=$(echo "$LAUNCH_A" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
sleep 4

# Get flags
CID_A=$(docker ps -q --filter "label=ctflab.managed=true" | head -1)
FLAGS_A=$(docker exec $CID_A bash -c 'echo $FLAGS_JSON' 2>/dev/null)
check "Flags generated" "NBL01" "$FLAGS_A"

# Submit all 7 flags to correct challenges
for i in 1 2 3 4 5 6 7; do
    PREFIX="NBL$(printf '%02d' $i)"
    FLAG=$(echo "$FLAGS_A" | python3 -c "import sys,json; print(json.load(sys.stdin)['$PREFIX'])" 2>/dev/null)
    RESULT=$(api_post "/tmp/jarA" "/api/v1/challenges/attempt" "{\"challenge_id\": $i, \"submission\": \"$FLAG\"}")
    check "UserA $PREFIX -> Challenge $i" "correct" "$RESULT"
done

# Check score = 100+100+150+100+200+200+300 = 1150
SCORE_A=$(curl -s "$BASE/api/v1/scoreboard" | python3 -c "
import sys,json
for e in json.load(sys.stdin).get('data',[]):
    if e['name']=='userA': print(e['score'])
" 2>/dev/null)
check "UserA score = 1150" "1150" "$SCORE_A"

# ---- Test 3: User B - Partial solve ----
echo -e "${YELLOW}[3] User B: Partial solve (3/7 challenges)${NC}"
register_user "userB" "userB@test.com" "passB123" "/tmp/jarB"
login_user "userB" "passB123" "/tmp/jarB"

LAUNCH_B=$(api_post "/tmp/jarB" "/api/ctflab/instances" '{"challenge_id": 2}')
check "UserB instance launched" "running" "$LAUNCH_B"
sleep 4

CID_B=$(docker ps --filter "label=ctflab.managed=true" --format "{{.ID}}" | grep -v "$CID_A" | head -1)
if [ -z "$CID_B" ]; then CID_B=$(docker ps -q --filter "label=ctflab.managed=true" | tail -1); fi
FLAGS_B=$(docker exec $CID_B bash -c 'echo $FLAGS_JSON' 2>/dev/null)

# Submit only 3 flags
for i in 1 2 3; do
    PREFIX="NBL$(printf '%02d' $i)"
    FLAG=$(echo "$FLAGS_B" | python3 -c "import sys,json; print(json.load(sys.stdin)['$PREFIX'])" 2>/dev/null)
    RESULT=$(api_post "/tmp/jarB" "/api/v1/challenges/attempt" "{\"challenge_id\": $i, \"submission\": \"$FLAG\"}")
    check "UserB $PREFIX -> Challenge $i" "correct" "$RESULT"
done

SCORE_B=$(curl -s "$BASE/api/v1/scoreboard" | python3 -c "
import sys,json
for e in json.load(sys.stdin).get('data',[]):
    if e['name']=='userB': print(e['score'])
" 2>/dev/null)
check "UserB score = 350 (100+100+150)" "350" "$SCORE_B"

# ---- Test 4: Cross-flag validation ----
echo -e "${YELLOW}[4] Cross-flag validation${NC}"
# UserB submits NBL01 flag to challenge 5 (should fail)
NBL01_B=$(echo "$FLAGS_B" | python3 -c "import sys,json; print(json.load(sys.stdin)['NBL01'])" 2>/dev/null)
CROSS=$(api_post "/tmp/jarB" "/api/v1/challenges/attempt" "{\"challenge_id\": 5, \"submission\": \"$NBL01_B\"}")
check "Wrong prefix rejected" "incorrect" "$CROSS"

# UserB submits UserA's flag (should fail - different instance)
NBL05_A=$(echo "$FLAGS_A" | python3 -c "import sys,json; print(json.load(sys.stdin)['NBL05'])" 2>/dev/null)
STOLEN=$(api_post "/tmp/jarB" "/api/v1/challenges/attempt" "{\"challenge_id\": 5, \"submission\": \"$NBL05_A\"}")
check "Other user's flag rejected" "incorrect" "$STOLEN"

# ---- Test 5: Instance sharing ----
echo -e "${YELLOW}[5] Instance sharing across challenges${NC}"
# UserB launches from challenge 5 - should reuse existing instance (not create new)
LAUNCH_B2=$(api_post "/tmp/jarB" "/api/ctflab/instances" '{"challenge_id": 5}')
check "Reuses existing instance" "running" "$LAUNCH_B2"
# Should NOT create a new container
CONTAINER_COUNT=$(docker ps --filter "label=ctflab.managed=true" --format "{{.ID}}" | wc -l)
check "Still only 2 containers" "2" "$CONTAINER_COUNT"

# ---- Test 6: Reset ----
echo -e "${YELLOW}[6] Reset instance${NC}"
INST_B=$(echo "$LAUNCH_B" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
RESET=$(api_post "/tmp/jarB" "/api/ctflab/instances/${INST_B}/reset" '{}')
check "Reset succeeds" "reset" "$RESET"

# ---- Test 7: Destroy + re-launch ----
echo -e "${YELLOW}[7] Destroy and re-launch${NC}"
DESTROY_A=$(api_delete "/tmp/jarA" "/api/ctflab/instances/${INST_A}")
check "UserA destroy" "stopped" "$DESTROY_A"
sleep 2
check "UserA container gone" "1" "$(docker ps --filter 'label=ctflab.managed=true' --format '{{.ID}}' | wc -l)"

# Re-launch userA
RELAUNCH=$(api_post "/tmp/jarA" "/api/ctflab/instances" '{"challenge_id": 4}')
check "UserA re-launch" "running" "$RELAUNCH"
sleep 3

# New flags should be different
CID_A_NEW=$(docker ps --filter "label=ctflab.managed=true" --format "{{.ID}}" | head -1)
FLAGS_A_NEW=$(docker exec $CID_A_NEW bash -c 'echo $FLAGS_JSON' 2>/dev/null)
NBL01_NEW=$(echo "$FLAGS_A_NEW" | python3 -c "import sys,json; print(json.load(sys.stdin)['NBL01'])" 2>/dev/null)
NBL01_OLD=$(echo "$FLAGS_A" | python3 -c "import sys,json; print(json.load(sys.stdin)['NBL01'])" 2>/dev/null)
if [ "$NBL01_NEW" != "$NBL01_OLD" ]; then
    check "New flags are different" "." "DIFFERENT"
else
    check "New flags are different" "DIFFERENT" "SAME"
fi

# ---- Test 8: Scoreboard ----
echo -e "${YELLOW}[8] Final scoreboard${NC}"
BOARD=$(curl -s "$BASE/api/v1/scoreboard" | python3 -c "
import sys,json
for e in json.load(sys.stdin).get('data',[]):
    print(f'  #{e[\"pos\"]} {e[\"name\"]:<10} {e[\"score\"]}pts')
" 2>/dev/null)
echo "$BOARD"
check "UserA is #1 with 1150" "userA.*1150" "$BOARD"
check "UserB is #2 with 350" "userB.*350" "$BOARD"

# ---- Cleanup ----
echo -e "${YELLOW}[9] Cleanup${NC}"
INST_A_NEW=$(echo "$RELAUNCH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
api_delete "/tmp/jarA" "/api/ctflab/instances/${INST_A_NEW}" > /dev/null 2>&1
api_delete "/tmp/jarB" "/api/ctflab/instances/${INST_B}" > /dev/null 2>&1
sleep 2
REMAINING=$(docker ps --filter "label=ctflab.managed=true" --format "{{.ID}}" | wc -l)
check "All containers cleaned" "0" "$REMAINING"

# ---- Results ----
echo ""
echo "============================================"
echo -e "  Results: ${GREEN}${PASS} PASS${NC} / ${RED}${FAIL} FAIL${NC} / ${TOTAL} TOTAL"
echo "============================================"
if [ "$FAIL" -eq 0 ]; then
    echo -e "  ${GREEN}ALL TESTS PASSED!${NC}"
else
    echo -e "  ${RED}${FAIL} test(s) failed${NC}"
fi
echo ""
exit $FAIL
