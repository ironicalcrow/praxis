from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import api_router
from app.core.session import get_engine
from app.models import Base, User, Resume, ResumeSkill, ResumeEducation, ResumeExperience, ResumeProject, ResumeCertification
from app.modules.jobs.models import JobQuery

app = FastAPI(title="PRAXIS")


@app.on_event("startup")
def on_startup():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root():
    return {"message": "Praxis server is running"}
