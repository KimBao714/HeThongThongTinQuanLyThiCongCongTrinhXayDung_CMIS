# Kiến trúc 3 lớp (3-Layer Architecture)

Mỗi module trong `app/modules/<ten_module>/` được tách thành đúng 3 file,
mỗi file đảm nhiệm 1 lớp riêng biệt, không lẫn trách nhiệm:

## 1. Presentation Layer — `routes.py`
- Nhận HTTP request (`request.form`, `request.args`, `request.files`)
- Gọi xuống Business layer (`service.py`) để xử lý
- Trả về `render_template(...)` hoặc `redirect(...)`
- KHÔNG tự viết câu SQL, KHÔNG tự validate nghiệp vụ

## 2. Business Layer — `service.py`
- Validate dữ liệu (VD: kiểm tra trùng mã trước khi thêm)
- Tính toán / quy đổi (VD: cộng dồn ngân sách ở module Hạng mục,
  tính chi phí vật liệu + nhân công ở module Chi phí)
- Ném `LoiNghiepVu` (exception tự định nghĩa) khi vi phạm quy tắc
- Gọi xuống Data layer (`repository.py`) để đọc/ghi dữ liệu
- KHÔNG biết gì về Flask request/response, KHÔNG tự viết câu SQL

## 3. Data Layer — `repository.py`
- CHỈ chứa các câu truy vấn CSDL thuần túy qua SQLAlchemy
  (`Model.query...`, `db.session.add/commit/delete`)
- Module Bản vẽ có thêm phần lưu trữ file vật lý (cũng là 1 dạng "persistence")
- KHÔNG chứa logic nghiệp vụ, KHÔNG validate

## Sơ đồ luồng gọi

```
Trình duyệt
    │  HTTP request
    ▼
routes.py        (Presentation) ─── render_template / redirect ──► Trình duyệt
    │  gọi hàm
    ▼
service.py       (Business)     ─── validate, tính toán, LoiNghiepVu
    │  gọi hàm
    ▼
repository.py     (Data)         ─── SQLAlchemy query, db.session
    │
    ▼
  MySQL
```

## Ví dụ cụ thể: Thêm 1 hạng mục mới

1. `routes.py` → `add_hangmuc()`: nhận `request.form`, gọi `service.them_moi(request.form)`
2. `service.py` → `them_moi()`: kiểm tra mã đã tồn tại chưa (`repository.exists(ma)`),
   kiểm tra hạng mục cha tồn tại (nếu có), validate ngân sách và ngày tháng —
   vi phạm bất kỳ quy tắc nào thì `raise LoiNghiepVu(...)`; nếu hợp lệ, tạo
   entity rồi gọi `repository.insert(entity)`
3. `repository.py` → `insert()`: `db.session.add(entity)` + `db.session.commit()`

Nếu sau này đổi CSDL (VD: MySQL sang PostgreSQL) hoặc đổi ORM, chỉ cần sửa
`repository.py` — `service.py` và `routes.py` không cần đổi gì.
