from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentWorkflowStepCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    instruction: str = Field(min_length=1, max_length=6000)

    @field_validator("name", "instruction")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("القيمة لا يمكن أن تكون فارغة")
        return value


class AgentWorkflowCreate(BaseModel):
    workspace_id: int
    project_id: int
    name: str = Field(min_length=1, max_length=120)
    steps: list[AgentWorkflowStepCreate] = Field(min_length=1, max_length=12)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("اسم الـworkflow لا يمكن أن يكون فارغًا")
        return value


class AgentWorkflowStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    name: str
    instruction: str
    status: str
    attempt_count: int
    run_id: str | None
    result_text: str | None
    result_sources: list | None
    input_tokens: int | None
    output_tokens: int | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None


class AgentWorkflowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    project_id: int
    conversation_id: int
    name: str
    status: str
    cancel_requested: bool
    current_step_position: int
    checkpoint: dict
    result_text: str | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    steps: list[AgentWorkflowStepOut]


class AgentWorkflowCancelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    cancel_requested: bool


class AgentWorkflowResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    current_step_position: int
