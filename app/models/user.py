
from beanie import Document
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    CLIENT = "CLIENT"
    ADMIN_STAFF = "ADMIN_STAFF"

class User(Document):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr = Field(..., unique=True)
    password: str = Field(..., min_length=6)
    role: UserRole = Field(default=UserRole.CLIENT)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "users"
        indexes = [
            "email",
            "username",
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "securepassword123",
                "role": "CLIENT"
            }
        }