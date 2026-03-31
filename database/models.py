"""
CampusAgent 데이터 모델 정의
- Pydantic 기반 스키마 (직렬화/역직렬화 지원)
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class AssignmentStatus(str, Enum):
    """과제 상태 열거형"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    OVERDUE = "overdue"


class AssignmentCreate(BaseModel):
    """과제 생성 요청 모델"""
    title: str = Field(..., description="과제 제목")
    course_name: str = Field(..., description="과목명")
    description: Optional[str] = Field(None, description="과제 상세 설명")
    due_date: str = Field(..., description="마감일 (YYYY-MM-DD HH:MM 형식)")
    priority: Optional[str] = Field("medium", description="우선순위 (low/medium/high)")


class Assignment(BaseModel):
    """과제 전체 모델 (DB 조회 결과)"""
    id: int
    title: str
    course_name: str
    description: Optional[str] = None
    due_date: str
    status: AssignmentStatus = AssignmentStatus.PENDING
    priority: str = "medium"
    created_at: Optional[str] = None

    def to_display_string(self) -> str:
        """채팅 응답용 문자열 변환"""
        status_emoji = {
            "pending": "📋",
            "in_progress": "🔄",
            "done": "✅",
            "overdue": "⚠️",
        }
        emoji = status_emoji.get(self.status, "📋")
        priority_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(self.priority, "🟡")
        
        return (
            f"{emoji} **[{self.id}] {self.title}**\n"
            f"   📚 과목: {self.course_name}\n"
            f"   📅 마감: {self.due_date}\n"
            f"   {priority_emoji} 우선순위: {self.priority}\n"
            f"   상태: {self.status.value}"
        )


class UserSetting(BaseModel):
    """사용자 설정 모델"""
    key: str
    value: str
