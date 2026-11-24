# TodoCI — ระบบจดงาน (Mini-Project DevOps: GitHub + Jenkins CI/CD)

ระบบจดงานที่ใช้งานได้จริง 2 แบบ: **เว็บ (REST API + หน้าเว็บ)** และ **CLI** เขียนด้วย Python ล้วน (ไม่ต้องติดตั้งไลบรารีเพิ่ม ยกเว้น `pytest` ตอนเทสต์)

## ฟีเจอร์
- เพิ่ม / แก้ไข / ลบงาน, กำหนดส่ง, ความสำคัญ (high/medium/low), แท็ก
- สถานะ `todo → doing → done` (บันทึกวันที่เสร็จ)
- ค้นหา, กรอง (สถานะ/ความสำคัญ/แท็ก), เรียง (ลำดับ/กำหนดส่ง/ความสำคัญ/ชื่อ)
- งานเลยกำหนด, สถิติ + % ความคืบหน้า, ล้างงานที่เสร็จแล้ว
- เก็บข้อมูลลงไฟล์ JSON (เขียนแบบ atomic), รองรับภาษาไทย

## โครงสร้าง
| ไฟล์ | หน้าที่ |
|---|---|
| `todo.py` | logic หลัก (TodoList, Task) |
| `storage.py` | อ่าน/เขียนไฟล์ JSON |
| `server.py` | เว็บเซิร์ฟเวอร์ + REST API |
| `static/index.html` | หน้าเว็บ (single page) |
| `app.py` | CLI |
| `tests/` | unit test, CLI test, API test (38 เทสต์) |
| `Jenkinsfile` | pipeline Build → Test → Deploy |

## วิธีรัน
```bash
# เว็บ  -> เปิด http://localhost:3002
python3 server.py --port 3002

# CLI
python3 app.py add "ส่งรายงาน" --due 2026-12-31 --priority high --tags uni,report
python3 app.py list --sort due
python3 app.py start 1
python3 app.py done 1
python3 app.py search รายงาน
python3 app.py stats
```

## REST API
| Method | Path | ความหมาย |
|---|---|---|
| GET | `/health` | ตรวจสถานะเซิร์ฟเวอร์ |
| GET | `/api/tasks?status=&priority=&tag=&q=&sort=` | รายการงาน |
| POST | `/api/tasks` | เพิ่มงาน `{title, due, priority, tags}` |
| GET/PATCH/DELETE | `/api/tasks/<id>` | ดู / แก้ (รวมเปลี่ยน `status`) / ลบ |
| GET | `/api/stats` | สถิติ |
| POST | `/api/clear-done` | ลบงานที่เสร็จทั้งหมด |

## เทสต์
```bash
pip install -r requirements.txt
pytest -v
```

## CI/CD
### 1) GitHub — รวมโค้ดด้วย branch + Pull Request
```bash
git checkout -b feature/ชื่อฟีเจอร์
git add . && git commit -m "feat: ..."
git push -u origin feature/ชื่อฟีเจอร์
# เปิด Pull Request บน GitHub -> review -> Merge เข้า main
```
สมาชิกแต่ละคนทำงานคนละ branch แล้ว merge เข้า `main` ผ่าน PR

### 2) Jenkins — Pipeline from SCM (`Jenkinsfile`)
1. New Item → ตั้งชื่อ `TodoCI` → **Pipeline**
2. Build Triggers → **Poll SCM** → `* * * * *`
3. Pipeline → *Pipeline script from SCM* → Git → ใส่ URL repo → Branch `*/main` → Script Path `Jenkinsfile`
4. Save → Build Now

| Stage | ทำอะไร |
|---|---|
| **Checkout** | ดึงโค้ดล่าสุดจาก GitHub |
| **Setup Python** | สร้าง venv, ติดตั้ง pytest + flake8 |
| **Lint** | ตรวจสไตล์โค้ดด้วย flake8 (ถ้าไม่ผ่าน build จะล้มทันที) |
| **Test** | รัน pytest 38 เทสต์ + รายงาน JUnit |
| **Build** | คอมไพล์ตรวจ syntax |
| **Deploy** | จำลอง deploy ไป `deploy/`, สตาร์ทเว็บจริง, health check + ยิง API (smoke test), แพ็ก `todo-app.tar.gz` เป็น artifact |

เมื่อ push/merge เข้า `main` Jenkins จะตรวจพบและรันให้อัตโนมัติ (ต้องมี Python 3 บนเครื่อง Jenkins และ `curl`)
