import fastapi
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, date
from typing import List, Optional

from src.repositories.appointment_repository import (
    DepartmentRepository, DoctorRepository, AvailableSlotRepository,
    PatientRepository, AppointmentRepository
)
from src.models.appointment import (
    Department, Doctor, Patient, Appointment, AppointmentStatus
)
from src.dto.appointment_dto import (
    DepartmentResponseDTO, DoctorResponseDTO, PatientResponseDTO,
    AvailableSlotResponseDTO, AppointmentCreateDTO, AppointmentUpdateDTO,
    AppointmentConfirmDTO, AppointmentCancelDTO, AppointmentResponseDTO,
    AppointmentDetailResponseDTO, PendingAppointmentResponseDTO,
    AppointmentListQueryDTO, AvailableSlotQueryDTO, MessageResponseDTO
)
from src.dto.pagination_dto import PaginatedResponseDTO, PaginationRequestDTO
from src.services.user_auth_service import UserAuthService
from src.services.event_publisher import get_event_publisher  # Import event publisher
import logging

logger = logging.getLogger(__name__)

class AppointmentService:
    def __init__(self, db: Session):
        self.db = db
        self.dept_repo = DepartmentRepository(db)
        self.doctor_repo = DoctorRepository(db)
        self.slot_repo = AvailableSlotRepository(db)
        self.patient_repo = PatientRepository(db)
        self.appointment_repo = AppointmentRepository(db)
        self.user_auth_service = UserAuthService(self.doctor_repo, self.patient_repo)
        self.event_publisher = get_event_publisher()

    # ===============================
    # Use Case Support Methods
    # ===============================

    def get_departments(self) -> List[DepartmentResponseDTO]:
        """Lấy danh sách khoa cho use case: Đặt lịch khám"""
        departments = self.dept_repo.get_all_active()
        return [DepartmentResponseDTO.model_validate(dept) for dept in departments]

    def get_doctors_by_department(self, department_id: int) -> List[DoctorResponseDTO]:
        """Lấy bác sĩ theo khoa cho use case: Đặt lịch khám"""
        # Validate department exists
        department = self.dept_repo.get_by_id(department_id)
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Department with id {department_id} not found"
            )

        doctors = self.doctor_repo.get_by_department(department_id)
        result = []
        for doctor in doctors:
            doctor_dto = DoctorResponseDTO.model_validate(doctor)
            doctor_dto.department_name = doctor.department.name
            result.append(doctor_dto)
        return result

    def get_available_slots(self, query_params: AvailableSlotQueryDTO) -> List[AvailableSlotResponseDTO]:
        """Lấy lịch trống cho use case: Đặt lịch khám"""
        slots = self.slot_repo.get_available_slots(
            doctor_id=query_params.doctor_id,
            department_id=query_params.department_id,
            from_date=query_params.from_date or date.today(),
            to_date=query_params.to_date
        )

        return [AvailableSlotResponseDTO(**slot) for slot in slots]

    # ===============================
    # Use Case 1: Đặt lịch khám
    # ===============================

    def create_appointment(self, appointment_data: AppointmentCreateDTO) -> AppointmentResponseDTO:
        """Use Case 1: Đặt lịch khám"""

        # 1. Validate patient exists (managed by other microservice)
        self._validate_patient_exists(appointment_data.patient_id)

        # 2. Validate doctor exists and is active
        doctor = self.doctor_repo.get_by_id(appointment_data.doctor_id)
        if not doctor or not doctor.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Doctor with id {appointment_data.doctor_id} not found or inactive"
            )

        # 3. Validate department matches doctor's department
        if doctor.department_id != appointment_data.department_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Doctor does not belong to the specified department"
            )

        # 4. Validate slot is available
        if not self.slot_repo.is_slot_available(appointment_data.slot_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected time slot is not available"
            )

        # 5. Get slot details
        slot = self.slot_repo.get_by_id(appointment_data.slot_id)
        if not slot or slot.doctor_id != appointment_data.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid slot for the selected doctor"
            )

        # 6. Create appointment
        appointment = Appointment(
            patient_id=appointment_data.patient_id,
            doctor_id=appointment_data.doctor_id,
            department_id=appointment_data.department_id,
            slot_id=appointment_data.slot_id,
            appointment_date=slot.available_date,
            appointment_time=slot.start_time,
            reason=appointment_data.reason,
            is_emergency=appointment_data.is_emergency,
            status=AppointmentStatus.PENDING
        )

        # 7. Save appointment (trigger will automatically book the slot)
        created_appointment = self.appointment_repo.create(appointment)

        # 8. Return response
        return self._build_appointment_response(created_appointment)

    # ===============================
    # Use Case 2: Xác nhận lịch khám
    # ===============================

    def get_pending_appointments_by_doctor(self, doctor_id: int) -> List[PendingAppointmentResponseDTO]:
        """Use Case 2: Lấy lịch chờ xác nhận"""
        # Validate doctor exists
        doctor = self.doctor_repo.get_by_id(doctor_id)
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Doctor with id {doctor_id} not found"
            )

        pending_appointments = self.appointment_repo.get_pending_appointments_by_doctor(doctor_id)
        return [PendingAppointmentResponseDTO(**appointment) for appointment in pending_appointments]

    def confirm_appointment(self, appointment_id: int, confirm_data: AppointmentConfirmDTO, confirmed_by: int) -> MessageResponseDTO:
        """Use Case 2: Xác nhận hoặc từ chối lịch khám"""

        # 1. Get appointment
        appointment = self.appointment_repo.get_by_id(appointment_id)
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with id {appointment_id} not found"
            )

        # 2. Validate appointment is pending
        if appointment.status != AppointmentStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Appointment is not in PENDING status, current status: {appointment.status}"
            )

        # 3. Validate doctor authorization
        if appointment.doctor_id != confirmed_by:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only confirm your own appointments"
            )

        # 4. Process confirmation or rejection
        if confirm_data.action.lower() == 'confirm':
            appointment.status = AppointmentStatus.CONFIRMED
            appointment.confirmed_by = confirmed_by
            appointment.confirmed_at = datetime.now()
            message = f"Appointment {appointment_id} has been confirmed successfully"

            # PUBLISH RABBITMQ EVENT CHỈ KHI APPOINTMENT ĐƯỢC CONFIRM (PENDING → CONFIRMED)
            try:
                appointment_response = self._build_appointment_response(appointment)
                appointment_data = {
                    "id": appointment_response.id,
                    "patient_id": appointment_response.patient_id,
                    "patient_name": appointment_response.patient_name,
                    "doctor_id": appointment_response.doctor_id,
                    "doctor_name": appointment_response.doctor_name,
                    "department_id": appointment_response.department_id,
                    "department_name": appointment_response.department_name,
                    "appointment_date": appointment_response.appointment_date,
                    "appointment_time": appointment_response.appointment_time,
                    "reason": appointment_response.reason,
                    "is_emergency": appointment_response.is_emergency,
                    "confirmed_at": appointment.confirmed_at,
                    "confirmed_by": confirmed_by
                }

                self.event_publisher.publish_appointment_confirmed_today(appointment_data)
                logger.info(f"Published RabbitMQ event for confirmed appointment {appointment_id}")

            except Exception as e:
                # Log error but don't fail the main operation
                logger.error(f"Failed to publish RabbitMQ event for appointment {appointment_id}: {e}")

        elif confirm_data.action.lower() == 'reject':
            if not confirm_data.rejection_reason:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Rejection reason is required when rejecting an appointment"
                )

            appointment.status = AppointmentStatus.REJECTED
            appointment.rejection_reason = confirm_data.rejection_reason
            appointment.rejected_at = datetime.now()
            message = f"Appointment {appointment_id} has been rejected"

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action must be either 'confirm' or 'reject'"
            )

        # 5. Update appointment
        self.appointment_repo.update(appointment)

        return MessageResponseDTO(message=message)

    # ===============================
    # Use Case 3: Cập nhật lịch khám
    # ===============================

    def update_appointment(self, appointment_id: int, update_data: AppointmentUpdateDTO, updated_by_patient_id: int) -> AppointmentResponseDTO:
        """Use Case 3: Cập nhật lịch khám"""

        # 1. Get appointment
        appointment = self.appointment_repo.get_by_id(appointment_id)
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with id {appointment_id} not found"
            )

        # Validate ownership
        if appointment.patient_id != updated_by_patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own appointments"
            )

        # Validate appointment can be updated
        if appointment.status not in [AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update appointment with status: {appointment.status}"
            )

        # Validate appointment is not in the past
        if appointment.appointment_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update past appointments"
            )

        # 5. Process updates
        if update_data.doctor_id and update_data.doctor_id != appointment.doctor_id:
            new_doctor = self.doctor_repo.get_by_id(update_data.doctor_id)
            if not new_doctor or not new_doctor.is_active:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="New doctor not found or inactive"
                )
            if new_doctor.department_id != appointment.department_id:
                appointment.department_id = new_doctor.department_id
            appointment.doctor_id = update_data.doctor_id

        if update_data.slot_id and update_data.slot_id != appointment.slot_id:
            if not self.slot_repo.is_slot_available(update_data.slot_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="New time slot is not available"
                )
            new_slot = self.slot_repo.get_by_id(update_data.slot_id)
            if not new_slot:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="New slot not found"
                )
            if new_slot.doctor_id != appointment.doctor_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="New slot does not belong to the selected doctor"
                )
            appointment.slot_id = update_data.slot_id
            appointment.appointment_date = new_slot.available_date
            appointment.appointment_time = new_slot.start_time

        if update_data.reason:
            appointment.reason = update_data.reason

        if update_data.is_emergency is not None:
            appointment.is_emergency = update_data.is_emergency

        # 6. Update appointment
        updated_appointment = self.appointment_repo.update(appointment)

        return self._build_appointment_response(updated_appointment)

    # ===============================
    # Use Case 4: Hủy lịch khám
    # ===============================

    def cancel_appointment(self, appointment_id: int, cancel_data: AppointmentCancelDTO, cancelled_by_user_id: int) -> MessageResponseDTO:
        """Use Case 4: Hủy lịch khám"""

        # 1. Get appointment
        appointment = self.appointment_repo.get_by_id(appointment_id)
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with id {appointment_id} not found"
            )

        # 2. Validate appointment can be cancelled
        if appointment.status == AppointmentStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Appointment is already cancelled"
            )

        if appointment.status not in [AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel appointment with status: {appointment.status}"
            )

        # 3. Validate authorization
        if cancel_data.cancelled_by == "PATIENT":
            if appointment.patient_id != cancelled_by_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only cancel your own appointments"
                )
        elif cancel_data.cancelled_by == "DOCTOR":
            if appointment.doctor_id != cancelled_by_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only cancel your own appointments"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cancelled_by value"
            )

        # 4. Check time constraints for emergency vs regular appointments
        appointment_datetime = datetime.combine(appointment.appointment_date, appointment.appointment_time)
        hours_until_appointment = (appointment_datetime - datetime.now()).total_seconds() / 3600

        # Different rules for emergency vs regular appointments
        if not appointment.is_emergency and hours_until_appointment < 2:  # Regular appointments: 2 hours minimum
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel regular appointment within 2 hours of scheduled time. Please contact the hospital directly."
            )
        elif appointment.is_emergency and hours_until_appointment < 0.5:  # Emergency appointments: 30 minutes minimum
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel emergency appointment within 30 minutes of scheduled time. Please contact the hospital directly."
            )


        was_previously_confirmed = appointment.status == AppointmentStatus.CONFIRMED

        # 5. Cancel appointment
        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancelled_by = cancel_data.cancelled_by
        appointment.cancelled_at = datetime.now()
        appointment.cancellation_reason = cancel_data.cancellation_reason

        # 6. Update appointment (trigger will release the slot)
        updated_appointment = self.appointment_repo.update(appointment)

        # PUBLISH RABBITMQ EVENT CHỈ NẾU APPOINTMENT TRƯỚC ĐÓ ĐÃ CONFIRMED (CONFIRMED → CANCELLED)
        if was_previously_confirmed:
            try:
                appointment_response = self._build_appointment_response(updated_appointment)
                appointment_data = {
                    "id": appointment_response.id,
                    "patient_id": appointment_response.patient_id,
                    "patient_name": appointment_response.patient_name,
                    "doctor_id": appointment_response.doctor_id,
                    "doctor_name": appointment_response.doctor_name,
                    "department_id": appointment_response.department_id,
                    "department_name": appointment_response.department_name,
                    "appointment_date": appointment_response.appointment_date,
                    "appointment_time": appointment_response.appointment_time,
                    "reason": appointment_response.reason,
                    "is_emergency": appointment_response.is_emergency,
                    "status": appointment_response.status.value,
                    "cancelled_by": cancel_data.cancelled_by,
                    "cancelled_at": appointment.cancelled_at.isoformat(),
                    "cancellation_reason": cancel_data.cancellation_reason
                }

                self.event_publisher.publish_appointment_cancelled(appointment_data)
                logger.info(f"Published RabbitMQ event for cancelled appointment {appointment_id} (was previously confirmed)")

            except Exception as e:
                logger.error(f"Failed to publish RabbitMQ event for cancelled appointment {appointment_id}: {e}")
        else:
            logger.info(f"No event published for cancelled appointment {appointment_id} (was not previously confirmed)")

        return MessageResponseDTO(message=f"Appointment {appointment_id} has been cancelled successfully")

    # ===============================
    # Query Methods
    # ===============================

    def get_appointments(self, query_params: AppointmentListQueryDTO, pagination: PaginationRequestDTO) -> PaginatedResponseDTO[AppointmentResponseDTO]:
        """Lấy danh sách lịch khám với phân trang"""

        # Get all appointments matching filters (for now, without pagination in repository)
        appointments = self.appointment_repo.get_appointments_by_filters(
            patient_id=query_params.patient_id,
            doctor_id=query_params.doctor_id,
            department_id=query_params.department_id,
            status=query_params.status,
            is_emergency=query_params.is_emergency,
            appointment_date=query_params.appointment_date,
            from_date=query_params.from_date,
            to_date=query_params.to_date
        )

        # Manual pagination
        total = len(appointments)
        if total == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No appointments found matching the criteria"
            )

        skip = pagination.calc_skip()
        if skip >= total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page number exceeds total number of pages"
            )

        paginated_appointments = appointments[skip:skip + pagination.page_size]

        # Convert to response DTOs
        appointment_responses = [self._build_appointment_response(appointment) for appointment in paginated_appointments]

        return PaginatedResponseDTO.create(
            data=appointment_responses,
            page=pagination.page,
            page_size=pagination.page_size,
            total=total
        )

    def get_appointment_detail(self, appointment_id: int) -> AppointmentDetailResponseDTO:
        """Lấy chi tiết lịch khám"""
        appointment = self.appointment_repo.get_by_id(appointment_id)
        if not appointment:
            raise HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with id {appointment_id} not found"
            )

        return AppointmentDetailResponseDTO.model_validate(appointment, from_attributes=True)

    def get_patient_appointments(self, patient_id: int, status: Optional[str] = None) -> List[AppointmentResponseDTO]:
        """Lấy lịch khám của bệnh nhân"""
        # Validate patient exists (managed by other microservice)
        self._validate_patient_exists(patient_id)

        status_enum = None
        if status:
            try:
                status_enum = AppointmentStatus(status.upper())
            except ValueError:
                raise HTTPException(
                    status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}"
                )

        appointments = self.appointment_repo.get_patient_appointments(patient_id, status_enum)
        return [self._build_appointment_response(appointment) for appointment in appointments]

    # ===============================
    # User Profile Management
    # ===============================

    def get_user_profile(self, user_id: int) -> dict:
        """Lấy thông tin profile của user (doctor hoặc patient)"""
        role, doctor, patient = self.user_auth_service.get_user_role_and_profile(user_id)

        profile_data = {
            "role": role
        }

        if doctor:
            profile_data["doctor"] = DoctorResponseDTO.model_validate(doctor)
            profile_data["doctor"].department_name = doctor.department.name

        if patient:
            profile_data["patient"] = PatientResponseDTO.model_validate(patient)

        return profile_data

    def get_current_user_appointments(self, user_id: int) -> List[AppointmentResponseDTO]:
        """Lấy lịch khám của user hiện tại (tùy theo role)"""
        role, doctor, patient = self.user_auth_service.get_user_role_and_profile(user_id)

        if doctor:
            # Nếu là doctor, lấy lịch khám của doctor đó
            appointments = self.appointment_repo.get_appointments_by_filters(doctor_id=doctor.id)
        elif patient:
            # Nếu là patient, lấy lịch khám của patient đó
            appointments = self.appointment_repo.get_appointments_by_filters(patient_id=patient.id)
        else:
            # User không có profile
            return []

        return [self._build_appointment_response(appointment) for appointment in appointments]

    def _validate_patient_exists(self, patient_id: int) -> None:
        """Validate patient exists (assume managed by other microservice)"""
        patient = self.patient_repo.get_by_id(patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with id {patient_id} not found. Please ensure patient is registered in the patient management system."
            )

    # ===============================
    # Helper Methods
    # ===============================

    def _build_appointment_response(self, appointment: Appointment) -> AppointmentResponseDTO:
        """Build appointment response DTO with related data"""
        return AppointmentResponseDTO(
            id=appointment.id,
            patient_id=appointment.patient_id,
            patient_name=appointment.patient.name,
            doctor_id=appointment.doctor_id,
            doctor_name=appointment.doctor.name,
            department_id=appointment.department_id,
            department_name=appointment.department.name,
            appointment_date=appointment.appointment_date,
            appointment_time=appointment.appointment_time,
            reason=appointment.reason,
            is_emergency=appointment.is_emergency,
            status=appointment.status,
            created_at=appointment.created_at,
            updated_at=appointment.updated_at
        )