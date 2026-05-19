"""
CampusAgent 데이터 모델 정의
- Pydantic 기반 스키마 (직렬화/역직렬화 지원)
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum
import re


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

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('title is required and cannot be empty')
        return v.strip()

    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v):
        if not re.match(r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2})?$', v.strip()):
            raise ValueError('due_date must be in absolute YYYY-MM-DD or YYYY-MM-DD HH:MM format')
        return v.strip()


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


class SubtaskCreate(BaseModel):
    """서브태스크 생성 요청 모델"""
    assignment_id: int = Field(..., description="부모 과제 ID")
    title: str = Field(..., description="서브태스크 제목")
    description: Optional[str] = Field(None, description="서브태스크 상세 설명")
    due_date: Optional[str] = Field(None, description="마감일 (YYYY-MM-DD 또는 YYYY-MM-DD HH:MM)")
    status: str = Field("pending", description="상태 (pending/in_progress/done)")
    sort_order: int = Field(0, description="표시 순서")

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('title is required and cannot be empty')
        return v.strip()

    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v):
        if v is None or not str(v).strip():
            return None
        value = str(v).strip()
        if not re.match(r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2})?$', value):
            raise ValueError('due_date must be in absolute YYYY-MM-DD or YYYY-MM-DD HH:MM format')
        return value

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        valid = {AssignmentStatus.PENDING.value, AssignmentStatus.IN_PROGRESS.value, AssignmentStatus.DONE.value}
        if v not in valid:
            raise ValueError(f'status must be one of {valid}')
        return v


class Subtask(BaseModel):
    """서브태스크 전체 모델 (DB 조회 결과)"""
    id: int
    assignment_id: int
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    status: AssignmentStatus = AssignmentStatus.PENDING
    sort_order: int = 0
    created_at: Optional[str] = None

    def to_display_string(self) -> str:
        """채팅 응답용 문자열 변환"""
        status_emoji = {
            "pending": "📋",
            "in_progress": "🔄",
            "done": "✅",
        }
        emoji = status_emoji.get(self.status.value, "📋")
        due = f" | 마감: {self.due_date}" if self.due_date else ""
        return f"{emoji} [{self.id}] {self.title}{due} ({self.status.value})"


class AssignmentWithProgress(BaseModel):
    """부모 과제, 서브태스크, 진행률을 함께 표현하는 모델"""
    assignment: Assignment
    subtasks: list[Subtask] = Field(default_factory=list)
    progress: int = 0
    total_subtasks: int = 0
    done_subtasks: int = 0


class UserSetting(BaseModel):
    """사용자 설정 모델"""
    key: str
    value: str


# ──────────────────────────────────────
# 캘린더 / 일정 모델
# ──────────────────────────────────────


class ScheduleCategory(str, Enum):
    """일정 카테고리 열거형"""
    CLASS = "class"          # 수업
    EXAM = "exam"            # 시험
    PERSONAL = "personal"    # 개인 일정
    MEETING = "meeting"      # 모임/회의
    OTHER = "other"          # 기타


class ScheduleCreate(BaseModel):
    """일정 생성 요청 모델"""
    title: str = Field(..., description="일정 제목")
    date: str = Field(..., description="일정 날짜 (YYYY-MM-DD 형식)")
    start_time: Optional[str] = Field(None, description="시작 시간 (HH:MM 형식)")
    end_time: Optional[str] = Field(None, description="종료 시간 (HH:MM 형식)")
    category: Optional[str] = Field("personal", description="카테고리 (class/exam/personal/meeting/other)")
    description: Optional[str] = Field(None, description="일정 상세 설명")
    is_recurring: Optional[bool] = Field(False, description="매주 반복 여부")

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('title is required and cannot be empty')
        return v.strip()

    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v.strip()):
            raise ValueError('date must be in absolute YYYY-MM-DD format')
        return v.strip()


class Schedule(BaseModel):
    """일정 전체 모델 (DB 조회 결과)"""
    id: int
    title: str
    date: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    category: str = "personal"
    description: Optional[str] = None
    is_recurring: bool = False
    created_at: Optional[str] = None

    def to_display_string(self) -> str:
        """채팅 응답용 문자열 변환"""
        cat_emoji = {
            "class": "📖", "exam": "📝", "personal": "👤",
            "meeting": "👥", "other": "📌",
        }
        emoji = cat_emoji.get(self.category, "📌")
        time_str = ""
        if self.start_time:
            time_str = f"   🕐 시간: {self.start_time}"
            if self.end_time:
                time_str += f" ~ {self.end_time}"
            time_str += "\n"
        recurring = "   🔁 매주 반복\n" if self.is_recurring else ""

        return (
            f"{emoji} **[{self.id}] {self.title}**\n"
            f"   📅 날짜: {self.date}\n"
            f"{time_str}"
            f"   📂 카테고리: {self.category}\n"
            f"{recurring}"
        ).rstrip()
