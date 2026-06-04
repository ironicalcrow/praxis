from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

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
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
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
    skill = Column(String(255), nullable=False)
    
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
    
    resume = relationship("Resume", back_populates="projects")
    
    def __repr__(self):
        return f"<ResumeProject(id={self.id})>"


class ResumeCertification(Base):
    """Resume certification model"""
    __tablename__ = "resume_certifications"
    
    id = Column(String, primary_key=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)
    certification = Column(String(255), nullable=False)
    
    resume = relationship("Resume", back_populates="certifications")
    
    def __repr__(self):
        return f"<ResumeCertification(id={self.id})>"

def generate_uuid():
    return str(uuid.uuid4())

class ApplicationStatus(str, enum.Enum):
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    REJECTED = "rejected"
    SAVED = "saved"

class Job(Base):
    __tablename__="jobs"
    id= Column(String, primary_key=True, default=generate_uuid)
    external_id = Column(String(255), index=True, nullable=True)
    source = Column(String(100), nullable=True)

    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)

    company_logo = Column(Text, nullable=True)
    company_website = Column(Text, nullable=True)

    publisher = Column(String(255), nullable=True)
    employment_type = Column(String(100), nullable=True)
    employment_types = Column(JSON, nullable=True)

    location = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    is_remote = Column(Boolean, default=False)

    apply_url = Column(Text, nullable=True)
    is_direct_apply = Column(Boolean, default=False)

    description_preview = Column(Text, nullable=True)
    salary = Column(String(255), nullable=True)

    raw_payload = Column(JSON, nullable=True)

    posted_at = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    applications = relationship("Application", back_populates="job")
    def __repr__(self):
        return f"<Job(id={self.id}, title={self.title}, company={self.company})>"

class Application(Base):
    __tablename__="applications"

    id = Column(String, primary_key=True, default=generate_uuid)

    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=True)

    status = Column(
        SQLEnum(ApplicationStatus),
        nullable=False,
        default=ApplicationStatus.SAVED,
        index=True,
    )

    job_title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    apply_url = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    salary = Column(String(255), nullable=True)

    applied_at = Column(DateTime, default=datetime.utcnow)
    last_status_changed_at = Column(DateTime, default=datetime.utcnow)

    is_archived = Column(Boolean, default=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")

    status_history = relationship( 
        "ApplicationStatusHistory", 
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationStatusHistory.changed_at.desc()",
        )

    notes = relationship(
        "ApplicationNote",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationNote.created_at.desc()",
    )

    def __repr__(self):
        return f"<Application(id={self.id}, company={self.company}, status={self.status})>"

class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"

    id = Column(String, primary_key=True, default=generate_uuid)

    application_id = Column(String, ForeignKey("applications.id"), nullable=False)

    old_status = Column(SQLEnum(ApplicationStatus), nullable=True)
    new_status = Column(SQLEnum(ApplicationStatus), nullable=False)

    changed_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=True)

    changed_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="status_history")

    def __repr__(self):
        return f"<ApplicationStatusHistory(id={self.id}, new_status={self.new_status})>"


class ApplicationNote(Base):
    __tablename__ = "application_notes"

    id = Column(String, primary_key=True, default=generate_uuid)

    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    content = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    application = relationship("Application", back_populates="notes")

    def __repr__(self):
        return f"<ApplicationNote(id={self.id}, application_id={self.application_id})>"