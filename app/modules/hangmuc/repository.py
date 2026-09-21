"""
LỚP DATA (Data Access Layer)
----------------------------
Truy vấn CSDL thuần túy cho Hạng mục. Không chứa logic nghiệp vụ (validate
vòng lặp cha/con, quy ước hạng mục gốc tự trỏ vào chính nó, ... đều nằm ở
service.py).
"""

from app.extensions import db
from app.models import HangMuc, PhanCong, SuDungVatLieu, BanVe, ChiPhi


def get_all(keyword=None):
    query = HangMuc.query
    if keyword:
        query = query.filter(
            (HangMuc.TenHangMuc.ilike(f'%{keyword}%')) |
            (HangMuc.MaHangMuc.ilike(f'%{keyword}%'))
        )
    return query.order_by(HangMuc.MaHangMuc).all()


def get_by_id_or_404(ma):
    return HangMuc.query.get_or_404(ma)


def exists(ma):
    return HangMuc.query.get(ma) is not None


def count_hang_muc_con(ma):
    """Đếm số hạng mục con TRỰC TIẾP của 1 hạng mục (dùng để chặn xóa khi
    còn hạng mục con phụ thuộc)."""
    return HangMuc.query.filter(
        HangMuc.hangmuc_MaHangMuc == ma,
        HangMuc.MaHangMuc != ma  # loại trừ chính hạng mục gốc tự trỏ vào mình
    ).count()


# ---------------------- Kiểm tra toàn vẹn tham chiếu (dùng khi xóa) ----------------------
# hangmuc còn được 4 bảng khác tham chiếu tới qua khóa ngoại: banve, phancong,
# sudungvatlieu, chiphi. Xóa 1 hạng mục đang bị tham chiếu sẽ vi phạm ràng
# buộc khóa ngoại ở CSDL (mặc định ON DELETE RESTRICT) và văng lỗi
# IntegrityError xấu xí ra tận giao diện - nên phải tự kiểm tra trước và
# báo lỗi nghiệp vụ rõ ràng ở service.py.

def co_banve_su_dung(ma):
    return BanVe.query.filter(BanVe.hangmuc_hangmuc_MaHangMuc == ma).count() > 0


def co_phan_cong_su_dung(ma):
    return PhanCong.query.filter(PhanCong.hangmuc_MaHangMuc == ma).count() > 0


def co_vat_lieu_su_dung(ma):
    return SuDungVatLieu.query.filter(SuDungVatLieu.hangmuc_MaHangMuc == ma).count() > 0


def co_chi_phi_gan_truc_tiep(ma):
    return ChiPhi.query.filter(ChiPhi.hangmuc_MaHangMuc == ma).count() > 0


def insert(entity: HangMuc):
    db.session.add(entity)
    db.session.commit()


def update():
    db.session.commit()


def delete(entity: HangMuc):
    """LƯU Ý QUAN TRỌNG: KHÔNG dùng `db.session.delete(entity)` (cách ORM
    thông thường) ở đây. Cột `hangmuc_MaHangMuc` tự tham chiếu vào chính
    bảng `hangmuc`, và với HẠNG MỤC GỐC, cột này trỏ vào chính MaHangMuc
    của nó (tự tham chiếu 1-dòng). Khi đó, cơ chế "topological sort" của
    SQLAlchemy ORM (dùng để tính thứ tự xóa an toàn cho các quan hệ FK) coi
    dòng này vừa là "cha" vừa là "con" của chính nó và không thể xác định
    thứ tự xóa - ném `sqlalchemy.exc.CircularDependencyError` (KHÔNG phải
    `LoiNghiepVu`, nên rơi thẳng ra lỗi 500 thô nếu dùng cách xóa thông
    thường). Toàn vẹn tham chiếu đã được kiểm tra đầy đủ ở service.py
    (không còn hạng mục con/bản vẽ/phân công/vật liệu/chi phí phụ thuộc)
    trước khi gọi tới đây, nên có thể an toàn dùng DELETE trực tiếp theo
    khóa chính (không đi qua cơ chế cascade/dependency-sort của ORM)."""
    HangMuc.query.filter(HangMuc.MaHangMuc == entity.MaHangMuc).delete()
    db.session.commit()


# ---------------------- Phân công (dữ liệu tham chiếu, chỉ đọc) ----------------------
# Bảng `phancong` không thuộc phạm vi module này - việc thêm/sửa/xóa phân
# công thuộc module Nhân sự (xem app/modules/nhansu). Module Hạng mục chỉ
# ĐỌC để hiển thị ngược "hạng mục này đang có ai làm".

def danh_sach_phan_cong_tat_ca():
    return PhanCong.query.order_by(PhanCong.hangmuc_MaHangMuc, PhanCong.MaPhanCong).all()


# ---------------------- Sử dụng vật liệu (dữ liệu tham chiếu, chỉ đọc) ----------------------
# Bảng `sudungvatlieu` không thuộc phạm vi module này - việc thêm/sửa/xóa
# lượt sử dụng vật liệu thuộc module Vật liệu (xem app/modules/vatlieu).
# Module Hạng mục chỉ ĐỌC để hiển thị ngược "hạng mục này đang dùng vật
# liệu gì, số lượng bao nhiêu" - tương tự danh_sach_phan_cong_tat_ca() ở trên.

def danh_sach_su_dung_vat_lieu_tat_ca():
    return SuDungVatLieu.query.order_by(
        SuDungVatLieu.hangmuc_MaHangMuc, SuDungVatLieu.vatlieu_MaVL
    ).all()
