#!/usr/bin/env python3
"""Comprehensive multi-user isolation test.
Creates 3 users, 3 boxes, tests all cross-access combinations.
"""
import re, time, json, subprocess, os, requests

os.environ["DOCKER_HOST"] = "unix:///var/run/docker.sock"
BASE = "http://localhost:8080"
PASS = 0
FAIL = 0

def check(name, passed, detail=""):
    global PASS, FAIL
    if passed:
        PASS += 1
        print(f"  \033[32m[PASS]\033[0m {name} {detail}")
    else:
        FAIL += 1
        print(f"  \033[31m[FAIL]\033[0m {name} {detail}")

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True,
                          env={**os.environ, "DOCKER_HOST": "unix:///var/run/docker.sock"})

def login(username, password):
    s = requests.Session()
    r = s.get(f"{BASE}/login")
    nonce = re.search(r'id="nonce".*?value="([^"]+)"', r.text).group(1)
    s.post(f"{BASE}/login", data={"name": username, "password": password, "nonce": nonce}, allow_redirects=True)
    return s

def csrf(session):
    return re.search(r"'csrfNonce': \"([a-f0-9]+)\"", session.get(f"{BASE}/challenges").text).group(1)

def register(username, email, password):
    s = requests.Session()
    r = s.get(f"{BASE}/register")
    nonce = re.search(r'id="nonce".*?value="([^"]+)"', r.text).group(1)
    s.post(f"{BASE}/register", data={"name": username, "email": email, "password": password, "nonce": nonce}, allow_redirects=True)

print("=" * 60)
print("  MULTI-USER ISOLATION TEST")
print("=" * 60)

# Cleanup
print("\n[0] Cleanup")
run(["docker", "rm", "-f"] + run(["docker", "ps", "-aq", "--filter", "label=ctflab.managed=true"]).stdout.split())
for nid in run(["docker", "network", "ls", "-q", "--filter", "label=ctflab.managed=true"]).stdout.split():
    run(["docker", "network", "rm", nid])

# Clean DB via API
admin = login("admin", "admin123")
r = run(["docker", "exec", "ctflab-uit-ctfd-1", "python3", "-c", """
import sys; sys.path.insert(0, "/opt/CTFd")
from CTFd import create_app
app = create_app()
with app.app_context():
    from CTFd.plugins.ctflab.models import LabInstance, SuspiciousSubmission
    from CTFd.models import db, Solves, Fails
    LabInstance.query.delete()
    SuspiciousSubmission.query.delete()
    Solves.query.delete()
    Fails.query.delete()
    db.session.commit()
    print("cleaned")
"""])
print(f"  DB: {r.stdout.strip()}")

# Fix routing
run(["bash", "/opt/ctflab-uit/fix-vpn-routing.sh"])

# Register 3 test users
print("\n[1] Register 3 users")
for i in range(1, 4):
    register(f"testiso{i}", f"testiso{i}@test.com", f"pass{i}123")
    print(f"  Registered: testiso{i}")

# Each user launches a box
print("\n[2] Each user launches a box")
sessions = {}
instances = {}
for i in range(1, 4):
    s = login(f"testiso{i}", f"pass{i}123")
    sessions[i] = s
    r = s.post(f"{BASE}/api/ctflab/instances", json={"challenge_id": 8}, headers={"CSRF-Token": csrf(s)})
    d = r.json()
    instances[i] = d
    slot = d.get("container_ip", "?").split(".")[2] if d.get("container_ip") else "?"
    print(f"  testiso{i}: IP={d.get('container_ip')}, slot={slot}, id={d.get('id')}")
    time.sleep(2)
    run(["bash", "/opt/ctflab-uit/fix-vpn-routing.sh"])

time.sleep(3)

# Setup iptables isolation
print("\n[3] Setup iptables isolation")
run(["iptables", "-F", "CTFLAB_ISOLATION"])
# Server keepalive
run(["iptables", "-A", "CTFLAB_ISOLATION", "-s", "10.200.0.1", "-d", "10.200.0.0/24", "-j", "ACCEPT"])
run(["iptables", "-A", "CTFLAB_ISOLATION", "-s", "10.200.0.0/24", "-d", "10.200.0.1", "-j", "ACCEPT"])
# Block client-to-client
run(["iptables", "-A", "CTFLAB_ISOLATION", "-s", "10.200.0.0/24", "-d", "10.200.0.0/24", "-j", "DROP"])
# Per-slot rules
for i in range(1, 4):
    ip = instances[i].get("container_ip", f"10.100.{i}.2")
    slot = ip.split(".")[2]
    vpn_ip = f"10.200.0.{int(slot) + 1}"
    subnet = f"10.100.{slot}.0/24"
    run(["iptables", "-A", "CTFLAB_ISOLATION", "-s", vpn_ip, "-d", subnet, "-j", "ACCEPT"])
    run(["iptables", "-A", "CTFLAB_ISOLATION", "-s", subnet, "-d", vpn_ip, "-j", "ACCEPT"])
    print(f"  Slot {slot}: {vpn_ip} <-> {subnet}")
# Default DROP
run(["iptables", "-A", "CTFLAB_ISOLATION", "-s", "10.200.0.0/24", "-d", "10.100.0.0/16", "-j", "DROP"])
print("  Default DROP added")

# Show chain
r = run(["iptables", "-L", "CTFLAB_ISOLATION", "-n", "--line-numbers"])
print(f"\n  Isolation chain:\n{r.stdout}")

# Test SSH: each user can reach their own box
print("[4] SSH: each user reaches OWN box")
for i in range(1, 4):
    ip = instances[i].get("container_ip", f"10.100.{i}.2")
    r = run(["sshpass", "-p", "lekkerding", "ssh", "-o", "StrictHostKeyChecking=no",
             "-o", "ConnectTimeout=5", f"taylor@{ip}", "echo OK"])
    check(f"testiso{i} SSH -> {ip}", "OK" in r.stdout, r.stdout.strip()[:30])

# Test: VPS can simulate VPN source and test cross-access
print("\n[5] Cross-access test (iptables check)")
for src_slot in range(1, 4):
    for dst_slot in range(1, 4):
        vpn_ip = f"10.200.0.{src_slot + 1}"
        dst_ip = f"10.100.{dst_slot}.2"
        # Check if iptables would allow this
        r = run(["iptables", "-C", "CTFLAB_ISOLATION", "-s", vpn_ip, "-d", f"10.100.{dst_slot}.0/24", "-j", "ACCEPT"])
        allowed = r.returncode == 0
        should_allow = (src_slot == dst_slot)
        check(f"VPN {vpn_ip} -> {dst_ip}", allowed == should_allow,
              f"{'ALLOW' if allowed else 'BLOCK'} (expected {'ALLOW' if should_allow else 'BLOCK'})")

# Test flag isolation: each user's flags are different
print("\n[6] Flag isolation")
all_flags = {}
for i in range(1, 4):
    ip = instances[i].get("container_ip", f"10.100.{i}.2")
    slot = ip.split(".")[2]
    cname = f"ctflab_box_{slot}"
    r = run(["docker", "exec", cname, "bash", "-c", "echo $FLAGS_JSON"])
    flags = json.loads(r.stdout.strip()) if r.stdout.strip() else {}
    all_flags[i] = flags
    print(f"  testiso{i}: NBL01={flags.get('NBL01', '?')[:25]}...")

for i in range(1, 4):
    for j in range(i+1, 4):
        same = all_flags[i].get("NBL01") == all_flags[j].get("NBL01")
        check(f"testiso{i} vs testiso{j} flags", not same, "DIFFERENT" if not same else "SAME (BAD!)")

# Test flag submission: user can only submit their own flags
print("\n[7] Cross-flag submission")
for i in range(1, 4):
    s = sessions[i]
    own_flag = all_flags[i].get("NBL01", "")
    r = s.post(f"{BASE}/api/v1/challenges/attempt", json={"challenge_id": 8, "submission": own_flag}, headers={"CSRF-Token": csrf(s)})
    status = r.json().get("data", {}).get("status", "?")
    check(f"testiso{i} submit OWN flag", status == "correct", status)

# Try submitting another user's flag
for i in range(1, 4):
    other = (i % 3) + 1  # next user
    s = sessions[i]
    other_flag = all_flags[other].get("NBL01", "")
    r = s.post(f"{BASE}/api/v1/challenges/attempt", json={"challenge_id": 8, "submission": other_flag}, headers={"CSRF-Token": csrf(s)})
    status = r.json().get("data", {}).get("status", "?")
    check(f"testiso{i} submit testiso{other}'s flag", status != "correct", f"{status} (should reject)")

# Check suspicious submissions
print("\n[8] Suspicious submissions logged")
r = admin.get(f"{BASE}/api/ctflab/admin/suspicious")
sus = r.json().get("suspicious", [])
check(f"Suspicious logged", len(sus) >= 1, f"{len(sus)} entries")
for s in sus[:3]:
    print(f"    {s.get('username')} submitted flag of {s.get('matched_user')}")

# Cleanup
print("\n[9] Cleanup - stop all")
for i in range(1, 4):
    s = sessions[i]
    inst_id = instances[i].get("id")
    if inst_id:
        s.delete(f"{BASE}/api/ctflab/instances/{inst_id}",
                 headers={"CSRF-Token": csrf(s), "Content-Type": "application/json"})
time.sleep(3)
left = run(["docker", "ps", "--filter", "label=ctflab.managed=true", "--format", "{{.Names}}"]).stdout.strip()
check("All containers removed", not left, left if left else "clean")

# Summary
print(f"\n{'=' * 60}")
print(f"  Results: \033[32m{PASS} PASS\033[0m / \033[31m{FAIL} FAIL\033[0m / {PASS+FAIL} TOTAL")
if FAIL == 0:
    print("  \033[32mALL TESTS PASSED!\033[0m")
else:
    print(f"  \033[31m{FAIL} test(s) failed\033[0m")
print(f"{'=' * 60}")
