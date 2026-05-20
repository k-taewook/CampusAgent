import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import graph as graph_module
from agent.prompts import SYSTEM_PROMPT_TEMPLATE


def test_task_decomposition_tools_are_bound():
    tool_names = {tool.name for tool in graph_module.ALL_TOOLS}

    assert "add_task_with_subtasks" in tool_names
    assert "list_task_tree" in tool_names
    assert "update_subtask_status_tool" in tool_names
    assert "get_task_progress" in tool_names
    assert "search_personalized_student_info" in tool_names


def test_prompt_mentions_subtask_tools():
    assert "add_task_with_subtasks" in SYSTEM_PROMPT_TEMPLATE
    assert "update_subtask_status_tool" in SYSTEM_PROMPT_TEMPLATE
    assert "get_task_progress" in SYSTEM_PROMPT_TEMPLATE
    assert "search_personalized_student_info" in SYSTEM_PROMPT_TEMPLATE


def test_graph_fallback_without_llm(monkeypatch):
    monkeypatch.setattr(graph_module, "is_llm_available", lambda: False)

    app = graph_module.build_graph()
    result = app.invoke(
        {
            "messages": [("user", "안녕")],
            "current_context": {
                "current_time": "2026-05-19 12:00:00",
                "user_major": "컴퓨터시스템공학과",
                "user_grade": "2학년",
                "user_profile": "관심 영역: policy,contest\n희망 진로: 백엔드 개발자",
                "memory_summary": "테스트 요약",
            },
        },
        {"configurable": {"thread_id": "test_fallback_without_llm"}},
    )

    assert result["messages"][-1].type == "ai"
    assert "LLM API 키가 설정되지 않았습니다" in result["messages"][-1].content
