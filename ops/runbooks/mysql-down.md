# Runbook: MysqlDown / MysqlTooManyConnections

> 状态：AI 起草 v1 → 人工验证签收：____（日期）

## 1. 确认
```bash
docker ps -a --filter name=clinic-mysql
docker logs --tail 100 clinic-mysql 2>&1 | grep -iE 'error|shutdown'
docker exec clinic-mysql sh -c 'mysqladmin -uroot -p"$MYSQL_ROOT_PASSWORD" status'
free -m    # innodb_buffer_pool 256M + 系统内存压力？
```

## 2. 分支处置
- **OOM killed** → 2G 机器先砍其它大户（Grafana/Loki retention），再调小 buffer_pool
- **连接数打满** → `SHOW PROCESSLIST` 找长事务/慢查询 → `KILL <id>`；应用侧 pool_size=5+overflow=5 上限可控
- **磁盘满导致停写** → Runbook: disk-full
- **数据文件损坏（起不来）** → 最后手段走 restore.sh（先备份现状数据目录！）

## 3. 恢复验证
`up{job="mysqld"}` 回 1；`/api/health/deep` db:ok；页面能预约一单。

## 4. 数据风险专项
宕机窗口内的注册/预约是否丢失（业务侧确认）；备份链是否完整（ls /opt/clinic/backups）。
