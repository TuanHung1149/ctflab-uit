# CTFLab UIT

Nền tảng thực hành CTF kiểu **Hack The Box** cho môn NT140 – UIT.  
Mỗi sinh viên nhận một máy ảo Docker riêng biệt, kết nối qua WireGuard VPN, giải các bài theo thứ tự từ recon đến root.

---

## Kiến trúc tổng quan

```
Sinh viên (WireGuard client)
    │  45.122.249.68:11194 (pfSense / HAProxy)
    ▼
WireGuard Server  10.200.0.1  (host 152.42.233.178:51820)
    │
    ├── 10.200.0.X  → cấp cho từng sinh viên (tối đa 50 slot)
    │
    └── Docker networks  10.100.{slot}.0/24
              │
              └── ctflab_box_{slot}   IP: 10.100.{slot}.2
```

Mỗi sinh viên có:
- **VPN IP cố định** (`10.200.0.X`) – tự động cấp khi đăng ký
- **Slot cố định** (1–50) – persist qua các lần khởi động lại
- **Mạng Docker riêng** – không thể ping máy của sinh viên khác
- **Flag ngẫu nhiên theo instance** – chống copy cờ

---

## Thành phần

| Thư mục | Mô tả |
|---|---|
| `ctfd/` | CTFd 3.7 + plugin `ctflab` tùy chỉnh |
| `boxes/infinity/` | Box "Nebula Nexus" – 7 challenge |
| `wireguard/` | Script cài WireGuard server |
| `scripts/` | Script vận hành: setup VPN user, update route, test E2E |
| `openvpn/` | *(Legacy)* OpenVPN – đã thay bằng WireGuard |
| `backend/` | FastAPI backend (thay thế CTFd – chưa production) |
| `frontend/` | Next.js frontend (thay thế CTFd – chưa production) |

---

## Plugin CTFd (`ctflab`)

Plugin bổ sung chức năng HTB vào CTFd chuẩn:

### API Endpoints

| Endpoint | Method | Mô tả |
|---|---|---|
| `/api/ctflab/vpn` | GET | Tải file `.conf` WireGuard của user |
| `/api/ctflab/instances` | POST | Khởi động máy ảo |
| `/api/ctflab/instances` | GET | Xem instance đang chạy |
| `/api/ctflab/instances/<id>` | DELETE | Tắt máy ảo |
| `/api/ctflab/instances/<id>/reset` | POST | Reset máy về trạng thái ban đầu |
| `/api/ctflab/admin/instances` | GET | *(Admin)* Danh sách instances đang chạy |
| `/api/ctflab/admin/instances/history` | GET | *(Admin)* Lịch sử 100 instance gần nhất |
| `/api/ctflab/admin/stats` | GET | *(Admin)* Thống kê tổng quan |
| `/api/ctflab/admin/logs` | GET | *(Admin)* Activity log (`?action=start_machine`) |
| `/api/ctflab/admin/suspicious` | GET | *(Admin)* Danh sách nghi vấn chia sẻ flag |
| `/api/ctflab/admin/bash-history/<slot>` | GET | *(Admin)* Lịch sử lệnh trong box |
| `/api/ctflab/admin/container-logs/<slot>` | GET | *(Admin)* Docker container logs |
| `/api/ctflab/admin/dashboard` | GET | *(Admin)* Trang dashboard HTML |
| `/api/ctflab/admin/challenges` | GET | *(Admin)* Quản lý challenge |

### Cơ chế flag

- Khi user khởi động box, hệ thống **tạo flag ngẫu nhiên** cho từng prefix (NBL01–NBL07).
- Flag được inject vào box qua biến môi trường `FLAGS_JSON`.
- Khi submit, CTFd gọi validator riêng – so sánh với flag đã lưu trong DB theo `(user_id, challenge_id, instance_id)`.
- Nếu user A submit flag của user B → bị phát hiện và ghi vào bảng `SuspiciousSubmission`.

### Cấu hình biến môi trường (docker-compose)

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `WG_SERVER_IP` | `45.122.249.68` | IP public của VPN endpoint (pfSense) |
| `WG_PORT` | `11194` | Port VPN endpoint (HAProxy forward) |
| `MAX_SLOT` | `50` | Số máy ảo tối đa chạy đồng thời |
| `INSTANCE_LIFETIME_HOURS` | `4` | Thời gian sống của instance |
| `SECRET_KEY` | *(thay trước deploy)* | Flask secret key |

---

## Box "Infinity" – Nebula Nexus

7 challenge lũy tiến trên một box duy nhất:

| # | Tên | Kỹ thuật | CTFd ID | Prefix | Điểm |
|---|---|---|---|---|---|
| 1 | Network Service Recon | Port scan → TCP math quiz | 22 | NBL01 | 100 |
| 2 | DNS Enumeration | Zone transfer → TXT record ẩn | 17 | NBL02 | 100 |
| 3 | Web Exploitation | TinyFileManager → đọc file | 18 | NBL03 | 150 |
| 4 | Credential Access | SSH → đọc flag user | 19 | NBL04 | 100 |
| 5 | Maltrail RCE | CVE-2023-27163 → shell `brown` | – | NBL05 | 200 |
| 6 | SUID Privilege Escalation | `sysinfo` SUID → `john` | – | NBL06 | 200 |
| 7 | Buffer Overflow | `rootnow` BOF → root | – | NBL07 | 300 |

### Cổng dịch vụ trong box

| Port | Dịch vụ | Challenge |
|---|---|---|
| 22 | SSH (`taylor` / mật khẩu hiển thị trên UI) | Tất cả |
| 53 | BIND9 DNS | NBL02 |
| 80 | Nginx → TinyFileManager | NBL03 |
| 7171 | Python TCP server (math quiz) | NBL01 |
| 8338 | Maltrail 0.53 | NBL05 |

### Hướng dẫn giải (gợi ý)

**NBL01 – Network Service Recon**
```bash
nmap -sV 10.100.X.2          # tìm port 7171
nc 10.100.X.2 7171            # nhận bài toán cộng, trả lời → flag
```

**NBL02 – DNS Enumeration**
```bash
dig axfr nebula.lab @10.100.X.2       # zone transfer → thấy subdomain unk
dig TXT unk.nebula.lab @10.100.X.2    # → flag trong TXT record
```

**NBL03 – Web Exploitation**
```bash
# Vhost: inffile123.nebula.lab
curl -H "Host: inffile123.nebula.lab" http://10.100.X.2/
# TinyFileManager → khai thác đọc /opt/chall3/tinyfilemanager/infinity.txt
```

**NBL04 – Credential Access**
```bash
ssh taylor@10.100.X.2    # dùng mật khẩu hiển thị trên CTFd
cat ~/user.txt            # flag
```

---

## Triển khai nhanh

### Yêu cầu

- Ubuntu 22.04+ (hoặc Debian 12+)
- RAM ≥ 4 GB, Disk ≥ 40 GB
- Root access
- Port mở: `8080/tcp` (CTFd UI), `51820/udp` (WireGuard)

### Bước cài đặt

```bash
# 1. Clone repo
git clone https://github.com/TuanHung1149/ctflab-uit.git
cd ctflab-uit

# 2. Cấu hình endpoint VPN (nếu dùng pfSense/HAProxy)
export WG_SERVER_IP=45.122.249.68
export WG_PORT=11194

# 3. Deploy toàn bộ
sudo bash deploy.sh
```

Script `deploy.sh` tự động:
1. Cài Docker + Docker Compose
2. Cài WireGuard tools
3. Khởi tạo keypair WireGuard server (`wireguard/setup-server.sh`)
4. Build Docker image `ctflab/infinity`
5. Chạy `docker compose up -d --build`

### Sau khi deploy

```
CTFd Web UI:    http://<SERVER_IP>:8080
WireGuard:      <WG_SERVER_IP>:<WG_PORT>/udp
```

1. Truy cập CTFd, tạo tài khoản **admin**.
2. Vào **Admin → Challenges → Create** → chọn type `ctflab`.
3. Nhập `docker_image = ctflab/infinity`, `flag_prefix = NBL01` (hoặc NBL02…).
4. Sinh viên đăng ký → tải VPN → khởi động máy → hack.

---

## Quy trình sinh viên (Student Flow)

```
1. Đăng ký tài khoản tại http://ctf.example.com
2. Vào Challenges → chọn bài bất kỳ
3. Click "Download VPN" → tải file <username>.conf
4. Kết nối VPN:
       sudo wg-quick up ./<username>.conf      # Linux / Kali / WSL2
5. Click "Start Machine" → chờ ~10 giây
6. SSH vào box:
       ssh taylor@10.100.X.2
       Password: <hiển thị trên UI>
7. Tìm flag → submit lên CTFd
8. Click "Reset" nếu muốn làm lại từ đầu
```

---

## Giám sát (Admin)

### Dashboard

```
http://<SERVER>:8080/api/ctflab/admin/dashboard
```

Hiển thị: instances đang chạy, slot map, lịch sử, suspicious submissions.

### CLI nhanh (trên server)

```bash
# Xem instances đang chạy
curl -s -b <admin_cookie> http://localhost:8080/api/ctflab/admin/instances | python3 -m json.tool

# Thống kê tổng quan
curl -s -b <admin_cookie> http://localhost:8080/api/ctflab/admin/stats | python3 -m json.tool

# Nghi vấn chia sẻ flag
curl -s -b <admin_cookie> http://localhost:8080/api/ctflab/admin/suspicious | python3 -m json.tool

# Lịch sử lệnh trong box slot 1
curl -s -b <admin_cookie> http://localhost:8080/api/ctflab/admin/bash-history/1 | python3 -m json.tool

# Docker containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Networks}}"

# WireGuard peers
wg show wg0
```

### Kiểm tra isolation

```bash
# Xem iptables rules cô lập giữa các box
iptables -L CTFLAB_ISOLATION -n

# Box 1 không được phép ping box 2
docker exec ctflab_box_1 ping -c1 10.100.2.2   # phải bị DROP
```

---

## Phát triển

### Chạy local (không Docker)

```bash
# Khởi động DB + Redis
docker compose up -d db cache

# Cài dependencies CTFd
cd ctfd
pip install -r requirements.txt

# Chạy CTFd
python serve.py
```

### Thêm box mới

1. Tạo thư mục `boxes/<tên>/`
2. Viết `Dockerfile`, `chall*/`, `docker/entrypoint.sh`, `docker/inject-flags.py`
3. Build: `docker build -t ctflab/<tên> ./boxes/<tên>/`
4. Tạo challenge trên CTFd với `docker_image = ctflab/<tên>`

### Seed challenge mẫu

```bash
bash scripts/seed-challenges.sh
```

---

## Biến môi trường đầy đủ (`.env`)

```env
# Database
DATABASE_URL=postgresql+asyncpg://ctflab:ctflab@postgres:5432/ctflab

# WireGuard VPN endpoint (pfSense public)
WG_SERVER_IP=45.122.249.68
WG_PORT=11194

# Instance limits
MAX_SLOT=50
INSTANCE_LIFETIME_HOURS=4
MAX_INSTANCES_PER_USER=1

# CTFd
SECRET_KEY=<generate: openssl rand -hex 32>
MYSQL_PASSWORD=<strong_password>
```

---

## Tech Stack

| Layer | Công nghệ |
|---|---|
| Web UI | CTFd 3.7 |
| Plugin | Python / Flask Blueprint |
| VPN | WireGuard |
| Container | Docker + Docker SDK (Python) |
| Database | MariaDB 10.11 |
| Cache | Redis 7 |
| Box OS | Debian 12 Slim |
| Box services | BIND9, Nginx, Python3, Maltrail |

---

## License

Educational use – NT140 UIT  
Không sử dụng cho mục đích thương mại.
