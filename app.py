"""TodoCI: โปรแกรมจดงานแบบบรรทัดคำสั่ง (CLI)

ตัวอย่าง:
  python3 app.py add "ส่งรายงาน" --due 2026-12-31 --priority high --tags uni,report
  python3 app.py list --sort due
  python3 app.py start 1 / done 1
  python3 app.py search รายงาน
  python3 app.py stats
"""
import argparse
import sys

import storage
from todo import PRIORITIES, SORTS, STATUSES, VERSION

MARK = {"todo": "[ ]", "doing": "[~]", "done": "[x]"}
PRI = {"high": "!!!", "medium": "!! ", "low": "!  "}


def fmt(t) -> str:
    due = " (ส่ง %s)" % t.due if t.due else ""
    tags = " #" + " #".join(t.tags) if t.tags else ""
    return "%s %s #%d %s%s%s" % (MARK[t.status], PRI[t.priority], t.id, t.title, due, tags)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="todo", description="TodoCI - ระบบจดงาน")
    p.add_argument("--file", default="tasks.json", help="ไฟล์เก็บข้อมูล (ค่าเริ่มต้น tasks.json)")
    p.add_argument("--version", action="version", version="TodoCI " + VERSION)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="เพิ่มงาน")
    a.add_argument("title")
    a.add_argument("--due", help="กำหนดส่ง YYYY-MM-DD")
    a.add_argument("--priority", choices=PRIORITIES, default="medium")
    a.add_argument("--tags", help="คั่นด้วย comma เช่น uni,report")

    e = sub.add_parser("edit", help="แก้งาน")
    e.add_argument("id", type=int)
    e.add_argument("--title")
    e.add_argument("--due", help='YYYY-MM-DD หรือ "" เพื่อลบกำหนดส่ง')
    e.add_argument("--priority", choices=PRIORITIES)
    e.add_argument("--tags", help='คั่นด้วย comma หรือ "" เพื่อล้าง')

    for name, helptext in (("delete", "ลบงาน"), ("start", "เริ่มทำงาน (doing)"),
                           ("done", "ทำงานเสร็จ")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("id", type=int)

    lp = sub.add_parser("list", help="แสดงรายการงาน")
    lp.add_argument("--status", choices=STATUSES)
    lp.add_argument("--priority", choices=PRIORITIES)
    lp.add_argument("--tag")
    lp.add_argument("--sort", choices=SORTS, default="id")

    s = sub.add_parser("search", help="ค้นหาจากชื่องาน/แท็ก")
    s.add_argument("query")

    sub.add_parser("overdue", help="งานที่เลยกำหนด")
    sub.add_parser("stats", help="สรุปสถิติ")
    sub.add_parser("clear-done", help="ลบงานที่เสร็จแล้วทั้งหมด")
    return p


def _print_list(tasks) -> None:
    if not tasks:
        print("(ไม่มีงาน)")
    for t in tasks:
        print(fmt(t))


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        tl = storage.load(args.file)
        changed = True
        if args.cmd == "add":
            print("เพิ่มแล้ว:", fmt(tl.add(args.title, args.due, args.priority, args.tags)))
        elif args.cmd == "edit":
            print("แก้แล้ว:", fmt(tl.edit(args.id, args.title, args.due, args.priority, args.tags)))
        elif args.cmd == "delete":
            tl.delete(args.id)
            print("ลบงาน #%d แล้ว" % args.id)
        elif args.cmd == "start":
            print("เริ่มทำ:", fmt(tl.start(args.id)))
        elif args.cmd == "done":
            print("เสร็จแล้ว:", fmt(tl.complete(args.id)))
        elif args.cmd == "clear-done":
            print("ลบงานที่เสร็จแล้ว %d งาน" % tl.clear_done())
        else:
            changed = False
            if args.cmd == "list":
                _print_list(tl.list(args.status, args.priority, args.tag, None, args.sort))
            elif args.cmd == "search":
                _print_list(tl.list(q=args.query))
            elif args.cmd == "overdue":
                _print_list(tl.overdue())
            elif args.cmd == "stats":
                s = tl.stats()
                print("งานทั้งหมด %d | ทำเสร็จ %d%% | เลยกำหนด %d" %
                      (s["total"], s["completion_rate"], s["overdue"]))
                print("สถานะ:", ", ".join("%s=%d" % kv for kv in s["by_status"].items()))
        if changed:
            storage.save(tl, args.file)
    except (ValueError, KeyError) as e:
        print("ผิดพลาด: %s" % (e.args[0] if isinstance(e, KeyError) else e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
