"""
CampusAgent - Agent 구성 테스트
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("langgraph")

from agent.graph import ALL_TOOLS, build_graph
from agent.prompts import SYSTEM_PROMPT_TEMPLATE


def test_task_tools_include_subtask_features():
    tool_names = {tool.name for tool in ALL_TOOLS}
    assert "add_task_with_subtasks" in tool_names
    assert "list_task_tree" in tool_names
    assert "update_subtask_status_tool" in tool_names
    assert "get_task_progress" in tool_names


def test_prompt_mentions_subtask_tools():
    assert "add_task_with_subtasks" in SYSTEM_PROMPT_TEMPLATE
    assert "update_subtask_status_tool" in SYSTEM_PROMPT_TEMPLATE
    assert "get_task_progress" in SYSTEM_PROMPT_TEMPLATE


def test_graph_returns_fallback_when_llm_unavailable(monkeypatch):
    monkeypatch.setattr("config.settings.GOOGLE_API_KEY", "")
    monkeypatch.setattr("config.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr("config.settings.LLM_PROVIDER", "auto")
    monkeypatch.setattr("agent.graph.is_llm_available", lambda: False)

    graph = build_graph()
    result = graph.invoke(
        {
            "messages": [("user", "안녕")],
            "current_context": {
                "current_time": "2026-05-18 18:00:00",
                "user_major": "컴퓨터시스템공학과",
                "user_grade": "2학년",
                "memory_summary": "저장된 장기기억 요약 없음",
            },
        },
        {"configurable": {"thread_id": "test-thread"}},
    )

    final_message = result["messages"][-1]
    assert "LLM API 키가 설정되지 않았습니다" in final_message.content


def test_graph_accepts_memory_summary_without_error(monkeypatch):
    monkeypatch.setattr("agent.graph.is_llm_available", lambda: False)

    graph = build_graph()
    result = graph.invoke(
        {
            "messages": [("user", "과제 진행률 알려줘")],
            "current_context": {
                "current_time": "2026-05-18 18:00:00",
                "user_major": "컴퓨터시스템공학과",
                "user_grade": "2학년",
                "memory_summary": "사용자는 자료구조 프로젝트를 진행 중이다.",
            },
        },
        {"configurable": {"thread_id": "test-thread-memory"}},
    )

    assert result["messages"][-1].content
