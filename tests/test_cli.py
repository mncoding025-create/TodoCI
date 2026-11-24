import app


def run(tmp_path, *argv):
    return app.main(["--file", str(tmp_path / "t.json"), *argv])


def test_add_list_done_flow(tmp_path, capsys):
    assert run(tmp_path, "add", "ส่งรายงาน", "--due", "2026-12-31", "--priority", "high", "--tags", "uni") == 0
    assert run(tmp_path, "start", "1") == 0
    assert run(tmp_path, "done", "1") == 0
    capsys.readouterr()
    assert run(tmp_path, "list", "--status", "done") == 0
    out = capsys.readouterr().out
    assert "[x]" in out and "ส่งรายงาน" in out and "#uni" in out


def test_persists_between_runs(tmp_path, capsys):
    run(tmp_path, "add", "a")
    run(tmp_path, "add", "b")
    capsys.readouterr()
    run(tmp_path, "list")
    assert capsys.readouterr().out.count("#") == 2


def test_error_exit_code(tmp_path, capsys):
    assert run(tmp_path, "add", "x", "--due", "bad") == 1
    assert run(tmp_path, "done", "99") == 1
    assert "ผิดพลาด" in capsys.readouterr().err


def test_search_stats_overdue_clear(tmp_path, capsys):
    run(tmp_path, "add", "เก่า", "--due", "2000-01-01")
    run(tmp_path, "add", "ใหม่")
    run(tmp_path, "done", "2")
    capsys.readouterr()
    run(tmp_path, "overdue")
    assert "เก่า" in capsys.readouterr().out
    run(tmp_path, "search", "ใหม่")
    assert "ใหม่" in capsys.readouterr().out
    run(tmp_path, "stats")
    assert "งานทั้งหมด 2" in capsys.readouterr().out
    run(tmp_path, "clear-done")
    assert "1 งาน" in capsys.readouterr().out
