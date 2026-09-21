"""
LỚP DATA (Data Access Layer)
----------------------------
Truy vấn CSDL thuần túy cho Vật liệu VÀ Sử dụng vật liệu (`sudungvatlieu`).
Sử dụng vật liệu là THỰC THỂ KẾT HỢP giữa Vật liệu và Hạng mục (ghi nhận 1
loại vật liệu được dùng bao nhiêu cho 1 hạng mục cụ thể), được quản lý gộp
vào module này theo hướng "từ 1 vật liệu, xem/thêm/sửa/xóa các lượt sử dụng
của vật liệu đó cho từng hạng mục" - giống cách `phancong` được gộp vào
module Nhân sự (xem app/modules/nhansu/repository.py). Không chứa logic
nghiệp vụ (validate hạng mục con, chặn trùng cặp khóa, chặn xóa khi còn chi
phí phụ thuộc... đều nằm ở service.py).
"""

from sqlalchemy import func

from app.extensions import db
from app.models import VatLieu, SuDungVatLieu, HangMuc, ChiPhi


# ---------------------- Vật liệu ----------------------

def get_all(keyword=None, ma_hangmuc=None):
    query = VatLieu.query
    if ma_hangmuc:
        query = query.join(
            SuDungVatLieu, SuDungVatLieu.vatlieu_MaVL == VatLieu.MaVL
        ).filter(SuDungVatLieu.hangmuc_MaHangMuc == ma_hangmuc).distinct()
    if keyword:
        query = query.filter(VatLieu.TenVL.ilike(f'%{keyword}%'))
    return query.order_by(VatLieu.MaVL).all()


def get_by_id(ma):
    return VatLieu.query.get(ma)


def get_by_id_or_404(ma):
    return VatLieu.query.get_or_404(ma)


def exists(ma):
    return VatLieu.query.get(ma) is not None


def insert(entity: VatLieu):
    db.session.add(entity)
    db.session.commit()


def update():
    db.session.commit()


def delete(entity: VatLieu):
    db.session.delete(entity)
    db.session.commit()


def dem_su_dung(ma_vl):
    """Đếm số lượt sử dụng (số hạng mục) hiện có của 1 vật liệu - dùng chặn
    xóa vật liệu khi vẫn còn hạng mục đang sử dụng nó (tương tự quy tắc chặn
    xóa nhân sự còn phân công ở module Nhân sự)."""
    return SuDungVatLieu.query.filter(SuDungVatLieu.vatlieu_MaVL == ma_vl).count()


def tong_so_luong_da_dung(ma_vl):
    """Tổng SoLuongSD của 1 vật liệu, cộng dồn qua TẤT CẢ hạng mục đang dùng
    nó - dùng so sánh với SoLuongDangCo (số lượng đang có) khai báo ở bảng
    `vatlieu` (xem service.tinh_su_dung)."""
    tong = db.session.query(func.sum(SuDungVatLieu.SoLuongSD)).filter(
        SuDungVatLieu.vatlieu_MaVL == ma_vl
    ).scalar()
    return tong or 0


def tong_so_luong_da_dung_theo_tat_ca():
    """[(MaVL, tong_so_luong), ...] - tổng SoLuongSD cộng dồn theo TỪNG vật
    liệu, cho TOÀN BỘ vật liệu trong 1 truy vấn GROUP BY duy nhất. Dùng ở
    Dashboard tổng quan (service.danh_sach_vuot_du_kien) để tính cảnh báo
    vượt số lượng đang có cho tất cả vật liệu cùng lúc, tránh phải gọi lặp
    lại tong_so_luong_da_dung() cho từng vật liệu (N+1 query)."""
    return db.session.query(
        SuDungVatLieu.vatlieu_MaVL, func.sum(SuDungVatLieu.SoLuongSD)
    ).group_by(SuDungVatLieu.vatlieu_MaVL).all()


# ---------------------- Sử dụng vật liệu ----------------------

def danh_sach_su_dung_theo_vatlieu(ma_vl):
    return SuDungVatLieu.query.filter(SuDungVatLieu.vatlieu_MaVL == ma_vl) \
        .order_by(SuDungVatLieu.hangmuc_MaHangMuc).all()


def get_su_dung_or_404(ma_vl, ma_hangmuc):
    return SuDungVatLieu.query.get_or_404((ma_vl, ma_hangmuc))


def su_dung_theo_khoa(ma_vl, ma_hangmuc):
    """Khóa chính của `sudungvatlieu` là khóa kép (vatlieu_MaVL,
    hangmuc_MaHangMuc) - dùng để kiểm tra 1 cặp (vật liệu, hạng mục) đã có
    dòng ghi nhận từ trước hay chưa (chặn trùng khi thêm mới)."""
    return SuDungVatLieu.query.get((ma_vl, ma_hangmuc))


def insert_su_dung(entity: SuDungVatLieu):
    db.session.add(entity)
    db.session.commit()


def update_su_dung():
    db.session.commit()


def delete_su_dung(entity: SuDungVatLieu):
    db.session.delete(entity)
    db.session.commit()


def dem_chi_phi_theo_su_dung(ma_vl, ma_hangmuc):
    """Đếm số dòng chi phí (`chiphi`) đang tham chiếu tới 1 lượt sử dụng vật
    liệu - dùng chặn xóa khi đã có chi phí ghi nhận gắn với nó (ràng buộc
    khóa ngoại thật `fk_chiphi_sudungvatlieu1` trong mainDB_latest.sql - nếu
    không chặn ở đây, CSDL sẽ tự chặn bằng lỗi IntegrityError khó hiểu hơn
    cho người dùng)."""
    return ChiPhi.query.filter(
        ChiPhi.sudungvatlieu_vatlieu_MaVL == ma_vl,
        ChiPhi.sudungvatlieu_hangmuc_MaHangMuc == ma_hangmuc
    ).count()


# ---------------------- Hạng mục (dữ liệu tham chiếu) ----------------------
# Bảng `hangmuc` không thuộc phạm vi module này - chỉ ĐỌC để phục vụ dropdown
# chọn hạng mục khi ghi nhận sử dụng vật liệu.

def danh_sach_hang_muc_con():
    """Chỉ những hạng mục CÓ hạng mục cha thực sự (không tự trỏ vào chính
    nó) - lý do nghiệp vụ xem service.py (áp dụng đúng quy tắc đã có ở
    module Nhân sự cho `phancong`)."""
    return HangMuc.query.filter(
        HangMuc.hangmuc_MaHangMuc != HangMuc.MaHangMuc
    ).order_by(HangMuc.MaHangMuc).all()


def hang_muc_con_theo_ma(ma_hangmuc):
    hangmuc = HangMuc.query.get(ma_hangmuc)
    if hangmuc is None or hangmuc.hangmuc_MaHangMuc == hangmuc.MaHangMuc:
        return None
    return hangmuc
