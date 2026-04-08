# CTFLab UIT - Project Context

**GitHub**: https://github.com/TuanHung1149/ctflab-uit (PUBLIC)
**VPS**: 152.42.233.178 (8GB RAM, Ubuntu 24.04)
**Web**: http://152.42.233.178:8080 | Admin: admin / admin123
**Mon hoc**: NT140 - UIT | **Giang vien**: Thay Khoa
**Last updated**: 2026-04-08

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
