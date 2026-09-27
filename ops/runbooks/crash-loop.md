# Runbook: CrashLoop（容器重启风暴）

> 状态：AI 起草 v1 → 人工验证签收：____（日期）
> 告警: ContainerRestartStorm (P1) · 10 分钟重启 >3 次

## 1. 确认（先看是谁）
```bash
docker ps --format '{{.Names}} {{.Status}}' | grep -i restart
docker inspect <容器> --format '{{.RestartCount}} {{.State.OOMKilled}} {{.State.ExitCode}}'
docker logs --tail 80 <容器>
```

## 2. 分支
- ExitCode 137 + OOMKilled → 内存围栏（对照 runbook backend-down / mysql-down）
- ExitCode 1 + 应用栈 → 最近 push 引入？CI 回滚（pull 上个 sha）
- 配置错误（env 缺失 :?required 生效）→ .env 改动回滚

## 3. 恢复验证
restart 计数停止增长；up 指标回 1。

## 4. 复盘
restart: unless-stopped 掩盖了 crash（一直拉起）——告警规则就是为此设的，写进复盘。
