"""首次启动种子数据：3 科室 6 医生 + 未来 3 天号源。幂等（表非空则跳过）。"""
import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Doctor, Schedule

DOCTORS = [
    ("全科", "王建平", "主治医师", "常见病、慢性病随访（合成演示数据）"),
    ("全科", "李文静", "副主任医师", "全科诊疗 12 年（合成演示数据）"),
    ("口腔科", "张伟", "主治医师", "龋齿/洁牙/牙体修复（合成演示数据）"),
    ("口腔科", "刘洋", "主任医师", "口腔外科与种植（合成演示数据）"),
    ("儿科", "陈静", "副主任医师", "儿童呼吸与消化（合成演示数据）"),
    ("儿科", "赵磊", "主治医师", "儿童保健与疫苗咨询（合成演示数据）"),
]

SLOT_TIMES = ("09:00", "09:30", "10:00", "10:30", "14:00", "14:30", "15:00", "15:30")


def seed(db: Session) -> None:
    if db.scalar(select(Doctor.id).limit(1)) is not None:
        return
    today = dt.date.today()
    for dept, name, title, intro in DOCTORS:
        doc = Doctor(dept=dept, name=name, title=title, intro=intro)
        db.add(doc)
        db.flush()
        for offset in range(3):
            for hhmm in SLOT_TIMES:
                hh, mm = hhmm.split(":")
                db.add(
                    Schedule(
                        doctor_id=doc.id,
                        slot_date=today + dt.timedelta(days=offset),
                        slot_time=dt.time(int(hh), int(mm)),
                        capacity=1,
                    )
                )
    db.commit()
