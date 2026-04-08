#!/bin/bash
# ============================================
# CTFLab UIT - Comprehensive E2E Test Script
# ============================================
set -uo pipefail
export DOCKER_HOST=unix:///var/run/docker.sock

BASE="http://localhost:8080"
JAR="/tmp/ctfd_e2e_jar"
PASS=0
FAIL=0
TOTAL=0

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

check() {
    TOTAL=$((TOTAL + 1))
    local name="$1" expected="$2" actual="$3"
    if echo "$actual" | grep -qE "$expected"; then
        PASS=$((PASS + 1)); echo -e "  ${GREEN}[PASS]${NC} $name"
    else
        FAIL=$((FAIL + 1)); echo -e "  ${RED}[FAIL]${NC} $name"
        echo -e "         Expected: $expected"
        echo -e "         Got: $(echo "$actual" | head -1 | cut -c1-80)"
    fi
}

get_csrf() {
    curl -s -b "$JAR" "$BASE/challenges" 2>/dev/null | grep -oP "'csrfNonce': \"\K[^\"]+" || echo ""
}

api_post() {
    local endpoint="$1" data="$2"
    local csrf; csrf=$(get_csrf)
    curl -s -b "$JAR" -X POST "$BASE$endpoint" \
        -H "Content-Type: application/json" -H "CSRF-Token: $csrf" \
        -d "$data" 2>/dev/null
}

api_delete() {
    local endpoint="$1"
    local csrf; csrf=$(get_csrf)
    curl -s -b "$JAR" -X DELETE "$BASE$endpoint" \
        -H "Content-Type: application/json" -H "CSRF-Token: $csrf" 2>/dev/null
}

api_get() {
    curl -s -b "$JAR" "$BASE$1" 2>/dev/null
}

echo ""
echo "============================================"
echo "  CTFLab UIT - Full E2E Test"
echo "============================================"
echo ""

# ---- Clean up ----
echo -e "${YELLOW}[0/10] Cleanup previous state${NC}"
docker rm -f $(docker ps -q --filter "label=ctflab.managed=true") 2>/dev/null || true
docker network rm $(docker network ls -q --filter "label=ctflab.managed=true") 2>/dev/null || true
docker exec trogiang-ctfd-1 python3 -c "
from CTFd import create_app
app = create_app()
with app.app_context():
    from CTFd.plugins.ctflab.models import LabInstance
    from CTFd.models import db, Solves, Fails
    Solves.query.delete(); Fails.query.delete()
    LabInstance.query.delete()
    db.session.commit()
    print('  DB cleaned')
" 2>&1 | grep -v "Loaded\|alembic\|INFO"

# ---- 1. Health ----
echo -e "${YELLOW}[1/10] CTFd Health${NC}"
check "CTFd responds" "200|302" "$(curl -s -o /dev/null -w '%{http_code}' $BASE/)"

# ---- 2. Login ----
echo -e "${YELLOW}[2/10] Login${NC}"
rm -f "$JAR"
NONCE=$(curl -s -c "$JAR" "$BASE/login" | grep -oP 'id="nonce".*?value="\K[^"]+')
curl -s -c "$JAR" -b "$JAR" -X POST "$BASE/login" \
    -d "name=testuser&password=test123&nonce=${NONCE}&_submit=Submit" -o /dev/null -L
ME=$(api_get "/api/v1/users/me")
check "Logged in as testuser" "testuser" "$ME"

# ---- 3. Challenge ----
echo -e "${YELLOW}[3/10] Challenge listing${NC}"
CHALLS=$(api_get "/api/v1/challenges")
check "Challenge exists" "Nebula Nexus" "$CHALLS"

# ---- 4. Launch instance ----
echo -e "${YELLOW}[4/10] Launch instance${NC}"
LAUNCH=$(api_post "/api/ctflab/instances" '{"challenge_id": 1}')
check "Instance launched" "running" "$LAUNCH"
check "Got container IP" "10\.100" "$LAUNCH"

INST_ID=$(echo "$LAUNCH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
CONT_IP=$(echo "$LAUNCH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('container_ip',''))" 2>/dev/null || echo "")
echo -e "         Instance=$INST_ID, IP=$CONT_IP"
sleep 3

# ---- 5. Docker verification ----
echo -e "${YELLOW}[5/10] Docker verification${NC}"
check "Container running" "ctflab_box" "$(docker ps --format '{{.Names}}' | grep ctflab_box || echo NOT_FOUND)"
check "Network exists" "ctflab_slot" "$(docker network ls --format '{{.Name}}' | grep ctflab_slot || echo NOT_FOUND)"

SVCS=$(docker exec $(docker ps -q --filter "label=ctflab.managed=true" | head -1) supervisorctl status 2>/dev/null || echo "ERROR")
check "chall1 RUNNING" "chall1.*RUNNING" "$SVCS"
check "named RUNNING" "named.*RUNNING" "$SVCS"
check "nginx RUNNING" "nginx.*RUNNING" "$SVCS"
check "tinyfilemanager RUNNING" "tinyfilemanager.*RUNNING" "$SVCS"
check "chall5 RUNNING" "chall5.*RUNNING" "$SVCS"

FENV=$(docker exec $(docker ps -q --filter "label=ctflab.managed=true" | head -1) bash -c 'echo "$FLAGS_JSON"' 2>/dev/null || echo "{}")
check "FLAGS_JSON set" "NBL01" "$FENV"

# ---- 6. Instance status API ----
echo -e "${YELLOW}[6/10] Instance status${NC}"
STATUS=$(api_get "/api/ctflab/instances")
check "Status shows running" "running" "$STATUS"
check "Has VPN config" "has_vpn" "$STATUS"

# ---- 7. VPN download ----
echo -e "${YELLOW}[7/10] VPN download${NC}"
if [ -n "$INST_ID" ]; then
    VPN=$(api_get "/api/ctflab/instances/${INST_ID}/vpn")
    check "VPN has Interface section" "Interface" "$VPN"
    check "VPN has Peer section" "Peer" "$VPN"
    check "VPN has Endpoint" "Endpoint" "$VPN"
fi

# ---- 8. Flag submission ----
echo -e "${YELLOW}[8/10] Flag submission${NC}"
NBL01=$(echo "$FENV" | python3 -c "import sys,json; print(json.load(sys.stdin)['NBL01'])" 2>/dev/null || echo "")
NBL03=$(echo "$FENV" | python3 -c "import sys,json; print(json.load(sys.stdin)['NBL03'])" 2>/dev/null || echo "")
NBL07=$(echo "$FENV" | python3 -c "import sys,json; print(json.load(sys.stdin)['NBL07'])" 2>/dev/null || echo "")

if [ -n "$NBL01" ]; then
    R1=$(api_post "/api/v1/challenges/attempt" "{\"challenge_id\": 1, \"submission\": \"$NBL01\"}")
    check "Correct flag accepted" "correct" "$R1"
fi

R_WRONG=$(api_post "/api/v1/challenges/attempt" '{"challenge_id": 1, "submission": "NBL01{wrong}"}')
check "Wrong flag rejected" "incorrect|already_solved" "$R_WRONG"

R_DUP=$(api_post "/api/v1/challenges/attempt" "{\"challenge_id\": 1, \"submission\": \"$NBL01\"}")
check "Duplicate solve blocked" "already_solved" "$R_DUP"

SCORE=$(api_get "/api/v1/scoreboard")
check "Scoreboard works" "data" "$SCORE"

# ---- 9. Reset ----
echo -e "${YELLOW}[9/10] Reset instance${NC}"
if [ -n "$INST_ID" ]; then
    R_RESET=$(api_post "/api/ctflab/instances/${INST_ID}/reset" '{}')
    check "Reset succeeds" "reset" "$R_RESET"
    check "Container still alive" "ctflab_box" "$(docker ps --format '{{.Names}}' | grep ctflab_box || echo NOT_FOUND)"
fi

# ---- 10. Destroy + re-launch ----
echo -e "${YELLOW}[10/10] Destroy + re-launch${NC}"
if [ -n "$INST_ID" ]; then
    R_DEST=$(api_delete "/api/ctflab/instances/${INST_ID}")
    check "Destroy succeeds" "stopped" "$R_DEST"
    sleep 2
    check "Container removed" "REMOVED" "$(docker ps --format '{{.Names}}' | grep ctflab_box || echo REMOVED)"
    check "Network removed" "REMOVED" "$(docker network ls --format '{{.Name}}' | grep ctflab_slot || echo REMOVED)"
fi

# Re-launch
R_LAUNCH2=$(api_post "/api/ctflab/instances" '{"challenge_id": 1}')
check "Re-launch works" "running" "$R_LAUNCH2"

INST_ID2=$(echo "$R_LAUNCH2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

# Duplicate launch
R_DUP_LAUNCH=$(api_post "/api/ctflab/instances" '{"challenge_id": 1}')
check "Duplicate launch blocked" "already.*running|409" "$R_DUP_LAUNCH"

# Cleanup
if [ -n "$INST_ID2" ]; then
    api_delete "/api/ctflab/instances/${INST_ID2}" > /dev/null 2>&1
fi

echo ""
echo "============================================"
echo -e "  Results: ${GREEN}${PASS} PASS${NC} / ${RED}${FAIL} FAIL${NC} / ${TOTAL} TOTAL"
echo "============================================"
if [ "$FAIL" -eq 0 ]; then
    echo -e "  ${GREEN}ALL TESTS PASSED!${NC}"
else
    echo -e "  ${RED}${FAIL} test(s) need attention${NC}"
fi
echo ""
exit $FAIL
