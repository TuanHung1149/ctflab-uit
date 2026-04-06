#!/usr/bin/env python3
"""Prove: Stop + Start = completely fresh box with new flags."""
import re, time, json, subprocess, os, requests

os.environ["DOCKER_HOST"] = "unix:///var/run/docker.sock"
BASE = "http://localhost:8080"
s = requests.Session()

def csrf():
    return re.search(r"'csrfNonce': \"([a-f0-9]+)\"", s.get(f"{BASE}/challenges").text).group(1)

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, env={**os.environ}).stdout.strip()

# Login
r = s.get(f"{BASE}/login")
nonce = re.search(r'id="nonce".*?value="([^"]+)"', r.text).group(1)
s.post(f"{BASE}/login", data={"name": "tester", "password": "test123", "nonce": nonce}, allow_redirects=True)

print("=== LAN 1: Start Machine ===")
r = s.post(f"{BASE}/api/ctflab/instances", json={"challenge_id": 8}, headers={"CSRF-Token": csrf()})
d1 = r.json()
print(f"IP: {d1.get('container_ip')}")
time.sleep(4)
cid1 = run(["docker", "ps", "-q", "--filter", "label=ctflab.managed=true"]).split("\n")[0]
fj1 = run(["docker", "exec", cid1, "bash", "-c", "echo $FLAGS_JSON"])
flags1 = json.loads(fj1)
print(f"Container: {cid1[:12]}")
print(f"NBL01: {flags1['NBL01']}")
print(f"NBL07: {flags1['NBL07']}")

print("\n=== STOP MACHINE ===")
s.delete(f"{BASE}/api/ctflab/instances/{d1['id']}", headers={"CSRF-Token": csrf(), "Content-Type": "application/json"})
time.sleep(3)
left = run(["docker", "ps", "--filter", "label=ctflab.managed=true", "--format", "{{.Names}}"])
print(f"Container sau stop: {'DA XOA SACH' if not left else left}")

print("\n=== LAN 2: Start Machine (MOI HOAN TOAN) ===")
subprocess.run(["bash", "/opt/ctflab-uit/fix-vpn-routing.sh"], capture_output=True)
r = s.post(f"{BASE}/api/ctflab/instances", json={"challenge_id": 8}, headers={"CSRF-Token": csrf()})
d2 = r.json()
print(f"IP: {d2.get('container_ip')}")
time.sleep(4)
cid2 = run(["docker", "ps", "-q", "--filter", "label=ctflab.managed=true"]).split("\n")[0]
fj2 = run(["docker", "exec", cid2, "bash", "-c", "echo $FLAGS_JSON"])
flags2 = json.loads(fj2)
print(f"Container: {cid2[:12]}")
print(f"NBL01: {flags2['NBL01']}")
print(f"NBL07: {flags2['NBL07']}")

print(f"\n{'='*50}")
print(f"Container lan 1: {cid1[:12]}")
print(f"Container lan 2: {cid2[:12]}")
same_container = cid1 == cid2
print(f"Cung container?  {'CO (LOI!)' if same_container else 'KHONG -> Box moi hoan toan'}")

same_flags = flags1['NBL01'] == flags2['NBL01']
print(f"NBL01 lan 1: {flags1['NBL01']}")
print(f"NBL01 lan 2: {flags2['NBL01']}")
print(f"Flag giong?      {'CO (LOI!)' if same_flags else 'KHONG -> Flag random moi'}")
print(f"{'='*50}")

if not same_container and not same_flags:
    print("VERIFIED: Stop + Start = RESET MOI THU!")
else:
    print("LOI: co gi do khong reset!")

# Cleanup
s.delete(f"{BASE}/api/ctflab/instances/{d2['id']}", headers={"CSRF-Token": csrf(), "Content-Type": "application/json"})
