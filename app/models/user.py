from typing import Optional
import datetime

from sqlalchemy import PrimaryKeyConstraint, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Users(Base):
    """User accounts for the lease accounting system"""
    __tablename__ = 'users'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='users_pkey'),
        UniqueConstraint('username', name='users_username_unique'),
        {'schema': 'kontracts'}
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, server_default=text('gen_random_uuid()'))
    username: Mapped[str] = mapped_column(Text)
    password: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, server_default=text("'Contract Administrator'::text"))
