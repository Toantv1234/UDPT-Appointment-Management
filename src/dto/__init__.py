# src/dto/__init__.py
from .appointment_dto import (
    # Enums
    AppointmentStatusEnum, CancelledByEnum,

    # Department DTOs
    DepartmentResponseDTO,

    # Doctor DTOs
    DoctorResponseDTO,

    # Patient DTOs (Read-only)
    PatientResponseDTO,

    # Available Slot DTOs
    AvailableSlotResponseDTO,

    # Appointment DTOs
    AppointmentCreateDTO, AppointmentUpdateDTO,
    AppointmentConfirmDTO, AppointmentCancelDTO,
    AppointmentResponseDTO, AppointmentDetailResponseDTO,
    PendingAppointmentResponseDTO,

    # Query DTOs
    DepartmentListQueryDTO, DoctorListQueryDTO,
    AvailableSlotQueryDTO, AppointmentListQueryDTO,

    # Common DTOs
    MessageResponseDTO, ErrorResponseDTO
)
from .pagination_dto import (
    PaginationRequestDTO,
    PaginationMetaDTO,
    PaginatedResponseDTO
)

__all__ = [
    # Enums
    "AppointmentStatusEnum",
    "CancelledByEnum",

    # Department DTOs
    "DepartmentResponseDTO",

    # Doctor DTOs
    "DoctorResponseDTO",

    # Patient DTOs (Read-only)
    "PatientResponseDTO",

    # Available Slot DTOs
    "AvailableSlotResponseDTO",

    # Appointment DTOs
    "AppointmentCreateDTO",
    "AppointmentUpdateDTO",
    "AppointmentConfirmDTO",
    "AppointmentCancelDTO",
    "AppointmentResponseDTO",
    "AppointmentDetailResponseDTO",
    "PendingAppointmentResponseDTO",

    # Query DTOs
    "DepartmentListQueryDTO",
    "DoctorListQueryDTO",
    "AvailableSlotQueryDTO",
    "AppointmentListQueryDTO",

    # Common DTOs
    "MessageResponseDTO",
    "ErrorResponseDTO",

    # Pagination DTOs
    "PaginationRequestDTO",
    "PaginationMetaDTO",
    "PaginatedResponseDTO"
]
