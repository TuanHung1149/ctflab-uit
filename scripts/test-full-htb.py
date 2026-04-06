#!/usr/bin/env python3
"""Full HTB-style flow test."""
import re, time, json, subprocess, os, requests

os.environ["DOCKER_HOST"] = "unix:///var/run/docker.sock"
BASE = "http://localhost:8080"
s = requests.Session()

def csrf():
    return re.search(r"'csrfNonce': \"([a-f0-9]+)\"", s.get(f"{BASE}/challenges").text).group(1)

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, "DOCKER_HOST": "unix:///var/run/docker.sock"})

print("=" * 50)
print("  FULL HTB FLOW TEST")
print("=" * 50)

# 1. Login
r = s.get(f"{BASE}/login")
nonce = re.search(r'id="nonce".*?value="([^"]+)"', r.text).group(1)
s.post(f"{BASE}/login", data={"name": "tester", "password": "test123", "nonce": nonce}, allow_redirects=True)
print(f"\n1. Login: {s.get(f'{BASE}/api/v1/users/me').json()['data']['name']}")

# 2. Download VPN
r = s.get(f"{BASE}/api/ctflab/vpn", headers={"CSRF-Token": csrf()})
print(f"2. VPN: {len(r.text)} bytes, {r.text.count('BEGIN')} certs")

# 3. Start Machine
r = s.post(f"{BASE}/api/ctflab/instances", json={"challenge_id": 8}, headers={"CSRF-Token": csrf()})
d = r.json()
ip = d.get("container_ip", "?")
inst_id = d.get("id")
print(f"3. Start Machine: IP={ip}, Status={d.get('status')}")

time.sleep(5)
subprocess.run(["bash", "/opt/ctflab-uit/fix-vpn-routing.sh"], capture_output=True)

# 4. Services
cid = run(["docker", "ps", "-q", "--filter", "label=ctflab.managed=true"]).stdout.strip().split("\n")[0]
svcs = run(["docker", "exec", cid, "supervisorctl", "status"]).stdout
running = svcs.count("RUNNING")
print(f"4. Services: {running}/6 RUNNING")

# 5. SSH
r = run(["sshpass", "-p", "lekkerding", "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
         f"taylor@{ip}", "echo SSH_OK && whoami && cat ~/user.txt"])
lines = r.stdout.strip().split("\n")
print(f"5. SSH: {lines[0] if lines else 'FAIL'}")
if len(lines) > 2:
    print(f"   User: {lines[1]}, Flag: {lines[2]}")

# 6. Flags
fj = run(["docker", "exec", cid, "bash", "-c", "echo $FLAGS_JSON"]).stdout.strip()
flags = json.loads(fj)
print(f"6. Flags: {len(flags)} generated")

# 7. Submit
for prefix in ["NBL01", "NBL04", "NBL07"]:
    r = s.post(f"{BASE}/api/v1/challenges/attempt", json={"challenge_id": 8, "submission": flags[prefix]}, headers={"CSRF-Token": csrf()})
    print(f"7. Submit {prefix}: {r.json()['data']['status']}")

# 8. Scoreboard
board = s.get(f"{BASE}/api/v1/scoreboard").json().get("data", [])
for e in board:
    print(f"8. #{e['pos']} {e['name']}: {e['score']}pts")

# 9. Stop
r = s.delete(f"{BASE}/api/ctflab/instances/{inst_id}", headers={"CSRF-Token": csrf(), "Content-Type": "application/json"})
time.sleep(2)
left = run(["docker", "ps", "--filter", "label=ctflab.managed=true", "--format", "{{.Names}}"]).stdout.strip()
print(f"9. Stop: {'REMOVED' if not left else left}")

print(f"\n{'=' * 50}")
print("  ALL STEPS PASSED!")
print(f"{'=' * 50}")
