"""
LỚP DATA (Data Access Layer)
----------------------------
Truy vấn tổng hợp (COUNT/SUM/GROUP BY) phục vụ trang Dashboard tổng quan.
Module này không có bảng CSDL riêng - chỉ ĐỌC dữ liệu từ các bảng đã có của
những module khác.

QUY ƯỚC QUAN TRỌNG: mọi phép tính NGÂN SÁCH/CHI PHÍ (đã chi thực tế, đã sử
dụng ước tính từ vật liệu+nhân công, hạng mục nào vượt ngân sách...) và mọi
phép tính VẬT LIỆU VƯỢT DỰ KIẾN đều KHÔNG được tính lại ở đây - Dashboard
chỉ GỌI LẠI đúng hàm đã có sẵn ở module Chi phí (`chiphi.service`) và module
Vật liệu (`vatlieu.service`), để tránh 2 nơi tính cùng 1 logic nghiệp vụ
theo 2 cách khác nhau (rủi ro lệch số liệu giữa Dashboard và trang chi tiết
của module gốc). Module này chỉ tự truy vấn những số liệu mà KHÔNG module
nào khác đã tổng hợp sẵn (đếm số dòng đơn thuần, phân bố theo trạng thái,
hạng mục trễ tiến độ...). Mọi truy vấn tự viết ở đây đều dùng 1 câu SQL
tổng hợp duy nhất (GROUP BY/JOIN) thay vì lặp query cho từng dòng, để tránh
N+1 query khi số lượng hạng mục/nhân sự/bản vẽ... tăng lên.
"""

from datetime import date

from sqlalchemy import func

from app.extensions import db
from app.models import HangMuc, VatLieu, NhanSu, PhanCong, BanVe, PhienBan, TrangThaiPhienBan


# ---------------------- Hạng mục ----------------------

def dem_hang_muc():
    return HangMuc.query.count()


def danh_sach_hang_muc():
    return HangMuc.query.order_by(HangMuc.MaHangMuc).all()


def dem_hang_muc_goc():
    return HangMuc.query.filter(HangMuc.hangmuc_MaHangMuc == HangMuc.MaHangMuc).count()


def danh_sach_hang_muc_goc():
    """Chỉ những hạng mục GỐC (tự trỏ vào chính mình - tương đương 1 "công
    trình") - dùng làm trục X cho biểu đồ ngân sách theo hạng mục ở
    Dashboard. Chỉ vẽ biểu đồ ở cấp GỐC (không vẽ tất cả hạng mục con) vì
    số liệu ngân sách/đã dùng của module Chi phí đã CỘNG DỒN luôn cả hạng
    mục con/cháu vào hạng mục cha (xem chiphi.service._ma_hang_muc_lien_quan)
    - nếu vẽ luôn cả hạng mục con thì giá trị của cha và con sẽ bị trùng lặp
    (đè lên nhau) trên cùng 1 biểu đồ, gây hiểu nhầm."""
    return HangMuc.query.filter(HangMuc.hangmuc_MaHangMuc == HangMuc.MaHangMuc) \
        .order_by(HangMuc.MaHangMuc).all()


def hang_muc_tre_tien_do():
    """Hạng mục có `ThoiGianHoanThanhDuKien` đã qua ngày hôm nay - dùng
    cảnh báo TRỄ TIẾN ĐỘ ở Dashboard. Đây là logic MỚI, chưa module nào
    trong hệ thống tính (xem giải thích đầy đủ + giới hạn của cảnh báo này
    ở dashboard/service.py, hàm `_hang_muc_tre_tien_do()`)."""
    return HangMuc.query.filter(
        HangMuc.ThoiGianHoanThanhDuKien.isnot(None),
        HangMuc.ThoiGianHoanThanhDuKien < date.today()
    ).order_by(HangMuc.ThoiGianHoanThanhDuKien.asc()).all()


# ---------------------- Vật liệu ----------------------

def dem_vat_lieu():
    return VatLieu.query.count()


# ---------------------- Nhân sự ----------------------

def dem_nhan_su():
    return NhanSu.query.count()


def nhan_su_theo_trang_thai():
    """[(TrangThaiLamViec, so_luong), ...] - TrangThaiLamViec có thể là
    None/rỗng (cột tự do, không bắt buộc nhập khi thêm nhân sự)."""
    return db.session.query(
        NhanSu.TrangThaiLamViec, func.count(NhanSu.MaNV)
    ).group_by(NhanSu.TrangThaiLamViec).all()


# ---------------------- Phân công ----------------------

def dem_phan_cong():
    return PhanCong.query.count()


# ---------------------- Bản vẽ / Phiên bản ----------------------

def dem_ban_ve():
    return BanVe.query.count()


def danh_sach_ban_ve():
    """Toàn bộ bản vẽ - dùng ở dashboard/service.py để tính "bản vẽ chưa có
    phiên bản chính thức (Đã duyệt)" bằng cách gọi lại
    banve.service.phien_ban_hien_hanh() cho từng bản vẽ (đúng theo cách
    banve/routes.py đã làm ở trang danh sách bản vẽ - xem giải thích ở
    dashboard/service.py)."""
    return BanVe.query.all()


def dem_phien_ban():
    return PhienBan.query.count()


def phien_ban_theo_trang_thai():
    """[(MaTrangThai, TenTrangThai, so_luong), ...] - LEFT JOIN từ phía
    `trangthaiphienban` (bảng tra cứu luôn có sẵn 3 dòng cố định do
    banve_repository seed lúc khởi động app) để cả trạng thái đang có 0
    phiên bản (VD: chưa từ chối cái nào) vẫn xuất hiện trong biểu đồ."""
    return db.session.query(
        TrangThaiPhienBan.MaTrangThai, TrangThaiPhienBan.TenTrangThai, func.count(PhienBan.MaPB)
    ).outerjoin(PhienBan, PhienBan.trangthaiphienban_MaTrangThai == TrangThaiPhienBan.MaTrangThai) \
     .group_by(TrangThaiPhienBan.MaTrangThai, TrangThaiPhienBan.TenTrangThai).all()


def phien_ban_dang_cho_duyet(ma_trang_thai_cho_duyet, gioi_han=5):
    """Top N phiên bản đang chờ duyệt, tạo lâu nhất trước (chờ lâu nhất) -
    dùng cảnh báo hồ sơ bị treo trên dashboard."""
    return PhienBan.query.filter(
        PhienBan.trangthaiphienban_MaTrangThai == ma_trang_thai_cho_duyet
    ).order_by(PhienBan.NgayTao.asc()).limit(gioi_han).all()
