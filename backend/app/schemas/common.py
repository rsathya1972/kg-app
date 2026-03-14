"""
Shared Pydantic response models used across all modules.
"""
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class BaseResponse(BaseModel):
    success: bool
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: str
    details: dict | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class NotImplementedResponse(BaseModel):
    status: str = "not_implemented"
    module: str
    message: str = "This endpoint is not yet implemented."
