"""ai-bot：Alertmanager webhook → LLM 分诊 → Telegram 推送；每日巡检报告。
设计红线（面试必讲）：
1. 只喂运维指标与告警元数据，绝不接触业务数据（医疗合规）
2. LLM 不可达时降级为原始告警透传，告警链路永不因 AI 挂掉而静默
3. 只读不改：bot 无任何服务器操作权限，处置仍由人执行
"""
import logging
import os
import time

import httpx
from fastapi import FastAPI, HTTPException, Request

log = logging.getLogger("ai-bot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.getenv("TG_CHAT_ID", "")
PROM_URL = os.getenv("PROM_URL", "http://prometheus:9090")

AI_ENABLED = bool(LLM_BASE_URL and LLM_API_KEY)

app = FastAPI(title="clinic ai-bot")


# ---------------------------------------------------------------- LLM
def llm_triage(alert_name: str, severity: str, summary: str, runbook: str) -> str:
    """调 LLM 出分诊建议；任何异常都抛给上层走降级路径。"""
    prompt = (
        "你是值班运维助手。以下是一条监控系统告警，请用不超过 5 行输出："
        "1)最可能的原因(按概率排序,最多3条) 2)第一步先查什么(具体命令) 3)风险等级(高/中/低)。\n"
        f"告警: {alert_name}\n级别: {severity}\n摘要: {summary}\n"
        f"参考runbook: {runbook or '暂无'}\n不要输出与运维无关的内容。"
    )
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


def tg_send(text: str) -> None:
    """Telegram 推送；失败只记日志（不阻断告警主流程）。"""
    if not (TG_BOT_TOKEN and TG_CHAT_ID):
        log.warning("TG 未配置，消息只落日志:\n%s", text)
        return
    try:
        with httpx.Client(timeout=15) as client:
            client.post(
                f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT_ID, "text": text[:4000]},
            )
    except httpx.HTTPError as exc:
        log.error("TG 推送失败: %s", exc)


# ------------------------------------------------------------- webhook
@app.post("/alert")
async def alert(request: Request):
    """Alertmanager webhook 入口。payload: {alerts: [{status,labels,annotations,...}]}"""
    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="bad json") from exc

    for item in payload.get("alerts", []):
        labels = item.get("labels", {})
        annotations = item.get("annotations", {})
        name = labels.get("alertname", "Unknown")
        severity = labels.get("severity", "?")
        summary = annotations.get("summary", "")
        runbook = annotations.get("runbook", "")
        status = item.get("status", "firing")
        emoji = "🔴" if severity == "P1" else "🟡"

        body = (
            f"{emoji} [{status.upper()}] {name} ({severity})\n"
            f"摘要: {summary}\n"
        )
        if AI_ENABLED:
            try:
                advice = llm_triage(name, severity, summary, runbook)
                body += f"\n🤖 AI 分诊:\n{advice}"
            except Exception as exc:  # noqa: BLE001
                log.error("LLM 分诊失败，降级透传: %s", exc)
                body += "\n(AI 分诊不可用，原始告警透传)"
        tg_send(body)
    return {"ok": True}


# ------------------------------------------------------------ 巡检报告
def prom_query(query: str) -> str:
    """即时查询，返回人类可读值；异常返回 'n/a'（巡检不能因单条查询挂掉）。"""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{PROM_URL}/api/v1/query", params={"query": query})
            resp.raise_for_status()
            data = resp.json()["data"]["result"]
            if not data:
                return "n/a"
            return data[0]["value"][1]
    except Exception:  # noqa: BLE001
        return "n/a"


def collect_snapshot() -> str:
    up_node = prom_query('up{job="node"}')
    up_backend = prom_query('up{job="backend"}')
    up_mysql = prom_query('up{job="mysqld"}')
    up_redis = prom_query('up{job="redis"}')
    probe = prom_query('probe_success{job="blackbox-http"}')
    disk_free = prom_query(
        'node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"}'
    )
    disk_free_g = f"{float(disk_free)/2**30:.1f}G" if disk_free not in ("n/a",) else disk_free
    mem_used = prom_query("1 - node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes")
    mem_pct = f"{float(mem_used)*100:.0f}%" if mem_used != "n/a" else mem_used
    appts = prom_query("clinic_appointments_created_total")

    return (
        f"📋 每日巡检 {time.strftime('%F %T')}\n"
        f"站点探测: {'✅' if probe == '1' else '❌ ' + probe}\n"
        f"up: node={up_node} backend={up_backend} mysql={up_mysql} redis={up_redis}\n"
        f"磁盘剩余: {disk_free_g} | 内存使用: {mem_pct}\n"
        f"累计预约单: {appts}\n"
    )


def daily_report() -> str:
    snapshot = collect_snapshot()
    if AI_ENABLED:
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    f"{LLM_BASE_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                    json={
                        "model": LLM_MODEL,
                        "messages": [{
                            "role": "user",
                            "content": "以下是服务器巡检数据，请给出不超过4行的健康简评与需要关注的事项:\n" + snapshot,
                        }],
                        "temperature": 0.2,
                    },
                )
                resp.raise_for_status()
                snapshot += "\n🤖 AI 简评:\n" + resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # noqa: BLE001
            log.error("巡检 AI 简评失败: %s", exc)
    return snapshot


@app.post("/report/run")
def run_report():
    """手动/定时触发巡检（cron: curl -X POST http://ai-bot:9500/report/run）"""
    report = daily_report()
    tg_send(report)
    return {"ok": True, "report": report}


@app.get("/health")
def health():
    return {"ok": True, "ai": AI_ENABLED, "tg": bool(TG_BOT_TOKEN and TG_CHAT_ID)}
