from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List
from math import ceil
from starlette import status

T = TypeVar('T')

class PaginationRequestDTO(BaseModel):
    page: int = Field(1, ge=1, description="Page number (starts from 1)")
    page_size: int = Field(10, ge=1, le=100, description="Number of items per page (max 100)")

    def calc_skip(self) -> int:
        """Calculate the number of items to skip based on page and page_size."""
        if self.page < 1 :
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page number must be greater than 0"
            )
        if self.page_size < 1 or self.page_size > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page size must be between 1 and 100"
            )
        return (self.page - 1) * self.page_size

class PaginationMetaDTO(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool

class PaginatedResponseDTO(BaseModel, Generic[T]):
    data: List[T]
    meta: PaginationMetaDTO

    @classmethod
    def create(
            cls,
            data: List[T],
            page: int,
            page_size: int,
            total: int
    ):
        total_pages = ceil(total / page_size) if total > 0 else 0

        return cls(
            data=data,
            meta=PaginationMetaDTO(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1
            )
        )