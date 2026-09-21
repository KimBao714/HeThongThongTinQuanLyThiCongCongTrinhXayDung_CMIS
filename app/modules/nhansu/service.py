"""
LỚP BUSINESS (Business Logic Layer)
------------------------------------
Module này quản lý Nhân sự (`nhansu`) VÀ Phân công (`phancong`) gộp chung,
theo hướng nhìn từ 1 nhân sự: "người này đang/đã được phân công làm việc ở
những hạng mục nào".

`phancong` là THỰC THỂ KẾT HỢP (associative entity) sinh ra từ quan hệ
nhiều-nhiều giữa `hangmuc` và `nhansu` — mỗi phân công gắn 1 nhân sự cụ thể
với 1 hạng mục cụ thể trong 1 khoảng thời gian. Khác với `sudungvatlieu`
(khóa chính là khóa kép, không có mã riêng), `phancong` có mã riêng
(`MaPhanCong`) nên 1 cặp (nhân sự, hạng mục) vẫn có thể xuất hiện nhiều lần
với các khoảng thời gian khác nhau (VD: cùng 1 người quay lại làm hạng mục
đó ở 1 đợt sau) — vì vậy không đặt ràng buộc unique theo cặp, mà kiểm soát
bằng ràng buộc CHỒNG LỊCH ở dưới.

Vì Chi phí (`chiphi`) có khóa ngoại THẬT bắt buộc trỏ tới đúng 1 `phancong`
(xem `app/modules/chiphi/service.py`), module này cũng phải tự chặn xóa khi
còn phụ thuộc — CSDL sẽ tự chặn bằng lỗi kỹ thuật (IntegrityError) nếu
không chặn trước ở đây.

Hiển thị: module Hạng mục (`app/modules/hangmuc`) chỉ ĐỌC dữ liệu `phancong`
để hiển thị ngược "hạng mục này đang có ai làm" trên trang danh sách hạng
mục — quyền thêm/sửa/xóa phân công vẫn chỉ nằm ở module Nhân sự này.

Các quy tắc nghiệp vụ xử lý ở tầng này (CSDL không tự đảm bảo được):
1. `TrangThaiLamViec` giới hạn theo danh sách cố định (`TRANG_THAI_LAM_VIEC`)
   để đồng nhất - cột này trong CSDL là văn bản tự do.
2. Không cho xóa nhân sự khi vẫn còn phân công (tương tự quy tắc chặn xóa
   hạng mục còn con) - phải xóa hết phân công của người đó trước.
3. CHỈ ĐƯỢC PHÂN CÔNG VÀO HẠNG MỤC CON (hạng mục có hạng mục cha cụ thể,
   không phải hạng mục gốc/công trình). Hạng mục gốc là cấp quản lý tổng
   thể (ngân sách, thời gian chung của cả công trình), còn công việc thực
   tế luôn diễn ra ở hạng mục con cụ thể - phân công thẳng vào hạng mục gốc
   không có ý nghĩa nghiệp vụ rõ ràng và dễ nhầm với việc quản lý tổng thể.
4. Chỉ nhân sự đang ở trạng thái "Đang làm việc" mới được nhận phân công
   mới (nhân sự "Tạm nghỉ"/"Đã nghỉ việc" không hợp lý để giao việc mới).
5. Ngày bắt đầu phải trước hoặc bằng ngày kết thúc (nếu có khai báo cả 2).
   Số ngày công phải > 0 nếu có nhập. Chi phí thuê không được âm nếu có nhập.
6. KHÔNG TRÙNG LỊCH: 1 nhân sự không thể có 2 phân công chồng lấn khoảng
   thời gian làm việc (không thể "làm 2 nơi cùng lúc"). CSDL không có ràng
   buộc nào kiểm tra việc này (mỗi phân công là 1 dòng độc lập trong bảng,
   không có ràng buộc thời gian giữa các dòng), nên phải tự kiểm ở đây. Chỉ
   so sánh được khi CẢ HAI phân công đều có đủ ngày bắt đầu/kết thúc; phân
   công còn thiếu ngày (chưa xác định lịch cụ thể) thì bỏ qua kiểm tra này.
7. Xóa phân công: chặn nếu đã có dòng chi phí (`chiphi`) tham chiếu tới nó.
8. Thêm ngày công (cộng dồn vào `SoNgayCong` đã có): số ngày thêm phải > 0,
   và nếu phân công đã có đủ ngày bắt đầu/kết thúc thì tổng số công sau khi
   cộng không được vượt quá số lượng tối đa quy đổi được theo ĐÚNG
   `DonViTinh` đang chọn (ngày hoặc tháng) từ khoảng thời gian đó - không so
   trực tiếp số công (đơn vị tháng) với số ngày lịch. `SoNgayCong` là số
   lượng chính thức dùng để tính lại Thành tiền (`thanh_tien_phan_cong`),
   nên Thành tiền sẽ tự động cập nhật đúng sau mỗi lần cộng dồn.
"""

import random
import string

from app.models import NhanSu, PhanCong
from app.modules.nhansu import repository
from app.utils import DON_VI_TINH_NHAN_CONG, parse_date, so_luong_theo_thoi_gian, tinh_chi_phi_nhan_cong


class LoiNghiepVu(Exception):
    pass


# Danh sách cố định - cột TrangThaiLamViec trong CSDL là varchar(50) tự do,
# form giao diện cũng chỉ cho chọn trong 3 giá trị này (xem templates).
TRANG_THAI_LAM_VIEC = ['Đang làm việc', 'Tạm nghỉ', 'Đã nghỉ việc']


def _sinh_ma_phan_cong():
    """Sinh mã gồm 2 chữ cái in hoa và số ngẫu nhiên từ 01 đến 10000000."""
    while True:
        ma = ''.join(random.choices(string.ascii_uppercase, k=2))
        ma += str(random.randint(1, 10_000_000))
        if not repository.exists(ma):
            return ma


# ==================== NHÂN SỰ ====================

def lay_danh_sach(keyword=None, ma_hangmuc=None):
    return repository.get_all(keyword, ma_hangmuc)


def lay_theo_ma(ma):
    return repository.get_by_id_or_404(ma)


def danh_sach_hang_muc_dang_lam(ma_nv):
    """Danh sách mã hạng mục mà nhân sự này đang được phân công - dùng hiển
    thị trực tiếp trên trang danh sách nhân sự (yêu cầu: hiển thị qua mã
    hạng mục của người đó) mà không cần bấm vào xem chi tiết."""
    return [pc.hangmuc_MaHangMuc for pc in repository.danh_sach_phan_cong_theo_nhansu(ma_nv)]


def them_moi(du_lieu_form):
    ma = du_lieu_form.get('MaNV', '').strip()
    ho = du_lieu_form.get('HoNV', '').strip()
    ten = du_lieu_form.get('TenNV', '').strip()
    ngay_sinh_raw = du_lieu_form.get('NgayThangNamSinh', '').strip()
    chuc_vu = du_lieu_form.get('ChucVu', '').strip()
    trang_thai = du_lieu_form.get('TrangThaiLamViec', '').strip()

    if not ma:
        raise LoiNghiepVu('Vui lòng nhập mã nhân viên.')
    if repository.exists(ma):
        raise LoiNghiepVu(f'Mã nhân viên "{ma}" đã tồn tại.')
    if not ten:
        raise LoiNghiepVu('Vui lòng nhập tên nhân viên.')
    if trang_thai and trang_thai not in TRANG_THAI_LAM_VIEC:
        raise LoiNghiepVu(f'Trạng thái làm việc không hợp lệ. Chỉ chấp nhận: {", ".join(TRANG_THAI_LAM_VIEC)}.')

    ngay_sinh = parse_date(ngay_sinh_raw)
    if ngay_sinh_raw and ngay_sinh is None:
        raise LoiNghiepVu('Ngày sinh không hợp lệ.')

    entity = NhanSu(
        MaNV=ma, HoNV=ho, TenNV=ten, NgayThangNamSinh=ngay_sinh,
        ChucVu=chuc_vu, TrangThaiLamViec=trang_thai,
    )
    repository.insert(entity)
    return entity


def cap_nhat(ma, du_lieu_form):
    entity = repository.get_by_id_or_404(ma)

    ten = du_lieu_form.get('TenNV', '').strip()
    trang_thai = du_lieu_form.get('TrangThaiLamViec', '').strip()
    ngay_sinh_raw = du_lieu_form.get('NgayThangNamSinh', '').strip()

    if not ten:
        raise LoiNghiepVu('Vui lòng nhập tên nhân viên.')
    if trang_thai and trang_thai not in TRANG_THAI_LAM_VIEC:
        raise LoiNghiepVu(f'Trạng thái làm việc không hợp lệ. Chỉ chấp nhận: {", ".join(TRANG_THAI_LAM_VIEC)}.')

    ngay_sinh = parse_date(ngay_sinh_raw)
    if ngay_sinh_raw and ngay_sinh is None:
        raise LoiNghiepVu('Ngày sinh không hợp lệ.')

    entity.HoNV = du_lieu_form.get('HoNV', '').strip()
    entity.TenNV = ten
    entity.NgayThangNamSinh = ngay_sinh
    entity.ChucVu = du_lieu_form.get('ChucVu', '').strip()
    entity.TrangThaiLamViec = trang_thai
    repository.update()
    return entity


def xoa(ma):
    entity = repository.get_by_id_or_404(ma)
    if repository.dem_phan_cong(ma) > 0:
        raise LoiNghiepVu(
            'Không thể xóa nhân sự này vì vẫn còn phân công gắn với họ. '
            'Hãy xóa hết phân công của người này trước (xem trang Phân công).'
        )
    repository.delete(entity)


# ==================== PHÂN CÔNG ====================

def danh_sach_hang_muc_con_de_chon():
    return repository.danh_sach_hang_muc_con()


def danh_sach_phan_cong(ma_nv):
    repository.get_by_id_or_404(ma_nv)  # đảm bảo nhân sự tồn tại (404 nếu không)
    return repository.danh_sach_phan_cong_theo_nhansu(ma_nv)


def thanh_tien_phan_cong(phan_cong):
    return tinh_chi_phi_nhan_cong(
        phan_cong.ChiphiThue, phan_cong.SoNgayCong, phan_cong.DonViTinh,
        phan_cong.NgayBatDau, phan_cong.NgayKetThuc,
    )


def lay_phan_cong_theo_ma(ma_phancong):
    return repository.get_phan_cong_or_404(ma_phancong)


def _trung_lich(ma_nv, ngay_bat_dau, ngay_ket_thuc, bo_qua_ma_phancong=None):
    """Kiểm tra nhân sự này đã có phân công khác chồng lấn khoảng thời gian
    làm việc hay chưa. Chỉ kiểm tra được khi cả 2 phân công (mới và đang có
    sẵn) đều có đủ ngày bắt đầu/kết thúc; nếu 1 trong 2 bên thiếu ngày thì bỏ
    qua so sánh (không đủ thông tin để khẳng định có trùng hay không)."""
    if not ngay_bat_dau or not ngay_ket_thuc:
        return False
    for pc in repository.danh_sach_phan_cong_theo_nhansu(ma_nv):
        if bo_qua_ma_phancong and pc.MaPhanCong == bo_qua_ma_phancong:
            continue
        if not pc.NgayBatDau or not pc.NgayKetThuc:
            continue
        if ngay_bat_dau <= pc.NgayKetThuc and pc.NgayBatDau <= ngay_ket_thuc:
            return True
    return False


def _validate_phan_cong(ma_nv, du_lieu_form, ma_phancong_dang_sua=None):
    ma_hangmuc = du_lieu_form.get('MaHangMuc', '').strip()
    dia_diem = du_lieu_form.get('DiaDiemLamViec', '').strip()
    so_ngay_cong_raw = du_lieu_form.get('SoNgayCong', '').strip()
    ngay_bd_raw = du_lieu_form.get('NgayBatDau', '').strip()
    ngay_kt_raw = du_lieu_form.get('NgayKetThuc', '').strip()
    chi_phi_thue_raw = du_lieu_form.get('ChiphiThue', '').strip()
    don_vi_tinh = (du_lieu_form.get('DonViTinh') or 'ngày').strip()

    if not ma_hangmuc or repository.hang_muc_con_theo_ma(ma_hangmuc) is None:
        raise LoiNghiepVu(
            'Chỉ được phân công nhân sự vào hạng mục CON (hạng mục có hạng mục '
            'cha cụ thể) - không phân công trực tiếp vào hạng mục gốc/công trình.'
        )

    ngay_bat_dau = parse_date(ngay_bd_raw)
    if ngay_bd_raw and ngay_bat_dau is None:
        raise LoiNghiepVu('Ngày bắt đầu không hợp lệ.')

    ngay_ket_thuc = parse_date(ngay_kt_raw)
    if ngay_kt_raw and ngay_ket_thuc is None:
        raise LoiNghiepVu('Ngày kết thúc không hợp lệ.')

    if ngay_bat_dau and ngay_ket_thuc and ngay_bat_dau > ngay_ket_thuc:
        raise LoiNghiepVu('Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.')
    if bool(ngay_bat_dau) != bool(ngay_ket_thuc):
        raise LoiNghiepVu('Phải nhập đầy đủ cả ngày bắt đầu và ngày kết thúc.')

    so_ngay_cong = None
    if so_ngay_cong_raw:
        try:
            so_ngay_cong = int(so_ngay_cong_raw)
        except ValueError:
            raise LoiNghiepVu('Số ngày công không hợp lệ.')
        if so_ngay_cong <= 0:
            raise LoiNghiepVu('Số ngày công phải lớn hơn 0.')
    elif ngay_bat_dau and ngay_ket_thuc:
        # Không nhập Số ngày công - tự động tính từ khoảng NgayBatDau-
        # NgayKetThuc theo ĐÚNG DonViTinh đang chọn (ngày hoặc tháng), thay
        # vì để trống rồi chỉ ước tính tạm mỗi lần tính Thành tiền.
        so_don_vi = so_luong_theo_thoi_gian(ngay_bat_dau, ngay_ket_thuc, don_vi_tinh)
        if so_don_vi is not None:
            so_ngay_cong = int(so_don_vi)

    chi_phi_thue = None
    if chi_phi_thue_raw:
        try:
            chi_phi_thue = float(chi_phi_thue_raw)
        except ValueError:
            raise LoiNghiepVu('Chi phí thuê không hợp lệ.')
        if chi_phi_thue < 0:
            raise LoiNghiepVu('Chi phí thuê không được âm.')
    if don_vi_tinh not in DON_VI_TINH_NHAN_CONG:
        raise LoiNghiepVu('Đơn vị tính không hợp lệ. Chỉ chấp nhận ngày hoặc tháng.')

    # Số ngày công không được CAO HƠN số lượng tối đa quy đổi được theo ĐÚNG
    # DonViTinh đang chọn từ khoảng NgayBatDau-NgayKetThuc (thấp hơn vẫn hợp
    # lệ - VD nghỉ giữa chừng - chỉ chặn khi vượt quá thực tế lịch làm việc).
    if so_ngay_cong is not None and ngay_bat_dau and ngay_ket_thuc:
        so_don_vi_toi_da = so_luong_theo_thoi_gian(ngay_bat_dau, ngay_ket_thuc, don_vi_tinh)
        if so_don_vi_toi_da is not None and so_ngay_cong > so_don_vi_toi_da:
            raise LoiNghiepVu(
                f'Số ngày công ({so_ngay_cong} {don_vi_tinh}) vượt quá số lượng tối đa '
                f'quy đổi được từ khoảng thời gian phân công ({so_don_vi_toi_da} {don_vi_tinh}, '
                f'từ {ngay_bat_dau} đến {ngay_ket_thuc}).'
            )

    if _trung_lich(ma_nv, ngay_bat_dau, ngay_ket_thuc, bo_qua_ma_phancong=ma_phancong_dang_sua):
        raise LoiNghiepVu(
            'Nhân sự này đã có 1 phân công khác trùng khoảng thời gian làm việc - '
            'không thể phân công làm việc ở 2 nơi cùng lúc.'
        )

    return {
        'DiaDiemLamViec': dia_diem,
        'SoNgayCong': so_ngay_cong,
        'NgayBatDau': ngay_bat_dau,
        'NgayKetThuc': ngay_ket_thuc,
        'hangmuc_MaHangMuc': ma_hangmuc,
        'ChiphiThue': chi_phi_thue,
        'DonViTinh': don_vi_tinh,
    }


def them_phan_cong(ma_nv, du_lieu_form):
    nhan_vien = repository.get_by_id_or_404(ma_nv)
    if nhan_vien.TrangThaiLamViec != 'Đang làm việc':
        raise LoiNghiepVu(
            f'Không thể phân công vì nhân sự đang ở trạng thái '
            f'"{nhan_vien.TrangThaiLamViec or "chưa xác định"}" - chỉ nhân sự '
            f'"Đang làm việc" mới được nhận phân công mới.'
        )

    du_lieu = _validate_phan_cong(ma_nv, du_lieu_form)
    entity = PhanCong(MaPhanCong=_sinh_ma_phan_cong(), nhansu_MaNV=ma_nv, **du_lieu)
    repository.insert_phan_cong(entity)
    return entity


def sua_phan_cong(ma_phancong, du_lieu_form):
    entity = repository.get_phan_cong_or_404(ma_phancong)
    du_lieu = _validate_phan_cong(entity.nhansu_MaNV, du_lieu_form, ma_phancong_dang_sua=ma_phancong)
    for ten_cot, gia_tri in du_lieu.items():
        setattr(entity, ten_cot, gia_tri)
    repository.update_phan_cong()
    return entity


def xoa_phan_cong(ma_phancong):
    entity = repository.get_phan_cong_or_404(ma_phancong)
    if repository.dem_chi_phi_theo_phancong(ma_phancong) > 0:
        raise LoiNghiepVu(
            'Không thể xóa phân công này vì đã có chi phí ghi nhận gắn với nó. '
            'Hãy xóa các chi phí liên quan trước (xem module Chi phí).'
        )
    repository.delete_phan_cong(entity)


def them_ngay_cong(ma_phancong, so_ngay_them_raw):
    """Cộng dồn thêm N công vào 1 phân công đã có (thay vì bắt người dùng
    phải tự tính lại tổng rồi ghi đè qua form Sửa - dễ gõ nhầm và mất dấu
    vết đã chấm công bao nhiêu đợt). Quy tắc nghiệp vụ áp dụng vì CSDL không
    có bảng chấm công riêng theo từng ngày, chỉ có 1 cột tổng `SoNgayCong`:
    1. Số công cần thêm phải là số nguyên dương.
    2. Nếu phân công đã khai báo đủ NgayBatDau và NgayKetThuc, tổng số công
       sau khi cộng KHÔNG được vượt quá số lượng TỐI ĐA quy đổi theo ĐÚNG
       `DonViTinh` đang chọn của phân công (VD: đơn vị "tháng" thì so sánh
       với số THÁNG tối đa quy đổi được từ khoảng ngày đó - KHÔNG so trực
       tiếp với số NGÀY lịch, vì 2 đơn vị khác nhau không thể so thẳng).
    3. `SoNgayCong` là số lượng CHÍNH THỨC dùng để tính lại Thành tiền (xem
       `thanh_tien_phan_cong`) - nên sau khi cộng dồn, Thành tiền hiển thị ở
       trang Phân công sẽ tự động phản ánh đúng số công mới này."""
    entity = repository.get_phan_cong_or_404(ma_phancong)

    try:
        so_ngay_them = int((so_ngay_them_raw or '').strip())
    except (TypeError, ValueError):
        raise LoiNghiepVu('Số công cần thêm không hợp lệ.')
    if so_ngay_them <= 0:
        raise LoiNghiepVu('Số công cần thêm phải lớn hơn 0.')

    tong_moi = (entity.SoNgayCong or 0) + so_ngay_them

    if entity.NgayBatDau and entity.NgayKetThuc:
        don_vi = entity.DonViTinh or 'ngày'
        so_don_vi_toi_da = so_luong_theo_thoi_gian(entity.NgayBatDau, entity.NgayKetThuc, don_vi)
        if so_don_vi_toi_da is not None and tong_moi > so_don_vi_toi_da:
            raise LoiNghiepVu(
                f'Tổng số công sau khi cộng ({tong_moi} {don_vi}) vượt quá số lượng tối đa '
                f'quy đổi được từ khoảng thời gian phân công ({so_don_vi_toi_da} {don_vi}, từ '
                f'{entity.NgayBatDau} đến {entity.NgayKetThuc}).'
            )

    entity.SoNgayCong = tong_moi
    repository.update_phan_cong()
    return entity
