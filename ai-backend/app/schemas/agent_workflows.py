from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgentWorkflowStepCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=12000)

    def normalized(self) -> tuple[str, str]:
        title = self.title.strip()
        prompt = self.prompt.strip()
        if not title:
            raise ValueError("عنوان الخطوة لا يمكن أن يكون فارغًا")
        if not prompt:
            raise ValueError("تعليمات الخطوة لا يمكن أن تكون فارغة")
        return title, prompt


class AgentWorkflowStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_job_id: int
    sequence: int
    title: str
    prompt: str
    status: str
    attempt_count: int
    run_id: str | None
    result_text: str | None
    result_sources: list | None
    checkpoint: dict | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
