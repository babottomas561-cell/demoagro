from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Mantenimiento(Base, TimestampMixin):
    __tablename__ = "mantenimientos"

    id = Column(Integer, primary_key=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=False, index=True)
    tipo = Column(String(50), nullable=False)   # preventivo, correctivo
    fecha = Column(Date, nullable=False)
    descripcion = Column(Text, nullable=True)
    costo = Column(Float, nullable=False, default=0)   # ARS
    horas_maquina = Column(Float, nullable=True)        # horas al momento del service
    proximo_service_hs = Column(Float, nullable=True)   # próximo service en horas

    # Relationships
    maquinaria = relationship("Maquinaria", back_populates="mantenimientos")
