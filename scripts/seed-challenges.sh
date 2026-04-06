#!/bin/bash
# Seed CTFd with the 7 Nebula Nexus challenges
# Run after CTFd is set up with admin account
set -euo pipefail

BASE="${CTFD_URL:-http://localhost:8080}"
ADMIN_USER="${CTFD_ADMIN:-admin}"
ADMIN_PASS="${CTFD_ADMIN_PASS:-admin123}"

echo "=== Seeding CTFd with Nebula Nexus challenges ==="

# Login
NONCE=$(curl -s -c /tmp/seed_jar "$BASE/login" | grep -oP 'id="nonce".*?value="\K[^"]+')
curl -s -c /tmp/seed_jar -b /tmp/seed_jar -X POST "$BASE/login" \
    -d "name=${ADMIN_USER}&password=${ADMIN_PASS}&nonce=${NONCE}&_submit=Submit" -o /dev/null -L

CSRF=$(curl -s -b /tmp/seed_jar "$BASE/admin/challenges/new" | grep -oP "'csrfNonce': \"\K[^\"]+")

# Challenge definitions
declare -A CHALLENGES
CHALLENGES[1]="NBL01|100|Nebula - Network Recon|Connect to port 7171 and solve the math quiz to get the flag|Network"
CHALLENGES[2]="NBL02|100|Nebula - DNS Enumeration|Enumerate DNS records to find hidden flags in TXT records|Network"
CHALLENGES[3]="NBL03|150|Nebula - Web Exploitation|Exploit the TinyFileManager web application|Web"
CHALLENGES[4]="NBL04|100|Nebula - Credential Access|Use discovered credentials to access user files|Crypto"
CHALLENGES[5]="NBL05|200|Nebula - Maltrail RCE|Exploit the Maltrail service to get a shell as user brown|Exploit"
CHALLENGES[6]="NBL06|200|Nebula - SUID Privesc|Escalate from brown to john using the SUID binary|Privesc"
CHALLENGES[7]="NBL07|300|Nebula - Buffer Overflow|Exploit the buffer overflow in rootnow to get root|Pwn"

ENV_JSON='{"BOX_SLUG":"nebula","BOX_TITLE":"Nebula Nexus","BASE_DOMAIN":"nebula.lab","TXT_SUBDOMAIN":"unk","FILE_SUBDOMAIN":"inffile123"}'

for i in 1 2 3 4 5 6 7; do
    IFS='|' read -r PREFIX POINTS NAME DESC CATEGORY <<< "${CHALLENGES[$i]}"

    CSRF=$(curl -s -b /tmp/seed_jar "$BASE/admin/challenges/new" | grep -oP "'csrfNonce': \"\K[^\"]+")

    RESULT=$(curl -s -b /tmp/seed_jar \
        -X POST "$BASE/api/v1/challenges" \
        -H "Content-Type: application/json" \
        -H "CSRF-Token: $CSRF" \
        -d "{
            \"name\": \"$NAME\",
            \"category\": \"$CATEGORY\",
            \"description\": \"$DESC\",
            \"value\": $POINTS,
            \"type\": \"ctflab\",
            \"state\": \"visible\",
            \"docker_image\": \"ctflab/infinity\",
            \"flag_prefix\": \"$PREFIX\",
            \"instance_timeout\": 14400,
            \"box_env_json\": $(echo "$ENV_JSON" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')
        }")

    ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('id','FAIL'))" 2>/dev/null || echo "FAIL")
    echo "  [$i/7] $NAME ($PREFIX, ${POINTS}pts) -> Challenge ID: $ID"
done

echo ""
echo "=== Done! 7 challenges created ==="
echo "Students can now browse $BASE/challenges"

rm -f /tmp/seed_jar
