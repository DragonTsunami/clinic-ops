"""E2E 冒烟：注册→登录→看号源→预约→重复预约被拒→我的预约→取消→取消后再取消被拒。
跑法：python e2e_smoke.py [base_url]  默认 http://127.0.0.1:8080（经 nginx 链路）"""
import sys
import time
import uuid

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"
API = f"{BASE}/api"
client = httpx.Client(timeout=15)
failures = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        failures.append(name)


# 1) 注册（手机号随机，可重复跑）
phone = f"1{int(time.time())%10**10:010d}"[:11]
r = client.post(f"{API}/auth/register", json={"name": "冒烟测试", "phone": phone, "password": "smoke123456"})
check("register 200", r.status_code == 200, r.text)
token = r.json().get("token", "")
H = {"Authorization": f"Bearer {token}"}

# 2) 登录
r = client.post(f"{API}/auth/login", json={"phone": phone, "password": "smoke123456"})
check("login 200", r.status_code == 200, r.text)

# 3) 错密码登录被拒
r = client.post(f"{API}/auth/login", json={"phone": phone, "password": "wrong-password"})
check("login wrong-pw 401", r.status_code == 401)

# 4) 号源列表
r = client.get(f"{API}/schedules?days=2")
slots = r.json() if r.status_code == 200 else []
check("schedules non-empty", len(slots) > 0, f"status={r.status_code}")
free = next((s for s in slots if s["booked"] < s["capacity"]), None)
check("free slot exists", free is not None)

# 5) 预约
r = client.post(f"{API}/appointments", json={"schedule_id": free["schedule_id"]}, headers=H)
check("book 200", r.status_code == 200, r.text)
appt = r.json() if r.status_code == 200 else {}

# 6) 再约同一号源（同账号）→ 409
r = client.post(f"{API}/appointments", json={"schedule_id": free["schedule_id"]}, headers=H)
check("double-book 409", r.status_code == 409, r.text)

# 7) 未登录预约 → 401
r = client.post(f"{API}/appointments", json={"schedule_id": free["schedule_id"]})
check("book no-auth 401", r.status_code == 401)

# 8) 我的预约里有单
r = client.get(f"{API}/appointments/mine", headers=H)
mine = r.json() if r.status_code == 200 else []
check("mine has 1 booked", len(mine) == 1 and mine[0]["status"] == "BOOKED", r.text)

# 9) 取消
r = client.post(f"{API}/appointments/{appt.get('id')}/cancel", headers=H)
check("cancel ok", r.status_code == 200, r.text)

# 10) 重复取消 → 409
r = client.post(f"{API}/appointments/{appt.get('id')}/cancel", headers=H)
check("re-cancel 409", r.status_code == 409)

# 11) 取消后号源释放：能再次约上同一号源
r = client.post(f"{API}/appointments", json={"schedule_id": free["schedule_id"]}, headers=H)
check("re-book same slot after cancel", r.status_code == 200, r.text)
if r.status_code == 200:
    client.post(f"{API}/appointments/{r.json()['id']}/cancel", headers=H)

# 12) 深度健康（app 根路径，不在 /api 前缀下；经 nginx / 全量反代可达）
r = client.get(f"{BASE}/health/deep")
check("health/deep ok", r.status_code == 200 and r.json().get("ok") is True, r.text)

# 13) 前端页面
r = client.get(BASE)
check("frontend 200 html", r.status_code == 200 and "<div id=\"app\">" in r.text)

# 14) 业务指标（经后端直连；注意 make_asgi_app 挂载点 /metrics 带 307→/metrics/ 重定向，跟随后取）
r = httpx.get("http://127.0.0.1:8000/metrics", timeout=10, follow_redirects=True)
check("metrics exposed", r.status_code == 200 and "clinic_appointments_created_total" in r.text)

print(f"\n{'ALL PASS (14)' if not failures else 'FAILED: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
