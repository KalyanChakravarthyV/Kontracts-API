from pydantic import BaseModel, Field
from typing import Optional


class UserBase(BaseModel):
    username: str = Field(..., description="Unique username for the user")
    name: str = Field(..., description="Full name of the user")
    role: str = Field(default="Contract Administrator", description="User role in the system")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="User password (minimum 8 characters)")


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, description="Unique username for the user")
    name: Optional[str] = Field(None, description="Full name of the user")
    role: Optional[str] = Field(None, description="User role in the system")
    password: Optional[str] = Field(None, min_length=8, description="User password (minimum 8 characters)")


class UserResponse(UserBase):
    id: str

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
