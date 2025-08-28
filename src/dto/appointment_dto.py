from pydantic import BaseModel, Field
from datetime import datetime, date, time
from typing import Optional, List
from enum import Enum

class AppointmentStatusEnum(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class CancelledByEnum(str, Enum):
    PATIENT = "PATIENT"
    DOCTOR = "DOCTOR"

# ===============================
# Department DTOs
# ===============================

class DepartmentResponseDTO(BaseModel):
    id: int
    name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ===============================
# Doctor DTOs
# ===============================

class DoctorResponseDTO(BaseModel):
    id: int
    name: str
    department_id: int
    department_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ===============================
# Patient DTOs (Read-only - patients managed by other microservice)
# ===============================

class PatientResponseDTO(BaseModel):
    id: int
    name: str
    phone: Optional[str]
    email: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# ===============================
# Available Slot DTOs
# ===============================

class AvailableSlotResponseDTO(BaseModel):
    slot_id: int
    doctor_id: int
    doctor_name: str
    department_name: str
    available_date: date
    start_time: time
    end_time: time

    class Config:
        from_attributes = True

# ===============================
# Appointment DTOs
# ===============================

class AppointmentCreateDTO(BaseModel):
    """Use Case 1: Đặt lịch khám"""
    patient_id: int = Field(..., gt=0, description="Patient ID")
    doctor_id: int = Field(..., gt=0, description="Doctor ID")
    department_id: int = Field(..., gt=0, description="Department ID")
    slot_id: int = Field(..., gt=0, description="Available slot ID")
    reason: str = Field(..., min_length=5, max_length=500, description="Reason for appointment")
    is_emergency: bool = Field(default=False, description="Emergency appointment flag")

class AppointmentUpdateDTO(BaseModel):
    """Use Case 3: Cập nhật lịch khám"""
    doctor_id: Optional[int] = Field(None, gt=0, description="New doctor ID")
    slot_id: Optional[int] = Field(None, gt=0, description="New slot ID")
    reason: Optional[str] = Field(None, min_length=5, max_length=500, description="Updated reason")
    is_emergency: Optional[bool] = Field(None, description="Update emergency status")

class AppointmentConfirmDTO(BaseModel):
    """Use Case 2: Xác nhận lịch khám"""
    action: str = Field(..., description="'confirm' or 'reject'")
    rejection_reason: Optional[str] = Field(None, description="Required if action is 'reject'")

class AppointmentCancelDTO(BaseModel):
    """Use Case 4: Hủy lịch khám"""
    cancelled_by: CancelledByEnum = Field(..., description="Who cancelled the appointment")
    cancellation_reason: Optional[str] = Field(None, max_length=500, description="Reason for cancellation")

class AppointmentResponseDTO(BaseModel):
    id: int
    patient_id: int
    patient_name: str
    doctor_id: int
    doctor_name: str
    department_id: int
    department_name: str
    appointment_date: date
    appointment_time: time
    reason: str
    is_emergency: bool
    status: AppointmentStatusEnum
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AppointmentDetailResponseDTO(AppointmentResponseDTO):
    """Extended appointment details"""
    slot_id: int
    confirmed_by: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    rejected_at: Optional[datetime] = None
    cancelled_by: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None

    class Config:
        from_attributes = True

class PendingAppointmentResponseDTO(BaseModel):
    """Use Case 2: Lịch chờ xác nhận của bác sĩ"""
    id: int
    doctor_id: int
    patient_name: str
    patient_phone: Optional[str]
    doctor_name: str
    department_name: str
    appointment_date: date
    appointment_time: time
    reason: str
    is_emergency: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ===============================
# Common Response DTOs
# ===============================

class MessageResponseDTO(BaseModel):
    message: str
    status: str = "success"

class ErrorResponseDTO(BaseModel):
    message: str
    status: str = "error"
    error_code: Optional[str] = None

# ===============================
# Query DTOs
# ===============================

class DepartmentListQueryDTO(BaseModel):
    is_active: Optional[bool] = True

class DoctorListQueryDTO(BaseModel):
    department_id: Optional[int] = None
    is_active: Optional[bool] = True

class AvailableSlotQueryDTO(BaseModel):
    doctor_id: Optional[int] = None
    department_id: Optional[int] = None
    available_date: Optional[date] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None

class AppointmentListQueryDTO(BaseModel):
    patient_id: Optional[int] = None
    doctor_id: Optional[int] = None
    department_id: Optional[int] = None
    status: Optional[AppointmentStatusEnum] = None
    is_emergency: Optional[bool] = None
    appointment_date: Optional[date] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None