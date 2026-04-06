#!/usr/bin/env python3
"""Create single Nebula Nexus machine challenge (HTB-style)."""
from CTFd import create_app
app = create_app()
with app.app_context():
    from CTFd.plugins.ctflab.models import CTFLabChallengeModel, LabInstance
    from CTFd.models import db, Solves, Fails, Challenges

    Solves.query.delete()
    Fails.query.delete()
    LabInstance.query.delete()
    CTFLabChallengeModel.query.delete()
    Challenges.query.delete()
    db.session.commit()
    print("Old challenges deleted")

    desc = """## Nebula Nexus - HTB-Style Machine

**Difficulty:** Medium | **OS:** Linux | **Total: 1150pts**

### How to play:
1. Click **Start Machine** below
2. Connect VPN: `sudo openvpn your-username.ovpn`
3. SSH into box: `ssh taylor@<IP>` (password: `lekkerding`)
4. Find all 7 flags inside the box

### Flags (submit any NBL01-NBL07):
| # | Flag | Points | Hint |
|---|------|--------|------|
| 1 | NBL01 | 100 | Network service on port 7171 |
| 2 | NBL02 | 100 | DNS enumeration |
| 3 | NBL03 | 150 | Web application exploit |
| 4 | NBL04 | 100 | User flag in taylor home dir |
| 5 | NBL05 | 200 | Maltrail on port 8338 |
| 6 | NBL06 | 200 | Privilege escalation (SUID) |
| 7 | NBL07 | 300 | Root flag (buffer overflow) |

### Attack Chain:
```
taylor (SSH) -> read user.txt -> NBL04
nc localhost 7171 -> solve math -> NBL01
dig @localhost -> zone transfer -> NBL02
curl localhost:80 -> TinyFileManager -> NBL03
curl localhost:8338 -> Maltrail RCE -> shell as brown -> NBL05
/usr/local/bin/sysinfo (SUID) -> escalate to john -> NBL06
sudo /opt/chall7/rootnow -> buffer overflow -> root -> NBL07
```
"""

    c = CTFLabChallengeModel(
        name="Nebula Nexus",
        description=desc,
        value=1150,
        category="Machine",
        type="ctflab",
        state="visible",
        docker_image="ctflab/infinity",
        flag_prefix="NBL",
        instance_timeout=86400,
        box_env_json='{"BOX_SLUG":"nebula","BOX_TITLE":"Nebula Nexus","BASE_DOMAIN":"nebula.lab","TXT_SUBDOMAIN":"unk","FILE_SUBDOMAIN":"inffile123"}'
    )
    db.session.add(c)
    db.session.commit()
    print(f"Created: Nebula Nexus (id={c.id}, 1150pts)")
