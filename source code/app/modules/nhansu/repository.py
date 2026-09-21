"""
LỚP DATA (Data Access Layer)
----------------------------
Truy vấn CSDL thuần túy cho Nhân sự VÀ Phân công (`phancong`). Phân công là
THỰC THỂ KẾT HỢP giữa Nhân sự và Hạng mục (gán 1 nhân sự vào làm việc tại 1
hạng mục cụ thể trong 1 khoảng thời gian), được quản lý gộp vào module này
theo hướng "từ 1 nhân sự, xem/thêm/sửa/xóa các phân công của người đó" - xem
service.py để biết đầy đủ lý do và các quy tắc nghiệp vụ liên quan. Không
chứa logic nghiệp vụ (validate chồng lịch, giới hạn hạng mục con, chặn xóa
khi còn phụ thuộc... đều nằm ở service.py).
"""

from app.extensions import db
from app.models import NhanSu, PhanCong, HangMuc, ChiPhi


# ---------------------- Nhân sự ----------------------

def get_all(keyword=None, ma_hangmuc=None):
    query = NhanSu.query
    if ma_hangmuc:
        query = query.join(PhanCong, PhanCong.nhansu_MaNV == NhanSu.MaNV) \
            .filter(PhanCong.hangmuc_MaHangMuc == ma_hangmuc).distinct()
    if keyword:
        query = query.filter(
            (NhanSu.TenNV.ilike(f'%{keyword}%')) |
            (NhanSu.HoNV.ilike(f'%{keyword}%')) |
            (NhanSu.ChucVu.ilike(f'%{keyword}%'))
        )
    return query.order_by(NhanSu.MaNV).all()


def get_by_id_or_404(ma):
    return NhanSu.query.get_or_404(ma)


def exists(ma):
    return NhanSu.query.get(ma) is not None


def insert(entity: NhanSu):
    db.session.add(entity)
    db.session.commit()


def update():
    db.session.commit()


def delete(entity: NhanSu):
    db.session.delete(entity)
    db.session.commit()


def dem_phan_cong(ma_nv):
    """Đếm số phân công hiện có của 1 nhân sự - dùng chặn xóa nhân sự khi
    vẫn còn phân công phụ thuộc (tương tự quy tắc chặn xóa hạng mục còn con
    ở module Hạng mục)."""
    return PhanCong.query.filter(PhanCong.nhansu_MaNV == ma_nv).count()


# ---------------------- Phân công ----------------------

def danh_sach_phan_cong_theo_nhansu(ma_nv):
    # LƯU Ý: KHÔNG dùng .nullslast() ở đây - đó là cú pháp ORDER BY ...
    # NULLS LAST của PostgreSQL/Oracle, MySQL không hỗ trợ và sẽ ném lỗi
    # ProgrammingError (1064) ngay tại đây. May mắn là MySQL vốn đã tự xếp
    # NULL xuống CUỐI khi ORDER BY ... DESC (ngược lại, NULL lên ĐẦU khi
    # ASC) - nên .desc() không kèm gì thêm đã cho đúng hành vi mong muốn
    # (phân công chưa có NgayBatDau sẽ tự động rơi xuống cuối danh sách).
    return PhanCong.query.filter(PhanCong.nhansu_MaNV == ma_nv)\
        .order_by(PhanCong.NgayBatDau.desc(), PhanCong.MaPhanCong).all()


def get_phan_cong_or_404(ma_phancong):
    return PhanCong.query.get_or_404(ma_phancong)


def insert_phan_cong(entity: PhanCong):
    db.session.add(entity)
    db.session.commit()


def update_phan_cong():
    db.session.commit()


def delete_phan_cong(entity: PhanCong):
    db.session.delete(entity)
    db.session.commit()


def dem_chi_phi_theo_phancong(ma_phancong):
    """Đếm số dòng chi phí (`chiphi`) đang tham chiếu tới 1 phân công - dùng
    chặn xóa phân công khi đã có chi phí ghi nhận gắn với nó (ràng buộc khóa
    ngoại thật `fk_chiphi_phancong1` trong mainDB_latest.sql - nếu không chặn ở
    đây, CSDL sẽ tự chặn bằng lỗi IntegrityError khó hiểu hơn cho người dùng)."""
    return ChiPhi.query.filter(ChiPhi.phancong_MaPhanCong == ma_phancong).count()


# ---------------------- Hạng mục (dữ liệu tham chiếu) ----------------------
# Bảng `hangmuc` không thuộc phạm vi module này - chỉ ĐỌC để phục vụ dropdown
# chọn hạng mục con khi phân công.

def danh_sach_hang_muc_con():
    """Chỉ những hạng mục CÓ hạng mục cha thực sự (không tự trỏ vào chính
    nó) - xem lý do nghiệp vụ ở service.py."""
    return HangMuc.query.filter(
        HangMuc.hangmuc_MaHangMuc != HangMuc.MaHangMuc
    ).order_by(HangMuc.MaHangMuc).all()


def hang_muc_con_theo_ma(ma_hangmuc):
    hangmuc = HangMuc.query.get(ma_hangmuc)
    if hangmuc is None or hangmuc.hangmuc_MaHangMuc == hangmuc.MaHangMuc:
        return None
    return hangmuc
