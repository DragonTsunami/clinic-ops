"""配置层：全部来自环境变量（.env），本地与生产共用一份代码。"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://clinic:clinic_pw@mysql:3306/clinic?charset=utf8mb4"
    REDIS_URL: str = "redis://redis:6379/0"
    JWT_SECRET: str = "change-me-in-production"
    JWT_EXPIRE_HOURS: int = 24
    CORS_ORIGINS: str = "*"  # 逗号分隔；生产由 nginx 同源代理，保持 * 亦无跨域面

    class Config:
        env_file = ".env"


settings = Settings()
