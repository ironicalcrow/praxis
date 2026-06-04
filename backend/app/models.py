"""
SQLAlchemy ORM models for the application.
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    name = Column(String(255))
    username = Column(String(255), unique=True)
    email = Column(String(255), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"


class Resume(Base):
    """Resume model"""
    __tablename__ = "resumes"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(20))
    location = Column(String(255))
    years_of_experience = Column(Integer)
    raw_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="resumes")
    skills = relationship("ResumeSkill", back_populates="resume", cascade="all, delete-orphan")
    education = relationship("ResumeEducation", back_populates="resume", cascade="all, delete-orphan")
    experience = relationship("ResumeExperience", back_populates="resume", cascade="all, delete-orphan")
    projects = relationship("ResumeProject", back_populates="resume", cascade="all, delete-orphan")
    certifications = relationship("ResumeCertification", back_populates="resume", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Resume(id={self.id}, user_id={self.user_id})>"


class ResumeSkill(Base):
    """Resume skill model"""
    __tablename__ = "resume_skills"
    
    id = Column(String, primary_key=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)
    skill = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    resume = relationship("Resume", back_populates="skills")
    
    def __repr__(self):
        return f"<ResumeSkill(id={self.id}, skill={self.skill})>"


class ResumeEducation(Base):
    """Resume education model"""
    __tablename__ = "resume_education"
    
    id = Column(String, primary_key=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)
    degree = Column(String(255))
    institution = Column(String(255))
    year = Column(String(20))
    gpa = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    resume = relationship("Resume", back_populates="education")
    
    def __repr__(self):
        return f"<ResumeEducation(id={self.id})>"


class ResumeExperience(Base):
    """Resume experience model"""
    __tablename__ = "resume_experience"
    
    id = Column(String, primary_key=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)
    role = Column(String(255))
    organization = Column(String(255))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    resume = relationship("Resume", back_populates="experience")
    
    def __repr__(self):
        return f"<ResumeExperience(id={self.id})>"


class ResumeProject(Base):
    """Resume project model"""
    __tablename__ = "resume_projects"
    
    id = Column(String, primary_key=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)
    name = Column(String(255))
    description = Column(Text)
    technology = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    resume = relationship("Resume", back_populates="projects")
    
    def __repr__(self):
        return f"<ResumeProject(id={self.id})>"


class ResumeCertification(Base):
    """Resume certification model"""
    __tablename__ = "resume_certifications"
    
    id = Column(String, primary_key=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)
    certification = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    resume = relationship("Resume", back_populates="certifications")
    
    def __repr__(self):
        return f"<ResumeCertification(id={self.id})>"
