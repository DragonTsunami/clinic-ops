# Runbook: SiteProbeDown（站点黑盒探测失败）

> 状态：AI 起草 v1 → 人工验证签收：____（日期）
> 告警: `SiteProbeDown` (P1) · 用户视角整站不可用，优先级最高

## 1. 确认
```bash
curl -sI http://127.0.0.1:8080 | head -1        # 容器内入口
curl -sI https://<域名> | head -1               # 公网视角
docker ps --filter name=clinic-frontend
systemctl status nginx                          # 宿主 nginx（生产）
```

## 2. 分支处置
- **本机 8080 通、公网不通** → 云安全组/ufw 80/443 被关（对照三云控制台）；DNS 解析漂移 `dig <域名>`
- **8080 不通** → frontend 容器挂 → `docker compose up -d frontend`；backend 连带查
- **生产 nginx 挂** → `nginx -t` 看配置（最近 certbot 改写？）→ `systemctl reload nginx`

## 3. 恢复验证
黑盒 probe_success 回 1；手机浏览器真开一次站点。

## 4. 复盘必答
单点在哪（单机部署天然单点——如实说，PPT 里写清 RTO）
