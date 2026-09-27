"""FastAPI 入口：建表+种子(lifespan) → CORS → 路由 → /metrics(Prometheus)。"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, make_asgi_app
from sqlalchemy import text

from .config import settings
from .db import Base, SessionLocal, engine
from .routers import auth, clinic
from .seed import seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("clinic")

app = FastAPI(title="青衫诊所预约系统", version="0.1.0")

# HTTP 总量/状态码指标（5xx 告警规则的依赖）。endpoint 取路由模板防高基数
HTTP_REQUESTS = Counter(
    "http_requests_total", "HTTP 请求总数", ["method", "endpoint", "status"]
)


@app.middleware("http")
async def http_metrics(request: Request, call_next):
    response = await call_next(request)
    route = request.scope.get("route")
    endpoint = getattr(route, "path", None) or "unmatched"
    HTTP_REQUESTS.labels(request.method, endpoint, str(response.status_code)).inc()
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 参数校验失败(422)统一翻译成人话：Pydantic 默认吐英文结构体，前端没法直接展示
_FIELD_NAMES = {"name": "姓名", "phone": "手机号", "password": "密码"}


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    msgs = []
    for err in exc.errors():
        field = err.get("loc", [])[-1] if err.get("loc") else ""
        name = _FIELD_NAMES.get(field, field)
        etype = err.get("type", "")
        if etype == "string_pattern_mismatch":
            msgs.append(f"{name}格式不正确（手机号需 11 位、以 1 开头）" if field == "phone"
                        else f"{name}格式不正确")
        elif etype == "string_too_short":
            msgs.append(f"{name}太短（密码至少 6 位）" if field == "password"
                        else f"{name}不能为空")
        elif etype == "string_too_long":
            msgs.append(f"{name}太长了")
        elif etype == "missing":
            msgs.append(f"请填写{name}")
        else:
            msgs.append(f"{name}填写有误")
    detail = "；".join(msgs) or "填写内容有误，请检查后重试"
    return JSONResponse(status_code=422, content={"detail": detail})


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    log.info("startup: tables ready, seed done")


@app.get("/health")
def health():
    """容器健康检查端点：只证明进程活着；DB 深度检查由监控的 blackbox 承担。"""
    return {"ok": True}


@app.get("/health/deep")
def health_deep():
    """供巡检用：真实打一次 DB/Redis。失败返回 503，可接告警。"""
    import redis as redis_lib

    from .config import settings as s

    try:
        db_status = "ok"
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        db_status = f"error: {exc}"

    try:
        r = redis_lib.Redis.from_url(s.REDIS_URL, socket_connect_timeout=2)
        redis_status = "ok" if r.ping() else "no-ping"
    except Exception as exc:  # noqa: BLE001
        redis_status = f"error: {exc}"

    ok = db_status == "ok" and redis_status == "ok"
    body = {"ok": ok, "db": db_status, "redis": redis_status}
    if ok:
        return body
    return JSONResponse(status_code=503, content=body)


app.include_router(auth.router, prefix="/api")
app.include_router(clinic.router, prefix="/api")
app.mount("/metrics", make_asgi_app())
