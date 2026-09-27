"""医生/排班/预约。核心规则：
- active_key 唯一索引 = 数据库层双订防线（取消置 NULL 释放号源）
- booking_delay_seconds() = Redis 只读探活 + 可观测业务指标
"""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, Histogram
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Appointment, Doctor, Patient, Schedule
from .auth import current_patient

router = APIRouter(tags=["clinic"])

# Prometheus 业务指标：面试讲「自定义业务指标接入监控」的落点
APPT_CREATED = Counter("clinic_appointments_created_total", "预约创建成功数")
APPT_CANCELLED = Counter("clinic_appointments_cancelled_total", "预约取消数")
APPT_CONFLICTS = Counter("clinic_appointment_conflicts_total", "号源冲突(409)次数")
BOOKING_LATENCY = Histogram(
    "clinic_booking_request_seconds", "预约接口耗时", buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5)
)


@BOOKING_LATENCY.time()
@router.post("/appointments")
def book(body: dict, db: Session = Depends(get_db), patient: Patient = Depends(current_patient)):
    schedule_id = body.get("schedule_id")
    if not isinstance(schedule_id, int):
        raise HTTPException(status_code=422, detail="schedule_id 必须是整数")
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="号源不存在")
    if schedule.slot_date < dt.date.today():
        raise HTTPException(status_code=409, detail="不能预约过去的时段")

    booked = db.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.schedule_id == schedule_id,
            Appointment.status == "BOOKED",
        )
    )
    if booked >= schedule.capacity:
        APPT_CONFLICTS.inc()
        raise HTTPException(status_code=409, detail="该号源已被约满")

    doctor = db.get(Doctor, schedule.doctor_id)
    appt = Appointment(
        patient_id=patient.id,
        doctor_id=schedule.doctor_id,
        schedule_id=schedule.id,
        slot_date=schedule.slot_date,
        slot_time=schedule.slot_time,
        status="BOOKED",
        active_key=f"doc-{schedule.doctor_id}-{schedule.slot_date.isoformat()}-{schedule.slot_time.isoformat()}",
    )
    db.add(appt)
    try:
        db.commit()  # 撞 active_key 唯一索引 → IntegrityError = 双订防线兜底
    except IntegrityError:
        db.rollback()
        APPT_CONFLICTS.inc()
        raise HTTPException(status_code=409, detail="该号源刚刚被抢，请选其它时段")
    APPT_CREATED.inc()
    return _appt_view(db, appt)


@router.get("/doctors")
def list_doctors(db: Session = Depends(get_db)):
    doctors = db.scalars(select(Doctor).order_by(Doctor.dept, Doctor.name)).all()
    return [
        {"id": d.id, "dept": d.dept, "name": d.name, "title": d.title, "intro": d.intro}
        for d in doctors
    ]


@router.get("/schedules")
def list_schedules(days: int = 3, db: Session = Depends(get_db)):
    """未来 days 天的排班 + 已约人数（前端据此渲染 可约/约满）。"""
    today = dt.date.today()
    end = today + dt.timedelta(days=max(1, min(days, 14)))
    # SUM(CASE WHEN ...) 统计有效预约：MySQL 无 COUNT FILTER（那是 PG 语法），CASE 全方言通吃
    rows = db.execute(
        select(
            Schedule,
            Doctor,
            func.sum(case((Appointment.status == "BOOKED", 1), else_=0)),
        )
        .join(Doctor, Doctor.id == Schedule.doctor_id)
        .outerjoin(Appointment, Appointment.schedule_id == Schedule.id)
        .where(Schedule.slot_date >= today, Schedule.slot_date <= end)
        .group_by(Schedule.id)
        .order_by(Schedule.slot_date, Schedule.slot_time, Doctor.dept)
    ).all()
    return [
        {
            "schedule_id": s.id,
            "doctor_id": d.id,
            "dept": d.dept,
            "doctor": d.name,
            "title": d.title,
            "date": s.slot_date.isoformat(),
            "time": s.slot_time.isoformat(timespec="minutes"),
            "booked": cnt,
            "capacity": s.capacity,
        }
        for s, d, cnt in rows
    ]


@router.get("/appointments/mine")
def my_appointments(db: Session = Depends(get_db), patient: Patient = Depends(current_patient)):
    rows = db.execute(
        select(Appointment, Doctor)
        .join(Doctor, Doctor.id == Appointment.doctor_id)
        .where(Appointment.patient_id == patient.id)
        .order_by(Appointment.created_at.desc())
    ).all()
    return [
        {
            "id": a.id,
            "dept": d.dept,
            "doctor": d.name,
            "date": a.slot_date.isoformat(),
            "time": a.slot_time.isoformat(timespec="minutes"),
            "status": a.status,
        }
        for a, d in rows
    ]


@router.post("/appointments/{appt_id}/cancel")
def cancel(appt_id: int, db: Session = Depends(get_db), patient: Patient = Depends(current_patient)):
    appt = db.get(Appointment, appt_id)
    if appt is None or appt.patient_id != patient.id:
        raise HTTPException(status_code=404, detail="预约不存在")
    if appt.status != "BOOKED":
        raise HTTPException(status_code=409, detail="预约已取消")
    appt.status = "CANCELLED"
    appt.active_key = None  # 释放号源：唯一索引允许多个 NULL
    appt.cancelled_at = dt.datetime.utcnow()
    db.commit()
    APPT_CANCELLED.inc()
    return {"ok": True}


def _appt_view(db: Session, appt: Appointment) -> dict:
    doctor = db.get(Doctor, appt.doctor_id)
    return {
        "id": appt.id,
        "dept": doctor.dept,
        "doctor": doctor.name,
        "date": appt.slot_date.isoformat(),
        "time": appt.slot_time.isoformat(timespec="minutes"),
        "status": appt.status,
    }
