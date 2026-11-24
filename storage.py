"""อ่าน/เขียน TodoList ลงไฟล์ JSON (เขียนแบบ atomic กันไฟล์พัง)"""
import os
import tempfile

from todo import TodoList


def load(path: str) -> TodoList:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return TodoList.from_json(f.read())
    return TodoList()


def save(tl: TodoList, path: str) -> None:
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(tl.to_json())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
