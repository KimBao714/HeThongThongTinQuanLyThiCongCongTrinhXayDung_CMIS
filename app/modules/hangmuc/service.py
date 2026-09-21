"""
LỚP BUSINESS (Business Logic Layer)
------------------------------------
Hạng mục (bảng `hangmuc`) là entity phân cấp cha/con qua khóa tự tham chiếu
`hangmuc_MaHangMuc`, và cột này NOT NULL trong CSDL - tức MỌI hạng mục đều
phải có "cha", kể cả hạng mục gốc (tương đương "công trình" ở schema cũ).

Quy ước nghiệp vụ áp dụng ở đây (vì CSDL không có cách nào biểu diễn NULL):
- Hạng mục KHÔNG chọn hạng mục cha khi thêm/sửa  => hangmuc_MaHangMuc tự trỏ
  về chính MaHangMuc của nó (hạng mục gốc / công trình).
- Hạng mục CÓ chọn hạng mục cha => hangmuc_MaHangMuc = mã hạng mục cha.

Ngoài ra module này còn đảm nhiệm 2 quy tắc nghiệp vụ quan trọng khác:
- Chặn vòng lặp cha/con (không cho chọn 1 hạng mục con/cháu của chính nó
  làm hạng mục cha).
- Chặn xóa hạng mục khi vẫn còn hạng mục con phụ thuộc, HOẶC khi hạng mục
  đang bị tham chiếu bởi bản vẽ (`banve`), phân công (`phancong`), sử dụng
  vật liệu (`sudungvatlieu`), hoặc chi phí (`chiphi`) - tránh vi phạm ràng
  buộc khóa ngoại ở CSDL (mặc định ON DELETE RESTRICT).

Hiển thị 2 chiều (chỉ ĐỌC): module này đọc thêm dữ liệu `phancong` (thuộc
module Nhân sự) và `sudungvatlieu` (thuộc module Vật liệu) để hiển thị
ngược "hạng mục này đang có ai làm, đang dùng vật liệu gì" trên trang danh
sách - xem `nhan_su_dang_lam_theo_hangmuc()` và
`vat_lieu_dang_dung_theo_hangmuc()` bên dưới. Quyền thêm/sửa/xóa 2 loại dữ
liệu đó vẫn chỉ thuộc về module sở hữu tương ứng.
"""

from decimal import Decimal, InvalidOperation

from app.models import HangMuc
from app.modules.hangmuc import repository
from app.utils import parse_date
from app.utils import tinh_chi_phi_nhan_cong


class LoiNghiepVu(Exception):
    pass


def _validate_ngan_sach(raw):
    """Ngân sách đang có là trường TÙY CHỌN (cột cho phép NULL) nên chuỗi
    rỗng hợp lệ (= chưa khai báo). Nếu có nhập thì phải là số và không được
    âm - tránh lỗi 500 thô từ CSDL khi người dùng gõ nhầm chữ (SQLAlchemy sẽ
    ném ValueError ngay lúc insert/update nếu không chặn ở đây, giống lỗi đã
    từng xảy ra với `SoTienChi` ở module Chi phí trước khi được validate).

    Trả về Decimal (không phải float) vì cột CSDL là Numeric/Decimal - khi
    đọc lại 1 hạng mục đã có sẵn, SQLAlchemy trả về NganSachDangCo dạng
    Decimal, nên giá trị validate ở đây PHẢI cùng kiểu Decimal thì mới cộng
    được với nhau (`cong_ngan_sach` bên dưới), tránh lỗi
    "unsupported operand type(s) for +: 'decimal.Decimal' and 'float'"."""
    raw = (raw or '').strip()
    if not raw:
        return None
    try:
        gia_tri = Decimal(raw)
    except InvalidOperation:
        raise LoiNghiepVu('Ngân sách đang có không hợp lệ - vui lòng nhập số.')
    if gia_tri < 0:
        raise LoiNghiepVu('Ngân sách đang có không được âm.')
    return gia_tri


def lay_danh_sach(keyword=None):
    return repository.get_all(keyword)


def lay_theo_ma(ma):
    return repository.get_by_id_or_404(ma)


def lay_cay_hang_muc(keyword=None):
    """Trả về danh sách hạng mục theo thứ tự cây (duyệt sâu - DFS), kèm cấp
    độ (`cap`) để tầng Presentation hiển thị thụt lề phân cấp cha/con."""
    danh_sach = repository.get_all(keyword)
    theo_ma = {h.MaHangMuc: h for h in danh_sach}
    con_cua = {}
    goc = []

    for h in danh_sach:
        la_goc = (h.hangmuc_MaHangMuc == h.MaHangMuc) or (h.hangmuc_MaHangMuc not in theo_ma)
        if la_goc:
            goc.append(h)
        else:
            con_cua.setdefault(h.hangmuc_MaHangMuc, []).append(h)

    ket_qua = []

    def duyet(h, cap):
        ket_qua.append({'item': h, 'cap': cap})
        for con in sorted(con_cua.get(h.MaHangMuc, []), key=lambda x: x.MaHangMuc):
            duyet(con, cap + 1)

    for h in sorted(goc, key=lambda x: x.MaHangMuc):
        duyet(h, 0)

    return ket_qua


def danh_sach_hang_muc_hau_due(ma):
    """Trả về toàn bộ hạng mục con/cháu của một hạng mục."""
    danh_sach_tat_ca = repository.get_all()
    ma_hau_due = _danh_sach_hau_due(ma, danh_sach_tat_ca)
    return [h for h in danh_sach_tat_ca if h.MaHangMuc in ma_hau_due]


def _danh_sach_hau_due(ma, danh_sach_tat_ca):
    """Trả về tập hợp mã của toàn bộ hạng mục con/cháu (mọi cấp) của `ma`."""
    con_cua = {}
    for h in danh_sach_tat_ca:
        if h.hangmuc_MaHangMuc != h.MaHangMuc:
            con_cua.setdefault(h.hangmuc_MaHangMuc, []).append(h.MaHangMuc)

    hau_due = set()
    hang_doi = list(con_cua.get(ma, []))
    while hang_doi:
        ma_con = hang_doi.pop()
        if ma_con in hau_due:
            continue
        hau_due.add(ma_con)
        hang_doi.extend(con_cua.get(ma_con, []))
    return hau_due


def danh_sach_hang_muc_cha_de_chon(ma_dang_sua=None):
    """Dữ liệu tham chiếu cho dropdown chọn hạng mục cha.
    Khi đang SỬA (`ma_dang_sua` có giá trị): loại trừ chính hạng mục đó và
    toàn bộ hạng mục con/cháu của nó, để tránh chọn nhầm tạo vòng lặp."""
    danh_sach_tat_ca = repository.get_all()
    if not ma_dang_sua:
        return danh_sach_tat_ca

    hau_due = _danh_sach_hau_due(ma_dang_sua, danh_sach_tat_ca)
    return [
        h for h in danh_sach_tat_ca
        if h.MaHangMuc != ma_dang_sua and h.MaHangMuc not in hau_due
    ]


def _validate_ngay_thang(ngay_khoi_cong, ngay_hoan_thanh_du_kien):
    """Cả 2 trường đều TÙY CHỌN (cột cho phép NULL) nên chỉ kiểm tra khi CẢ
    HAI đều đã được khai báo - không thể so sánh khi thiếu 1 trong 2. Ngày
    dự kiến hoàn thành phải sau (hoặc bằng) ngày khởi công, nếu không cảnh
    báo "Hạng mục trễ tiến độ" ở Dashboard (xem dashboard/service.py) sẽ vô
    nghĩa ngay từ lúc nhập liệu (hạng mục "trễ" trước cả khi khởi công)."""
    if ngay_khoi_cong and ngay_hoan_thanh_du_kien and ngay_khoi_cong > ngay_hoan_thanh_du_kien:
        raise LoiNghiepVu(
            'Thời gian hoàn thành dự kiến không được trước ngày khởi công.'
        )


def them_moi(du_lieu_form):
    ma = du_lieu_form.get('MaHangMuc', '').strip()
    ma_cha = du_lieu_form.get('HangMucCha', '').strip()

    if repository.exists(ma):
        raise LoiNghiepVu(f'Mã hạng mục "{ma}" đã tồn tại.')

    if ma_cha:
        if not repository.exists(ma_cha):
            raise LoiNghiepVu(f'Hạng mục cha "{ma_cha}" không tồn tại.')
    else:
        # Không chọn cha => là hạng mục gốc, tự trỏ vào chính mình theo
        # quy ước (vì cột hangmuc_MaHangMuc NOT NULL trong CSDL).
        ma_cha = ma

    entity = HangMuc(
        MaHangMuc=ma,
        TenHangMuc=du_lieu_form.get('TenHangMuc', '').strip(),
        NganSachDangCo=_validate_ngan_sach(du_lieu_form.get('NganSachDangCo')),
        NgayKhoiCong=parse_date(du_lieu_form.get('NgayKhoiCong')),
        ThoiGianHoanThanhDuKien=parse_date(du_lieu_form.get('ThoiGianHoanThanhDuKien')),
        hangmuc_MaHangMuc=ma_cha
    )
    _validate_ngay_thang(entity.NgayKhoiCong, entity.ThoiGianHoanThanhDuKien)
    repository.insert(entity)
    return entity


def cap_nhat(ma, du_lieu_form):
    entity = repository.get_by_id_or_404(ma)
    ma_cha = du_lieu_form.get('HangMucCha', '').strip()

    if not ma_cha:
        ma_cha = ma
    elif ma_cha != ma:
        if not repository.exists(ma_cha):
            raise LoiNghiepVu(f'Hạng mục cha "{ma_cha}" không tồn tại.')
        danh_sach_tat_ca = repository.get_all()
        if ma_cha in _danh_sach_hau_due(ma, danh_sach_tat_ca):
            raise LoiNghiepVu(
                'Không thể chọn hạng mục con/cháu của chính hạng mục này làm hạng mục cha '
                '(sẽ tạo vòng lặp phân cấp).'
            )

    entity.TenHangMuc = du_lieu_form.get('TenHangMuc', '').strip()
    entity.NganSachDangCo = _validate_ngan_sach(du_lieu_form.get('NganSachDangCo'))
    ngay_khoi_cong = parse_date(du_lieu_form.get('NgayKhoiCong'))
    thoi_gian_hoan_thanh = parse_date(du_lieu_form.get('ThoiGianHoanThanhDuKien'))
    _validate_ngay_thang(ngay_khoi_cong, thoi_gian_hoan_thanh)
    entity.NgayKhoiCong = ngay_khoi_cong
    entity.ThoiGianHoanThanhDuKien = thoi_gian_hoan_thanh
    entity.hangmuc_MaHangMuc = ma_cha
    repository.update()
    return entity


def cong_ngan_sach(ma, so_tien_raw):
    entity = repository.get_by_id_or_404(ma)
    so_tien = _validate_ngan_sach(so_tien_raw)
    if so_tien is None or so_tien <= 0:
        raise LoiNghiepVu('Số tiền ngân sách cộng thêm phải lớn hơn 0.')
    entity.NganSachDangCo = (entity.NganSachDangCo or Decimal('0')) + so_tien
    repository.update()
    return entity


def xoa(ma):
    entity = repository.get_by_id_or_404(ma)
    if repository.count_hang_muc_con(ma) > 0:
        raise LoiNghiepVu('Không thể xóa vì vẫn còn hạng mục con phụ thuộc vào hạng mục này.')
    if repository.co_banve_su_dung(ma):
        raise LoiNghiepVu('Không thể xóa vì đang có bản vẽ gắn với hạng mục này.')
    if repository.co_phan_cong_su_dung(ma):
        raise LoiNghiepVu('Không thể xóa vì đang có phân công nhân sự gắn với hạng mục này.')
    if repository.co_vat_lieu_su_dung(ma):
        raise LoiNghiepVu('Không thể xóa vì đang có vật liệu được sử dụng cho hạng mục này.')
    if repository.co_chi_phi_gan_truc_tiep(ma):
        raise LoiNghiepVu('Không thể xóa vì đang có chi phí ghi nhận trực tiếp cho hạng mục này.')
    repository.delete(entity)


def nhan_su_dang_lam_theo_hangmuc():
    """Trả về dict {MaHangMuc: [PhanCong, ...]} - dùng hiển thị "hạng mục
    này đang có ai làm" trên trang danh sách hạng mục. Đọc trực tiếp bảng
    `phancong` bằng 1 truy vấn duy nhất cho toàn bộ hạng mục (thay vì truy
    vấn riêng từng hạng mục) để tránh N+1 query khi trang có nhiều hạng mục.

    Module Hạng mục chỉ ĐỌC dữ liệu này - việc thêm/sửa/xóa phân công thuộc
    về module Nhân sự (xem app/modules/nhansu), vì phân công được xem là
    thực thể kết hợp quản lý theo hướng "từ 1 nhân sự" chứ không phải từ
    hạng mục."""
    ket_qua = {}
    for pc in repository.danh_sach_phan_cong_tat_ca():
        ket_qua.setdefault(pc.hangmuc_MaHangMuc, []).append(pc)
    return ket_qua


def vat_lieu_dang_dung_theo_hangmuc():
    """Trả về dict {MaHangMuc: [SuDungVatLieu, ...]} - dùng hiển thị "hạng
    mục này đang dùng vật liệu gì, số lượng bao nhiêu" trên trang danh sách
    hạng mục. Đọc trực tiếp bảng `sudungvatlieu` bằng 1 truy vấn duy nhất
    cho toàn bộ hạng mục (tương tự nhan_su_dang_lam_theo_hangmuc ở trên, để
    tránh N+1 query khi trang có nhiều hạng mục).

    Module Hạng mục chỉ ĐỌC dữ liệu này - việc thêm/sửa/xóa lượt sử dụng
    vật liệu thuộc về module Vật liệu (xem app/modules/vatlieu), vì
    `sudungvatlieu` được xem là thực thể kết hợp quản lý theo hướng "từ 1
    vật liệu" chứ không phải từ hạng mục."""
    ket_qua = {}
    for sd in repository.danh_sach_su_dung_vat_lieu_tat_ca():
        ket_qua.setdefault(sd.hangmuc_MaHangMuc, []).append(sd)
    return ket_qua


def ngan_sach_da_su_dung_theo_hangmuc():
    """Tính chi phí vật liệu và nhân công theo từng hạng mục.
    Chi phí vật liệu = đơn giá x số lượng sử dụng; chi phí nhân công =
    chi phí thuê x số ngày công."""
    ket_qua = {}
    for sd in repository.danh_sach_su_dung_vat_lieu_tat_ca():
        chi_phi = (sd.vatlieu.DonGia or Decimal('0')) * (sd.SoLuongSD or Decimal('0'))
        ket_qua[sd.hangmuc_MaHangMuc] = ket_qua.get(sd.hangmuc_MaHangMuc, Decimal('0')) + chi_phi
    for pc in repository.danh_sach_phan_cong_tat_ca():
        chi_phi = tinh_chi_phi_nhan_cong(pc.ChiphiThue, pc.SoNgayCong, pc.DonViTinh, pc.NgayBatDau, pc.NgayKetThuc)
        ket_qua[pc.hangmuc_MaHangMuc] = ket_qua.get(pc.hangmuc_MaHangMuc, Decimal('0')) + chi_phi
    return ket_qua


def tinh_ngan_sach_da_su_dung(ma):
    """Tổng ngân sách đã sử dụng của hạng mục, gồm cả các hạng mục con."""
    ngan_sach_theo_hangmuc = ngan_sach_da_su_dung_theo_hangmuc()
    ma_lien_quan = {ma} | {h.MaHangMuc for h in danh_sach_hang_muc_hau_due(ma)}
    return sum((ngan_sach_theo_hangmuc.get(ma_hm, Decimal('0')) for ma_hm in ma_lien_quan), Decimal('0'))


def tinh_trang_ngan_sach(ma):
    hang_muc = lay_theo_ma(ma)
    ngan_sach_du_kien = hang_muc.NganSachDangCo or Decimal('0')
    da_su_dung = tinh_ngan_sach_da_su_dung(ma)
    return {
        'du_kien': ngan_sach_du_kien,
        'da_su_dung': da_su_dung,
        'con_lai': ngan_sach_du_kien - da_su_dung,
        'vuot': da_su_dung > ngan_sach_du_kien,
    }
