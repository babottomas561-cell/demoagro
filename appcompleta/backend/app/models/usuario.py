from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Usuario(Base, TimestampMixin):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True, index=True)
    nombre = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    hashed_password = Column(String(300), nullable=False)
    rol = Column(String(50), nullable=False, default="operativo")  # admin, gerente, operativo
    activo = Column(Boolean, default=True, nullable=False)

    empresa = relationship("Empresa", back_populates="usuarios", lazy="select")
