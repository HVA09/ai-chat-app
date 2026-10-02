from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgentJobCreate(BaseModel):
    workspace_id: int
    task: str = Field(min_length=1, max_length=12000)

    def normalized_task(self) -> str:
        task = self.task.strip()
        if not task:
            raise ValueError("المهمة لا يمكن أن تكون فارغة")
        return task


class AgentJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    conversation_id: int
    task: str
    status: str
    cancel_requested: bool
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


class AgentJobCancelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    cancel_requested: bool
