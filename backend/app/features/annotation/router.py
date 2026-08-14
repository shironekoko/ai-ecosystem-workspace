"""
Annotation Router — API endpoints สำหรับโต้ตอบกับ Label Studio Data Labeling Platform
"""

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from label_studio_sdk.client import LabelStudio

from core.config import settings

router = APIRouter(prefix="/annotation", tags=["Label Studio Annotation"])


class LabelStudioProject(BaseModel):
    id: int = Field(..., example=1)
    title: str = Field(..., example="Customer Sentiment Analysis")
    description: str | None = Field(None, example="Text classification project")


class LabelStudioTask(BaseModel):
    id: int = Field(..., example=101)
    project_id: int = Field(..., example=1)
    data: dict


@router.get(
    "/projects",
    response_model=list[LabelStudioProject],
    summary="เรียกดูรายการโครงการทั้งหมดใน Label Studio (List Projects)",
)
def list_annotation_projects():
    """ดึงรายชื่อโครงการทั้งหมดที่ลงทะเบียนไว้ในระบบ Label Studio"""
    try:
        ls = LabelStudio(
            base_url=settings.label_studio_url,
            api_key=settings.label_studio_api_key,
        )
        projects = list(ls.projects.list())
        return [
            LabelStudioProject(
                id=p.id,
                title=p.title or f"Project #{p.id}",
                description=getattr(p, "description", None),
            )
            for p in projects
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ไม่สามารถเชื่อมต่อดึงรายการโครงการจาก Label Studio ได้: {str(e)}",
        )


@router.get(
    "/projects/{project_id}/tasks",
    response_model=list[LabelStudioTask],
    summary="เรียกดูรายการ Task ข้อมูลในโครงการ Label Studio (List Tasks)",
)
def list_project_tasks(
    project_id: int,
    limit: int = Query(default=10, ge=1, le=100, description="จำนวนรายการสูงสุดที่ดึงกลับมา"),
):
    """ดึงรายการข้อมูล (Tasks) ภายในโครงการ Label Studio ที่ระบุ"""
    try:
        ls = LabelStudio(
            base_url=settings.label_studio_url,
            api_key=settings.label_studio_api_key,
        )
        tasks_list = list(ls.tasks.list(project=project_id))
        result = []
        for i, t in enumerate(tasks_list):
            if i >= limit:
                break
            result.append(
                LabelStudioTask(
                    id=t.id,
                    project_id=project_id,
                    data=t.data if isinstance(t.data, dict) else {"content": str(t.data)},
                )
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ไม่สามารถดึงข้อมูล Tasks สำหรับ Project #{project_id}: {str(e)}",
        )
