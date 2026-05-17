from datetime import datetime, timezone
from sqlalchemy import Boolean, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    urls: Mapped[list["URL"]] = relationship("URL", back_populates="user", cascade="all, delete")


class URL(Base):
    __tablename__ = "urls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    short_code: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    user: Mapped["User"] = relationship("User", back_populates="urls")
    clicks: Mapped[list["Click"]] = relationship("Click", back_populates="url", cascade="all, delete")


class Click(Base):
    __tablename__ = "clicks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url_id: Mapped[int] = mapped_column(Integer, ForeignKey("urls.id"), nullable=False)
    clicked_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(512), nullable=True)
    url: Mapped["URL"] = relationship("URL", back_populates="clicks")
