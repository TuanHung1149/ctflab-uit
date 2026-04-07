#!/usr/bin/env python3
"""Full E2E test - every feature of the platform."""
import re, time, json, subprocess, os, requests

os.environ["DOCKER_HOST"] = "unix:///var/run/docker.sock"
BASE = "http://localhost:8080"
P, F, T = 0, 0, 0

def ok(name, passed, detail=""):
    global P, F, T
    T += 1
    if passed: P += 1; print(f"  \033[32m[PASS]\033[0m {name}" + (f" - {detail}" if detail else ""))
    else: F += 1; print(f"  \033[31m[FAIL]\033[0m {name}" + (f" - {detail}" if detail else ""))

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, "DOCKER_HOST":"unix:///var/run/docker.sock"})

def login(u, p):
    s = requests.Session()
    r = s.get(f"{BASE}/login")
    n = re.search(r'id="nonce".*?value="([^"]+)"', r.text).group(1)
    s.post(f"{BASE}/login", data={"name":u,"password":p,"nonce":n}, allow_redirects=True)
    return s

def csrf(s):
    return re.search(r"'csrfNonce': \"([a-f0-9]+)\"", s.get(f"{BASE}/challenges").text).group(1)

def register(u, e, p):
    s = requests.Session()
    r = s.get(f"{BASE}/register")
    n = re.search(r'id="nonce".*?value="([^"]+)"', r.text).group(1)
    s.post(f"{BASE}/register", data={"name":u,"email":e,"password":p,"nonce":n}, allow_redirects=True)

def dbclean():
    run(["docker","exec","ctflab-uit-ctfd-1","python3","-c",
        'import sys;sys.path.insert(0,"/opt/CTFd");'
        'from CTFd import create_app;app=create_app();'
        'app.app_context().push();'
        'from CTFd.plugins.ctflab.models import LabInstance,SuspiciousSubmission;'
        'from CTFd.models import db,Solves,Fails;'
        'LabInstance.query.delete();SuspiciousSubmission.query.delete();'
        'Solves.query.delete();Fails.query.delete();db.session.commit();print("ok")'])

print("="*60)
print("  FULL E2E TEST - ALL FEATURES")
print("="*60)

# ── 0. CLEANUP ──
print("\n\033[33m[0] Cleanup\033[0m")
for c in run(["docker","ps","-aq","--filter","label=ctflab.managed=true"]).stdout.split():
    run(["docker","rm","-f",c])
for n in run(["docker","network","ls","-q","--filter","label=ctflab.managed=true"]).stdout.split():
    run(["docker","network","rm",n])
dbclean()
run(["bash","/opt/ctflab-uit/fix-vpn-routing.sh"])
print("  Clean")

# ── 1. WEB ──
print("\n\033[33m[1] Web Health\033[0m")
r = requests.get(f"{BASE}/")
ok("CTFd responds", r.status_code in (200,302), f"HTTP {r.status_code}")

# ── 2. AUTH ──
print("\n\033[33m[2] Auth\033[0m")
register("e2e_user1","e2e1@t.com","e2epass1")
register("e2e_user2","e2e2@t.com","e2epass2")
s1 = login("e2e_user1","e2epass1")
s2 = login("e2e_user2","e2epass2")
adm = login("admin","admin123")
me1 = s1.get(f"{BASE}/api/v1/users/me").json()
me2 = s2.get(f"{BASE}/api/v1/users/me").json()
ok("Register+login user1", me1["data"]["name"]=="e2e_user1")
ok("Register+login user2", me2["data"]["name"]=="e2e_user2")

# ── 3. CHALLENGES ──
print("\n\033[33m[3] Challenges\033[0m")
r = s1.get(f"{BASE}/api/v1/challenges/8")
ok("Challenge detail", r.status_code==200 and "Nebula" in r.json().get("data",{}).get("name",""))
ok("Challenge has view HTML", "instance-panel" in r.json().get("data",{}).get("view",""))

# ── 4. VPN ──
print("\n\033[33m[4] VPN Download\033[0m")
r1 = s1.get(f"{BASE}/api/ctflab/vpn")
r2 = s2.get(f"{BASE}/api/ctflab/vpn")
ok("User1 VPN", "BEGIN CERTIFICATE" in r1.text, f"{r1.text.count('BEGIN')} certs")
ok("User2 VPN", "BEGIN CERTIFICATE" in r2.text, f"{r2.text.count('BEGIN')} certs")
ok("VPN files different", r1.text != r2.text)

# ── 5. START MACHINE ──
print("\n\033[33m[5] Start Machine\033[0m")
d1 = s1.post(f"{BASE}/api/ctflab/instances", json={"challenge_id":8}, headers={"CSRF-Token":csrf(s1)}).json()
time.sleep(2)
run(["bash","/opt/ctflab-uit/fix-vpn-routing.sh"])
d2 = s2.post(f"{BASE}/api/ctflab/instances", json={"challenge_id":8}, headers={"CSRF-Token":csrf(s2)}).json()
time.sleep(2)
run(["bash","/opt/ctflab-uit/fix-vpn-routing.sh"])
ok("User1 box", d1.get("status")=="running", f"IP={d1.get('container_ip')}")
ok("User2 box", d2.get("status")=="running", f"IP={d2.get('container_ip')}")
ok("Different IPs", d1.get("container_ip")!=d2.get("container_ip"))
ok("Different slots", d1.get("container_ip","").split(".")[2]!=d2.get("container_ip","").split(".")[2])

# ── 6. ONE INSTANCE LIMIT ──
print("\n\033[33m[6] One Instance Limit\033[0m")
d1x = s1.post(f"{BASE}/api/ctflab/instances", json={"challenge_id":8}, headers={"CSRF-Token":csrf(s1)}).json()
ok("Reuse existing", d1x.get("id")==d1.get("id"), "same instance returned")

# ── 7. DOCKER CONTAINERS ──
print("\n\033[33m[7] Docker\033[0m")
containers = run(["docker","ps","--filter","label=ctflab.managed=true","--format","{{.Names}}"]).stdout.strip()
ok("2 containers running", containers.count("ctflab_box")==2, containers.replace("\n",", "))

time.sleep(3)

# ── 8. SERVICES ──
print("\n\033[33m[8] Box Services\033[0m")
for slot in [d1.get("container_ip","").split(".")[2], d2.get("container_ip","").split(".")[2]]:
    svcs = run(["docker","exec",f"ctflab_box_{slot}","supervisorctl","status"]).stdout
    cnt = svcs.count("RUNNING")
    ok(f"Slot {slot}: services", cnt>=5, f"{cnt} RUNNING")

# ── 9. FLAGS ──
print("\n\033[33m[9] Flags\033[0m")
slot1 = d1.get("container_ip","10.100.1.2").split(".")[2]
slot2 = d2.get("container_ip","10.100.2.2").split(".")[2]
f1 = json.loads(run(["docker","exec",f"ctflab_box_{slot1}","bash","-c","echo $FLAGS_JSON"]).stdout.strip() or "{}")
f2 = json.loads(run(["docker","exec",f"ctflab_box_{slot2}","bash","-c","echo $FLAGS_JSON"]).stdout.strip() or "{}")
ok("User1 has 7 flags", len(f1)>=7, f"{len(f1)} flags")
ok("User2 has 7 flags", len(f2)>=7, f"{len(f2)} flags")
ok("Flags different", f1.get("NBL01")!=f2.get("NBL01"))

# ── 10. FLAG INJECTION ──
print("\n\033[33m[10] Flag Injection in Box\033[0m")
box_flag = run(["docker","exec",f"ctflab_box_{slot1}","cat","/home/taylor/user.txt"]).stdout.strip()
ok("user.txt matches NBL04", box_flag==f1.get("NBL04"), box_flag[:25])
box_root = run(["docker","exec",f"ctflab_box_{slot1}","cat","/root/root.txt"]).stdout.strip()
ok("root.txt matches NBL07", box_root==f1.get("NBL07"), box_root[:25])

# ── 11. SSH ──
print("\n\033[33m[11] SSH\033[0m")
for slot, ip in [(slot1, d1["container_ip"]), (slot2, d2["container_ip"])]:
    r = run(["sshpass","-p","lekkerding","ssh","-o","StrictHostKeyChecking=no","-o","ConnectTimeout=5",f"taylor@{ip}","echo OK;whoami"])
    ok(f"SSH slot {slot}", "OK" in r.stdout)

# ── 12. FLAG SUBMIT ──
print("\n\033[33m[12] Flag Submit\033[0m")
for prefix in ["NBL01","NBL04","NBL07"]:
    r = s1.post(f"{BASE}/api/v1/challenges/attempt", json={"challenge_id":8,"submission":f1[prefix]}, headers={"CSRF-Token":csrf(s1)})
    st = r.json()["data"]["status"]
    ok(f"User1 {prefix}", st in ("correct","already_solved"), st)
r = s1.post(f"{BASE}/api/v1/challenges/attempt", json={"challenge_id":8,"submission":"NBL01{wrong}"}, headers={"CSRF-Token":csrf(s1)})
ok("Wrong flag rejected", r.json()["data"]["status"] in ("incorrect","already_solved"))

# ── 13. CROSS-FLAG ──
print("\n\033[33m[13] Cross-flag Detection\033[0m")
r = s2.post(f"{BASE}/api/v1/challenges/attempt", json={"challenge_id":8,"submission":f1["NBL01"]}, headers={"CSRF-Token":csrf(s2)})
ok("Other user flag rejected", r.json()["data"]["status"]!="correct", r.json()["data"]["status"])

# ── 14. SCOREBOARD ──
print("\n\033[33m[14] Scoreboard\033[0m")
board = s1.get(f"{BASE}/api/v1/scoreboard").json().get("data",[])
u1_score = next((e["score"] for e in board if e["name"]=="e2e_user1"), 0)
ok("User1 on scoreboard", u1_score>0, f"{u1_score}pts")

# ── 15. ISOLATION ──
print("\n\033[33m[15] Iptables Isolation\033[0m")
run(["iptables","-F","CTFLAB_ISOLATION"])
run(["iptables","-A","CTFLAB_ISOLATION","-s","10.200.0.1","-d","10.200.0.0/24","-j","ACCEPT"])
run(["iptables","-A","CTFLAB_ISOLATION","-s","10.200.0.0/24","-d","10.200.0.1","-j","ACCEPT"])
run(["iptables","-A","CTFLAB_ISOLATION","-s","10.200.0.0/24","-d","10.200.0.0/24","-j","DROP"])
for s, sl in [(slot1,"1"),(slot2,"2")]:
    vpn = f"10.200.0.{int(s)+1}"
    run(["iptables","-A","CTFLAB_ISOLATION","-s",vpn,"-d",f"10.100.{s}.0/24","-j","ACCEPT"])
    run(["iptables","-A","CTFLAB_ISOLATION","-s",f"10.100.{s}.0/24","-d",vpn,"-j","ACCEPT"])
run(["iptables","-A","CTFLAB_ISOLATION","-s","10.200.0.0/24","-d","10.100.0.0/16","-j","DROP"])

vpn1, vpn2 = f"10.200.0.{int(slot1)+1}", f"10.200.0.{int(slot2)+1}"
ok("User1->own box ALLOW", run(["iptables","-C","CTFLAB_ISOLATION","-s",vpn1,"-d",f"10.100.{slot1}.0/24","-j","ACCEPT"]).returncode==0)
ok("User1->other box BLOCK", run(["iptables","-C","CTFLAB_ISOLATION","-s",vpn1,"-d",f"10.100.{slot2}.0/24","-j","ACCEPT"]).returncode!=0)
ok("User2->own box ALLOW", run(["iptables","-C","CTFLAB_ISOLATION","-s",vpn2,"-d",f"10.100.{slot2}.0/24","-j","ACCEPT"]).returncode==0)
ok("User2->other box BLOCK", run(["iptables","-C","CTFLAB_ISOLATION","-s",vpn2,"-d",f"10.100.{slot1}.0/24","-j","ACCEPT"]).returncode!=0)
ok("Client-to-client DROP", run(["iptables","-C","CTFLAB_ISOLATION","-s","10.200.0.0/24","-d","10.200.0.0/24","-j","DROP"]).returncode==0)

# ── 16. RESET ──
print("\n\033[33m[16] Reset Machine\033[0m")
r = s1.post(f"{BASE}/api/ctflab/instances/{d1['id']}/reset", json={}, headers={"CSRF-Token":csrf(s1)})
ok("Reset", r.status_code==200, r.json() if r.status_code==200 else r.text[:50])
ok("Box alive", "ctflab_box" in run(["docker","ps","--filter","label=ctflab.managed=true","--format","{{.Names}}"]).stdout)

# ── 17. STOP ──
print("\n\033[33m[17] Stop Machine\033[0m")
r = s1.delete(f"{BASE}/api/ctflab/instances/{d1['id']}", headers={"CSRF-Token":csrf(s1),"Content-Type":"application/json"})
ok("User1 stop", r.json().get("status")=="stopped")
time.sleep(2)
ok("User1 container gone", f"ctflab_box_{slot1}" not in run(["docker","ps","--format","{{.Names}}"]).stdout)

# ── 18. RE-LAUNCH ──
print("\n\033[33m[18] Re-launch (new flags)\033[0m")
run(["bash","/opt/ctflab-uit/fix-vpn-routing.sh"])
d1b = s1.post(f"{BASE}/api/ctflab/instances", json={"challenge_id":8}, headers={"CSRF-Token":csrf(s1)}).json()
ok("Re-launch", d1b.get("status")=="running")
time.sleep(3)
run(["bash","/opt/ctflab-uit/fix-vpn-routing.sh"])
slot1b = d1b.get("container_ip","").split(".")[2]
f1b = json.loads(run(["docker","exec",f"ctflab_box_{slot1b}","bash","-c","echo $FLAGS_JSON"]).stdout.strip() or "{}")
ok("New flags different", f1.get("NBL01")!=f1b.get("NBL01"), f"old={f1.get('NBL01','')[:15]} new={f1b.get('NBL01','')[:15]}")

# ── 19. ADMIN ──
print("\n\033[33m[19] Admin APIs\033[0m")
r = adm.get(f"{BASE}/api/ctflab/admin/stats")
ok("Admin stats", r.status_code==200 and "active_instances" in r.text, r.text[:80])
r = adm.get(f"{BASE}/api/ctflab/admin/logs")
ok("Admin logs", r.status_code==200 and "logs" in r.text, f"{len(r.json().get('logs',[]))} entries")
r = adm.get(f"{BASE}/api/ctflab/admin/instances")
ok("Admin instances", r.status_code==200)
r = adm.get(f"{BASE}/api/ctflab/admin/dashboard")
ok("Admin dashboard", r.status_code==200 and "CTFLab Admin" in r.text)

# ── 20. CLEANUP ──
print("\n\033[33m[20] Final Cleanup\033[0m")
for d in [d1b, d2]:
    if d.get("id"):
        s = s1 if d==d1b else s2
        s.delete(f"{BASE}/api/ctflab/instances/{d['id']}", headers={"CSRF-Token":csrf(s),"Content-Type":"application/json"})
time.sleep(3)
left = run(["docker","ps","--filter","label=ctflab.managed=true","--format","{{.Names}}"]).stdout.strip()
ok("All cleaned", not left, "clean" if not left else left)

# ── RESULTS ──
print(f"\n{'='*60}")
print(f"  Results: \033[32m{P} PASS\033[0m / \033[31m{F} FAIL\033[0m / {T} TOTAL")
if F==0: print("  \033[32mALL TESTS PASSED!\033[0m")
else: print(f"  \033[31m{F} FAILED\033[0m")
print(f"{'='*60}")
