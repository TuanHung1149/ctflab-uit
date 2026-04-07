#!/usr/bin/env python3
"""Create EasyBox challenge on CTFd."""
import re, requests
BASE = "http://localhost:8080"
s = requests.Session()
r = s.get(f"{BASE}/login")
nonce = re.search(r'id="nonce".*?value="([^"]+)"', r.text).group(1)
s.post(f"{BASE}/login", data={"name": "admin", "password": "admin123", "nonce": nonce}, allow_redirects=True)
csrf = re.search(r"'csrfNonce': \"([a-f0-9]+)\"", s.get(f"{BASE}/admin/challenges/new").text).group(1)
r = s.post(f"{BASE}/api/v1/challenges", json={
    "name": "EasyBox - Beginner",
    "category": "Machine",
    "description": "Simple beginner box.\n\nSSH: `hacker@<IP>` password: `hacker123`\n\nFind `user.txt` (FLAG01) and `root.txt` (FLAG02).",
    "value": 200,
    "type": "ctflab",
    "state": "visible",
    "docker_image": "ctflab/easybox",
    "flag_prefix": "FLAG",
    "instance_timeout": 14400,
    "box_env_json": "{}"
}, headers={"CSRF-Token": csrf})
d = r.json().get("data", {})
print(f"Created: {d.get('name')} (id={d.get('id')}, {d.get('value')}pts)")
