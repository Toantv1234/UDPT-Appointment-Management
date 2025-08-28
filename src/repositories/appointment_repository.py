from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, text
from typing import Optional, List
from datetime import date, datetime

from src.models.appointment import (
    Department, Doctor, DoctorAvailableSlot,
    Patient, Appointment, AppointmentStatus
)

class DepartmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_active(self) -> List[Department]:
        """Lấy danh sách khoa đang hoạt động"""
        return self.db.query(Department).filter(Department.is_active == True).all()

    def get_by_id(self, department_id: int) -> Optional[Department]:
        """Lấy khoa theo ID"""
        return self.db.query(Department).filter(Department.id == department_id).first()

class DoctorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_department(self, department_id: int) -> List[Doctor]:
        """Lấy danh sách bác sĩ theo khoa"""
        return (self.db.query(Doctor)
                .options(joinedload(Doctor.department))
                .filter(
            and_(
                Doctor.department_id == department_id,
                Doctor.is_active == True
            )
        )
                .all())

    def get_by_id(self, doctor_id: int) -> Optional[Doctor]:
        """Lấy bác sĩ theo ID"""
        return (self.db.query(Doctor)
                .options(joinedload(Doctor.department))
                .filter(Doctor.id == doctor_id)
                .first())

    def get_all_active(self) -> List[Doctor]:
        """Lấy tất cả bác sĩ đang hoạt động"""
        return (self.db.query(Doctor)
                .options(joinedload(Doctor.department))
                .filter(Doctor.is_active == True)
                .all())

class AvailableSlotRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_available_slots(
            self,
            doctor_id: Optional[int] = None,
            department_id: Optional[int] = None,
            from_date: Optional[date] = None,
            to_date: Optional[date] = None
    ) -> List[dict]:
        """Lấy lịch trống (sử dụng view)"""
        query = text("""
                     SELECT
                         s.id as slot_id,
                         s.doctor_id,
                         d.name as doctor_name,
                         dept.name as department_name,
                         s.available_date,
                         s.start_time,
                         s.end_time
                     FROM appointment_mgmt.doctor_available_slots s
                              JOIN appointment_mgmt.doctors d ON s.doctor_id = d.id
                              JOIN appointment_mgmt.departments dept ON d.department_id = dept.id
                     WHERE s.is_booked = FALSE
                       AND s.available_date >= CURRENT_DATE
                       AND d.is_active = TRUE
                       AND (:doctor_id IS NULL OR s.doctor_id = :doctor_id)
                       AND (:department_id IS NULL OR d.department_id = :department_id)
                       AND (:from_date IS NULL OR s.available_date >= :from_date)
                       AND (:to_date IS NULL OR s.available_date <= :to_date)
                     ORDER BY s.available_date, s.start_time
                     """)

        result = self.db.execute(query, {
            'doctor_id': doctor_id,
            'department_id': department_id,
            'from_date': from_date,
            'to_date': to_date
        })

        return [dict(row._mapping) for row in result.fetchall()]

    def get_by_id(self, slot_id: int) -> Optional[DoctorAvailableSlot]:
        """Lấy slot theo ID"""
        return self.db.query(DoctorAvailableSlot).filter(DoctorAvailableSlot.id == slot_id).first()

    def is_slot_available(self, slot_id: int) -> bool:
        """Kiểm tra slot có sẵn không"""
        slot = self.db.query(DoctorAvailableSlot).filter(
            and_(
                DoctorAvailableSlot.id == slot_id,
                DoctorAvailableSlot.is_booked == False,
                DoctorAvailableSlot.available_date >= date.today()
            )
        ).first()
        return slot is not None

class PatientRepository:
    """Read-only repository for patient validation (patients managed by other microservice)"""
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, patient_id: int) -> Optional[Patient]:
        """Lấy bệnh nhân theo ID - chỉ để validation"""
        return self.db.query(Patient).filter(Patient.id == patient_id).first()

class AppointmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, appointment: Appointment) -> Appointment:
        """Tạo lịch khám mới"""
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def get_by_id(self, appointment_id: int) -> Optional[Appointment]:
        """Lấy lịch khám theo ID với đầy đủ thông tin"""
        return (self.db.query(Appointment)
                .options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor),
            joinedload(Appointment.department),
            joinedload(Appointment.slot)
        )
                .filter(Appointment.id == appointment_id)
                .first())

    def get_patient_appointments(
            self,
            patient_id: int,
            status: Optional[AppointmentStatus] = None,
            from_date: Optional[date] = None,
            to_date: Optional[date] = None
    ) -> List[Appointment]:
        """Lấy lịch khám của bệnh nhân"""
        query = (self.db.query(Appointment)
                 .options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor),
            joinedload(Appointment.department)
        )
                 .filter(Appointment.patient_id == patient_id))

        if status:
            query = query.filter(Appointment.status == status)
        if from_date:
            query = query.filter(Appointment.appointment_date >= from_date)
        if to_date:
            query = query.filter(Appointment.appointment_date <= to_date)

        return query.order_by(Appointment.appointment_date.desc()).all()

    def get_pending_appointments_by_doctor(self, doctor_id: int) -> List[dict]:
        """Lấy lịch chờ xác nhận của bác sĩ (sử dụng view)"""
        query = text("""
                     SELECT
                         a.id,
                         a.doctor_id,
                         p.name as patient_name,
                         p.phone as patient_phone,
                         d.name as doctor_name,
                         dept.name as department_name,
                         a.appointment_date,
                         a.appointment_time,
                         a.reason,
                         a.created_at
                     FROM appointment_mgmt.appointments a
                              JOIN appointment_mgmt.patients p ON a.patient_id = p.id
                              JOIN appointment_mgmt.doctors d ON a.doctor_id = d.id
                              JOIN appointment_mgmt.departments dept ON a.department_id = dept.id
                     WHERE a.status = 'PENDING' AND a.doctor_id = :doctor_id
                     ORDER BY a.created_at ASC
                     """)

        result = self.db.execute(query, {'doctor_id': doctor_id})
        return [dict(row._mapping) for row in result.fetchall()]

    def update(self, appointment: Appointment) -> Appointment:
        """Cập nhật lịch khám"""
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def get_appointments_by_filters(
            self,
            patient_id: Optional[int] = None,
            doctor_id: Optional[int] = None,
            department_id: Optional[int] = None,
            status: Optional[AppointmentStatus] = None,
            appointment_date: Optional[date] = None,
            from_date: Optional[date] = None,
            to_date: Optional[date] = None
    ) -> List[Appointment]:
        """Lấy lịch khám theo bộ lọc"""
        query = (self.db.query(Appointment)
        .options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor),
            joinedload(Appointment.department)
        ))

        if patient_id:
            query = query.filter(Appointment.patient_id == patient_id)
        if doctor_id:
            query = query.filter(Appointment.doctor_id == doctor_id)
        if department_id:
            query = query.filter(Appointment.department_id == department_id)
        if status:
            query = query.filter(Appointment.status == status)
        if appointment_date:
            query = query.filter(Appointment.appointment_date == appointment_date)
        if from_date:
            query = query.filter(Appointment.appointment_date >= from_date)
        if to_date:
            query = query.filter(Appointment.appointment_date <= to_date)

        return query.order_by(Appointment.appointment_date.desc()).all()

    def check_appointment_conflict(
            self,
            doctor_id: int,
            appointment_date: date,
            appointment_time,
            exclude_appointment_id: Optional[int] = None
    ) -> bool:
        """Kiểm tra xung đột lịch khám"""
        query = self.db.query(Appointment).filter(
            and_(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == appointment_date,
                Appointment.appointment_time == appointment_time,
                Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED])
            )
        )

        if exclude_appointment_id:
            query = query.filter(Appointment.id != exclude_appointment_id)

        return query.first() is not None