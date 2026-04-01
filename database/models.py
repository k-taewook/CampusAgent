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
