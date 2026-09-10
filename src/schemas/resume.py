"""Factual resume extraction models; competency assessment happens later."""

from pydantic import BaseModel, ConfigDict, Field


class ResumeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkExperience(ResumeRecord):
    employer: str | None
    title: str | None
    dates: str | None = Field(description="Date wording as stated in the resume.")
    responsibilities_and_achievements: list[str]


class ResumeProject(ResumeRecord):
    name: str | None
    description: str
    technologies: list[str]


class Education(ResumeRecord):
    qualification: str | None
    institution: str | None
    dates: str | None
    details: list[str]


class CandidateResume(ResumeRecord):
    candidate_id: str
    name: str | None
    email: str | None
    phone: str | None
    location: str | None
    target_role: str | None
    summary: str | None
    skills: list[str]
    work_experience: list[WorkExperience]
    projects: list[ResumeProject]
    education: list[Education]
    certifications: list[str]
