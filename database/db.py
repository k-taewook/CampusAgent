"""
CampusAgent SQLite 데이터베이스 모듈
- 테이블 초기화
- 과제 CRUD 함수 (추가, 조회, 수정, 삭제)
"""
import sqlite3
from typing import List, Optional
from datetime import datetime, timedelta

from config.settings import SQLITE_DB_PATH
from database.models import Assignment, AssignmentCreate, AssignmentStatus


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

    conn.commit()
    conn.close()
    print("✅ SQLite 세팅 완료")


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


if __name__ == "__main__":
    init_sqlite_db()
