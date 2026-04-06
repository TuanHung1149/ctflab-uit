# CTFLab UIT

CTF Lab Platform for NT140 course at UIT - Hack The Box style.

## Architecture

```
Users -> CTFd (Web UI) -> ctflab plugin -> Docker API
                                        -> OpenVPN (per-user VPN)
                                        -> Isolated networks (per-user)
```

## Quick Start

```bash
# Clone repo
git clone https://github.com/TuanHung1149/ctflab-uit.git
cd ctflab-uit

# Deploy (requires Ubuntu 22.04+, root access)
sudo bash deploy.sh
```

## Components

| Component | Description |
|-----------|-------------|
| `ctfd/` | CTFd deployment + custom ctflab plugin |
| `boxes/infinity/` | Sample CTF box - "Nebula Nexus" (7 challenges) |
| `openvpn/` | OpenVPN server setup + iptables isolation |
| `backend/` | Custom FastAPI backend (alternative to CTFd) |
| `frontend/` | Custom Next.js frontend (alternative to CTFd) |

## CTFd Plugin (ctflab)

The custom plugin adds HTB-style functionality:
- **Launch Instance**: Creates isolated Docker network + container per user
- **Download VPN**: Generates OpenVPN config for accessing the box
- **Reset**: Restores box to original state
- **Destroy**: Tears down container and network
- **Flag Submission**: Per-instance random flags validated through CTFd

## Infinity Box (Nebula Nexus)

7 progressive challenges:

| # | Challenge | Technique | Points |
|---|-----------|-----------|--------|
| 1 | Network Service Recon | TCP connection + math quiz | 100 |
| 2 | DNS Enumeration | Zone transfer + TXT record | 100 |
| 3 | Web Exploitation | TinyFileManager exploit | 150 |
| 4 | Credential Access | Read user flag | 100 |
| 5 | Maltrail RCE | CVE exploit -> shell as brown | 200 |
| 6 | SUID Privilege Escalation | sysinfo binary -> john | 200 |
| 7 | Buffer Overflow | rootnow binary -> root | 300 |

## Port Mapping

| Port | Service | Challenge |
|------|---------|-----------|
| 7171 | Python Server | Chall 1 |
| 80 | Nginx (Web) | Chall 3 |
| 53 | BIND9 (DNS) | Chall 2 |
| 8338 | Maltrail | Chall 5 |

## Network Design

```
User VPN (10.200.{slot}.2) 
  -> Host OpenVPN Server (10.200.0.1)
    -> Docker Bridge (10.100.{slot}.0/24)
      -> CTF Box (10.100.{slot}.2)
```

Each user gets:
- Unique slot (1-50)
- Isolated Docker network
- OpenVPN tunnel to their network only (split tunnel)
- Per-instance randomized flags

## Development

```bash
# Start infrastructure only
docker compose up -d db cache

# Run CTFd locally
cd ctfd && pip install -r requirements.txt
python serve.py

# Or use full docker-compose
docker compose up --build
```

## Tech Stack

- **Frontend**: CTFd 3.7
- **Container Management**: Docker SDK (Python)
- **VPN**: OpenVPN + EasyRSA
- **Database**: MariaDB
- **Cache**: Redis

## License

Educational use - NT140 UIT
