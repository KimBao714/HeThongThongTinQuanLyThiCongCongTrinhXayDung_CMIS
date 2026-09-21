"""
LỚP BUSINESS (Business Logic Layer)
------------------------------------
Chi phí (`chiphi`) ghi nhận 1 khoản tiền đã chi cho 1 hạng mục (`hangmuc`).

Điểm đặc biệt của bảng này trong file SQL gốc: ngoài `hangmuc_MaHangMuc`,
còn có 2 cột `phancong_MaPhanCong` và cặp
`sudungvatlieu_vatlieu_MaVL` + `sudungvatlieu_hangmuc_MaHangMuc` đều NOT
NULL và có ràng buộc FK THẬT (khác với cột dư ở `banve` - xem ghi chú đầu
`models.py`) trỏ tới `phancong` và `sudungvatlieu`.

Nói cách khác: theo đúng CSDL, MỌI dòng chi phí đều bắt buộc phải gắn với
ĐÚNG 1 phân công nhân sự ĐÃ CÓ SẴN và ĐÚNG 1 lượt sử dụng vật liệu ĐÃ CÓ
SẴN - chứ không phải tùy chọn "chi phí nhân công" HOẶC "chi phí vật liệu"
như cách hiểu thông thường. Đây là ràng buộc cứng của CSDL, module này
không có cách nào bỏ qua được.

=> Hệ quả quan trọng: để thêm được 1 dòng chi phí, 2 bảng `phancong` và
`sudungvatlieu` phải có dữ liệu từ trước. Hiện 2 bảng này CHƯA có module
quản lý riêng (chỉ có model, chưa có routes/service/repository) - xem
README, mục "Module chờ xây dựng". Module Chi phí chỉ ĐỌC dữ liệu có sẵn ở
2 bảng đó để hiển thị lên dropdown cho người dùng chọn.

Cột `LoaiChiPhi` (Nhân công/Vật liệu/Khác) chỉ mang tính PHÂN LOẠI để báo
cáo, KHÔNG làm thay đổi việc bắt buộc phải chọn cả phân công lẫn sử dụng
vật liệu ở trên (kể cả khi người dùng chọn loại "Vật liệu", CSDL vẫn đòi
hỏi phải có 1 phân công hợp lệ đi kèm, và ngược lại).

Các quy tắc nghiệp vụ xử lý ở tầng này (CSDL không tự đảm bảo được):
1. Số tiền chi phải > 0.
2. Ngày chi không được là ngày trong tương lai (không thể ghi nhận đã chi
   cho một ngày chưa tới).
3. `LoaiChiPhi` giới hạn theo danh sách cố định (`LOAI_CHI_PHI`) để đồng
   nhất khi tổng hợp báo cáo, tránh mỗi nơi gõ 1 kiểu chữ khác nhau (viết
   hoa/thường, dấu câu...) làm sai lệch số liệu thống kê theo loại.
4. NHẤT QUÁN HẠNG MỤC: phân công và lượt sử dụng vật liệu được chọn phải
   CÙNG thuộc hạng mục đã chọn cho dòng chi phí. CSDL không có ràng buộc
   nào kiểm tra việc này (3 cột hangmuc trong `chiphi`, `phancong`,
   `sudungvatlieu` là 3 cột hoàn toàn độc lập với nhau), nên nếu không
   chặn ở tầng này, dữ liệu có thể bị ghi nhận vô lý - VD: chi phí khai báo
   cho "Hạng mục A" nhưng lại trỏ tới 1 phân công/vật liệu thực tế đang
   dùng cho "Hạng mục B".
5. Không giới hạn khi xóa - rà theo `mainDB_latest.sql` thì không có bảng nào
   khác đặt FK trỏ tới `chiphi`, nên xóa 1 dòng chi phí không ảnh hưởng
   toàn vẹn dữ liệu ở bảng khác (khác với `banve`/`hangmuc` phải chặn xóa
   khi còn phụ thuộc).
6. So sánh chi phí thực tế lũy kế của 1 hạng mục với `NganSachDangCo` khai
   báo ở bảng `hangmuc` (hàm `tinh_ngan_sach`) để cảnh báo vượt ngân sách -
   hạng mục nào chưa khai báo ngân sách đang có thì chỉ hiển thị số đã chi,
   không tính được tỉ lệ %.
"""

from datetime import date
from decimal import Decimal

from app.models import ChiPhi
from app.modules.chiphi import repository
from app.utils import tinh_chi_phi_nhan_cong


class LoiNghiepVu(Exception):
    pass


# Danh sách cố định để đồng nhất báo cáo - cột LoaiChiPhi trong CSDL là
# varchar(45) tự do nên phải tự giới hạn ở tầng nghiệp vụ, CSDL không có
# ràng buộc CHECK hay bảng tra cứu riêng cho cột này.
LOAI_CHI_PHI = ['Ngân sách đang có', 'Nhân công', 'Vật liệu', 'Khác']


# ---------------------- Chi phí ----------------------

def lay_danh_sach(keyword=None, ma_hangmuc=None, loai_chi_phi=None):
    if ma_hangmuc:
        ma_lien_quan = _ma_hang_muc_lien_quan(ma_hangmuc)
        danh_sach = repository.get_all(keyword, None, loai_chi_phi)
        return [cp for cp in danh_sach if cp.hangmuc_MaHangMuc in ma_lien_quan]
    return repository.get_all(keyword, ma_hangmuc, loai_chi_phi)


def lay_theo_ma(ma):
    return repository.get_by_id_or_404(ma)


def danh_sach_hang_muc_de_chon():
    return repository.danh_sach_hang_muc()


def danh_sach_phan_cong_de_chon():
    return repository.danh_sach_phan_cong()


def danh_sach_su_dung_vat_lieu_de_chon():
    return repository.danh_sach_su_dung_vat_lieu()


def _ma_hang_muc_lien_quan(ma_hangmuc, danh_sach=None):
    danh_sach = danh_sach or repository.danh_sach_hang_muc()
    ma_lien_quan = {ma_hangmuc}
    ma_cho = [ma_hangmuc]
    while ma_cho:
        ma_cha = ma_cho.pop()
        for child in danh_sach:
            if child.hangmuc_MaHangMuc == ma_cha and child.MaHangMuc not in ma_lien_quan:
                ma_lien_quan.add(child.MaHangMuc)
                ma_cho.append(child.MaHangMuc)
    return ma_lien_quan


def tinh_ngan_sach(ma_hangmuc):
    """So sánh ngân sách đang có (`hangmuc.NganSachDangCo`) với tổng chi phí
    thực tế đã ghi nhận cho 1 hạng mục. Trả về None nếu hạng mục không tồn
    tại, để tầng Presentation biết không hiển thị khối so sánh này."""
    hangmuc = repository.hang_muc_theo_ma(ma_hangmuc)
    if hangmuc is None:
        return None

    ma_lien_quan = _ma_hang_muc_lien_quan(ma_hangmuc)
    tong_chi = sum(
        (cp.SoTienChi or Decimal('0') for cp in repository.get_all()
         if cp.hangmuc_MaHangMuc in ma_lien_quan), Decimal('0')
    )
    ngan_sach = sum(
        (hm.NganSachDangCo or Decimal('0') for hm in repository.danh_sach_hang_muc()
         if hm.MaHangMuc in ma_lien_quan), Decimal('0')
    )

    phan_tram = None
    vuot = False
    con_lai = None
    if ngan_sach and ngan_sach > 0:
        phan_tram = round(float(tong_chi) / float(ngan_sach) * 100, 1)
        vuot = tong_chi > ngan_sach
        con_lai = ngan_sach - tong_chi

    return {
        'ngan_sach': ngan_sach,
        'tong_chi': tong_chi,
        'phan_tram': phan_tram,
        'vuot': vuot,
        'con_lai': con_lai,
    }


def tinh_ngan_sach_su_dung(ma_hangmuc):
    """Tính ngân sách đã sử dụng từ vật liệu và nhân công của hạng mục.
    Khi chọn hạng mục cha, cộng cả các hạng mục con/cháu."""
    hang_muc = repository.hang_muc_theo_ma(ma_hangmuc)
    if hang_muc is None:
        return None
    danh_sach = repository.danh_sach_hang_muc()
    ma_lien_quan = _ma_hang_muc_lien_quan(ma_hangmuc, danh_sach)

    da_su_dung = Decimal('0')
    for sd in repository.danh_sach_su_dung_vat_lieu():
        if sd.hangmuc_MaHangMuc in ma_lien_quan:
            da_su_dung += (sd.vatlieu.DonGia or Decimal('0')) * (sd.SoLuongSD or Decimal('0'))
    for pc in repository.danh_sach_phan_cong():
        if pc.hangmuc_MaHangMuc in ma_lien_quan:
            da_su_dung += tinh_chi_phi_nhan_cong(pc.ChiphiThue, pc.SoNgayCong, pc.DonViTinh, pc.NgayBatDau, pc.NgayKetThuc)

    ngan_sach = sum(
        (hm.NganSachDangCo or Decimal('0') for hm in danh_sach if hm.MaHangMuc in ma_lien_quan),
        Decimal('0')
    )
    con_lai = ngan_sach - da_su_dung if ngan_sach is not None else None
    return {
        'ngan_sach': ngan_sach,
        'da_su_dung': da_su_dung,
        'con_lai': con_lai,
        'vuot': con_lai is not None and con_lai < 0,
    }


def lay_tong_quan_chi_phi():
    """Tổng hợp nhanh dữ liệu chi phí và hai nguồn phát sinh chi phí liên quan."""
    danh_sach_chi_phi = repository.get_all()
    tong_ngan_sach = sum(
        (hm.NganSachDangCo or Decimal('0') for hm in repository.danh_sach_hang_muc()),
        Decimal('0')
    )
    tong_chi = sum((cp.SoTienChi or Decimal('0') for cp in danh_sach_chi_phi), Decimal('0'))
    theo_loai = {
        loai: sum((cp.SoTienChi or Decimal('0') for cp in danh_sach_chi_phi if cp.LoaiChiPhi == loai), Decimal('0'))
        for loai in LOAI_CHI_PHI
    }
    tong_su_dung = Decimal('0')
    tong_so_luong_vat_lieu = Decimal('0')
    for sd in repository.danh_sach_su_dung_vat_lieu():
        tong_so_luong_vat_lieu += sd.SoLuongSD or Decimal('0')
        tong_su_dung += (sd.vatlieu.DonGia or Decimal('0')) * (sd.SoLuongSD or Decimal('0'))
    tong_nhan_cong = Decimal('0')
    tong_ngay_cong = 0
    for pc in repository.danh_sach_phan_cong():
        tong_ngay_cong += pc.SoNgayCong or 0
        tong_nhan_cong += tinh_chi_phi_nhan_cong(pc.ChiphiThue, pc.SoNgayCong, pc.DonViTinh, pc.NgayBatDau, pc.NgayKetThuc)
    return {
        'tong_chi': tong_chi,
        'tong_ngan_sach': tong_ngan_sach,
        'theo_loai': theo_loai,
        'so_dong_chi_phi': len(danh_sach_chi_phi),
        'so_hang_muc': len({cp.hangmuc_MaHangMuc for cp in danh_sach_chi_phi}),
        'tong_vat_lieu': tong_su_dung,
        'tong_so_luong_vat_lieu': tong_so_luong_vat_lieu,
        'tong_nhan_cong': tong_nhan_cong,
        'tong_ngay_cong': tong_ngay_cong,
        'tong_ngan_sach_su_dung': tong_su_dung + tong_nhan_cong,
        'so_phan_cong': len(repository.danh_sach_phan_cong()),
        'so_luot_vat_lieu': len(repository.danh_sach_su_dung_vat_lieu()),
    }


def lay_chi_tiet_nguon_chi_phi(ma_hangmuc=None):
    """Trả về chi tiết các khoản phát sinh từ Nhân sự và Vật liệu."""
    ma_lien_quan = _ma_hang_muc_lien_quan(ma_hangmuc) if ma_hangmuc else None
    phan_cong = []
    for pc in repository.danh_sach_phan_cong():
        if ma_lien_quan and pc.hangmuc_MaHangMuc not in ma_lien_quan:
            continue
        thanh_tien = tinh_chi_phi_nhan_cong(pc.ChiphiThue, pc.SoNgayCong, pc.DonViTinh, pc.NgayBatDau, pc.NgayKetThuc)
        phan_cong.append({'item': pc, 'thanh_tien': thanh_tien})

    vat_lieu = []
    for sd in repository.danh_sach_su_dung_vat_lieu():
        if ma_lien_quan and sd.hangmuc_MaHangMuc not in ma_lien_quan:
            continue
        thanh_tien = (sd.vatlieu.DonGia or Decimal('0')) * (sd.SoLuongSD or Decimal('0'))
        vat_lieu.append({'item': sd, 'thanh_tien': thanh_tien})
    return {
        'phan_cong': phan_cong,
        'vat_lieu': vat_lieu,
        'tong_ngay_cong': sum((dong['item'].SoNgayCong or 0 for dong in phan_cong), 0),
        'tong_so_luong_vat_lieu': sum(
            (dong['item'].SoLuongSD or Decimal('0') for dong in vat_lieu), Decimal('0')
        ),
        'tong_nhan_cong': sum((dong['thanh_tien'] for dong in phan_cong), Decimal('0')),
        'tong_vat_lieu': sum((dong['thanh_tien'] for dong in vat_lieu), Decimal('0')),
    }


def lay_tong_hop_theo_hang_muc():
    """Tổng hợp toàn bộ thông tin chi phí theo từng hạng mục.
    Hạng mục cha bao gồm cả dữ liệu của các hạng mục con/cháu."""
    danh_sach_hang_muc = repository.danh_sach_hang_muc()
    danh_sach_chi_phi = repository.get_all()
    danh_sach_vat_lieu = repository.danh_sach_su_dung_vat_lieu()
    danh_sach_phan_cong = repository.danh_sach_phan_cong()
    ket_qua = []

    for hang_muc in danh_sach_hang_muc:
        ma_lien_quan = _ma_hang_muc_lien_quan(hang_muc.MaHangMuc, danh_sach_hang_muc)

        chi_phi = [cp for cp in danh_sach_chi_phi if cp.hangmuc_MaHangMuc in ma_lien_quan]
        vat_lieu = [sd for sd in danh_sach_vat_lieu if sd.hangmuc_MaHangMuc in ma_lien_quan]
        phan_cong = [pc for pc in danh_sach_phan_cong if pc.hangmuc_MaHangMuc in ma_lien_quan]
        da_su_dung = sum(
            ((sd.vatlieu.DonGia or Decimal('0')) * (sd.SoLuongSD or Decimal('0')) for sd in vat_lieu),
            Decimal('0')
        ) + sum(
            (tinh_chi_phi_nhan_cong(pc.ChiphiThue, pc.SoNgayCong, pc.DonViTinh, pc.NgayBatDau, pc.NgayKetThuc) for pc in phan_cong),
            Decimal('0')
        )
        ngan_sach = sum(
            (hm.NganSachDangCo or Decimal('0') for hm in danh_sach_hang_muc
             if hm.MaHangMuc in ma_lien_quan), Decimal('0')
        )
        chi_phi_thuc_te = sum((cp.SoTienChi or Decimal('0') for cp in chi_phi), Decimal('0'))
        con_lai = ngan_sach - chi_phi_thuc_te if ngan_sach is not None else None
        ket_qua.append({
            'item': hang_muc,
            'ngan_sach': ngan_sach,
            'chi_phi': chi_phi_thuc_te,
            'da_su_dung': chi_phi_thuc_te,
            'con_lai': con_lai,
            'vuot': con_lai is not None and con_lai < 0,
            'da_su_dung_uoc_tinh': da_su_dung,
            'so_chi_phi': len(chi_phi),
            'so_vat_lieu': len(vat_lieu),
            'so_phan_cong': len(phan_cong),
        })
    return ket_qua


def _validate_chung(du_lieu_form):
    """Validate + làm sạch toàn bộ dữ liệu chung cho cả thêm mới lẫn cập
    nhật. Trả về dict tên cột -> giá trị đã hợp lệ, hoặc raise LoiNghiepVu
    ngay khi gặp vi phạm đầu tiên."""
    loai = du_lieu_form.get('LoaiChiPhi', '').strip()
    ngay_chi_raw = du_lieu_form.get('NgayChi', '').strip()
    so_tien_raw = du_lieu_form.get('SoTienChi', '').strip()
    mo_ta = du_lieu_form.get('MoTa', '').strip()
    ma_hangmuc = du_lieu_form.get('MaHangMuc', '').strip()
    ma_phancong = du_lieu_form.get('MaPhanCong', '').strip()
    ma_vl = du_lieu_form.get('MaVatLieu', '').strip()

    if loai not in LOAI_CHI_PHI:
        raise LoiNghiepVu(f'Loại chi phí không hợp lệ. Chỉ chấp nhận: {", ".join(LOAI_CHI_PHI)}.')

    if not ngay_chi_raw:
        raise LoiNghiepVu('Vui lòng chọn ngày chi.')
    try:
        ngay_chi = date.fromisoformat(ngay_chi_raw)
    except ValueError:
        raise LoiNghiepVu('Ngày chi không hợp lệ.')
    if ngay_chi > date.today():
        raise LoiNghiepVu('Ngày chi không được là ngày trong tương lai.')

    try:
        so_tien = float(so_tien_raw)
    except ValueError:
        raise LoiNghiepVu('Số tiền chi không hợp lệ.')
    if so_tien <= 0:
        raise LoiNghiepVu('Số tiền chi phải lớn hơn 0.')

    if not ma_hangmuc or repository.hang_muc_theo_ma(ma_hangmuc) is None:
        raise LoiNghiepVu('Hạng mục được chọn không tồn tại.')

    phancong = repository.phan_cong_theo_ma(ma_phancong) if ma_phancong else None
    if phancong is None:
        raise LoiNghiepVu(
            'Vui lòng chọn 1 phân công nhân sự hợp lệ (đã có sẵn trong hệ thống).'
        )
    if phancong.hangmuc_MaHangMuc != ma_hangmuc:
        raise LoiNghiepVu(
            'Phân công được chọn không thuộc hạng mục đã chọn ở trên. '
            'Hãy chọn 1 phân công cùng hạng mục với chi phí này.'
        )

    su_dung = repository.su_dung_vat_lieu_theo_khoa(ma_vl, ma_hangmuc) if ma_vl else None
    if su_dung is None:
        raise LoiNghiepVu(
            'Vui lòng chọn 1 lượt sử dụng vật liệu hợp lệ, thuộc đúng hạng mục đã chọn ở trên.'
        )

    return {
        'LoaiChiPhi': loai,
        'NgayChi': ngay_chi,
        'SoTienChi': so_tien,
        'MoTa': mo_ta,
        'hangmuc_MaHangMuc': ma_hangmuc,
        'phancong_MaPhanCong': ma_phancong,
        'sudungvatlieu_vatlieu_MaVL': ma_vl,
        'sudungvatlieu_hangmuc_MaHangMuc': ma_hangmuc,
    }


def them_moi(du_lieu_form):
    ma = du_lieu_form.get('MaCP', '').strip()
    if not ma:
        raise LoiNghiepVu('Vui lòng nhập mã chi phí.')
    if repository.exists(ma):
        raise LoiNghiepVu(f'Mã chi phí "{ma}" đã tồn tại.')

    du_lieu = _validate_chung(du_lieu_form)
    entity = ChiPhi(MaCP=ma, **du_lieu)
    repository.insert(entity)
    return entity


def cap_nhat(ma, du_lieu_form):
    entity = repository.get_by_id_or_404(ma)
    du_lieu = _validate_chung(du_lieu_form)
    for ten_cot, gia_tri in du_lieu.items():
        setattr(entity, ten_cot, gia_tri)
    repository.update()
    return entity


def xoa(ma):
    entity = repository.get_by_id_or_404(ma)
    repository.delete(entity)
