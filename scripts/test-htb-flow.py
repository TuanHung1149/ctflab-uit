#!/usr/bin/env python3
"""Full HTB-style flow test using Python requests."""
import re
import time
import requests

BASE = "http://localhost:8080"
s = requests.Session()

print("=== HTB-STYLE FLOW TEST ===\n")

# Login
r = s.get(f"{BASE}/login")
nonce = re.search(r'id="nonce".*?value="([^"]+)"', r.text).group(1)
s.post(f"{BASE}/login", data={"name": "tester", "password": "test123", "nonce": nonce, "_submit": "Submit"}, allow_redirects=True)
me = s.get(f"{BASE}/api/v1/users/me").json()
print(f"1. Login: {me['data']['name']}")

# Get CSRF
r = s.get(f"{BASE}/challenges")
csrf = re.search(r"'csrfNonce': \"([a-f0-9]+)\"", r.text).group(1)

# Download VPN (like HTB "Connect to HTB")
r = s.get(f"{BASE}/api/ctflab/vpn", headers={"CSRF-Token": csrf})
if "BEGIN" in r.text:
    print(f"2. Download VPN: OK ({r.text.count('BEGIN')} certs, {len(r.text)} bytes)")
else:
    print(f"2. Download VPN: FAIL - {r.text[:100]}")

# Start Machine
csrf = re.search(r"'csrfNonce': \"([a-f0-9]+)\"", s.get(f"{BASE}/challenges").text).group(1)
r = s.post(f"{BASE}/api/ctflab/instances", json={"challenge_id": 1}, headers={"CSRF-Token": csrf})
if r.status_code == 200:
    data = r.json()
    ip = data.get("container_ip", "?")
    status = data.get("status", "?")
    inst_id = data.get("id", "?")
    print(f"3. Start Machine: IP={ip}, Status={status}, ID={inst_id}")
else:
    print(f"3. Start Machine: FAIL HTTP {r.status_code} - {r.text[:100]}")
    exit(1)

time.sleep(3)

# Get instance status
csrf = re.search(r"'csrfNonce': \"([a-f0-9]+)\"", s.get(f"{BASE}/challenges").text).group(1)
r = s.get(f"{BASE}/api/ctflab/instances", headers={"CSRF-Token": csrf})
inst = r.json().get("instance")
if inst:
    print(f"4. Instance Status: {inst['status']}, IP: {inst['container_ip']}")
else:
    print("4. Instance Status: None")

# Submit flag
csrf = re.search(r"'csrfNonce': \"([a-f0-9]+)\"", s.get(f"{BASE}/challenges").text).group(1)
r = s.post(f"{BASE}/api/v1/challenges/attempt", json={"challenge_id": 1, "submission": "NBL01{test}"}, headers={"CSRF-Token": csrf})
print(f"5. Submit Flag: {r.json()['data']['status']} - {r.json()['data'].get('message','')}")

# Stop Machine
csrf = re.search(r"'csrfNonce': \"([a-f0-9]+)\"", s.get(f"{BASE}/challenges").text).group(1)
r = s.delete(f"{BASE}/api/ctflab/instances/{inst_id}", headers={"CSRF-Token": csrf, "Content-Type": "application/json"})
if r.status_code == 200:
    print(f"6. Stop Machine: {r.json()}")
else:
    print(f"6. Stop Machine: HTTP {r.status_code} - {r.text[:100]}")

print("\n=== TEST COMPLETE ===")
