import uuid
from datetime import datetime
from decimal import Decimal


DON_VI_TINH_NHAN_CONG = ('ngày', 'tháng')


def parse_date(value):
    """Chuyển chuỗi 'YYYY-MM-DD' từ input HTML type=date thành đối tượng date.
    Trả về None nếu rỗng hoặc không hợp lệ."""
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def so_luong_theo_thoi_gian(ngay_bat_dau, ngay_ket_thuc, don_vi_tinh='ngày'):
    """Tính số đơn vị tính tiền từ khoảng phân công, gồm cả ngày đầu/cuối."""
    if not ngay_bat_dau or not ngay_ket_thuc:
        return None
    so_ngay = (ngay_ket_thuc - ngay_bat_dau).days + 1
    if don_vi_tinh == 'tháng':
        return Decimal((so_ngay + 29) // 30)
    return Decimal(so_ngay)


def tinh_chi_phi_nhan_cong(chi_phi_thue, so_luong=None, don_vi_tinh=None,
                           ngay_bat_dau=None, ngay_ket_thuc=None):
    """Tính thành tiền = số lượng công (đã tính theo ĐÚNG đơn vị đang chọn -
    ngày hoặc tháng) x đơn giá thuê/đơn vị.

    ƯU TIÊN dùng `SoNgayCong` đã lưu (số lượng công NGƯỜI DÙNG NHẬP/CỘNG DỒN,
    đã tính sẵn theo đơn vị `don_vi_tinh`) làm số lượng chính thức - đây là
    con số được cập nhật mỗi khi dùng chức năng "+ Công" (`them_ngay_cong`),
    nên THÀNH TIỀN LUÔN ĐƯỢC TÍNH LẠI đúng theo số công mới nhất.

    Chỉ khi phân công KHÔNG có `SoNgayCong` (chưa nhập/dữ liệu cũ) mới ước
    tính lùi từ khoảng ngày bắt đầu/kết thúc (`so_luong_theo_thoi_gian`) như
    một giá trị tạm - đây CHỈ là phương án dự phòng, không phải nguồn chính."""
    if so_luong is not None:
        he_so = Decimal(str(so_luong))
    else:
        he_so = so_luong_theo_thoi_gian(ngay_bat_dau, ngay_ket_thuc, don_vi_tinh or 'ngày')
        if he_so is None:
            he_so = Decimal('0')
    don_gia = chi_phi_thue or Decimal('0')
    return don_gia * he_so


def allowed_file(filename, allowed_extensions):
    """Kiểm tra phần mở rộng file có nằm trong danh sách cho phép không
    (dùng khi upload file bản vẽ - xem config.ALLOWED_EXTENSIONS)."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed_extensions


def sinh_ten_file_duy_nhat(ten_file_goc):
    """Sinh tên file lưu trên đĩa không trùng nhau, giữ lại phần mở rộng gốc.
    Không dùng lại tên file người dùng upload để tránh: (1) trùng tên giữa
    nhiều lần tải lên, (2) ký tự lạ/tiếng Việt có dấu trong tên file gây lỗi
    hệ điều hành, (3) lộ tên file gốc ra ngoài. Cột `HinhBV` trong CSDL chỉ
    dài 45 ký tự nên tên sinh ra phải đủ ngắn."""
    ext = ten_file_goc.rsplit('.', 1)[1].lower() if '.' in ten_file_goc else ''
    ten_moi = uuid.uuid4().hex[:16]
    return f'{ten_moi}.{ext}' if ext else ten_moi
