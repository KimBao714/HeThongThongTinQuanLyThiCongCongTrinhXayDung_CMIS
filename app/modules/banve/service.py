"""
LỚP BUSINESS (Business Logic Layer)
------------------------------------
Bản vẽ (`banve`) thuộc về 1 hạng mục (`hangmuc`), và mỗi bản vẽ có thể có
nhiều PHIÊN BẢN (`phienban`) - mỗi lần tải file bản vẽ mới lên là 1 phiên
bản, gắn với 1 trạng thái (`trangthaiphienban`). CSDL không có ràng buộc
nào tự đảm bảo được các quy tắc dưới đây nên toàn bộ được xử lý ở tầng này:

0. TẠO BẢN VẼ BẮT BUỘC PHẢI CÓ FILE NGAY: khi tạo 1 bản vẽ mới, phải tải
   lên file luôn (tự động sinh phiên bản v1 kèm file đó) - không cho tạo 1
   bản vẽ "rỗng" (chỉ có thông tin, chưa có file nào). Đây là LOGIC NGHIỆP
   VỤ BỔ SUNG (không phải ràng buộc CSDL): `banve` (thông tin mô tả) và
   `phienban` (file thực tế) là 2 bảng tách rời, CSDL cho phép tạo 1 dòng
   `banve` mà không có dòng `phienban` nào đi kèm - nhưng về nghiệp vụ, 1
   "bản vẽ" không có file đính kèm thì không có giá trị sử dụng thực tế
   (không ai xem/tải xuống được gì). Việc tạo bản vẽ + phiên bản đầu tiên
   được gộp vào CÙNG 1 giao dịch CSDL (xem
   `repository.insert_banve_va_phien_ban`) - nếu bước lưu file/validate
   thất bại thì bản vẽ cũng KHÔNG được tạo, tránh để lại bản vẽ mồ côi
   không có phiên bản nào. Việc tải lên các phiên bản TIẾP THEO (v2, v3,
   ...) vẫn theo đúng quy trình đã có ở trang "Phiên bản" (mục 8 bên dưới).
1. Số phiên bản (`SoPhienBan`) và ngày tạo (`NgayTao`) do HỆ THỐNG tự sinh
   khi tải lên, không cho người dùng tự nhập, để tránh trùng/nhảy số và
   đảm bảo đúng thời điểm thực tế.
2. Phiên bản mới tải lên luôn ở trạng thái "Chờ duyệt" - không cho chọn
   trạng thái khác ngay khi tạo (phải qua bước duyệt/từ chối riêng, chỉ
   người có vai trò toàn quyền mới thực hiện được - chặn ở tầng route bằng
   `yeu_cau_toan_quyen`).
3. Chỉ phiên bản đang "Chờ duyệt" mới được duyệt hoặc từ chối. Phiên bản đã
   ở trạng thái cuối (Đã duyệt / Từ chối) không được duyệt/từ chối lại -
   muốn thay đổi thì phải tải lên phiên bản mới, để lịch sử phê duyệt không
   bao giờ bị viết đè.
4. `NgayDuyet` chỉ được gán khi duyệt (không gán khi từ chối).
5. Không cho xóa phiên bản đã "Đã duyệt" (giữ toàn vẹn hồ sơ đã phê duyệt
   chính thức) - chỉ được xóa phiên bản "Chờ duyệt" hoặc "Từ chối". Khi xóa
   thì xóa luôn file vật lý trên đĩa để tránh rác file mồ côi.
6. Xóa bản vẽ từ danh sách sẽ xóa luôn toàn bộ phiên bản và file vật lý đi
    kèm trong cùng một giao dịch.
7. "Phiên bản hiện hành" của 1 bản vẽ = phiên bản "Đã duyệt" có số phiên
   bản lớn nhất (không nhất thiết là phiên bản mới tải lên gần nhất - vì
   phiên bản mới nhất có thể đang "Chờ duyệt" hoặc đã bị "Từ chối").
8. Tại 1 thời điểm, mỗi bản vẽ chỉ được có TỐI ĐA 1 phiên bản đang "Chờ
   duyệt" - phải duyệt/từ chối phiên bản đang chờ trước khi tải lên phiên
   bản kế tiếp, tránh nhiều phiên bản cùng chờ duyệt chồng chéo. Áp dụng
   luôn cho phiên bản v1 vừa tạo (nghĩa là: vừa tạo xong bản vẽ, phải
   duyệt/từ chối v1 trước khi tải lên v2).
9. Số phiên bản kế tiếp = MAX(số hiện có) + 1, KHÔNG dùng COUNT - vì nếu 1
   phiên bản "Chờ duyệt"/"Từ chối" bị xóa (quy tắc 5), COUNT sẽ giảm và số
   phiên bản có thể bị cấp trùng cho 2 lần tải lên khác nhau.
"""

import uuid
from datetime import date

from app.models import BanVe, PhienBan
from app.modules.banve import repository
from app.utils import allowed_file


class LoiNghiepVu(Exception):
    pass


LOAI_BAN_VE = ('Kiến trúc', 'Kết cấu', 'Cơ điện (MEP)', 'Chi tiết thi công')


def _sinh_ma_phien_ban():
    """Sinh MaPB độc lập, ngắn (cột varchar(20)) và không đụng hàng. Không
    ghép trực tiếp từ MaBV vì MaBV có thể dài tới 20 ký tự (đúng bằng giới
    hạn cột) - ghép thêm hậu tố số phiên bản sẽ tràn cột."""
    return f'PB{uuid.uuid4().hex[:12].upper()}'


def _validate_file(file_storage, allowed_extensions):
    if not file_storage or not file_storage.filename:
        raise LoiNghiepVu('Vui lòng chọn file bản vẽ để tải lên.')
    if not allowed_file(file_storage.filename, allowed_extensions):
        raise LoiNghiepVu(
            f'Định dạng file không hợp lệ. Chỉ chấp nhận: {", ".join(sorted(allowed_extensions))}.'
        )


# ---------------------- Bản vẽ ----------------------

def lay_danh_sach(keyword=None, ma_hangmuc=None):
    return repository.get_all(keyword, ma_hangmuc)


def lay_theo_ma(ma):
    return repository.get_by_id_or_404(ma)


def danh_sach_hang_muc_de_chon():
    return repository.danh_sach_hang_muc()


def them_moi(du_lieu_form, file_storage, upload_folder, allowed_extensions):
    ma = du_lieu_form.get('MaBV', '').strip()
    ten = du_lieu_form.get('TenBV', '').strip()
    ma_hangmuc = du_lieu_form.get('MaHangMuc', '').strip()
    loai_ban_ve = du_lieu_form.get('LoaiBV', '').strip() or 'Kiến trúc'
    ho_nguoi_tao = du_lieu_form.get('HoNguoiTao', '').strip()
    ten_nguoi_tao = du_lieu_form.get('TenNguoiTao', '').strip()

    if repository.exists(ma):
        raise LoiNghiepVu(f'Mã bản vẽ "{ma}" đã tồn tại.')
    if not ten:
        raise LoiNghiepVu('Tên bản vẽ không được để trống.')
    if not ma_hangmuc or not repository.hang_muc_ton_tai(ma_hangmuc):
        raise LoiNghiepVu('Hạng mục được chọn không tồn tại.')
    if loai_ban_ve not in LOAI_BAN_VE:
        raise LoiNghiepVu('Loại bản vẽ không hợp lệ.')
    if not ho_nguoi_tao or not ten_nguoi_tao:
        raise LoiNghiepVu('Vui lòng nhập họ tên người tạo phiên bản đầu tiên (v1).')
    # Quy tắc 0: tạo bản vẽ bắt buộc phải có file đi kèm ngay (tự sinh
    # phiên bản v1) - xem giải thích ở docstring đầu file.
    _validate_file(file_storage, allowed_extensions)

    ten_file_da_luu = repository.luu_file_vat_ly(file_storage, upload_folder)

    banve_entity = BanVe(
        MaBV=ma,
        LoaiBV=loai_ban_ve,
        TenBV=ten,
        hangmuc_hangmuc_MaHangMuc=ma_hangmuc,
    )
    phienban_entity = PhienBan(
        MaPB=_sinh_ma_phien_ban(),
        SoPhienBan='1',
        NgayTao=date.today(),
        HinhBV=ten_file_da_luu,
        HoNguoiTao=ho_nguoi_tao,
        TenNguoiTao=ten_nguoi_tao,
        NgayDuyet=None,
        banve_MaBV=ma,
        trangthaiphienban_MaTrangThai=repository.CHO_DUYET,
    )
    # Chèn cả 2 dòng trong CÙNG 1 transaction (xem quy tắc 0) - nếu có lỗi
    # ở đây, cả bản vẽ lẫn phiên bản đều không được lưu, tránh để lại bản
    # vẽ "rỗng" không có phiên bản nào.
    repository.insert_banve_va_phien_ban(banve_entity, phienban_entity)
    return banve_entity


def cap_nhat(ma, du_lieu_form):
    entity = repository.get_by_id_or_404(ma)
    ten = du_lieu_form.get('TenBV', '').strip()
    ma_hangmuc = du_lieu_form.get('MaHangMuc', '').strip()
    loai_ban_ve = du_lieu_form.get('LoaiBV', '').strip() or 'Kiến trúc'

    if not ten:
        raise LoiNghiepVu('Tên bản vẽ không được để trống.')
    if not ma_hangmuc or not repository.hang_muc_ton_tai(ma_hangmuc):
        raise LoiNghiepVu('Hạng mục được chọn không tồn tại.')
    if loai_ban_ve not in LOAI_BAN_VE:
        raise LoiNghiepVu('Loại bản vẽ không hợp lệ.')

    entity.LoaiBV = loai_ban_ve
    entity.TenBV = ten
    entity.hangmuc_hangmuc_MaHangMuc = ma_hangmuc
    repository.update()
    return entity


def xoa(ma, upload_folder):
    entity = repository.get_by_id_or_404(ma)
    danh_sach_phien_ban = repository.lay_phien_ban_theo_banve(ma)
    for phien_ban in danh_sach_phien_ban:
        repository.xoa_file_vat_ly(upload_folder, phien_ban.HinhBV)
    repository.delete_banve_va_phien_ban(entity, danh_sach_phien_ban)


# ---------------------- Phiên bản ----------------------

def _so_phien_ban_int(pb):
    try:
        return int(pb.SoPhienBan)
    except (TypeError, ValueError):
        return 0


def lay_phien_ban(ma_bv):
    """Danh sách phiên bản của 1 bản vẽ, sắp xếp mới nhất trước."""
    ds = repository.lay_phien_ban_theo_banve(ma_bv)
    return sorted(ds, key=_so_phien_ban_int, reverse=True)


def lay_phien_ban_theo_ma(ma_pb):
    return repository.get_phien_ban_or_404(ma_pb)


def phien_ban_hien_hanh(ma_bv):
    """Phiên bản 'Đã duyệt' có số phiên bản lớn nhất - đại diện cho hồ sơ
    bản vẽ chính thức đang áp dụng. Trả về None nếu chưa có phiên bản nào
    được duyệt (kể cả khi đã có phiên bản đang chờ duyệt/bị từ chối)."""
    da_duyet = [pb for pb in repository.lay_phien_ban_theo_banve(ma_bv)
                if pb.trangthaiphienban_MaTrangThai == repository.DA_DUYET]
    if not da_duyet:
        return None
    return max(da_duyet, key=_so_phien_ban_int)


def _so_phien_ban_ke_tiep(ma_bv):
    """Số phiên bản kế tiếp = MAX(số phiên bản hiện có) + 1 - KHÔNG dùng
    COUNT vì nếu 1 phiên bản "Chờ duyệt"/"Từ chối" bị xóa, COUNT sẽ giảm và
    số bị tái sử dụng, gây nhầm lẫn khi tra cứu lịch sử (2 phiên bản khác
    nhau cùng mang số "v2" ở 2 thời điểm khác nhau)."""
    ds = repository.lay_phien_ban_theo_banve(ma_bv)
    if not ds:
        return 1
    return max(_so_phien_ban_int(pb) for pb in ds) + 1


def them_phien_ban(ma_bv, du_lieu_form, file_storage, upload_folder, allowed_extensions):
    repository.get_by_id_or_404(ma_bv)  # đảm bảo bản vẽ tồn tại (404 nếu không)

    ho_nguoi_tao = du_lieu_form.get('HoNguoiTao', '').strip()
    ten_nguoi_tao = du_lieu_form.get('TenNguoiTao', '').strip()

    if not ho_nguoi_tao or not ten_nguoi_tao:
        raise LoiNghiepVu('Vui lòng nhập họ tên người tạo phiên bản.')

    # Chỉ cho phép TỐI ĐA 1 phiên bản đang "Chờ duyệt" tại 1 thời điểm cho
    # mỗi bản vẽ - tránh tình trạng nhiều phiên bản cùng chờ duyệt chồng
    # chéo khiến người duyệt dễ duyệt nhầm bản cũ hơn phiên bản mới nhất.
    dang_cho_duyet = [pb for pb in repository.lay_phien_ban_theo_banve(ma_bv)
                      if pb.trangthaiphienban_MaTrangThai == repository.CHO_DUYET]
    if dang_cho_duyet:
        raise LoiNghiepVu(
            f'Đang có phiên bản v{dang_cho_duyet[0].SoPhienBan} chờ duyệt. '
            'Vui lòng duyệt hoặc từ chối phiên bản đó trước khi tải lên phiên bản mới.'
        )

    _validate_file(file_storage, allowed_extensions)

    so_moi = _so_phien_ban_ke_tiep(ma_bv)
    ten_file_da_luu = repository.luu_file_vat_ly(file_storage, upload_folder)

    entity = PhienBan(
        MaPB=_sinh_ma_phien_ban(),
        SoPhienBan=str(so_moi),
        NgayTao=date.today(),
        HinhBV=ten_file_da_luu,
        HoNguoiTao=ho_nguoi_tao,
        TenNguoiTao=ten_nguoi_tao,
        NgayDuyet=None,
        banve_MaBV=ma_bv,
        trangthaiphienban_MaTrangThai=repository.CHO_DUYET,
    )
    repository.insert_phien_ban(entity)
    return entity


def duyet_phien_ban(ma_pb):
    entity = repository.get_phien_ban_or_404(ma_pb)
    if entity.trangthaiphienban_MaTrangThai != repository.CHO_DUYET:
        raise LoiNghiepVu('Chỉ có thể duyệt phiên bản đang ở trạng thái "Chờ duyệt".')
    for phien_ban in repository.lay_phien_ban_theo_banve(entity.banve_MaBV):
        if phien_ban.trangthaiphienban_MaTrangThai == repository.DA_DUYET:
            phien_ban.trangthaiphienban_MaTrangThai = repository.CU
    entity.trangthaiphienban_MaTrangThai = repository.DA_DUYET
    entity.NgayDuyet = date.today()
    repository.update_phien_ban()
    return entity


def tu_choi_phien_ban(ma_pb):
    entity = repository.get_phien_ban_or_404(ma_pb)
    if entity.trangthaiphienban_MaTrangThai != repository.CHO_DUYET:
        raise LoiNghiepVu('Chỉ có thể từ chối phiên bản đang ở trạng thái "Chờ duyệt".')
    entity.trangthaiphienban_MaTrangThai = repository.TU_CHOI
    repository.update_phien_ban()
    return entity


def xoa_phien_ban(ma_pb, upload_folder):
    entity = repository.get_phien_ban_or_404(ma_pb)
    hien_hanh = phien_ban_hien_hanh(entity.banve_MaBV)
    if hien_hanh and hien_hanh.MaPB == entity.MaPB:
        raise LoiNghiepVu('Không thể xóa phiên bản hiện hành (Mới).')
    repository.xoa_file_vat_ly(upload_folder, entity.HinhBV)
    repository.delete_phien_ban(entity)
