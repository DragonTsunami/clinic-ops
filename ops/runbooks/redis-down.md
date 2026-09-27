# Runbook: RedisDown

> 状态：AI 起草 v1 → 人工验证签收：____（日期）

## 1. 确认
```bash
docker ps -a --filter name=clinic-redis
docker logs --tail 50 clinic-redis
docker exec clinic-redis redis-cli -a "$REDIS_PASSWORD" ping
```

## 2. 处置
- 容器挂 → `docker compose up -d redis`（命名卷 clinic_redis_data，数据在）
- 内存超限（60m 围栏小了）→ 调 mem_limit；给 redis 配 maxmemory+allkeys-lru（视用途）

## 3. 恢复验证
up{job=redis}=1；/api/health/deep redis:ok。

## 4. 业务影响评估
当前 Redis 用于探活与会话扩展位；宕机期间预约主链路（MySQL）不受影响——如实评估，不夸大。
