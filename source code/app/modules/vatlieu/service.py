"""
LỚP BUSINESS (Business Logic Layer)
------------------------------------
Module này quản lý Vật liệu (`vatlieu`) VÀ Sử dụng vật liệu
(`sudungvatlieu`) gộp chung, theo hướng nhìn từ 1 vật liệu: "vật liệu này
đang được dùng cho những hạng mục nào, số lượng bao nhiêu" - tương tự cách
`phancong` được gộp vào module Nhân sự (xem
app/modules/nhansu/service.py).

`sudungvatlieu` là THỰC THỂ KẾT HỢP (associative entity) sinh ra từ quan hệ
nhiều-nhiều giữa `vatlieu` và `hangmuc`. Khác với `phancong` (có mã riêng
`MaPhanCong`, tự sinh, nên 1 cặp nhân sự-hạng mục có thể lặp lại ở nhiều đợt
thời gian khác nhau), khóa chính của `sudungvatlieu` là KHÓA KÉP
(`vatlieu_MaVL`, `hangmuc_MaHangMuc`) - tức 1 vật liệu chỉ có ĐÚNG 1 dòng
ghi nhận số lượng sử dụng cho MỖI hạng mục (không lặp lại theo thời gian).
Do đó không có khái niệm "thêm nhiều lượt" cho cùng 1 cặp (vật liệu, hạng
mục) - muốn ghi nhận thêm vật liệu dùng vào đợt sau cho cùng hạng mục đó,
form "Thêm" TỰ ĐỘNG cộng dồn số lượng vào dòng đã có (không tạo dòng mới,
không cần người dùng tự tìm dòng cũ để sửa - xem quy tắc 4 bên dưới).

Vì Chi phí (`chiphi`) có khóa ngoại THẬT bắt buộc trỏ tới đúng 1 lượt sử
dụng vật liệu (xem `app/modules/chiphi/service.py`), module này cũng phải
tự chặn xóa khi còn phụ thuộc - CSDL sẽ tự chặn bằng lỗi kỹ thuật
(IntegrityError) nếu không chặn trước ở đây.

Hiển thị 2 chiều: module Hạng mục (`app/modules/hangmuc`) chỉ ĐỌC dữ liệu
`sudungvatlieu` để hiển thị ngược "hạng mục này đang dùng vật liệu gì, số
lượng bao nhiêu" trên trang danh sách hạng mục - quyền thêm/sửa/xóa lượt sử
dụng vẫn chỉ nằm ở module Vật liệu này (xem
app/modules/hangmuc/service.py, hàm `vat_lieu_dang_dung_theo_hangmuc`).

Các quy tắc nghiệp vụ xử lý ở tầng này (CSDL không tự đảm bảo được):

1. Không cho xóa vật liệu khi vẫn còn hạng mục đang sử dụng nó (tương tự
   quy tắc chặn xóa hạng mục còn con / nhân sự còn phân công).

2. CHỈ ĐƯỢC GHI NHẬN SỬ DỤNG VÀO HẠNG MỤC CON (hạng mục có hạng mục cha cụ
   thể, không phải hạng mục gốc/công trình). ĐÂY LÀ LOGIC NGHIỆP VỤ BỔ SUNG
   (áp dụng lại đúng lý do đã dùng cho `phancong` ở module Nhân sự, mục 6c
   README): hạng mục gốc là cấp quản lý tổng thể (ngân sách, thời gian
   chung của cả công trình), còn việc thi công thực tế - và do đó việc tiêu
   hao vật liệu - luôn diễn ra ở hạng mục con cụ thể. Ghi nhận vật liệu
   thẳng vào hạng mục gốc không có ý nghĩa nghiệp vụ rõ ràng và dễ nhầm với
   việc quản lý tổng thể.

3. Số lượng sử dụng (`SoLuongSD`) phải > 0.

4. TRÙNG CẶP (vật liệu, hạng mục) THÌ TỰ CỘNG DỒN, không tạo dòng mới: vì
   khóa chính là khóa kép, 1 vật liệu chỉ có đúng 1 dòng cho mỗi hạng mục.
   Khi ghi nhận sử dụng cho 1 cặp (vật liệu, hạng mục) đã có sẵn dòng từ
   trước (VD: dùng thêm vật liệu vào đợt thi công sau cho cùng hạng mục
   đó), hệ thống TỰ ĐỘNG cộng dồn số lượng mới vào dòng đã có, thay vì bắt
   người dùng phải tự tìm dòng cũ rồi sửa thủ công - form "Thêm" và hành vi
   "cộng dồn vào dòng cũ nếu trùng" dùng chung 1 luồng duy nhất, không cần
   phân biệt 2 thao tác khác nhau. Đây cũng là lý do tại sao CSDL không bao
   giờ tự chặn bằng `IntegrityError` ở thao tác này: ứng dụng luôn UPDATE
   dòng cũ thay vì thử INSERT trùng khóa.

5. KHÔNG CHO ĐỔI VẬT LIỆU/HẠNG MỤC KHI SỬA (2 cột này là khóa chính) - form
   Sửa chỉ cho phép thay đổi số lượng sử dụng. Đây là quyết định kỹ thuật
   an toàn: đổi khóa chính của 1 dòng đang được `chiphi` tham chiếu tới (2
   cột `sudungvatlieu_vatlieu_MaVL` + `sudungvatlieu_hangmuc_MaHangMuc`
   trong bảng `chiphi`) sẽ phá vỡ toàn vẹn dữ liệu. Muốn chuyển ghi nhận
   sang hạng mục khác, phải xóa dòng cũ (nếu chưa có chi phí phụ thuộc) và
   tạo dòng mới.

6. Xóa 1 lượt sử dụng: chặn nếu đã có dòng chi phí (`chiphi`) tham chiếu
   tới nó - khớp với ràng buộc khóa ngoại thật `fk_chiphi_sudungvatlieu1`
   trong `mainDB_latest.sql`, chặn ở đây để báo lỗi thân thiện thay vì để CSDL
   tự chặn bằng `IntegrityError`.

7. CẢNH BÁO (không chặn cứng) khi tổng số lượng đã sử dụng của 1 vật liệu
   (cộng dồn qua mọi hạng mục) vượt quá `SoLuongDangCo` (số lượng đang có) khai
   báo ở bảng `vatlieu`. ĐÂY LÀ LOGIC NGHIỆP VỤ BỔ SUNG - CSDL/yêu cầu gốc
   không đòi hỏi ràng buộc này, nhưng nó tận dụng đúng dữ liệu đã có
   (`SoLuongDangCo` từng bị "mồ côi" vì chưa có module nào dùng tới) để cảnh
   báo sớm cho người quản lý khi nào cần mua bổ sung vật liệu - mô phỏng
   đúng cách module Chi phí so sánh chi phí thực tế với `NganSachDangCo`
   (xem `chiphi/service.tinh_ngan_sach`). Vật liệu chưa khai báo số lượng
   đang có thì chỉ hiển thị số đã dùng, không tính được tỉ lệ %.
"""

from decimal import Decimal, InvalidOperation

from app.models import VatLieu, SuDungVatLieu
from app.modules.vatlieu import repository


class LoiNghiepVu(Exception):
    pass


def _validate_so_khong_am(raw, ten_truong):
    """Trường TÙY CHỌN (cột cho phép NULL) nên chuỗi rỗng hợp lệ. Nếu có
    nhập thì phải là số và không được âm - tránh lỗi 500 thô từ CSDL khi
    người dùng gõ nhầm chữ vào ô số (SQLAlchemy ném ValueError ngay lúc
    insert/update nếu không chặn ở đây)."""
    raw = (raw or '').strip()
    if not raw:
        return None
    try:
        gia_tri = float(raw)
    except ValueError:
        raise LoiNghiepVu(f'{ten_truong} không hợp lệ - vui lòng nhập số.')
    if gia_tri < 0:
        raise LoiNghiepVu(f'{ten_truong} không được âm.')
    return gia_tri


# ==================== VẬT LIỆU ====================

def lay_danh_sach(keyword=None, ma_hangmuc=None):
    return repository.get_all(keyword, ma_hangmuc)


def lay_theo_ma(ma):
    return repository.get_by_id_or_404(ma)


def danh_sach_hang_muc_dang_dung(ma_vl):
    """Danh sách mã hạng mục đang sử dụng vật liệu này - hiển thị trực tiếp
    trên trang danh sách vật liệu (yêu cầu: hiển thị qua mã hạng mục của
    vật liệu đó) mà không cần bấm vào xem chi tiết."""
    return [sd.hangmuc_MaHangMuc for sd in repository.danh_sach_su_dung_theo_vatlieu(ma_vl)]


def tinh_su_dung(ma_vl):
    """So sánh số lượng đang có (`vatlieu.SoLuongDangCo`) với tổng số lượng đã
    ghi nhận sử dụng thực tế (cộng dồn mọi hạng mục) cho 1 vật liệu. Trả về
    None nếu vật liệu không tồn tại, để tầng Presentation biết không hiển
    thị khối so sánh này."""
    vat_lieu = repository.get_by_id(ma_vl)
    if vat_lieu is None:
        return None

    tong_da_dung = repository.tong_so_luong_da_dung(ma_vl)
    du_kien = vat_lieu.SoLuongDangCo

    phan_tram = None
    vuot = False
    con_lai = None
    if du_kien and du_kien > 0:
        phan_tram = round(float(tong_da_dung) / float(du_kien) * 100, 1)
        vuot = tong_da_dung > du_kien
        con_lai = du_kien - tong_da_dung

    return {
        'du_kien': du_kien,
        'tong_da_dung': tong_da_dung,
        'phan_tram': phan_tram,
        'vuot': vuot,
        'con_lai': con_lai,
    }


def danh_sach_vuot_du_kien():
    """Danh sách TẤT CẢ vật liệu đã dùng (cộng dồn mọi hạng mục) VƯỢT số
    lượng đang có (`SoLuongDangCo`), sắp xếp % vượt nhiều nhất lên đầu - dùng
    cho cảnh báo ở Dashboard tổng quan (module Dashboard chỉ ĐỌC, không tự
    tính lại logic này). Dùng 2 truy vấn tổng hợp (1 lấy hết vật liệu, 1 lấy
    tổng số lượng đã dùng gộp theo từng vật liệu) thay vì gọi lặp lại
    tinh_su_dung() cho từng vật liệu, để tránh N+1 query."""
    da_dung_theo_ma = dict(repository.tong_so_luong_da_dung_theo_tat_ca())
    ket_qua = []
    for vl in repository.get_all():
        if not vl.SoLuongDangCo or vl.SoLuongDangCo <= 0:
            continue  # chưa khai báo số lượng đang có -> không có cơ sở so sánh
        da_dung = da_dung_theo_ma.get(vl.MaVL, 0)
        if da_dung > vl.SoLuongDangCo:
            ket_qua.append({
                'item': vl,
                'da_dung': da_dung,
                'du_kien': vl.SoLuongDangCo,
                'phan_tram': round(float(da_dung) / float(vl.SoLuongDangCo) * 100, 1),
            })
    ket_qua.sort(key=lambda x: x['phan_tram'], reverse=True)
    return ket_qua


def them_moi(du_lieu_form):
    ma = du_lieu_form.get('MaVL', '').strip()
    if not ma:
        raise LoiNghiepVu('Vui lòng nhập mã vật liệu.')
    if repository.exists(ma):
        raise LoiNghiepVu(f'Mã vật liệu "{ma}" đã tồn tại.')

    entity = VatLieu(
        MaVL=ma,
        TenVL=du_lieu_form.get('TenVL', '').strip(),
        SoLuongDangCo=_validate_so_khong_am(du_lieu_form.get('SoLuongDangCo'), 'Số lượng đang có'),
        DonViTinh=du_lieu_form.get('DonViTinh', '').strip(),
        DonGia=_validate_so_khong_am(du_lieu_form.get('DonGia'), 'Đơn giá')
    )
    repository.insert(entity)
    return entity


def cap_nhat(ma, du_lieu_form):
    entity = repository.get_by_id_or_404(ma)
    entity.TenVL = du_lieu_form.get('TenVL', '').strip()
    entity.SoLuongDangCo = _validate_so_khong_am(du_lieu_form.get('SoLuongDangCo'), 'Số lượng đang có')
    entity.DonViTinh = du_lieu_form.get('DonViTinh', '').strip()
    entity.DonGia = _validate_so_khong_am(du_lieu_form.get('DonGia'), 'Đơn giá')
    repository.update()
    return entity


def xoa(ma):
    entity = repository.get_by_id_or_404(ma)
    if repository.dem_su_dung(ma) > 0:
        raise LoiNghiepVu(
            'Không thể xóa vật liệu này vì vẫn còn hạng mục đang sử dụng nó. '
            'Hãy xóa hết các lượt sử dụng của vật liệu này trước (xem trang Sử dụng vật liệu).'
        )
    repository.delete(entity)


# ==================== SỬ DỤNG VẬT LIỆU ====================

def danh_sach_hang_muc_con_de_chon():
    return repository.danh_sach_hang_muc_con()


def danh_sach_su_dung(ma_vl):
    repository.get_by_id_or_404(ma_vl)  # đảm bảo vật liệu tồn tại (404 nếu không)
    return repository.danh_sach_su_dung_theo_vatlieu(ma_vl)


def lay_su_dung_theo_khoa(ma_vl, ma_hangmuc):
    return repository.get_su_dung_or_404(ma_vl, ma_hangmuc)


def _validate_so_luong(so_luong_raw):
    if not so_luong_raw:
        raise LoiNghiepVu('Vui lòng nhập số lượng sử dụng.')
    try:
        so_luong = Decimal(so_luong_raw)
    except InvalidOperation:
        raise LoiNghiepVu('Số lượng sử dụng không hợp lệ.')
    if so_luong <= 0:
        raise LoiNghiepVu('Số lượng sử dụng phải lớn hơn 0.')
    return so_luong


def them_su_dung(ma_vl, du_lieu_form):
    repository.get_by_id_or_404(ma_vl)  # đảm bảo vật liệu tồn tại

    ma_hangmuc = du_lieu_form.get('MaHangMuc', '').strip()
    if not ma_hangmuc or repository.hang_muc_con_theo_ma(ma_hangmuc) is None:
        raise LoiNghiepVu(
            'Chỉ được ghi nhận sử dụng vật liệu vào hạng mục CON (hạng mục có '
            'hạng mục cha cụ thể) - không ghi nhận trực tiếp vào hạng mục gốc/công trình.'
        )

    so_luong = _validate_so_luong(du_lieu_form.get('SoLuongSD', '').strip())
    entity_da_co = repository.su_dung_theo_khoa(ma_vl, ma_hangmuc)
    if entity_da_co is not None:
        entity_da_co.SoLuongSD = (entity_da_co.SoLuongSD or 0) + so_luong
        repository.update_su_dung()
        return entity_da_co

    entity = SuDungVatLieu(vatlieu_MaVL=ma_vl, hangmuc_MaHangMuc=ma_hangmuc, SoLuongSD=so_luong)
    repository.insert_su_dung(entity)
    return entity


def sua_su_dung(ma_vl, ma_hangmuc, du_lieu_form):
    entity = repository.get_su_dung_or_404(ma_vl, ma_hangmuc)
    so_luong = _validate_so_luong(du_lieu_form.get('SoLuongSD', '').strip())
    entity.SoLuongSD = so_luong
    repository.update_su_dung()
    return entity


def xoa_su_dung(ma_vl, ma_hangmuc):
    entity = repository.get_su_dung_or_404(ma_vl, ma_hangmuc)
    if repository.dem_chi_phi_theo_su_dung(ma_vl, ma_hangmuc) > 0:
        raise LoiNghiepVu(
            'Không thể xóa vì đã có chi phí ghi nhận gắn với lượt sử dụng vật liệu này. '
            'Hãy xóa các chi phí liên quan trước (xem module Chi phí).'
        )
    repository.delete_su_dung(entity)
