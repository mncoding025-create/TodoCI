import os

import storage
from todo import TodoList


def test_load_missing_returns_empty(tmp_path):
    assert len(storage.load(str(tmp_path / "none.json"))) == 0


def test_save_load_roundtrip_thai(tmp_path):
    p = str(tmp_path / "sub" / "t.json")
    tl = TodoList()
    tl.add("ภาษาไทย", tags="ไทย")
    storage.save(tl, p)
    assert storage.load(p).get(1).title == "ภาษาไทย"
    assert [f for f in os.listdir(os.path.dirname(p)) if f.endswith(".tmp")] == []
