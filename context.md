# CTFLab UIT - Project Context

**GitHub**: https://github.com/TuanHung1149/ctflab-uit (PUBLIC)
**VPS**: 152.42.233.178 (8GB RAM, Ubuntu 24.04)
**Web**: http://152.42.233.178:8080 | Admin: admin / admin123
**Mon hoc**: NT140 - UIT | **Giang vien**: Thay Khoa
**Last updated**: 2026-04-10

---

## 1. Platform La Gi?

CTF Lab giong **HackTheBox** cho sinh vien UIT:
- Moi sinh vien **connect VPN** -> **SSH vao box** -> **hack** -> **submit flag**
- Moi nguoi co **box rieng**, **flag rieng**, **mang rieng** (co lap hoan toan)
- 1 IP public phuc vu **40 users** dong thoi (chi dung port 1194 + 8080)

### Flow (y chang HTB):
```
1. Dang ky tren CTFd web
2. Download WireGuard .conf (1 file per user, dung mai)
3. Linux: sudo wg-quick up ./username.conf | Windows/Mac: WireGuard app -> Import -> Activate
4. Click "Start Machine" tren web -> box spawn -> IP hien thi
5. ssh taylor@10.100.{slot}.2 (password: lekkerding)
6. Hack: tim 7 flags (NBL01-NBL07)
7. Submit flag tren web -> scoreboard cap nhat
8. "Stop Machine" -> box bi xoa hoan toan
```

---

## 2. Kien Truc

```
Internet
  |
  +-- Port 8080: CTFd (web UI, challenge mgmt, scoreboard, flag submit)
  +-- Port 51820: WireGuard (40 users share 1 port)
        |
        User1 (10.200.0.2) --> [iptables ACCEPT] --> Docker net 10.100.1.0/24 --> Box1
        User2 (10.200.0.3) --> [iptables ACCEPT] --> Docker net 10.100.2.0/24 --> Box2
        User1 --> Docker net 10.100.2.0/24 --> [iptables DROP] (BLOCKED!)
```

### Tech Stack:
| Component | Technology |
|-----------|------------|
| Web UI | CTFd 3.7.1 + custom plugin "ctflab" |
| Database | MariaDB 10.11 |
| Cache | Redis 7 |
| Container | Docker (1 container per user per box) |
| VPN | WireGuard (port 51820/udp) |
| Isolation | iptables CTFLAB_ISOLATION chain + Docker bridge networks |

---

## 3. File Structure

```
ctflab-uit/
├── docker-compose.yml          # CTFd + MariaDB + Redis
├── fix-vpn-routing.sh          # Cron moi 30s: fix Docker nft + rebuild iptables isolation
├── deploy.sh                   # 1-command deploy (Docker + OpenVPN + CTFd)
├── ctfd/
│   ├── Dockerfile              # CTFd 3.7.1 + Docker CLI + plugin
│   └── plugins/ctflab/         # Custom CTFd plugin
│       ├── __init__.py          # Plugin loader + expire thread
│       ├── models.py            # CTFLabChallenge, LabInstance, SuspiciousSubmission, ActivityLog
│       ├── challenge_type.py    # Challenge type "ctflab" + flag validation + cross-flag detection
│       ├── routes.py            # API: instances, vpn, admin (logs, stats, suspicious, dashboard)
│       ├── docker_utils.py      # DockerManager: create/destroy/reset containers + VPN config
│       ├── flag_utils.py        # Random flag generator
│       ├── expire.py            # Auto-expire thread (moi 60s destroy expired instances)
│       └── assets/              # view.html/js, create.html/js, update.html/js
├── boxes/
│   ├── infinity/               # "Nebula Nexus" - 7 challenge box (2120 files)
│   │   ├── Dockerfile          # Ubuntu 22.04 + SSH + bind9 + nginx + php + python + supervisor
│   │   ├── docker/
│   │   │   ├── entrypoint.sh   # chpasswd + inject-flags + reset-state + supervisord
│   │   │   ├── bootstrap.sh    # Build-time setup (users, services, SSH kex fix)
│   │   │   ├── inject-flags.py # Runtime: replace flags from FLAGS_JSON env
│   │   │   └── supervisord.conf # 6 services: sshd, chall1, named, nginx, php, maltrail
│   │   └── chall1-7/           # Challenge source code
│   └── easybox/                # Example simple box (SSH + 2 flags)
├── wireguard/
│   └── setup-server.sh         # 1-time: install WireGuard + generate server keypair
├── scripts/
│   ├── setup-wg-user.sh        # Generate per-user WireGuard keypair + .conf
│   ├── update-wg-route.sh      # Update WireGuard AllowedIPs when box spawn/destroy
│   ├── seed-challenges.sh      # Create challenges in CTFd via API
│   ├── test-e2e-full.py        # 45-test full E2E test
│   ├── test-isolation.py       # 3-user cross-access isolation test
│   └── test-htb-flow.py        # HTB flow test (login->vpn->start->ssh->flag->stop)
├── backend/                    # (Backup) Custom FastAPI backend
└── frontend/                   # (Backup) Custom Next.js frontend
```

---

## 4. Box "Nebula Nexus" - 7 Challenges

| # | Flag | Points | Technique | Hint |
|---|------|--------|-----------|------|
| 1 | NBL01 | 100 | nc localhost 7171 -> solve math quiz | Port 7171 |
| 2 | NBL02 | 100 | dig axfr + TXT record | DNS port 53 |
| 3 | NBL03 | 150 | TinyFileManager exploit | HTTP port 80, subdomain inffile123 |
| 4 | NBL04 | 100 | cat /home/taylor/user.txt | SSH as taylor |
| 5 | NBL05 | 200 | Maltrail CVE RCE -> shell as brown | Port 8338 |
| 6 | NBL06 | 200 | SUID /usr/local/bin/sysinfo -> john | Privesc brown->john |
| 7 | NBL07 | 300 | sudo /opt/chall7/rootnow buffer overflow | Privesc john->root |

**Users**: taylor/lekkerding, brown/AI56JSPUac43v7MWkXdG, john/S6V1frkRJLo40GKuglzp
**Services**: sshd(22), nginx(80), bind9(53), python-bot(7171), maltrail(8338), php(8081)

---

## 5. Security & Isolation

### VPN Isolation (iptables CTFLAB_ISOLATION chain):
```
Rule 1-2: ACCEPT server keepalive (10.200.0.1)
Rule 3:   DROP client-to-client (10.200.0.0/24 -> 10.200.0.0/24)
Rule 4-5: ACCEPT slot1 VPN (10.200.0.2) <-> Docker net (10.100.1.0/24)
Rule 6-7: ACCEPT slot2 VPN (10.200.0.3) <-> Docker net (10.100.2.0/24)
...
Last:     DROP all other VPN -> Docker (10.200.0.0/24 -> 10.100.0.0/16)
```
- WireGuard peers have AllowedIPs restricted to their own Docker subnet
- Rules tu dong rebuild moi 30 giay (cron + fix-vpn-routing.sh)
- Per-user fixed slot: username -> slot mapping in /etc/wireguard/slots.json

### Per-Instance:
- Flags random moi khi Start Machine (inject-flags.py)
- Stop Machine = docker rm -f (xoa sach container + network)
- Start lai = container moi, flags moi, state moi
- Max 1 instance per user

### Anti-Cheat:
- Submit flag cua nguoi khac -> **REJECTED + logged** (SuspiciousSubmission model)
- Admin thay: ai submit, flag cua ai, thoi gian

---

## 6. Admin

### Web Admin:
- `/admin` - CTFd built-in (users, challenges, submissions, config)
- `/api/ctflab/admin/dashboard` - **Custom dashboard** (stats, instances, logs, container logs)

### Admin APIs:
| Endpoint | Chuc nang |
|----------|-----------|
| GET /api/ctflab/admin/stats | Thong ke: active instances, users, solves, fails, suspicious |
| GET /api/ctflab/admin/instances | Danh sach instances dang chay |
| GET /api/ctflab/admin/instances/history | Lich su tat ca instances |
| GET /api/ctflab/admin/logs | Activity logs (filterable: ?action=start_machine) |
| GET /api/ctflab/admin/suspicious | Flag sharing alerts |
| GET /api/ctflab/admin/container-logs/{slot} | Docker logs cua container |
| GET /api/ctflab/admin/dashboard | Web dashboard page |

### Activity Logged:
- vpn_download, start_machine, stop_machine, reset_machine (user, IP, timestamp, detail)

---

## 7. Deploy

### VPS moi (3 lenh):
```bash
git clone https://github.com/TuanHung1149/ctflab-uit.git
cd ctflab-uit
sudo bash deploy.sh
```
→ Auto install Docker + WireGuard + build images + start CTFd

### Them box moi:
```bash
# 1. Tao folder boxes/tenbox/ voi Dockerfile + entrypoint
# 2. Build: docker build -t ctflab/tenbox ./boxes/tenbox/
# 3. CTFd Admin -> Challenges -> Create -> type "ctflab" -> docker_image: ctflab/tenbox
```

### Cau truc box toi thieu:
```dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y openssh-server supervisor
RUN useradd -m -s /bin/bash hacker && echo "hacker:password" | chpasswd
# ... cai challenge services ...
COPY docker/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

---

## 8. Test Results (2026-04-07)

### Full E2E: 45/45 PASS
```
Web, Auth, Challenges, VPN Download, Start Machine, Docker, Services,
Flags (7 random), Flag Injection, SSH, Flag Submit, Cross-flag Detection,
Scoreboard, Iptables Isolation, Reset, Stop, Re-launch, Admin APIs, Dashboard
```

### Isolation: 22/23 PASS (3 users, 3 boxes)
```
User1->Box1: ALLOW    User1->Box2: BLOCK    User1->Box3: BLOCK
User2->Box1: BLOCK    User2->Box2: ALLOW    User2->Box3: BLOCK
User3->Box1: BLOCK    User3->Box2: BLOCK    User3->Box3: ALLOW
Flags: all different  Client-to-client: BLOCKED
```

### VPN + SSH verified:
- VPN connect 28ms, ping box OK, SSH OK (taylor@10.100.x.2)
- `sudo ip route add` bypass: BLOCKED by server iptables

---

## 9. Cac Van De Da Fix

| Van de | Nguyen nhan | Fix |
|--------|-------------|-----|
| CTFd plugin crash | get_current_user() ngoai request context | try/except wrap |
| Challenge modal trong | view.html dung `<script x-template>` | Bo script wrapper |
| Challenge ko click duoc | view.js dung `CTFd.plugin.run()` cu | Rewrite dung `CTFd._internal.challenge` |
| SSH hang qua VPN | Post-quantum kex packet qua lon | Force curve25519-sha256 trong sshd_config |
| VPN khong route toi Docker | rp_filter kernel drop packets | sysctl rp_filter=0 persistent |
| Docker nft drop VPN traffic | Docker raw PREROUTING drop rule | Cron xoa nft drops moi 30s |
| VPN route bypass (ip route add) | Khong co server-side check | iptables CTFLAB_ISOLATION per-slot |
| Client-to-client VPN | OpenVPN client-to-client enabled | Remove directive + iptables DROP |
| Flags khong random | inject-flags.sh chua goi | Them vao entrypoint.sh |
| Password SSH ko dung | chpasswd trong build khong persist | Them chpasswd vao entrypoint |

---

## 10. Thay Khoa Noi Gi

```
- "The same HTB" - platform giong Hack The Box
- Dung CTFd lam frontend
- Chi can Docker provider, khong can VM
- Moi dua 1 box voi flag khac nhau
- OpenVPN de co lap network
- 1 IP public, 10k ports
- Co san box infinity (docker-compose)
- Fake Provider = gia lap start/stop (de dev/test, lam sau)
- Thay co VPS (private, 1 IP public)
```

---

*Cap nhat: 2026-04-07 | Tao boi Claude Code*

---

## 11. MIGRATION: OpenVPN → WireGuard (2026-04-08)

### Why:
- OpenVPN 2.7_rc2 tren WSL2: `write to TUN/TAP: fd=-1` (tun device broken)
- WireGuard hoat dong tren tat ca: WSL2, Windows, Linux, Mac
- Config don gian hon (1 file .conf, khong can PKI/CA)
- Performance tot hon, kernel-level

### What changed:
- Port 1194/udp (OpenVPN) → **51820/udp** (WireGuard)
- `.ovpn` files → `.conf` files
- EasyRSA PKI → WireGuard keypairs (wg genkey/pubkey)
- CCD routing → WireGuard AllowedIPs
- Per-user fixed slot (slots.json) — config download 1 lan dung mai
- IP scheme **giu nguyen**: 10.200.0.0/24 (VPN), 10.100.x.0/24 (Docker)
- iptables CTFLAB_ISOLATION **giu nguyen** 100%

---

## 12. VPN ENDPOINT FIX: pfSense / HAProxy (2026-04-10)

### Van de:
- VPS 152.42.233.178 co WireGuard chay tren port **51820/udp** (WireGuard default)
- Nhung sinh vien download VPN config nhan duoc endpoint `152.42.233.178:51820`
- Thay te: port 51820 **bi block** boi firewall truong / mang truong (chi cho 80/443/1194)
- Thuc te traffic VPN di qua **pfSense HAProxy** tren port **11194** → forward vao 51820

### Fix:
- Doi WG_SERVER_IP = `45.122.249.68` (pfSense public IP)
- Doi WG_PORT = `11194` (HAProxy listener port)
- Files da sua:
  - `ctfd/plugins/ctflab/routes.py`: default `SERVER_IP → 45.122.249.68`, them `WG_PORT=11194`
  - `ctfd/plugins/ctflab/host_ops.py`: `ensure_user_vpn()` nhan `wg_port` param
  - `scripts/setup-wg-user.sh`: nhan `$3` optional wg_port, default `45.122.249.68:11194`
- Commit: `a2be93b` — "fix: update WireGuard VPN endpoint to 45.122.249.68:11194"

### Ket qua:
- Sinh vien tai VPN config nhan endpoint: `45.122.249.68:11194`
- pfSense HAProxy nhan tren 11194/udp → forward 152.42.233.178:51820
- Kiem tra E2E 2 player dong thoi: ca 2 connect duoc, giai duoc cac challenge

---

## 13. MULTI-AGENT E2E TEST (2026-04-10)

### Chay 3 agent song song de kiem tra platform:

**Agent Alpha** (alpha_player1, user_id=24):
- Dang ky → login → tai VPN → start box → lay flags → submit 4 challenge
- Box slot=1, IP=10.100.1.2
- Flags: NBL01{cCuaiNHb5n5wzjBej8}, NBL02{JvzuvPR1OAilEF3mxV}, NBL03{y2tQOWkxmhFheL7wUw}, NBL04{XOnVgkLKwRbhccg8dQ}
- Ket qua: 4/4 CORRECT, score=450pts

**Agent Beta** (beta_player1, user_id=23):
- Chay song song voi Alpha
- Box slot=2, IP=10.100.2.2
- Flags KHAC HOAN TOAN so voi Alpha:
  NBL01{FYuoFE9ceQR1JwuUbH}, NBL02{Wubo5AtYtVdFBNrFa3}, NBL03{enjdPHuF0Uoooct567}, NBL04{ydZaBZ4lUTz6mqLoTz}
- Ket qua: 4/4 CORRECT, score=450pts

**Agent Observer** (admin):
- Giam sat 3 rounds trong suot qua trinh Alpha+Beta chay
- DB vs Docker consistency: ✅ (container ID khop)
- WireGuard peers: 14 total, 4 active handshake
- Isolation: ctflab_box_1 (slot1) va ctflab_box_2 (slot2) tren mang rieng biet
- Khong co loi trong CTFd logs, khong co error

### Ket luan test:
- ✅ Flag per-instance: moi box co flags khac nhau hoan toan
- ✅ Isolation: 2 box chay dong thoi, mang rieng biet
- ✅ VPN endpoint pfSense 45.122.249.68:11194: hoat dong
- ✅ DB consistency: container_id trong DB khop Docker
- ✅ CSRF handling: POST /api/ctflab/instances can CSRF-Token header
- ✅ Suspicious detection: ghi nhan khi submit flag cua nguoi khac
- ✅ Total instances sau test: 108 (cong don tu truoc)

---

## 14. CHALLENGE SETUP DAY DU (2026-04-10)

### Truoc day chi co 4/7 challenge tren CTFd:
- id=17 DNS Enumeration (NBL02) — 100pts
- id=18 Web Exploitation (NBL03) — 150pts
- id=19 Credential Access (NBL04) — 100pts
- id=22 Network Service Recon (NBL01) — 100pts

### Da them 3 challenge con thieu:
- id=24 **Maltrail RCE** (NBL05) — 200pts — Exploit Maltrail 0.53 port 8338 → shell as brown
- id=25 **SUID Privilege Escalation** (NBL06) — 200pts — SUID binary sysinfo → leo quyen len john
- id=26 **Buffer Overflow** (NBL07) — 300pts — /usr/local/bin/rootnow BOF → root

### Tat ca 7 challenge day du, category = "Nebula Nexus", docker_image = ctflab/infinity

### Chi tiet cac challenge:
| CTFd ID | Flag | Diem | Technique | Service/Port |
|---------|------|------|-----------|--------------|
| 22 | NBL01 | 100 | TCP connect port 7171, giai phep tinh | Python server :7171 |
| 17 | NBL02 | 100 | dig axfr nebula.lab → tim subdomain unk → dig TXT unk.nebula.lab | BIND9 :53 |
| 18 | NBL03 | 150 | Exploit TinyFileManager doc /opt/chall3/tinyfilemanager/infinity.txt | Nginx :80, vhost inffile123.nebula.lab |
| 19 | NBL04 | 100 | SSH as taylor (pw hien tren UI) → cat ~/user.txt | SSH :22 |
| 24 | NBL05 | 200 | CVE Maltrail RCE → shell as brown → cat /opt/chall5/flag.txt | Maltrail :8338 |
| 25 | NBL06 | 200 | Binary sysinfo SUID → leo len john → cat /home/john/flag.txt | SSH shell |
| 26 | NBL07 | 300 | BOF rootnow → root → cat /root/root.txt | SSH shell |

### Luong leo quyen:
```
(network) → taylor (SSH password tren UI) → brown (Maltrail RCE) → john (SUID sysinfo) → root (BOF rootnow)
```

---

## 15. DNS CHALLENGE CHI TIET (NBL02)

### Cach giai:
```bash
# B1: Zone transfer zone chinh → thay subdomain "unk" an
dig axfr nebula.lab @<box_ip>
# → thay dong: unk.nebula.lab.  IN  A  127.0.0.1

# B2: Zone transfer zone unk (allow-transfer: none) - khong duoc
dig axfr unk.nebula.lab @<box_ip>    # REFUSED

# B3: Query TXT record cua unk.nebula.lab truc tiep
dig TXT unk.nebula.lab @<box_ip>
# → "NBL02{...flag...}"
```

### Cau hinh BIND9:
- `/etc/bind/named.conf.local`:
  - zone "nebula.lab" → allow-transfer: any (sinh vien co the axfr)
  - zone "unk.nebula.lab" → allow-transfer: none (khong axfr duoc, phai query TXT truc tiep)
- `/etc/bind/zones/db.nebula.lab`: co A record `unk.nebula.lab → 127.0.0.1` (lo ra subdomain)
- `/etc/bind/zones/db.unk.nebula.lab`: co `@ 3600 IN TXT "NBL02{...}"` (chua flag)

### Flag inject:
- `inject-flags.py` ghi flag NBL02 vao `/etc/bind/zones/db.unk.nebula.lab`
- Named duoc reload sau khi inject

---

## 16. README CAP NHAT (2026-04-10)

Da viet lai toan bo README.md bang tieng Viet, bao gom:
- Kien truc mang day du voi so do ASCII
- Bang 7 challenge voi technique, port, goi y giai
- Tat ca API endpoints cua plugin ctflab co documentation
- Co che flag random per-instance va suspicious detection
- Bien moi truong WG_SERVER_IP/WG_PORT
- Huong dan deploy, student flow, admin monitoring CLI
- Commit: `f3b73a8` — "docs: viet lai README day du bang tieng Viet"

---

## 17. GITHUB CREDENTIALS (2026-04-10)

- Remote: https://github.com/TuanHung1149/ctflab-uit.git
- Da luu credential vao `~/.git-credentials` (git credential.helper store)
- Push truc tiep bang `git push origin main` (khong can token moi lan)
- Token luu trong ~/.git-credentials (Personal Access Token, khong luu vao git)

---

## 18. CLAUDE CODE HOOKS FIX (2026-04-10)

### Van de:
- Moi lan chay Bash/Edit/Write deu hien loi do: "Hook command references ${CLAUDE_PLUGIN_ROOT}"
- Nguyen nhan: `~/.claude/settings.json` dung bien `${CLAUDE_PLUGIN_ROOT}` trong hook commands
- Bien nay chi duoc Claude Code inject khi hook chay TU BEN TRONG plugin, khong phai tu settings.json toan cuc
- Loi do hook fail → bao do, NHUNG lenh van chay binh thuong (khong anh huong output)

### Fix:
```bash
cp ~/.claude/settings.json ~/.claude/settings.json.bak
sed -i 's|${CLAUDE_PLUGIN_ROOT}|/root/.claude|g' ~/.claude/settings.json
# Thay the 21 occurrences
```
- 8 occurrences con lai la OK:
  - 1 dong dinh nghia env var `"CLAUDE_PLUGIN_ROOT": "/root/.claude"` (giu nguyen)
  - 7 dong JS inline dung `process.env.CLAUDE_PLUGIN_ROOT` (doc env var trong JS, hoat dong binh thuong)
- Backup tai: `~/.claude/settings.json.bak`
- **Can restart Claude Code session de ap dung**

---

## 19. SCOREBOARD HIEN TAI (2026-04-10)

| # | User | Score | Ghi chu |
|---|------|-------|---------|
| 1 | wgtest2 | 800 | Test account truoc do |
| 2 | wgtest1 | 450 | Test account truoc do |
| 3 | alpha_player1 | 450 | Multi-agent test |
| 4 | beta_player1 | 450 | Multi-agent test |
| 5 | wgtest3 | 100 | Test account truoc do |

Total stats: 24 users, 108 instances, 17 solves, 2 fails, 5 suspicious

---

*Cap nhat: 2026-04-10 | Session: VPN endpoint fix + 3-agent E2E test + 3 challenge missing + README rewrite*
