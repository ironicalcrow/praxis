from datetime import datetime

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.session import Base
from app.core.config import settings
from pgvector.sqlalchemy import Vector


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)

    name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(20))
    location = Column(String(255))
    country = Column(String(255))
    years_of_experience = Column(Integer)
    raw_text = Column(Text)
    embedding = Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=True)
    file_url = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="resumes")

    skills = relationship("ResumeSkill", back_populates="resume", cascade="all, delete-orphan")
    education = relationship("ResumeEducation", back_populates="resume", cascade="all, delete-orphan")
    experience = relationship("ResumeExperience", back_populates="resume", cascade="all, delete-orphan")
    projects = relationship("ResumeProject", back_populates="resume", cascade="all, delete-orphan")
    certifications = relationship("ResumeCertification", back_populates="resume", cascade="all, delete-orphan")


class CVUpload(Base):
    __tablename__ = "cv_uploads"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_url = Column(Text, nullable=False)
    storage_path = Column(Text, nullable=False)
    original_filename = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)


class ResumeSkill(Base):
    __tablename__ = "resume_skills"

    id = Column(String, primary_key=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)
    skill = Column(String(255), nullable=False)
    embedding = Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=True)

    resume = relationship("Resume", back_populates="skills")


class ResumeEducation(Base):
    __tablename__ = "resume_education"

    id = Column(String, primary_key=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)

    degree = Column(String(255))
    institution = Column(String(255))
    year = Column(String(20))
    gpa = Column(String(10))
    embedding = Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=True)

    resume = relationship("Resume", back_populates="education")


class ResumeExperience(Base):
    __tablename__ = "resume_experience"

    id = Column(String, primary_key=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)

    role = Column(String(255))
    organization = Column(String(255))
    description = Column(Text)
    embedding = Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=True)

    resume = relationship("Resume", back_populates="experience")


class ResumeProject(Base):
    __tablename__ = "resume_projects"

    id = Column(String, primary_key=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)

    name = Column(String(255))
    description = Column(Text)
    technology = Column(String(255))
    embedding = Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=True)

    resume = relationship("Resume", back_populates="projects")


class ResumeCertification(Base):
    __tablename__ = "resume_certifications"

    id = Column(String, primary_key=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)

    certification = Column(String(255), nullable=False)
    embedding = Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=True)

    resume = relationship("Resume", back_populates="certifications")
