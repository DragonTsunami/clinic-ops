"""ai-bot 自测：不依赖 LLM/TG 真实连通。
1. 模块可导入、路由齐全
2. 降级路径：LLM 未配置时 /alert 收标准 Alertmanager payload 不崩
3. prom_query 异常容错（PROM_URL 指向不可达地址时返回 n/a）
跑法：python selftest.py （exit 0 = PASS）
"""
import os
import sys

os.environ.setdefault("LLM_BASE_URL", "")          # 强制走降级路径
os.environ.setdefault("PROM_URL", "http://127.0.0.1:59999")  # 必然不可达

from fastapi.testclient import TestClient  # noqa: E402
import bot  # noqa: E402

failures = []


def check(name: str, cond: bool):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


client = TestClient(bot.app)

# 1) 路由
paths = {r.path for r in bot.app.routes}
check("routes: /alert /report/run /health", {"/alert", "/report/run", "/health"} <= paths)

# 2) 标准告警 payload 走降级（TG 未配置 → 只落日志，不崩）
payload = {
    "alerts": [
        {
            "status": "firing",
            "labels": {"alertname": "BackendDown", "severity": "P1"},
            "annotations": {"summary": "后端进程不可达", "runbook": "ops/runbooks/backend-down.md"},
        }
    ]
}
r = client.post("/alert", json=payload)
check("alert webhook 200 (fallback)", r.status_code == 200)

# 3) 坏 payload 400
r = client.post("/alert", content=b"not-json", headers={"Content-Type": "application/json"})
check("bad payload -> 400", r.status_code == 400)

# 4) prom_query 容错
check("prom_query unreachable -> n/a", bot.prom_query("up") == "n/a")

# 5) 巡检快照可生成（全部 n/a 也应成文）
snap = bot.collect_snapshot()
check("daily snapshot has header", snap.startswith("📋 每日巡检"))

# 6) health
check("health endpoint", client.get("/health").status_code == 200)

print(f"\n{'ALL PASS' if not failures else 'FAILED: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
