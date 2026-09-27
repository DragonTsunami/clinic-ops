# Runbook: DiskFull（磁盘 <20%）

> 状态：AI 起草 v1 → 人工验证签收：____（日期）

## 1. 定位
```bash
df -h /                                  # 哪个挂载点
du -xh --max-depth=2 / 2>/dev/null | sort -rh | head -15
docker system df                         # docker 占了多少
```

## 2. 常见大户（按概率）
1. docker 日志（已配 10m×3 轮转，检查未配的老容器）: `sh -c 'truncate -s 0 /var/lib/docker/containers/*/*-json.log'`（应急）→ 补 logging 配置
2. 无用镜像: `docker image prune -af`（注意保留在用 tag）
3. 构建缓存: `docker builder prune -f`
4. 备份堆积: `ls -lh /opt/clinic/backups`（轮转 cron 是否正常跑）
5. MySQL binlog: `SHOW BINARY LOGS;` → `PURGE BINARY LOGS BEFORE NOW();`（确认有备份后）

## 3. 恢复验证
df -h 回到 >25%；DiskSpaceLow 告警 resolved。

## 4. 预防
备份轮转 7 天；监控 20% 阈值留缓冲；生产挂载大日志目录前先想轮转。
