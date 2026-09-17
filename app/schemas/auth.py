from __future__ import annotations

from pydantic import BaseModel, Field


class AdminLogin(BaseModel):
    username: str = Field(default="admin")
    password: str = Field(...)
