"""Private administrator authentication endpoints."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from lib.access import (
    SESSION_COOKIE,
    admin_email,
    cookie_is_secure,
    cookie_samesite,
    get_admin_session,
    issue_admin_session,
    session_ttl_seconds,
    verify_admin_credentials,
)

router = APIRouter()


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class AuthUser(BaseModel):
    email: str
    role: Literal["admin"]


class SessionResponse(BaseModel):
    authenticated: bool
    user: AuthUser


@router.post("/auth/login", response_model=SessionResponse)
async def login(payload: LoginRequest, request: Request, response: Response):
    if not admin_email():
        raise HTTPException(status_code=503, detail="Account amministratore non configurato")
    if not verify_admin_credentials(payload.email, payload.password):
        raise HTTPException(status_code=401, detail="Email o password non corrette")

    response.set_cookie(
        key=SESSION_COOKIE,
        value=issue_admin_session(admin_email()),
        max_age=session_ttl_seconds(),
        httponly=True,
        secure=cookie_is_secure(request),
        samesite=cookie_samesite(request),
        path="/",
    )
    return {"authenticated": True, "user": {"email": admin_email(), "role": "admin"}}


@router.get("/auth/me", response_model=SessionResponse)
async def current_session(request: Request):
    session = get_admin_session(request)
    return {"authenticated": True, "user": {"email": session["sub"], "role": "admin"}}


@router.post("/auth/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie(key=SESSION_COOKIE, path="/")
