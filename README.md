# 青衫诊所 · 预约挂号系统（clinic-ops）

> 医疗预约最小业务系统（AI 代建）× 生产级运维（本人主导）× AI 运维四件套
> 目标硬件：2C2G~2C4G 云服务器（阿里云/AWS/腾讯云通用）· 本地与生产同构编排

## AI 协作方式

- 业务系统（app/）由 AI 起草，**人工逐文件验收**：每文件「我必须能讲清」的掌握边界见 [docs/ai-collab/读懂清单.md](docs/ai-collab/读懂清单.md)，实测拦截的 4 个 AI 产出缺陷及根因在同文件踩坑记录
- 验收靠证据不靠信任：E2E 14 项验收 + compose config 校验 + 删库恢复演练（D6），全部可复现
- AI 运维四件套三条红线：LLM 只接收运维指标不接触业务数据 / LLM 不可达降级为原始告警透传 / 只读不改无服务器操作权限

## 本地一键起

```bash
cp .env.example .env.local          # 本地默认值即可跑
docker compose --env-file .env.local -f infra/compose/docker-compose.yml up -d --build
# 浏览器打开 http://127.0.0.1:8080  → 注册 → 预约 → 「我的预约」
# 后端直调: http://127.0.0.1:8000/docs (Swagger)
```

监控面（可选，本地也可以起）：

```bash
docker network create clinic-net 2>/dev/null || true   # 首次需建共享网络（app 栈起过则已存在）
docker compose --env-file .env.local -f infra/monitoring-compose.yml up -d
# Grafana http://127.0.0.1:3000 (admin / .env 里的 GRAFANA_ADMIN_PASSWORD)
# Prometheus http://127.0.0.1:9090   Alertmanager http://127.0.0.1:9093
# 4g 加餐（日志+容器指标）: 追加 --profile extra
```

## 服务器部署（阿里云/AWS/腾讯云通用）

```bash
# 0) 密钥准备（本机，一次）
ssh-keygen -t ed25519

# 1) 云控制台：安全组放行 22/80/443（三云都做，ufw 是第二道门）
# 2) 填三处数据：
cp infra/ansible/vars.example.yml infra/ansible/vars.yml     # 🔴admin_user/公钥/域名
cp infra/ansible/inventory.example.ini infra/ansible/inventory.ini  # 🔴公网IP
# 3) 初始化服务器（用户/SSH加固/ufw/Docker/Nginx/备份cron，全幂等）
ssh-copy-id root@<IP>
ansible-playbook -i infra/ansible/inventory.ini infra/ansible/site.yml
# 4) 上代码 + 起栈
ssh devops@<IP>   # 之后全程用管理员账号
git clone <你的仓库> /opt/clinic/clinic-ops && cd /opt/clinic/clinic-ops
cp .env.example .env   # 🔴改 JWT_SECRET/各密码/GRAFANA_ADMIN_PASSWORD
docker compose --env-file .env -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.prod.yml up -d
docker compose --env-file .env -f infra/monitoring-compose.yml up -d
# 5) HTTPS（域名已解析到本机）
sudo certbot --nginx -d <域名>
# 6) 建库初始化（backend 启动自动建表+种子；exporter 账号由 mysql-init 自动建）
```

CI/CD：`.github/workflows/cicd.yml` push 即 lint+build+推 GHCR；服务器 secrets 配好后取消 deploy 注释即自动部署。

## 目录

```
app/backend     FastAPI + SQLAlchemy（预约事务/双订防线/JWT/Prometheus指标）
app/frontend    Vue3 + Vite（构建产物进 nginx 镜像）
infra/compose   应用栈编排（本地/生产同构，prod.yml 只收端口）
infra/monitoring(+yml)  监控栈编排 + prometheus/alertmanager/loki 配置（全部过官方校验器）
infra/ansible   云服务器初始化 playbook（三云通用）
infra/mysql-init  exporter 最小权限账号
ops/nginx       宿主 nginx 模板（certbot 升级 443）
ops/backup      每日备份(age加密) + 恢复脚本（演练用）
ops/ai-bot      告警AI分诊 + 每日巡检（selftest.py 可自测）
ops/runbooks    告警处置手册（AI起草→人工签收）
docs/ai-collab  ★ AI 协作痕迹（面试展品）
docs/drills     ★ 故障演练手册与记录
```

## 数据与合规声明

- 医生/排班为演示种子数据；患者数据全部来自测试注册（合成），**无任何真实患者信息**
- 备份静态加密（age）、AI 分诊只读运维指标（患者数据不出服务器）
- `.env*`/私钥/备份产物全部 gitignore

## 验收命令速查

```bash
docker compose --env-file .env.local -f infra/compose/docker-compose.yml ps        # 全 healthy
curl -s http://127.0.0.1:8080/health/deep | grep -o '"ok":true'                    # 深度健康
curl -s http://127.0.0.1:8000/metrics | grep clinic_appointments_created_total    # 业务指标
curl -sI http://127.0.0.1:8080 | head -1                                          # HTTP/1.1 200
```
