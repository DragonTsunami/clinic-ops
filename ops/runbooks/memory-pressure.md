# Runbook: MemoryPressure（内存 >90%）

> 状态：AI 起草 v1 → 人工验证签收：____（日期）

## 1. 定位
```bash
free -m
ps aux --sort=-%mem | head -8
docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' | sort -t/ -k1 -rh
```

## 2. 处置（按预算表逐层砍）
- 2G 机器：Loki/Promtail/cAdvisor 应在 slim 档（本就没起则跳过）
- Prometheus retention 15d→7d（重启生效）
- MySQL buffer_pool 256M→128M（预约低峰期做）
- 确认 swap：云主机默认无 swap → 加 1G swapfile 作为 OOM 缓冲（dd+fallocate 二选一，防卡死用 fallocate）

## 3. 恢复验证
内存 <80%；无 OOM kill 记录 `dmesg | grep -i oom`。

## 4. 复盘
谁是增长源（MySQL 连接池? Prometheus TSDB?）；容量规划是否要升级套餐。
