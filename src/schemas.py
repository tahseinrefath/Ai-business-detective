"""Pydantic request and response models for FastAPI routes and automatic OpenAPI generation."""
from typing import Any, Literal
from pydantic import BaseModel


class RegisterRequest(BaseModel):
    name: str = ""
    email: str = ""
    password: str = ""
    next: str | None = None


class LoginRequest(BaseModel):
    email: str = ""
    password: str = ""
    next: str | None = None


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    job_title: str | None = None
    company: str | None = None
    location: str | None = None
    bio: str | None = None


class PasswordChangeRequest(BaseModel):
    current: str = ""
    new: str = ""


class DeleteAccountRequest(BaseModel):
    password: str = ""


class ColumnMappingRequest(BaseModel):
    token: str = ""
    filename: str | None = None
    mapping: dict[str, str | None] = {}


class SampleRequest(BaseModel):
    kind: str = "clean"


class InvestigateRequest(BaseModel):
    dataset: str = ""
    metric: str | None = None
    previous: str | None = None
    current: str | None = None


class AskRequest(InvestigateRequest):
    question: str = ""


class ReportCreateRequest(BaseModel):
    metric: str | None = None
    previous: str | None = None
    current: str | None = None


class GoalSetRequest(BaseModel):
    dataset: str = ""
    metric: str = ""
    amount: Any = None


class GoalDeleteRequest(BaseModel):
    dataset: str = ""
    metric: str | None = None


class NoteCreateRequest(BaseModel):
    dataset: str = ""
    text: str = ""


class WhatIfRequest(BaseModel):
    dataset: str = ""
    segment: str = ""
    commit: bool = False
    order_change_pct: Any = 0
    price_change_pct: Any = 0
    margin_change_pts: Any = 0


class ErrorResponse(BaseModel):
    error: str
    login_required: bool | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
