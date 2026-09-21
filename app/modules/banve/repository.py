"""
LỚP DATA (Data Access Layer)
----------------------------
Truy vấn CSDL thuần túy cho Bản vẽ + Phiên bản bản vẽ. Module này còn đảm
nhiệm thêm phần LƯU TRỮ FILE VẬT LÝ trên đĩa (cũng là 1 dạng "persistence" -
xem README_3LAYER.md, mục "Module Bản vẽ"), vì mỗi phiên bản gắn với 1 file
(`HinhBV`). Không chứa logic nghiệp vụ (duyệt/từ chối, sinh số phiên bản,
quy tắc xóa... đều nằm ở service.py).
"""

import os

from app.extensions import db
from app.models import BanVe, PhienBan, TrangThaiPhienBan, HangMuc
from app.utils import sinh_ten_file_duy_nhat

# 4 trạng thái cố định của 1 phiên bản bản vẽ. Bảng `trangthaiphienban` là
# bảng tra cứu (lookup) không có route quản lý riêng - hệ thống tự đảm bảo
# đủ 3 dòng này tồn tại khi khởi động app (xem dam_bao_trang_thai_mac_dinh()
# được gọi từ app/__init__.py).
CHO_DUYET = 'CHO_DUYET'
DA_DUYET = 'DA_DUYET'
TU_CHOI = 'TU_CHOI'
CU = 'CU'

_TRANG_THAI_MAC_DINH = [
    (CHO_DUYET, 'Chờ duyệt', 'Phiên bản vừa tải lên, đang chờ phê duyệt.'),
    (DA_DUYET, 'Đã duyệt', 'Phiên bản đã được phê duyệt chính thức.'),
    (TU_CHOI, 'Từ chối', 'Phiên bản bị từ chối, cần tải lên phiên bản mới.'),
    (CU, 'Cũ', 'Phiên bản đã được thay thế bởi phiên bản mới hơn.'),
]


def dam_bao_trang_thai_mac_dinh():
    """Seed các trạng thái cố định vào bảng `trangthaiphienban` nếu CSDL chưa
    có (bảng này rỗng trong file SQL gốc). Gọi 1 lần khi khởi động app."""
    for ma, ten, mota in _TRANG_THAI_MAC_DINH:
        if TrangThaiPhienBan.query.get(ma) is None:
            db.session.add(TrangThaiPhienBan(MaTrangThai=ma, TenTrangThai=ten, MoTa=mota))
    db.session.commit()


# ---------------------- Bản vẽ ----------------------

def get_all(keyword=None, ma_hangmuc=None):
    query = BanVe.query
    if keyword:
        query = query.filter(
            (BanVe.TenBV.ilike(f'%{keyword}%')) |
            (BanVe.MaBV.ilike(f'%{keyword}%'))
        )
    if ma_hangmuc:
        query = query.filter(BanVe.hangmuc_hangmuc_MaHangMuc == ma_hangmuc)
    return query.order_by(BanVe.MaBV).all()


def get_by_id_or_404(ma):
    return BanVe.query.get_or_404(ma)


def exists(ma):
    return BanVe.query.get(ma) is not None


def insert(entity: BanVe):
    db.session.add(entity)
    db.session.commit()


def insert_banve_va_phien_ban(banve_entity: BanVe, phienban_entity: PhienBan):
    """Chèn đồng thời 1 bản vẽ + phiên bản đầu tiên của nó trong CÙNG 1
    transaction (1 lần commit duy nhất) - dùng khi tạo bản vẽ mới, để nếu
    có lỗi xảy ra thì KHÔNG để lại bản vẽ "rỗng" chưa có phiên bản/file nào
    (xem quy tắc 0 ở service.py). `banve_MaBV` của phiên bản chỉ là 1 chuỗi
    do người dùng nhập (không phải khóa tự sinh), nên không cần insert bản
    vẽ trước và lấy lại ID - gán thẳng được ngay từ đầu."""
    db.session.add(banve_entity)
    db.session.add(phienban_entity)
    db.session.commit()


def update():
    db.session.commit()


def delete(entity: BanVe):
    db.session.delete(entity)
    db.session.commit()


def delete_banve_va_phien_ban(entity: BanVe, danh_sach_phien_ban):
    """Xóa bản vẽ và toàn bộ phiên bản trong cùng một transaction."""
    for phien_ban in danh_sach_phien_ban:
        db.session.delete(phien_ban)
    db.session.delete(entity)
    db.session.commit()


def count_phien_ban(ma_bv):
    return PhienBan.query.filter(PhienBan.banve_MaBV == ma_bv).count()


# ---------------------- Hạng mục (dữ liệu tham chiếu) ----------------------

def danh_sach_hang_muc():
    return HangMuc.query.order_by(HangMuc.MaHangMuc).all()


def hang_muc_ton_tai(ma_hangmuc):
    return HangMuc.query.get(ma_hangmuc) is not None


# ---------------------- Phiên bản ----------------------

def lay_phien_ban_theo_banve(ma_bv):
    return PhienBan.query.filter(PhienBan.banve_MaBV == ma_bv).all()


def dem_so_phien_ban(ma_bv):
    return count_phien_ban(ma_bv)


def get_phien_ban_or_404(ma_pb):
    return PhienBan.query.get_or_404(ma_pb)


def insert_phien_ban(entity: PhienBan):
    db.session.add(entity)
    db.session.commit()


def update_phien_ban():
    db.session.commit()


def delete_phien_ban(entity: PhienBan):
    db.session.delete(entity)
    db.session.commit()


# ---------------------- Lưu trữ file vật lý ----------------------

def luu_file_vat_ly(file_storage, upload_folder):
    """Lưu file bản vẽ tải lên xuống đĩa với tên duy nhất, trả về tên file
    đã lưu (không kèm đường dẫn thư mục) để ghi vào cột `HinhBV`."""
    os.makedirs(upload_folder, exist_ok=True)
    ten_luu = sinh_ten_file_duy_nhat(file_storage.filename)
    file_storage.save(os.path.join(upload_folder, ten_luu))
    return ten_luu


def xoa_file_vat_ly(upload_folder, ten_file):
    if not ten_file:
        return
    duong_dan = os.path.join(upload_folder, ten_file)
    if os.path.isfile(duong_dan):
        os.remove(duong_dan)
