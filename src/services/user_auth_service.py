from typing import Optional, Tuple
from fastapi import HTTPException, status

from src.repositories.appointment_repository import DoctorRepository, PatientRepository
from src.models.appointment import Doctor, Patient

class UserAuthService:
    """Service to handle user authentication and role-based access"""

    def __init__(self, doctor_repo: DoctorRepository, patient_repo: PatientRepository):
        self.doctor_repo = doctor_repo
        self.patient_repo = patient_repo

    def get_user_role_and_profile(self, user_id: int) -> Tuple[str, Optional[type[Doctor]], Optional[type[Patient]]]:
        """
        Get user role and profile information

        Returns:
            Tuple of (role, doctor_profile, patient_profile)
        """
        # Try to find as doctor first
        doctor = self.doctor_repo.get_by_user_id(user_id)
        if doctor:
            return "DOCTOR", doctor, None

        # Try to find as patient
        patient = self.patient_repo.get_by_user_id(user_id)
        if patient:
            return "PATIENT", None, patient

        # User exists but not linked to any profile
        return "USER", None, None

    def validate_doctor_access(self, user_id: int, doctor_id: int) -> Doctor:
        """
        Validate that the user has access to doctor operations

        Args:
            user_id: The authenticated user ID
            doctor_id: The doctor ID being accessed

        Returns:
            Doctor object if authorized

        Raises:
            HTTPException if unauthorized
        """
        doctor = self.doctor_repo.get_by_id(doctor_id)
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Doctor with id {doctor_id} not found"
            )

        # Check if user is the same doctor
        if doctor.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own doctor profile"
            )

        return doctor

    def validate_patient_access(self, user_id: int, patient_id: int) -> Patient:
        """
        Validate that the user has access to patient operations

        Args:
            user_id: The authenticated user ID
            patient_id: The patient ID being accessed

        Returns:
            Patient object if authorized

        Raises:
            HTTPException if unauthorized
        """
        patient = self.patient_repo.get_by_id(patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with id {patient_id} not found"
            )

        # Check if user is the same patient
        if patient.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own patient profile"
            )

        return patient

    def get_doctor_by_user_id(self, user_id: int) -> type[Doctor]:
        """
        Get doctor profile by user_id

        Raises:
            HTTPException if user is not a doctor or not found
        """
        doctor = self.doctor_repo.get_by_user_id(user_id)
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not associated with any doctor profile"
            )
        return doctor

    def get_patient_by_user_id(self, user_id: int) -> type[Patient]:
        """
        Get patient profile by user_id

        Raises:
            HTTPException if user is not a patient or not found
        """
        patient = self.patient_repo.get_by_user_id(user_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not associated with any patient profile"
            )
        return patient