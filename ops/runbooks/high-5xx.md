# Runbook: High5xx（5xx 占比 >5%）

> 状态：AI 起草 v1 → 人工验证签收：____（日期）

## 1. 定位
```bash
# 哪个 endpoint 在 5xx（Prometheus）
sum by (endpoint,status) (rate(http_requests_total{status=~"5.."}[5m]))
# 日志找栈
docker logs --tail 200 clinic-backend 2>&1 | grep -B2 -A8 'Error\|Traceback'
```

## 2. 分支
- 500 + DB OperationalError → mysql 状态（runbook mysql-down）
- 500 + Redis Timeout → redis（runbook redis-down）
- 502/504（来自 nginx 层）→ backend 假死：`docker exec clinic-backend pkill -USR1 uvicorn`（日志重开）或 recreate
- 429/限流面 → 上游依赖容量问题，评估降级（关非核心功能）

## 3. 恢复验证
5xx 率回 <1%；业务冒烟：预约→取消一单。

## 4. 复盘
哪个依赖最脆弱；慢查询要不要加索引（EXPLAIN 实证）。
