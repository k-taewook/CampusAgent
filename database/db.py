"""
CampusAgent SQLite 데이터베이스 모듈
- 테이블 초기화
- 과제 CRUD 함수 (추가, 조회, 수정, 삭제)
- 캘린더 CRUD 함수 (추가, 조회, 수정, 삭제)
"""
import sqlite3
from typing import List, Optional
from datetime import datetime, timedelta

from config.settings import SQLITE_DB_PATH
from database.models import (
    Assignment, AssignmentCreate, AssignmentStatus,
    Schedule, ScheduleCreate,
)


def _get_connection() -> sqlite3.Connection:
    """DB 연결 생성 (row_factory 설정)"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite_db():
    """SQLite 테이블 초기화"""
    print(f"🗄️ SQLite 데이터베이스 초기화 중... ({SQLITE_DB_PATH})")
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        course_name TEXT NOT NULL,
        description TEXT,
        due_date TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        priority TEXT DEFAULT 'medium',
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        date TEXT NOT NULL,
        start_time TEXT,
        end_time TEXT,
        category TEXT DEFAULT 'personal',
        description TEXT,
        is_recurring INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_sessions (
        id TEXT PRIMARY KEY,
        title TEXT DEFAULT '기본 세션',
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime'))
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (session_id) REFERENCES conversation_sessions(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memory_summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        summary TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (session_id) REFERENCES conversation_sessions(id)
    );
    """)

    conn.commit()
    conn.close()
    print("✅ SQLite 세팅 완료")


# ──────────────────────────────────────
# 사용자 설정 CRUD
# ──────────────────────────────────────

def set_user_setting(key: str, value: str):
    """사용자 설정 저장 (Upsert)"""
    conn = _get_connection()
    conn.execute(
        "INSERT INTO user_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value)
    )
    conn.commit()
    conn.close()

def get_user_setting(key: str, default: str = "") -> str:
    """사용자 설정 조회"""
    conn = _get_connection()
    row = conn.execute("SELECT value FROM user_settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row:
        return row["value"]
    return default

# ──────────────────────────────────────
# 장기기억 / 대화 이력 CRUD
# ──────────────────────────────────────

def get_or_create_conversation_session(
    session_id: str,
    title: str = "기본 세션",
) -> dict:
    """대화 세션을 조회하고 없으면 생성"""
    conn = _get_connection()
    row = conn.execute(
        "SELECT * FROM conversation_sessions WHERE id = ?",
        (session_id,),
    ).fetchone()

    if row is None:
        conn.execute(
            "INSERT INTO conversation_sessions (id, title) VALUES (?, ?)",
            (session_id, title),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM conversation_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    else:
        conn.execute(
            "UPDATE conversation_sessions SET updated_at = datetime('now', 'localtime') WHERE id = ?",
            (session_id,),
        )
        conn.commit()

    conn.close()
    return dict(row)


def save_conversation_message(session_id: str, role: str, content: str) -> int:
    """대화 메시지를 장기기억 DB에 저장하고 message id 반환"""
    if role not in {"user", "assistant", "system", "tool"}:
        raise ValueError(f"유효하지 않은 메시지 role입니다: {role}")
    if not content or not str(content).strip():
        raise ValueError("저장할 메시지 내용이 비어 있습니다.")

    get_or_create_conversation_session(session_id)
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO conversation_messages (session_id, role, content)
        VALUES (?, ?, ?)
        """,
        (session_id, role, str(content)),
    )
    conn.execute(
        "UPDATE conversation_sessions SET updated_at = datetime('now', 'localtime') WHERE id = ?",
        (session_id,),
    )
    conn.commit()
    message_id = cursor.lastrowid
    conn.close()
    return int(message_id)


def load_recent_conversation_messages(
    session_id: str,
    limit: int = 20,
) -> List[dict]:
    """최근 대화 메시지를 시간순으로 반환"""
    conn = _get_connection()
    rows = conn.execute(
        """
        SELECT id, session_id, role, content, created_at
        FROM conversation_messages
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in reversed(rows)]


def save_memory_summary(session_id: str, summary: str) -> int:
    """대화 요약 메모리를 저장하고 summary id 반환"""
    if not summary or not summary.strip():
        raise ValueError("저장할 요약 내용이 비어 있습니다.")

    get_or_create_conversation_session(session_id)
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO memory_summaries (session_id, summary)
        VALUES (?, ?)
        """,
        (session_id, summary.strip()),
    )
    conn.execute(
        "UPDATE conversation_sessions SET updated_at = datetime('now', 'localtime') WHERE id = ?",
        (session_id,),
    )
    conn.commit()
    summary_id = cursor.lastrowid
    conn.close()
    return int(summary_id)


def get_latest_memory_summary(session_id: str) -> Optional[str]:
    """최근 요약 메모리 반환"""
    conn = _get_connection()
    row = conn.execute(
        """
        SELECT summary
        FROM memory_summaries
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    conn.close()
    return row["summary"] if row else None


def clear_conversation_history(session_id: str) -> bool:
    """특정 세션의 대화 메시지와 요약 메모리 삭제"""
    conn = _get_connection()
    cursor_messages = conn.execute(
        "DELETE FROM conversation_messages WHERE session_id = ?",
        (session_id,),
    )
    cursor_summaries = conn.execute(
        "DELETE FROM memory_summaries WHERE session_id = ?",
        (session_id,),
    )
    conn.execute(
        "UPDATE conversation_sessions SET updated_at = datetime('now', 'localtime') WHERE id = ?",
        (session_id,),
    )
    conn.commit()
    deleted = cursor_messages.rowcount > 0 or cursor_summaries.rowcount > 0
    conn.close()
    return deleted

# ──────────────────────────────────────
# 과제 CRUD
# ──────────────────────────────────────


def add_assignment(data: AssignmentCreate) -> Assignment:
    """과제 추가"""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO assignments (title, course_name, description, due_date, priority)
        VALUES (?, ?, ?, ?, ?)
        """,
        (data.title, data.course_name, data.description, data.due_date, data.priority),
    )
    conn.commit()
    new_id = cursor.lastrowid

    # 방금 삽입한 행을 다시 조회하여 반환
    row = cursor.execute("SELECT * FROM assignments WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return _row_to_assignment(row)


def get_assignments(
    status: Optional[str] = None,
    course_name: Optional[str] = None,
) -> List[Assignment]:
    """과제 목록 조회 (필터 옵션)"""
    conn = _get_connection()
    query = "SELECT * FROM assignments WHERE 1=1"
    params: list = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if course_name:
        query += " AND course_name LIKE ?"
        params.append(f"%{course_name}%")

    query += " ORDER BY due_date ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [_row_to_assignment(r) for r in rows]


def get_assignment_by_id(assignment_id: int) -> Optional[Assignment]:
    """ID로 과제 조회"""
    conn = _get_connection()
    row = conn.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_assignment(row)


def update_assignment_status(assignment_id: int, new_status: str) -> Optional[Assignment]:
    """과제 상태 변경"""
    valid = {s.value for s in AssignmentStatus}
    if new_status not in valid:
        raise ValueError(f"유효하지 않은 상태입니다: {new_status}. 가능한 값: {valid}")

    conn = _get_connection()
    conn.execute(
        "UPDATE assignments SET status = ? WHERE id = ?",
        (new_status, assignment_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_assignment(row)


def delete_assignment(assignment_id: int) -> bool:
    """과제 삭제 (성공 여부 반환)"""
    conn = _get_connection()
    cursor = conn.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def get_upcoming_assignments(days: int = 7) -> List[Assignment]:
    """마감 임박 과제 조회 (기본 7일 이내)"""
    conn = _get_connection()
    now = datetime.now().strftime("%Y-%m-%d")
    future = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    rows = conn.execute(
        """
        SELECT * FROM assignments
        WHERE due_date BETWEEN ? AND ?
          AND status != 'done'
        ORDER BY due_date ASC
        """,
        (now, future),
    ).fetchall()
    conn.close()
    return [_row_to_assignment(r) for r in rows]


# ──────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────


def _row_to_assignment(row: sqlite3.Row) -> Assignment:
    """sqlite3.Row → Assignment Pydantic 모델 변환"""
    return Assignment(
        id=row["id"],
        title=row["title"],
        course_name=row["course_name"],
        description=row["description"],
        due_date=row["due_date"],
        status=row["status"],
        priority=row["priority"] if row["priority"] else "medium",
        created_at=row["created_at"],
    )


# ──────────────────────────────────────
# 캘린더 / 일정 CRUD
# ──────────────────────────────────────


def add_schedule(data: ScheduleCreate) -> Schedule:
    """일정 추가"""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO schedules (title, date, start_time, end_time, category, description, is_recurring)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.title, data.date, data.start_time, data.end_time,
            data.category, data.description, 1 if data.is_recurring else 0,
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid
    row = cursor.execute("SELECT * FROM schedules WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return _row_to_schedule(row)


def get_schedules(
    category: Optional[str] = None,
    date: Optional[str] = None,
) -> List[Schedule]:
    """일정 목록 조회 (필터 옵션)"""
    conn = _get_connection()
    query = "SELECT * FROM schedules WHERE 1=1"
    params: list = []

    if category:
        query += " AND category = ?"
        params.append(category)
    if date:
        query += " AND date = ?"
        params.append(date)

    query += " ORDER BY date ASC, start_time ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [_row_to_schedule(r) for r in rows]


def get_schedules_by_date_range(start_date: str, end_date: str) -> List[Schedule]:
    """날짜 범위로 일정 조회"""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM schedules WHERE date BETWEEN ? AND ? ORDER BY date ASC, start_time ASC",
        (start_date, end_date),
    ).fetchall()
    conn.close()
    return [_row_to_schedule(r) for r in rows]


def get_today_schedules() -> List[Schedule]:
    """오늘 일정 조회"""
    today = datetime.now().strftime("%Y-%m-%d")
    return get_schedules(date=today)


def delete_schedule(schedule_id: int) -> bool:
    """일정 삭제"""
    conn = _get_connection()
    cursor = conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def get_schedule_by_id(schedule_id: int) -> Optional[Schedule]:
    """ID로 일정 조회"""
    conn = _get_connection()
    row = conn.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_schedule(row)


def get_dday_schedules(category: Optional[str] = "exam") -> List[dict]:
    """D-day 계산이 포함된 일정 조회 (기본: 시험)"""
    conn = _get_connection()
    query = "SELECT * FROM schedules WHERE date >= ? "
    params: list = [datetime.now().strftime("%Y-%m-%d")]
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY date ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    results = []
    today = datetime.now().date()
    for r in rows:
        schedule = _row_to_schedule(r)
        target = datetime.strptime(schedule.date, "%Y-%m-%d").date()
        d_day = (target - today).days
        results.append({
            "schedule": schedule,
            "d_day": d_day,
            "display": f"{'D-day' if d_day == 0 else f'D-{d_day}'} | {schedule.title} ({schedule.date})",
        })
    return results


def _row_to_schedule(row: sqlite3.Row) -> Schedule:
    """sqlite3.Row → Schedule Pydantic 모델 변환"""
    return Schedule(
        id=row["id"],
        title=row["title"],
        date=row["date"],
        start_time=row["start_time"],
        end_time=row["end_time"],
        category=row["category"] if row["category"] else "personal",
        description=row["description"],
        is_recurring=bool(row["is_recurring"]),
        created_at=row["created_at"],
    )


if __name__ == "__main__":
    init_sqlite_db()
