"""TodoCI: logic หลักของระบบจดงาน (ไม่ผูกกับ UI หรือเว็บ)"""
import json
from dataclasses import asdict, dataclass, field, fields
from datetime import date
from typing import Dict, Iterable, List, Optional, Union

VERSION = "1.0.0"
STATUSES = ("todo", "doing", "done")
PRIORITIES = ("low", "medium", "high")
SORTS = ("id", "due", "priority", "title")
_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


@dataclass
class Task:
    id: int
    title: str
    status: str = "todo"
    due: Optional[str] = None            # YYYY-MM-DD
    priority: str = "medium"
    tags: List[str] = field(default_factory=list)
    created: str = field(default_factory=lambda: date.today().isoformat())
    done_at: Optional[str] = None        # YYYY-MM-DD ตอนทำเสร็จ


def _parse_due(due: Optional[str]) -> Optional[str]:
    """ตรวจรูปแบบวันที่ คืนค่า YYYY-MM-DD หรือ None (ค่าว่าง = ไม่มีกำหนด)"""
    if due is None or due == "":
        return None
    try:
        return date.fromisoformat(due).isoformat()
    except (ValueError, TypeError):
        raise ValueError("วันที่ต้องอยู่ในรูปแบบ YYYY-MM-DD: %s" % due)


def _clean_title(title: Optional[str]) -> str:
    title = (title or "").strip()
    if not title:
        raise ValueError("ชื่องานห้ามว่าง")
    if len(title) > 200:
        raise ValueError("ชื่องานยาวเกิน 200 ตัวอักษร")
    return title


def _check_priority(priority: str) -> str:
    if priority not in PRIORITIES:
        raise ValueError("priority ต้องเป็นหนึ่งใน %s" % (PRIORITIES,))
    return priority


def _check_status(status: str) -> str:
    if status not in STATUSES:
        raise ValueError("สถานะต้องเป็นหนึ่งใน %s" % (STATUSES,))
    return status


def _clean_tags(tags: Union[None, str, Iterable[str]]) -> List[str]:
    """รับ list หรือสตริงคั่นด้วย comma -> list ตัวพิมพ์เล็ก ไม่ซ้ำ ไม่ว่าง"""
    if tags is None:
        return []
    if isinstance(tags, str):
        tags = tags.split(",")
    seen, out = set(), []
    for t in tags:
        t = str(t).strip().lower()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


class TodoList:
    def __init__(self):
        self._tasks: List[Task] = []
        self._next_id = 1

    def __len__(self) -> int:
        return len(self._tasks)

    # ---------- เพิ่ม / แก้ / ลบ ----------
    def add(self, title: str, due: Optional[str] = None,
            priority: str = "medium", tags=None) -> Task:
        task = Task(
            id=self._next_id,
            title=_clean_title(title),
            due=_parse_due(due),
            priority=_check_priority(priority),
            tags=_clean_tags(tags),
        )
        self._next_id += 1
        self._tasks.append(task)
        return task

    def get(self, task_id: int) -> Task:
        for t in self._tasks:
            if t.id == task_id:
                return t
        raise KeyError("ไม่พบงาน id=%s" % task_id)

    def edit(self, task_id: int, title: Optional[str] = None,
             due: Optional[str] = None, priority: Optional[str] = None,
             tags=None) -> Task:
        """แก้เฉพาะช่องที่ส่งมา (due="" = ลบกำหนดส่ง, tags=[] = ล้างแท็ก)"""
        task = self.get(task_id)
        new_title = _clean_title(title) if title is not None else task.title
        new_due = _parse_due(due) if due is not None else task.due
        new_priority = _check_priority(priority) if priority is not None else task.priority
        new_tags = _clean_tags(tags) if tags is not None else task.tags
        task.title, task.due, task.priority, task.tags = new_title, new_due, new_priority, new_tags
        return task

    def delete(self, task_id: int) -> None:
        self._tasks.remove(self.get(task_id))

    def clear_done(self) -> int:
        """ลบงานที่เสร็จแล้วทั้งหมด คืนจำนวนที่ลบ"""
        before = len(self._tasks)
        self._tasks = [t for t in self._tasks if t.status != "done"]
        return before - len(self._tasks)

    # ---------- สถานะ ----------
    def set_status(self, task_id: int, status: str,
                   today: Optional[date] = None) -> Task:
        _check_status(status)
        task = self.get(task_id)
        task.status = status
        if status == "done":
            task.done_at = (today or date.today()).isoformat()
        else:
            task.done_at = None
        return task

    def start(self, task_id: int) -> Task:
        return self.set_status(task_id, "doing")

    def complete(self, task_id: int, today: Optional[date] = None) -> Task:
        return self.set_status(task_id, "done", today)

    # ---------- ค้นหา / กรอง / เรียง ----------
    def list(self, status: Optional[str] = None, priority: Optional[str] = None,
             tag: Optional[str] = None, q: Optional[str] = None,
             sort: str = "id") -> List[Task]:
        if status is not None:
            _check_status(status)
        if priority is not None:
            _check_priority(priority)
        if sort not in SORTS:
            raise ValueError("sort ต้องเป็นหนึ่งใน %s" % (SORTS,))

        result = list(self._tasks)
        if status is not None:
            result = [t for t in result if t.status == status]
        if priority is not None:
            result = [t for t in result if t.priority == priority]
        if tag:
            tag = tag.strip().lower()
            result = [t for t in result if tag in t.tags]
        if q:
            needle = q.strip().lower()
            result = [t for t in result
                      if needle in t.title.lower() or any(needle in g for g in t.tags)]

        if sort == "due":      # งานที่ไม่มีกำหนดไปท้ายสุด
            result.sort(key=lambda t: (t.due is None, t.due or "", t.id))
        elif sort == "priority":
            result.sort(key=lambda t: (_PRIORITY_RANK[t.priority], t.id))
        elif sort == "title":
            result.sort(key=lambda t: (t.title.lower(), t.id))
        return result

    def overdue(self, today: Optional[date] = None) -> List[Task]:
        """งานที่เลยกำหนดและยังไม่เสร็จ"""
        today = today or date.today()
        return [
            t for t in self._tasks
            if t.due and t.status != "done" and date.fromisoformat(t.due) < today
        ]

    def stats(self, today: Optional[date] = None) -> Dict[str, object]:
        total = len(self._tasks)
        by_status = {s: 0 for s in STATUSES}
        open_by_priority = {p: 0 for p in PRIORITIES}
        for t in self._tasks:
            by_status[t.status] += 1
            if t.status != "done":
                open_by_priority[t.priority] += 1
        rate = round(by_status["done"] * 100 / total) if total else 0
        return {
            "total": total,
            "by_status": by_status,
            "open_by_priority": open_by_priority,
            "overdue": len(self.overdue(today)),
            "completion_rate": rate,
        }

    # ---------- บันทึก / โหลด ----------
    def to_json(self) -> str:
        return json.dumps(
            {"next_id": self._next_id, "tasks": [asdict(t) for t in self._tasks]},
            ensure_ascii=False, indent=2,
        )

    @classmethod
    def from_json(cls, text: str) -> "TodoList":
        data = json.loads(text)
        known = {f.name for f in fields(Task)}
        tl = cls()
        tl._tasks = [Task(**{k: v for k, v in t.items() if k in known})
                     for t in data.get("tasks", [])]
        tl._next_id = data.get("next_id", max([t.id for t in tl._tasks] + [0]) + 1)
        return tl
