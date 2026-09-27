"""患者注册/登录 + 当前用户依赖。"""
import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Patient
from ..security import create_token, decode_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    phone: str = Field(pattern=r"1\d{10}")  # 演示用中国大陆手机号格式
    password: str = Field(min_length=6, max_length=64)


class LoginIn(BaseModel):
    phone: str
    password: str


class TokenOut(BaseModel):
    token: str
    name: str


def current_patient(
    db: Session = Depends(get_db),
    # Header() 必须显式声明，否则同名参数会被当查询参数（踩过：Bearer 头读不到恒 401）
    authorization: Annotated[str | None, Header()] = None,
) -> Patient:
    """依赖注入：从 Authorization: Bearer <jwt> 解出患者。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    patient_id = decode_token(authorization.removeprefix("Bearer "))
    if patient_id is None:
        raise HTTPException(status_code=401, detail="登录已过期")
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return patient


@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    dup = db.scalar(select(Patient).where(Patient.phone == body.phone))
    if dup is not None:
        raise HTTPException(status_code=409, detail="该手机号已注册")
    patient = Patient(
        name=body.name,
        phone=body.phone,
        password_hash=hash_password(body.password),
        created_at=dt.datetime.utcnow(),
    )
    db.add(patient)
    db.commit()
    return TokenOut(token=create_token(patient.id), name=patient.name)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    patient = db.scalar(select(Patient).where(Patient.phone == body.phone))
    if patient is None or not verify_password(body.password, patient.password_hash):
        raise HTTPException(status_code=401, detail="手机号或密码错误")
    return TokenOut(token=create_token(patient.id), name=patient.name)
