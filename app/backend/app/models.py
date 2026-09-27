"""ORM 模型。关键设计：appointments.active_key = 医生+日期+时段 的唯一指纹，
取消后置 NULL —— MySQL 唯一索引允许多个 NULL，因此「同一号源同时只允许一张有效预约」
由数据库层保证，并发抢号也不会双订。"""
import datetime as dt

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dept: Mapped[str] = mapped_column(String(32), index=True)   # 科室
    name: Mapped[str] = mapped_column(String(32))               # 姓名（合成数据）
    title: Mapped[str] = mapped_column(String(32))              # 职称
    intro: Mapped[str] = mapped_column(String(255), default="")


class Schedule(Base):
    """排班：某医生某天某时段的号源。capacity 通常为 1。"""

    __tablename__ = "schedules"
    __table_args__ = (
        UniqueConstraint("doctor_id", "slot_date", "slot_time", name="uq_schedule"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    slot_date: Mapped[dt.date] = mapped_column(Date, index=True)
    slot_time: Mapped[dt.time] = mapped_column(Time)
    capacity: Mapped[int] = mapped_column(Integer, default=1)


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32))
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id"), index=True)
    slot_date: Mapped[dt.date] = mapped_column(Date)
    slot_time: Mapped[dt.time] = mapped_column(Time)
    status: Mapped[str] = mapped_column(
        Enum("BOOKED", "CANCELLED", name="appt_status"), default="BOOKED"
    )
    # BOOKED 时为 "doc-<id>-<date>-<time>"，CANCELLED 时置 NULL —— 双订防线
    active_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    cancelled_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
