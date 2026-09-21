"""
LỚP DATA (Data Access Layer)
----------------------------
Truy vấn CSDL thuần túy cho Chi phí. Module này cần đọc thêm dữ liệu tham
chiếu từ 3 bảng khác (`hangmuc`, `phancong`, `sudungvatlieu`) vì mỗi dòng
chi phí bắt buộc phải gắn với đúng 1 bản ghi có sẵn ở mỗi bảng đó (xem
service.py để biết lý do và các ràng buộc nghiệp vụ liên quan). Không chứa
logic nghiệp vụ (validate nhất quán hạng mục, giới hạn loại chi phí, so
sánh với ngân sách... đều nằm ở service.py).
"""

from sqlalchemy import func

from app.extensions import db
from app.models import ChiPhi, HangMuc, PhanCong, SuDungVatLieu


# ---------------------- Chi phí ----------------------

def get_all(keyword=None, ma_hangmuc=None, loai_chi_phi=None):
    query = ChiPhi.query
    if keyword:
        query = query.filter(
            (ChiPhi.MoTa.ilike(f'%{keyword}%')) |
            (ChiPhi.MaCP.ilike(f'%{keyword}%'))
        )
    if ma_hangmuc:
        query = query.filter(ChiPhi.hangmuc_MaHangMuc == ma_hangmuc)
    if loai_chi_phi:
        query = query.filter(ChiPhi.LoaiChiPhi == loai_chi_phi)
    return query.order_by(ChiPhi.NgayChi.desc(), ChiPhi.MaCP).all()


def get_by_id_or_404(ma):
    return ChiPhi.query.get_or_404(ma)


def exists(ma):
    return ChiPhi.query.get(ma) is not None


def insert(entity: ChiPhi):
    db.session.add(entity)
    db.session.commit()


def update():
    db.session.commit()


def delete(entity: ChiPhi):
    db.session.delete(entity)
    db.session.commit()


def tong_chi_phi_theo_hangmuc(ma_hangmuc):
    """Tổng SoTienChi của toàn bộ chi phí đã ghi nhận cho 1 hạng mục (dùng
    để so sánh với ngân sách đang có - xem service.tinh_ngan_sach)."""
    tong = db.session.query(func.sum(ChiPhi.SoTienChi)).filter(
        ChiPhi.hangmuc_MaHangMuc == ma_hangmuc
    ).scalar()
    return tong or 0


# ---------------------- Dữ liệu tham chiếu: Hạng mục ----------------------

def danh_sach_hang_muc():
    return HangMuc.query.order_by(HangMuc.MaHangMuc).all()


def hang_muc_theo_ma(ma_hangmuc):
    return HangMuc.query.get(ma_hangmuc)


# ---------------------- Dữ liệu tham chiếu: Phân công ----------------------
# Bảng `phancong` không có module quản lý riêng ở thời điểm hiện tại - module
# Chi phí chỉ ĐỌC dữ liệu có sẵn để chọn, không có quyền thêm/sửa/xóa phân
# công (nằm ngoài phạm vi module này).

def danh_sach_phan_cong():
    return PhanCong.query.order_by(PhanCong.MaPhanCong).all()


def phan_cong_theo_ma(ma_phancong):
    return PhanCong.query.get(ma_phancong)


# ---------------------- Dữ liệu tham chiếu: Sử dụng vật liệu ----------------------
# Tương tự `phancong`, bảng `sudungvatlieu` chỉ được ĐỌC ở đây.

def danh_sach_su_dung_vat_lieu():
    return SuDungVatLieu.query.order_by(
        SuDungVatLieu.hangmuc_MaHangMuc, SuDungVatLieu.vatlieu_MaVL
    ).all()


def su_dung_vat_lieu_theo_khoa(ma_vl, ma_hangmuc):
    """Khóa chính của `sudungvatlieu` là khóa kép (vatlieu_MaVL, hangmuc_MaHangMuc)."""
    return SuDungVatLieu.query.get((ma_vl, ma_hangmuc))
