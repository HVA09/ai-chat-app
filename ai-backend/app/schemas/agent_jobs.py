from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agent_workflows import AgentWorkflowStepCreate, AgentWorkflowStepOut


class AgentJobCreate(BaseModel):
    workspace_id: int
    task: str = Field(min_length=1, max_length=12000)
    workflow_steps: list[AgentWorkflowStepCreate] = Field(default_factory=list, max_length=6)

    def normalized_task(self) -> str:
        task = self.task.strip()
        if not task:
            raise ValueError("المهمة لا يمكن أن تكون فارغة")
        return task

    def normalized_steps(self) -> list[tuple[str, str]]:
        if not self.workflow_steps:
            return [("تنفيذ المهمة", self.normalized_task())]
        normalized = [step.normalized() for step in self.workflow_steps]
        if len(normalized) > 6:
            raise ValueError("الحد الأقصى لسير العمل هو 6 خطوات")
        return normalized


class AgentJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    conversation_id: int
    task: str
    status: str
    cancel_requested: bool
    pause_requested: bool
    workflow_phase: str
    retry_count: int
    max_retries: int
    checkpoint: dict | None
    checkpoint_at: datetime | None
    agent_version: str
    tool_policy_snapshot: dict | None
    celery_task_id: str | None
    run_id: str | None
    result_text: str | None
    result_sources: list | None
    error: str | None
    input_tokens: int | None
    output_tokens: int | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    workflow_steps: list[AgentWorkflowStepOut] = Field(default_factory=list)


class AgentJobCancelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    cancel_requested: bool


class AgentJobPauseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    pause_requested: bool
    workflow_phase: str
