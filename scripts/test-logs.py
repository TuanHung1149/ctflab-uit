#!/usr/bin/env python3
"""Test logging functionality."""
import re, time, json, requests

BASE = "http://localhost:8080"
s = requests.Session()

def csrf():
    return re.search(r"'csrfNonce': \"([a-f0-9]+)\"", s.get(f"{BASE}/challenges").text).group(1)

# Login tester
r = s.get(f"{BASE}/login")
nonce = re.search(r'id="nonce".*?value="([^"]+)"', r.text).group(1)
s.post(f"{BASE}/login", data={"name": "tester", "password": "test123", "nonce": nonce}, allow_redirects=True)

# VPN download
s.get(f"{BASE}/api/ctflab/vpn")
print("1. VPN downloaded")

# Start
r = s.post(f"{BASE}/api/ctflab/instances", json={"challenge_id": 8}, headers={"CSRF-Token": csrf()})
d = r.json()
inst = d.get("id")
print(f"2. Start: IP={d.get('container_ip')}, ID={inst}")
time.sleep(3)

# Reset
if inst:
    r = s.post(f"{BASE}/api/ctflab/instances/{inst}/reset", json={}, headers={"CSRF-Token": csrf()})
    print(f"3. Reset: {r.json()}")

    # Stop
    r = s.delete(f"{BASE}/api/ctflab/instances/{inst}", headers={"CSRF-Token": csrf(), "Content-Type": "application/json"})
    print(f"4. Stop: {r.json()}")

# Admin view logs
s2 = requests.Session()
r = s2.get(f"{BASE}/login")
nonce = re.search(r'id="nonce".*?value="([^"]+)"', r.text).group(1)
s2.post(f"{BASE}/login", data={"name": "admin", "password": "admin123", "nonce": nonce}, allow_redirects=True)

r = s2.get(f"{BASE}/api/ctflab/admin/logs")
logs = r.json().get("logs", [])
print(f"\n=== ADMIN LOGS ({len(logs)} entries) ===")
for l in logs:
    print(f"  {l['created_at'][:19]}  {(l.get('username') or '?'):<10}  {l['action']:<20}  {l.get('detail') or '-'}")
