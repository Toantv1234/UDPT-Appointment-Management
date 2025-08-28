from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from src.services.appointment_service import AppointmentService
from src.dto.appointment_dto import (
    # Response DTOs
    DepartmentResponseDTO, DoctorResponseDTO,
    AvailableSlotResponseDTO, AppointmentResponseDTO, AppointmentDetailResponseDTO,
    PendingAppointmentResponseDTO, MessageResponseDTO,

    # Request DTOs
    AppointmentCreateDTO, AppointmentUpdateDTO,
    AppointmentConfirmDTO, AppointmentCancelDTO,

    # Query DTOs
    AvailableSlotQueryDTO, AppointmentListQueryDTO,

    # Enums
    AppointmentStatusEnum
)
from src.dto.pagination_dto import PaginatedResponseDTO, PaginationRequestDTO
from config import get_db

router = APIRouter(prefix="/appointments", tags=["appointments"])

def get_appointment_service(db: Session = Depends(get_db)) -> AppointmentService:
    """Dependency để get AppointmentService instance"""
    return AppointmentService(db)

# ===============================
# User Profile & Authentication
# ===============================

@router.get(
    "/profile",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get user profile",
    description="Get current user's profile (doctor or patient)"
)
async def get_user_profile(
        current_user_id: int = Query(..., gt=0, description="Current authenticated user ID"),
        service: AppointmentService = Depends(get_appointment_service)
):
    """
    Lấy thông tin profile của user hiện tại
    """
    return service.get_user_profile(current_user_id)

@router.get(
    "/my-appointments",
    response_model=List[AppointmentResponseDTO],
    status_code=status.HTTP_200_OK,
    summary="Get current user appointments",
    description="Get appointments for current user (doctor or patient)"
)
async def get_my_appointments(
        current_user_id: int = Query(..., gt=0, description="Current authenticated user ID"),
        service: AppointmentService = Depends(get_appointment_service)
):
    """
    Lấy danh sách lịch khám của user hiện tại
    """
    return service.get_current_user_appointments(current_user_id)

# ===============================
# Supporting Endpoints for Use Cases
# ===============================

@router.get(
    "/departments",
    response_model=List[DepartmentResponseDTO],
    status_code=status.HTTP_200_OK,
    summary="Get departments list",
    description="Get list of active departments for appointment booking"
)
async def get_departments(
        service: AppointmentService = Depends(get_appointment_service)
):
    """
    Use Case Support: Lấy danh sách khoa cho bệnh nhân chọn
    """
    return service.get_departments()

@router.get(
    "/departments/{department_id}/doctors",
    response_model=List[DoctorResponseDTO],
    status_code=status.HTTP_200_OK,
    summary="Get doctors by department",
    description="Get list of active doctors in a specific department"
)
async def get_doctors_by_department(
        department_id: int = Path(..., gt=0, description="Department ID"),
        service: AppointmentService = Depends(get_appointment_service)
):
    """
    Use Case Support: Lấy danh sách bác sĩ trong khoa
    """
    return service.get_doctors_by_department(department_id)

@router.get(
    "/available-slots",
    response_model=List[AvailableSlotResponseDTO],
    status_code=status.HTTP_200_OK,
    summary="Get available time slots",
    description="Get available appointment slots for booking"
)
async def get_available_slots(
        doctor_id: Optional[int] = Query(None, gt=0, description="Filter by doctor ID"),
        department_id: Optional[int] = Query(None, gt=0, description="Filter by department ID"),
        available_date: Optional[date] = Query(None, description="Filter by specific date"),
        from_date: Optional[date] = Query(None, description="Filter from date"),
        to_date: Optional[date] = Query(None, description="Filter to date"),
        service: AppointmentService = Depends(get_appointment_service)
):
    """
    Use Case Support: Lấy lịch trống của bác sĩ
    """
    query_params = AvailableSlotQueryDTO(
        doctor_id=doctor_id,
        department_id=department_id,
        available_date=available_date,
        from_date=from_date,
        to_date=to_date
    )
    return service.get_available_slots(query_params)

# ===============================
# USE CASE 1: Đặt lịch khám
# ===============================

@router.post(
    "/",
    response_model=AppointmentResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Book new appointment",
    description="Create a new appointment booking"
)
async def create_appointment(
        appointment_data: AppointmentCreateDTO,
        service: AppointmentService = Depends(get_appointment_service)
):
    """
    USE CASE 1: Đặt lịch khám

    Flow:
    1. Bệnh nhân đã được tạo ở microservice khác
    2. Bệnh nhân chọn khoa khám
    3. Bệnh nhân chọn bác sĩ trong khoa
    4. Hệ thống hiển thị lịch trống của bác sĩ
    5. Bệnh nhân chọn thời gian và nhập lý do khám
    6. Tạo lịch khám với trạng thái PENDING
    """
    return service.create_appointment(appointment_data)

# ===============================
# USE CASE 2: Xác nhận lịch khám
# ===============================

@router.get(
    "/doctor/{doctor_id}/pending",
    response_model=List[PendingAppointmentResponseDTO],
    status_code=status.HTTP_200_OK,
    summary="Get pending appointments for doctor",
    description="Get list of pending appointments that need doctor confirmation"
)
async def get_pending_appointments(
        doctor_id: int = Path(..., gt=0, description="Doctor ID"),
        service: AppointmentService = Depends(get_appointment_service)
):
    """
    USE CASE 2: Lấy danh sách lịch chờ xác nhận của bác sĩ
    """
    return service.get_pending_appointments_by_doctor(doctor_id)

@router.put(
    "/{appointment_id}/confirm",
    response_model=MessageResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Confirm or reject appointment",
    description="Doctor confirms or rejects a pending appointment"
)
async def confirm_appointment(
        appointment_id: int = Path(..., gt=0, description="Appointment ID"),
        confirm_data: AppointmentConfirmDTO = ...,
        confirmed_by: int = Query(..., gt=0, description="Doctor ID who is confirming"),
        service: AppointmentService = Depends(get_appointment_service)
):
    """
    USE CASE 2: Xác nhận hoặc từ chối lịch khám

    Flow:
    1. Bác sĩ xem danh sách lịch chờ xác nhận
    2. Bác sĩ chọn lịch khám để xác nhận/từ chối
    3. Hệ thống cập nhật trạng thái lịch khám
    4. Gửi thông báo cho bệnh nhân
    """
    return service.confirm_appointment(appointment_id, confirm_data, confirmed_by)

# ===============================
# USE CASE 3: Cập nhật lịch khám
# ===============================

@router.put(
    "/{appointment_id}",
    response_model=AppointmentResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Update appointment",
    description="Patient updates their appointment details"
)
async def update_appointment(
        appointment_id: int = Path(..., gt=0, description="Appointment ID"),
        update_data: AppointmentUpdateDTO = ...,
        updated_by: int = Query(..., gt=0, description="Patient ID who is updating"),
        service: AppointmentService = Depends(get_appointment_service)
):
    """
    USE CASE 3: Cập nhật lịch khám

    Flow:
    1. Bệnh nhân truy cập danh sách lịch khám của mình
    2. Chọn lịch khám cần cập nhật
    3. Thay đổi thông tin (thời gian, bác sĩ, lý do)
    4. Hệ thống kiểm tra tính khả dụng
    5. Cập nhật lịch khám
    """
    return service.update_appointment(appointment_id, update_data, updated_by)

# ===============================
# USE CASE 4: Hủy lịch khám
# ===============================

@router.delete(
    "/{appointment_id}/cancel",
    response_model=MessageResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Cancel appointment",
    description="Cancel an existing appointment"
)
async def cancel_appointment(
        appointment_id: int = Path(..., gt=0, description="Appointment ID"),
        cancel_data: AppointmentCancelDTO = ...,
        cancelled_by_user: int = Query(..., gt=0, description="User ID who is cancelling"),
        service: AppointmentService = Depends(get_appointment_service)
):
    """
    USE CASE 4: Hủy lịch khám

    Flow:
    1. Người dùng truy cập danh sách lịch khám
    2. Chọn lịch khám cần hủy
    3. Nhập lý do hủy (tùy chọn)
    4. Xác nhận hủy lịch
    5. Hệ thống giải phóng slot thời gian
    """
    return service.cancel_appointment(appointment_id, cancel_data, cancelled_by_user)

# ===============================
# Query Endpoints
# ===============================

@router.get(
    "/",
    response_model=PaginatedResponseDTO[AppointmentResponseDTO],
    status_code=status.HTTP_200_OK,
    summary="Get appointments with filters",
    description="Get paginated list of appointments with various filters"
)
async def get_appointments(
        # Pagination
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, description="Items per page"),

        # Filters
        patient_id: Optional[int] = Query(None, gt=0, description="Filter by patient ID"),
        doctor_id: Optional[int] = Query(None, gt=0, description="Filter by doctor ID"),
        department_id: Optional[int] = Query(None, gt=0, description="Filter by department ID"),
        status: Optional[AppointmentStatusEnum] = Query(None, description="Filter by appointment status"),
        is_emergency: Optional[bool] = Query(None, description="Filter by emergency status"),
        appointment_date: Optional[date] = Query(None, description="Filter by specific date"),
        from_date: Optional[date] = Query(None, description="Filter from date"),
        to_date: Optional[date] = Query(None, description="Filter to date"),

        service: AppointmentService = Depends(get_appointment_service)
):
    """
    Lấy danh sách lịch khám với bộ lọc và phân trang
    """
    pagination_request = PaginationRequestDTO(page=page, page_size=page_size)
    query_params = AppointmentListQueryDTO(
        patient_id=patient_id,
        doctor_id=doctor_id,
        department_id=department_id,
        status=status,
        is_emergency=is_emergency,
        appointment_date=appointment_date,
        from_date=from_date,
        to_date=to_date
    )

    return service.get_appointments(query_params, pagination_request)

@router.get(
    "/{appointment_id}",
    response_model=AppointmentDetailResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Get appointment details",
    description="Get detailed information of a specific appointment"
)
async def get_appointment_detail(
        appointment_id: int = Path(..., gt=0, description="Appointment ID"),
        service: AppointmentService = Depends(get_appointment_service)
):
    """
    Lấy chi tiết lịch khám
    """
    return service.get_appointment_detail(appointment_id)

@router.get(
    "/patient/{patient_id}",
    response_model=List[AppointmentResponseDTO],
    status_code=status.HTTP_200_OK,
    summary="Get patient appointments",
    description="Get all appointments for a specific patient"
)
async def get_patient_appointments(
        patient_id: int = Path(..., gt=0, description="Patient ID"),
        status: Optional[str] = Query(None, description="Filter by status"),
        service: AppointmentService = Depends(get_appointment_service)
):
    """
    Lấy danh sách lịch khám của bệnh nhân (hỗ trợ Use Case 3, 4)
    """
    return service.get_patient_appointments(patient_id, status)