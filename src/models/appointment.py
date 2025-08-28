from sqlalchemy import Column, Integer, String, DateTime, Date, Time, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum
import enum
from config import Base

class AppointmentStatus(enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

# Department Model
class Department(Base):
    __tablename__ = "departments"
    __table_args__ = {"schema": "appointment_mgmt"}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    doctors = relationship("Doctor", back_populates="department")
    appointments = relationship("Appointment", back_populates="department")

    def __repr__(self):
        return f"<Department(id={self.id}, name='{self.name}')>"

# Doctor Model
class Doctor(Base):
    __tablename__ = "doctors"
    __table_args__ = {"schema": "appointment_mgmt"}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    department_id = Column(Integer, ForeignKey("appointment_mgmt.departments.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    department = relationship("Department", back_populates="doctors")
    available_slots = relationship("DoctorAvailableSlot", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")
    confirmed_appointments = relationship("Appointment", foreign_keys="Appointment.confirmed_by")

    def __repr__(self):
        return f"<Doctor(id={self.id}, name='{self.name}')>"

# Doctor Available Slots Model
class DoctorAvailableSlot(Base):
    __tablename__ = "doctor_available_slots"
    __table_args__ = {"schema": "appointment_mgmt"}

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("appointment_mgmt.doctors.id"), nullable=False)
    available_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_booked = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    doctor = relationship("Doctor", back_populates="available_slots")
    appointments = relationship("Appointment", back_populates="slot")

    def __repr__(self):
        return f"<DoctorAvailableSlot(id={self.id}, doctor_id={self.doctor_id}, date={self.available_date})>"

# Patient Model
class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = {"schema": "appointment_mgmt"}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    email = Column(String(100))
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    appointments = relationship("Appointment", back_populates="patient")

    def __repr__(self):
        return f"<Patient(id={self.id}, name='{self.name}')>"

# Appointment Model
class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = {"schema": "appointment_mgmt"}

    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    patient_id = Column(Integer, ForeignKey("appointment_mgmt.patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("appointment_mgmt.doctors.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("appointment_mgmt.departments.id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("appointment_mgmt.doctor_available_slots.id"), nullable=False)

    # Appointment Info
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time, nullable=False)
    reason = Column(Text, nullable=False)

    # Status Management
    status = Column(SQLEnum(AppointmentStatus), default=AppointmentStatus.PENDING)

    # Confirmation Info
    confirmed_by = Column(Integer, ForeignKey("appointment_mgmt.doctors.id"))
    confirmed_at = Column(DateTime)

    # Rejection Info
    rejection_reason = Column(Text)
    rejected_at = Column(DateTime)

    # Cancellation Info
    cancelled_by = Column(String(20))  # 'PATIENT' or 'DOCTOR'
    cancelled_at = Column(DateTime)
    cancellation_reason = Column(Text)

    # Audit
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments", foreign_keys=[doctor_id])
    department = relationship("Department", back_populates="appointments")
    slot = relationship("DoctorAvailableSlot", back_populates="appointments")
    confirmer = relationship("Doctor", foreign_keys=[confirmed_by])

    def __repr__(self):
        return f"<Appointment(id={self.id}, patient_id={self.patient_id}, status={self.status})>"