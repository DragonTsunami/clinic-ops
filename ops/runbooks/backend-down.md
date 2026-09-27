# Runbook: BackendDown（后端不可达）

> 状态：AI 起草 v1 → 人工验证签收：____（日期）
> 告警: `BackendDown` (P1) · upstream: prometheus up{job=backend}==0 持续 2m

## 1. 确认
```bash
docker ps -a --filter name=clinic-backend      # 状态？restarting？
docker logs --tail 100 clinic-backend          # 崩溃栈/OOM？
docker inspect clinic-backend --format '{{.State.OOMKilled}} {{.RestartCount}}'
```

## 2. 分支处置
- **OOMKilled=true** → 内存围栏 400m 太紧：查泄漏（uvicorn worker 常驻涨）→ 临时 `docker compose up -d --force-recreate backend`，事后调 mem_limit 或加 worker 上限
- **数据库连不上**（栈栈 ConnectionError）→ 跳 Runbook: mysql-down
- **代码异常 crash loop** → `git log -1` 看最近变更 → 回滚：`docker compose pull backend@sha256:<上个版本>`（或 git revert + 重新部署）

## 3. 恢复验证
```bash
curl -sf http://127.0.0.1:8080/api/health/deep   # ok:true
```
Prometheus `up{job="backend"}` 回 1，Alertmanager 收到 resolved。

## 4. 复盘必答
根因 / 为什么告警才发现 / 检测能否更早 / runbook 哪步要改
