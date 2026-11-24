from datetime import date

import pytest

from todo import TodoList


def make():
    tl = TodoList()
    tl.add("ส่งรายงาน", due="2026-12-01", priority="high", tags="uni, Report")
    tl.add("ซื้อของ", priority="low")
    tl.add("อ่านหนังสือ", due="2026-01-01")
    return tl


def test_add_assigns_incrementing_ids():
    tl = TodoList()
    assert [tl.add("a").id, tl.add("b").id] == [1, 2]


def test_add_cleans_title_and_tags():
    t = TodoList().add("  งาน  ", tags=" A, a ,b,, ")
    assert t.title == "งาน" and t.tags == ["a", "b"]


@pytest.mark.parametrize("title", ["", "   ", None])
def test_empty_title_rejected(title):
    with pytest.raises(ValueError):
        TodoList().add(title)


def test_long_title_rejected():
    with pytest.raises(ValueError):
        TodoList().add("x" * 201)


def test_bad_due_and_priority_rejected():
    tl = TodoList()
    with pytest.raises(ValueError):
        tl.add("a", due="31/12/2026")
    with pytest.raises(ValueError):
        tl.add("a", priority="urgent")


def test_get_missing_raises_keyerror():
    with pytest.raises(KeyError):
        TodoList().get(99)


def test_edit_changes_only_given_fields():
    tl = make()
    t = tl.edit(1, title="ใหม่")
    assert (t.title, t.due, t.priority) == ("ใหม่", "2026-12-01", "high")


def test_edit_can_clear_due_and_tags():
    tl = make()
    t = tl.edit(1, due="", tags=[])
    assert t.due is None and t.tags == []


def test_edit_invalid_leaves_task_unchanged():
    tl = make()
    with pytest.raises(ValueError):
        tl.edit(1, title="ok", due="bad")
    assert tl.get(1).title == "ส่งรายงาน"


def test_delete_and_ids_not_reused():
    tl = make()
    tl.delete(3)
    assert tl.add("ใหม่").id == 4
    with pytest.raises(KeyError):
        tl.delete(3)


def test_status_flow_and_done_at():
    tl = make()
    assert tl.start(1).status == "doing"
    t = tl.complete(1, today=date(2026, 5, 5))
    assert t.status == "done" and t.done_at == "2026-05-05"
    assert tl.set_status(1, "todo").done_at is None


def test_invalid_status_rejected():
    with pytest.raises(ValueError):
        make().set_status(1, "finished")


def test_list_filters():
    tl = make()
    tl.complete(2)
    assert [t.id for t in tl.list(status="done")] == [2]
    assert [t.id for t in tl.list(priority="high")] == [1]
    assert [t.id for t in tl.list(tag="REPORT")] == [1]


def test_search_title_and_tag():
    tl = make()
    assert [t.id for t in tl.list(q="รายงาน")] == [1]
    assert [t.id for t in tl.list(q="uni")] == [1]
    assert tl.list(q="ไม่มีแน่นอน") == []


def test_sorting():
    tl = make()
    assert [t.id for t in tl.list(sort="due")] == [3, 1, 2]       # ไม่มีกำหนดอยู่ท้าย
    assert [t.id for t in tl.list(sort="priority")] == [1, 3, 2]
    with pytest.raises(ValueError):
        tl.list(sort="nope")


def test_overdue_excludes_done_and_future():
    tl = make()
    today = date(2026, 6, 1)
    assert [t.id for t in tl.overdue(today)] == [3]
    tl.complete(3)
    assert tl.overdue(today) == []


def test_clear_done():
    tl = make()
    tl.complete(1)
    tl.complete(2)
    assert tl.clear_done() == 2 and len(tl) == 1


def test_stats():
    tl = make()
    tl.complete(2)
    s = tl.stats(today=date(2026, 6, 1))
    assert s["total"] == 3 and s["by_status"]["done"] == 1
    assert s["overdue"] == 1 and s["completion_rate"] == 33
    assert s["open_by_priority"] == {"low": 0, "medium": 1, "high": 1}


def test_stats_empty():
    assert TodoList().stats()["completion_rate"] == 0


def test_json_roundtrip_keeps_next_id():
    tl = make()
    tl.delete(3)
    again = TodoList.from_json(tl.to_json())
    assert [t.title for t in again.list()] == [t.title for t in tl.list()]
    assert again.add("x").id == 4


def test_from_json_old_format_compatible():
    old = '{"next_id": 2, "tasks": [{"id": 1, "title": "เก่า", "status": "todo", "due": null}]}'
    t = TodoList.from_json(old).get(1)
    assert t.priority == "medium" and t.tags == []
