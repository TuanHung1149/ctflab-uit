# Context: NT140 - CTF Box "Infinity" (Nebula Nexus)

**GitHub Repo**: https://github.com/TuanHung1149/ctflab-uit (PRIVATE)

## 1. Tong Quan Du An

### Boi canh
- **Mon hoc**: NT140 (UIT)
- **Giang vien**: Thay Khoa
- **Yeu cau**: Xay dung CTF platform co kha nang:
  - Upload box (VM hoac docker-compose)
  - Tao network co lap rieng cho moi user
  - Cap VPN (WireGuard/OpenVPN) de user truy cap box
- **Mau box tham khao**: `infinity.zip` - mot CTF box Docker chua 7 challenge

### Kien truc tong the (tu hinh anh thay cung cap)
```
+--------------------------+
|  Nguoi dung / Player     |
+-----------+--------------+
            |
  +---------v----------+        +----------------------+
  | Web Front-end       |------->| Mang VPN & Truy cap  |
  | (Next.js)           |        | (WireGuard/OpenVPN)  |
  +---------+-----------+        +----------+-----------+
            |                               |
  +---------v----------+        +-----------v-----------+
  | Backend API         |        | Mang Lab co lap       |
  | (FastAPI)           |        | (Isolated Lab Networks)|
  +---------+-----------+        +-----------+-----------+
            |                               |
  +---------v----------+        +-----------v-----------+
  | Background Worker   |        | Container Provider    |
  | (Celery / Arq)      |        | (Docker / Kubernetes) |
  +-----+---------+----+        +-----------------------+
        |         |
  +-----v--+ +---v----+ +--------+
  |Postgres| | Redis  | | Object |
  |  (DB)  | |(Cache) | |Storage |
  +--------+ +--------+ +--------+
        |
  +-----v--------------+
  | Giam sat & Kiem toan|
  | (Grafana / Logs)    |
  +---------------------+
```

**Ghi chu**: Trong hinh, "Fake Provider (Phase 5)" bi danh dau X = chua implement.
Focus hien tai la **Container Provider (Docker)**.

**Fake Provider (xac nhan tu thay Khoa 2026-04-06)**:
Fake Provider la provider gia lap cac thao tac start/stop/reset instance ma KHONG thuc su tao container/VM.
Muc dich: "Do ton time cho" - giup dev/test frontend va API flow ma khong can Docker infrastructure that.
-> Se implement sau (Phase 5 theo plan cua thay).

---

## 2. Phan Tich Box "Infinity" (Nebula Nexus)

### 2.1 Cau truc file (DAY DU - 2120 files)
```
infinity/
  .env                    # Bien moi truong: BOX_SLUG, BASE_DOMAIN, subdomain
  flags.txt               # 7 flag (NBL01 -> NBL07)
  Dockerfile              # Ubuntu 22.04, cai bind9/nginx/php/python/gcc
  docker-compose.yml      # 1 service duy nhat, expose 4 port
  setup.sh                # Script setup goc (chay tren VM, KHONG phai Docker)
  cleanup.sh              # Cron job reset state moi 5 phut
  docker/
    bootstrap.sh          # Setup trong Docker build (thay the setup.sh)
    entrypoint.sh         # Docker entrypoint -> reset-state + supervisord
    reset-state.sh        # Khoi phuc flag/file bi player xoa
    supervisord.conf      # Quan ly 5 process: chall1, named, tinyfilemanager, nginx, chall5
    nginx/
      infinity.conf       # Nginx reverse proxy config (template voi __BASE_DOMAIN__)
      landing.html        # Landing page HTML (template voi __BOX_TITLE__)
  chall1/
    server.py             # Python socket server port 7171 - bot checking math quiz
  chall2/
    named.conf.local      # BIND9 zone config
    zones/
      db.infinity.insec         # Zone file chinh
      db.unk.infinity.insec     # Zone file chua flag TXT record
  chall3/
    docker-compose.yml          # Nginx + TinyFileManager (dung rieng cho VM setup)
    tinyfilemanager/
      tinyfilemanager.php       # PHP file manager app
      translation.json          # i18n
      infinity.txt              # Flag file
      php-disable-function.ini  # Disable dangerous PHP functions
      Dockerfile                # PHP container
    nginx/
      Dockerfile                # Nginx container
      templates/
        default.conf            # Default vhost
        inffile123.conf         # TinyFileManager vhost
  chall4/
    flag.txt                    # User flag (copy to /home/taylor/user.txt)
  chall5/                       # Maltrail source (2000+ files)
    server.py                   # Maltrail server (port 8338)
    sensor.py                   # Maltrail sensor
    maltrail.conf               # Config
    core/                       # Core modules (httpd.py, common.py, ...)
    thirdparty/                 # Dependencies
    trails/                     # Threat intelligence feeds
    misc/                       # Misc files
  chall6/
    sysinfo.c                   # SUID binary - goi getinfo.sh voi quyen john
    getinfo.sh                  # Shell script hien thi system info
    flag.txt                    # Flag
  chall7/
    rootnow.c                   # Buffer overflow - fgets(buf, 1337, stdin) vao buf[20]
    flag.txt                    # Root flag
```

### 2.2 Port Mapping
| Port Host | Port Container | Service              | Challenge |
|-----------|---------------|----------------------|-----------|
| 7171      | 7171          | Python server        | Chall 1   |
| 8080      | 80            | Nginx (reverse proxy)| Chall 3   |
| 8053      | 53 (TCP+UDP)  | BIND9 DNS            | Chall 2   |
| 8338      | 8338          | Maltrail server      | Chall 5   |

### 2.3 User Accounts (tao trong container)
| User   | Password             | Vai tro                     |
|--------|----------------------|-----------------------------|
| taylor | lekkerding           | TinyFileManager Administrator|
| brown  | AI56JSPUac43v7MWkXdG | MalTrail Administrator       |
| john   | S6V1frkRJLo40GKuglzp | Information Asset Manager    |

### 2.4 Dich vu chay (supervisord)
1. **chall1**: `python3 /opt/chall1/server.py` (port 7171)
2. **named**: BIND9 DNS server (port 53)
3. **tinyfilemanager**: PHP built-in server `127.0.0.1:8081` (nginx proxy ra port 80)
4. **nginx**: Reverse proxy + landing page
5. **chall5**: Maltrail `python3 /opt/chall5/server.py` (port 8338, user brown)

---

## 3. Phan Tich 7 Challenge - Attack Chain

### Chall 1: Network Service Recon (Flag: NBL01)
- **Dich vu**: Python socket server tren port 7171
- **Ky thuat**: Ket noi (nc/telnet) -> server gui bai toan cong 2 so -> tra loi dung -> nhan flag
- **Code**: `server.py` - `genTest()` tao 2 so random, gui "[infinity.insec] What is the sum of X and Y?"
- **Flag vi tri**: Hardcode trong `server.py` (bien `FLAG`)

### Chall 2: DNS Enumeration (Flag: NBL02)
- **Dich vu**: BIND9 DNS server
- **Ky thuat**:
  - Zone transfer (`dig axfr nebula.lab @target`) -> phat hien subdomain `unk.nebula.lab`
  - Query TXT record: `dig TXT unk.nebula.lab @target`
  - Zone `nebula.lab` cho phep `allow-transfer {any}` (co y de lo)
  - Zone `unk.nebula.lab` cam transfer (`allow-transfer {none}`) nhung TXT record van query duoc
- **Flag vi tri**: TXT record cua `unk.nebula.lab`

### Chall 3: Web Exploitation - TinyFileManager (Flag: NBL03)
- **Dich vu**: TinyFileManager (PHP) phia sau Nginx, truy cap qua subdomain `inffile123.nebula.lab`
- **Nginx config**: 3 vhost - redirect mac dinh, landing page, reverse proxy den PHP :8081
- **Ky thuat**: Khai thac TinyFileManager (default creds admin/admin@123, file upload, path traversal...)
- **Flag vi tri**: `/opt/chall3/tinyfilemanager/infinity.txt`
- **Luu y**: PHP disable functions duoc cau hinh (`php-disable-function.ini`)

### Chall 4: Credential Access (Flag: NBL04)
- **Khong co dich vu rieng** - flag nam trong `/home/taylor/user.txt`
- **Ky thuat**: Su dung credentials cua taylor (`lekkerding`) de doc flag
- **Con duong**: Co the tu Chall3 (TinyFileManager chay duoi quyen co the doc file he thong) hoac SSH/shell tu chall khac

### Chall 5: Maltrail RCE (Flag: NBL05)
- **Dich vu**: Maltrail server tren port 8338 (chay voi user `brown`)
- **Ky thuat**: Khai thac lo hong Maltrail (CVE-2023-27163 - OS Command Injection trong login page)
- **Flag vi tri**: `/opt/chall5/flag.txt` (owned root:brown, permission 750)
- **Ket qua**: Co shell voi quyen user `brown`

### Chall 6: SUID Privilege Escalation brown -> john (Flag: NBL06)
- **Ky thuat**: Khai thac SUID binary `/usr/local/bin/sysinfo`
  - Owned by `root:brown`, permission `4750` (SUID bit)
  - Code `sysinfo.c`: goi `setuid(john)` roi `system("/home/john/getinfo.sh")`
  - `getinfo.sh`: hien thi system info (date, whoami, hostnamectl, /etc/passwd)
  - Tu user `brown`, chay `sysinfo` -> chuyen sang quyen john -> doc file cua john
- **Flag vi tri**: `/home/john/flag.txt`
- **Ket qua**: Truy cap duoc voi quyen john

### Chall 7: Buffer Overflow -> Root (Flag: NBL07)
- **Ky thuat**:
  - User `john` co sudo NOPASSWD cho `/opt/chall7/rootnow`
  - Code `rootnow.c`: `char yourGuess[20]` nhung `fgets(yourGuess, 1337, stdin)` -> **buffer overflow**
  - Compile voi `-fno-stack-protector` (CO Y tat bao ve stack)
  - Logic: random so, neu == 1337 thi cat /root/root.txt -> co the overflow de bypass check
  - Hoac don gian: `sudo /opt/chall7/rootnow` chay voi quyen root, chi can overflow bien `funNum`
- **Flag vi tri**: `/root/root.txt`

### Tong ket attack chain:
```
Recon (port scan)
  |
  +-> Chall1: Port 7171 -> tuong tac -> NBL01
  +-> Chall2: DNS enum -> zone transfer -> TXT record -> NBL02
  +-> Chall3: Web exploit TinyFileManager -> NBL03
        |
        +-> Chall4: Doc /home/taylor/user.txt -> NBL04
  +-> Chall5: Maltrail RCE -> shell as brown -> NBL05
        |
        +-> Chall6: SUID sysinfo -> escalate to john -> NBL06
              |
              +-> Chall7: sudo rootnow (bof) -> root -> NBL07
```

---

## 4. Kien Truc Ky Thuat Box

### Thiet ke hien tai: "All-in-one Docker Container"
```
+------------------------------------------+
|  Docker Container (Ubuntu 22.04)         |
|                                          |
|  supervisord (PID 1)                     |
|    |-- python3 server.py    (chall1)     |
|    |-- named (BIND9)        (chall2)     |
|    |-- php -S 127.0.0.1:8081(chall3)     |
|    |-- nginx                (proxy)      |
|    |-- python3 server.py    (chall5)     |
|                                          |
|  Users: taylor, brown, john              |
|  SUID: /usr/local/bin/sysinfo            |
|  Sudo: john -> /opt/chall7/rootnow       |
|  Cron: reset-state.sh (moi 5 phut)      |
+------------------------------------------+
  Ports: 53, 80, 7171, 8338
```

### Uu diem
- Don gian, 1 container duy nhat
- De deploy va clean up
- Phu hop cho CTF box doc lap

### Nhuoc diem
- Tat ca dich vu trong 1 container (anti-pattern Docker)
- Khong scale duoc
- Khong co network isolation giua cac challenge
- Player co root = pha het container

---

## 5. Workflow De Tich Hop Vao Platform

### Buoc 1: Chay thu box (test local)
```bash
cd infinity/infinity
docker-compose up --build
```
- Truy cap: http://localhost:8080 (web), port 7171 (chall1), port 8053 (dns), port 8338 (maltrail)

### Buoc 2: Tich hop vao platform (theo kien truc thay)
```
User request box -> Backend API (FastAPI)
  -> Background Worker (Celery)
    -> Container Provider (Docker API)
      -> docker-compose up (tao container tu infinity image)
      -> Tao isolated network (docker network create)
      -> Tao WireGuard peer config cho user
    -> Tra ve VPN config cho user
User connect VPN -> Truy cap box qua isolated network
```

### Buoc 3: Network Isolation (QUAN TRONG)
```
+-- Docker Network: user_123_net (172.20.1.0/24) --+
|                                                    |
|  [infinity-box]    [wireguard-peer]               |
|  172.20.1.2        172.20.1.1                     |
|                                                    |
+----------------------------------------------------+
```
- Moi user 1 docker network rieng
- WireGuard interface bridge vao network do
- Cac user KHONG thay nhau

---

## 6. Loi Khuyen & Nhung Dieu Can Luu Y

### A. Ve box hien tai (infinity) - DAY DU SOURCE CODE
1. **Tat ca 2120 file** da co day du trong zip, bao gom:
   - `chall1/server.py`, `chall6/sysinfo.c`, `chall7/rootnow.c`
   - TinyFileManager (PHP), Maltrail (Python), Nginx configs
   - Docker co the build thanh cong ngay

2. **Bao mat credentials**: File `.env` va `flags.txt` hardcode password + flag
   -> OK cho CTF box, nhung platform can generate random flags moi instance

3. **Reset mechanism**: `reset-state.sh` + cron 5 phut la tot
   -> Dam bao player khong pha box vinh vien

### B. Ve platform (theo kien truc thay)
1. **Uu tien Container Provider (Docker) truoc** - VM Provider (Proxmox) phuc tap hon nhieu
2. **WireGuard > OpenVPN** cho VPN - nhanh hon, nhe hon, de automate config
3. **Can lam**:
   - API tao/xoa container instances
   - API tao/xoa WireGuard peers
   - Network isolation (docker network per user)
   - Trang thai quan ly (PostgreSQL)
   - Queue system (Redis + Celery) cho async tasks
   - Web portal (Next.js) cho user dang ky/truy cap box

4. **Thu tu uu tien implementation**:
   ```
   Phase 1: Docker container management (tao/xoa box)
   Phase 2: Network isolation (docker network per user)
   Phase 3: WireGuard VPN auto-config
   Phase 4: Web API (FastAPI) + basic frontend
   Phase 5: Multi-user, queue, monitoring
   ```

### C. Rui ro can tranh
1. **Container escape**: Player co root trong container co the escape
   -> Dung `--security-opt=no-new-privileges`, drop capabilities, read-only rootfs
2. **Resource abuse**: Player co the mine crypto, DDoS
   -> Gioi han CPU/RAM (`--cpus`, `--memory`)
3. **Network leak**: Player co the scan infra
   -> Firewall rules, chi cho phep traffic trong isolated network

---

## 7. Cong Nghe Can Hoc/Dung

| Thanh phan        | Cong nghe           | Do uu tien |
|-------------------|---------------------|------------|
| Backend API       | FastAPI (Python)    | CAO        |
| Container mgmt    | Docker SDK (Python) | CAO        |
| VPN               | OpenVPN             | CAO        |
| Database          | PostgreSQL          | CAO        |
| Cache/Queue       | Redis               | TRUNG BINH |
| Task queue        | Celery hoac Arq     | TRUNG BINH |
| Frontend          | Next.js             | TRUNG BINH |
| Monitoring        | Grafana + Loki      | THAP       |
| Object Storage    | MinIO               | THAP       |

---

## 8. Tham Khao - Platform CTF Tuong Tu

- **HTB (Hack The Box)**: Mo hinh target - moi user 1 VPN, box chung hoac rieng
- **TryHackMe**: Tuong tu, dung OpenVPN
- **CTFd**: Open-source CTF framework (chi co scoreboard, khong co lab infra)
- **pwn.college**: Open-source, dung Docker cho challenge isolation

---

## 9. Cau Hoi Can Hoi Thay Khoa

### A. Ve server & deployment (UU TIEN CAO)
1. **Platform se deploy o dau?**
   - Thay co server/VPS rieng cho project nay khong?
   - Hay em tu chuan bi server (VPS tren cloud)?
   - Cau hinh toi thieu (RAM, CPU, disk) thay khuyennghj bao nhieu cho 20-50 user?

2. **Domain & SSL**
   - Co domain rieng (vd: ctflab.uit.edu.vn) hay chi dung IP?
   - Can HTTPS khong hay HTTP du cho lab?

### B. Ve chuc nang platform (UU TIEN CAO)
3. **VPN: WireGuard hay OpenVPN?**
   - Trong hinh thay ve co ca 2. Thay muon uu tien cai nao?
   - (Goi y: WireGuard nhe hon, nhanh hon, de automate - em khuyen dung WireGuard)

4. **Moi user duoc chay bao nhieu box cung luc?**
   - 1 box/user hay nhieu box dong thoi?

5. **Thoi gian song cua 1 instance?**
   - Tu dong tat sau bao lau? (vd: 2 gio, 4 gio, khong gioi han?)

6. **Cham diem / scoreboard?**
   - Co can scoreboard (leaderboard) khong?
   - Co can tich hop vao diem mon hoc khong?
   - Flag submit co gioi han so lan thu khong?

### C. Ve box format (TRUNG BINH)
7. **Cac box khac ngoai infinity?**
   - Thay co them box nao khac can ho tro khong?
   - Cac box moi se theo cung format (Dockerfile + docker-compose) hay co format khac (OVA, VM)?
   - Phase dau chi can ho tro Docker thoi dung khong?

8. **Ai se tao box moi?**
   - Chi thay (admin) hay sinh vien cung co the upload box?
   - Co can review/approve box truoc khi publish khong?

### D. Ve user & auth (TRUNG BINH)
9. **Dang nhap bang gi?**
   - Username/password tu dang ky?
   - Hay tich hop SSO truong (vd: dang nhap bang tai khoan UIT)?

10. **Phan quyen?**
    - Chi co 2 role (admin + player) hay can nhieu hon (vd: giang vien, tro giang, sinh vien)?

### E. Ve timeline (UU TIEN CAO)
11. **Deadline?**
    - Khi nao can co ban demo dau tien?
    - Khi nao can hoan thanh day du?

12. **Co nhom lam chung khong?**
    - Em lam 1 minh hay co nhom?
    - Neu co nhom thi phan cong nhu nao?

---

## 10. Trang Thai Cac Cau Hoi (Cap nhat sau khi hoi thay)

| # | Cau hoi | Tra loi cua thay | Ngay |
|---|---------|-------------------|------|
| 1 | Server deploy o dau? | Thay chua tra loi. Tam thoi lam local/VPS ca nhan truoc | 2026-04-06 |
| 2 | Domain & SSL? | ... | |
| 3 | WireGuard hay OpenVPN? | **OpenVPN** (thay chon) | 2026-04-06 |
| 4 | Bao nhieu box/user? | ... | |
| 5 | Thoi gian song instance? | ... | |
| 6 | Scoreboard/cham diem? | ... | |
| 7 | Box khac ngoai infinity? | Chi can Docker, khong can VM provider | 2026-04-06 |
| 8 | Ai tao box? | ... | |
| 9 | Auth method? | ... | |
| 10 | Phan quyen? | ... | |
| 11 | Deadline? | ... | |
| 12 | Lam nhom hay 1 minh? | ... | |
| 13 | Frontend? | **CTFd cung OK** - co the dung CTFd thay vi tu lam frontend | 2026-04-06 |

---

## 11. Tien Do Implementation (Cap nhat 2026-04-06)

| Phase | Status | Files |
|-------|--------|-------|
| Phase 0: Scaffolding | DONE | .gitignore, .env, docker-compose.yml, boxes/infinity/ |
| Phase 1: Backend Foundation | DONE | 32 Python files - 19 API routes verified |
| Phase 2: Docker Service | DONE | docker_service.py, slot_manager.py, flag_generator.py |
| Phase 3: OpenVPN Service | DONE | openvpn_service.py, setup-server.sh |
| Phase 4: Background Tasks | DONE | worker.py, instance_tasks.py, cleanup_tasks.py |
| Phase 5: Frontend | DONE | 15 TSX/TS files - 9 pages, build pass |
| Phase 6: Security Hardening | DONE | iptables-isolation.sh, container caps in docker_service |

### Security Audit (2026-04-06):
- Player (non-root) KHONG doc duoc /root/ (permission 700)
- flags.txt, setup.sh, bootstrap.sh: chi root doc duoc
- /proc/1/environ: chi root doc duoc
- FLAGS_JSON env: chi root doc duoc
- Per-instance random flags: 7/7 MATCH giua DB va box
- inject-flags.sh goi trong entrypoint TRUOC reset-state.sh
- Backup flags cung duoc update de reset khong ghi de flags sai
```
29/29 PASS - ALL TESTS PASSED
```
| Test | Result |
|------|--------|
| CTFd responds | PASS |
| User login | PASS |
| Challenge listing (Nebula Nexus) | PASS |
| Launch instance | PASS - container at 10.100.1.2 |
| Docker container running | PASS - 5/5 services |
| FLAGS_JSON injected | PASS - 7 random flags |
| Instance status API | PASS |
| VPN config download | PASS - split tunnel config |
| Correct flag submission | PASS |
| Wrong flag rejected | PASS |
| Duplicate solve blocked | PASS |
| Scoreboard | PASS |
| Reset instance | PASS |
| Destroy instance | PASS - container + network removed |
| Re-launch after destroy | PASS |
| Duplicate launch blocked | PASS |

### THAY DOI QUAN TRONG (2026-04-06 11:22):
Thay Khoa xac nhan:
- **"The same HTB"** - platform hoat dong giong Hack The Box
- **Dung CTFd** lam frontend (user mgmt, challenge, scoreboard, flag submit)
- **Chi can Docker** provider, khong can VM
- Phan **infra** (Docker + VPN + network isolation) la phan custom

-> **Kien truc moi**: CTFd + CTFd plugin (ctflab) + OpenVPN
-> Next.js frontend da lam van giu lai de tham khao / backup (docker-compose.custom.yml)
-> Focus chuyen sang: deploy CTFd + tich hop Docker + OpenVPN
-> **DA HOAN THANH**: Plugin ctflab voi day du chuc nang (2026-04-06)

### GitHub: https://github.com/TuanHung1149/ctflab-uit (PRIVATE)
### Commits:
- `12c9ae3` - feat: initial project scaffolding + infinity CTF box
- `1446afe` - feat: complete platform implementation (backend + frontend)
- `486a24c` - feat: add box manifest and runtime flag injection
- `3bc8161` - feat: CTFd integration + custom ctflab plugin

### CTFd Plugin (ctflab) - HOAN THANH:
- **models.py**: CTFLabChallenge (extends Challenges) + LabInstance
- **challenge_type.py**: Custom "ctflab" challenge type voi per-instance flag validation
- **routes.py**: 5 API endpoints (launch/destroy/reset/vpn/status)
- **docker_utils.py**: DockerManager (create/destroy/reset container + network)
- **flag_utils.py**: Random flag generator
- **assets/**: view.html/js, create.html/js, update.html/js (admin + user UI)

### De deploy:
```bash
sudo bash deploy.sh
```
Hoac thu cong:
```bash
docker build -t ctflab/infinity ./boxes/infinity/
docker compose up -d --build
# Mo http://localhost:8000 -> tao admin -> tao challenge type "ctflab"
```

---

*Tao boi Claude Code - 2026-04-06*
*Project: NT140 / UIT - Tro Giang CTF Platform*
