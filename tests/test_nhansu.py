"""Test module Nhân sự (đã gộp Phân công): chỉ phân công vào hạng mục con,
chặn trùng lịch, thêm ngày công cộng dồn, chặn xóa khi còn phụ thuộc."""

from conftest import tao_hang_muc_goc_va_con


def test_them_nhan_su(toan_quyen, app):
    toan_quyen.post('/nhansu/them', data={'MaNV': 'NV01', 'HoNV': 'Nguyễn', 'TenNV': 'Văn A',
                                            'TrangThaiLamViec': 'Đang làm việc'}, follow_redirects=True)
    with app.app_context():
        from app.models import NhanSu
        assert NhanSu.query.get('NV01') is not None


def test_chan_phan_cong_vao_hang_muc_goc(toan_quyen):
    toan_quyen.post('/hangmuc/them', data={'MaHangMuc': 'HM01', 'TenHangMuc': 'Công trình A'},
                     follow_redirects=True)
    toan_quyen.post('/nhansu/them', data={'MaNV': 'NV01', 'TenNV': 'Văn A',
                                            'TrangThaiLamViec': 'Đang làm việc'}, follow_redirects=True)
    r = toan_quyen.post('/nhansu/NV01/phan-cong/them', data={'MaHangMuc': 'HM01'}, follow_redirects=True)
    assert 'hạng mục con' in r.data.decode('utf-8').lower()


def test_chan_phan_cong_nhan_su_khong_dang_lam_viec(toan_quyen):
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/nhansu/them', data={'MaNV': 'NV01', 'TenNV': 'Văn A',
                                            'TrangThaiLamViec': 'Đã nghỉ việc'}, follow_redirects=True)
    r = toan_quyen.post('/nhansu/NV01/phan-cong/them', data={'MaHangMuc': 'HM02'}, follow_redirects=True)
    assert 'đang làm việc' in r.data.decode('utf-8').lower()


def test_chan_trung_lich(toan_quyen, app):
    tao_hang_muc_goc_va_con(toan_quyen, ma_con='HM02')
    toan_quyen.post('/hangmuc/them', data={'MaHangMuc': 'HM03', 'TenHangMuc': 'Hạng mục khác',
                                             'HangMucCha': 'HM01'}, follow_redirects=True)
    toan_quyen.post('/nhansu/them', data={'MaNV': 'NV01', 'TenNV': 'Văn A',
                                            'TrangThaiLamViec': 'Đang làm việc'}, follow_redirects=True)
    toan_quyen.post('/nhansu/NV01/phan-cong/them', data={
        'MaHangMuc': 'HM02', 'NgayBatDau': '2026-01-01', 'NgayKetThuc': '2026-01-10'
    }, follow_redirects=True)
    # phân công thứ 2 chồng lấn ngày -> phải bị chặn
    r = toan_quyen.post('/nhansu/NV01/phan-cong/them', data={
        'MaHangMuc': 'HM03', 'NgayBatDau': '2026-01-05', 'NgayKetThuc': '2026-01-15'
    }, follow_redirects=True)
    assert 'trùng khoảng thời gian' in r.data.decode('utf-8').lower()
    with app.app_context():
        from app.models import PhanCong
        assert PhanCong.query.count() == 1


def test_them_ngay_cong_vuot_so_ngay_lich_bi_chan(toan_quyen, app):
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/nhansu/them', data={'MaNV': 'NV01', 'TenNV': 'Văn A',
                                            'TrangThaiLamViec': 'Đang làm việc'}, follow_redirects=True)
    toan_quyen.post('/nhansu/NV01/phan-cong/them', data={
        'MaHangMuc': 'HM02', 'NgayBatDau': '2026-01-01', 'NgayKetThuc': '2026-01-05', 'SoNgayCong': '3'
    }, follow_redirects=True)
    with app.app_context():
        from app.models import PhanCong
        ma_pc = PhanCong.query.filter_by(nhansu_MaNV='NV01').first().MaPhanCong

    # khoang 2026-01-01 -> 2026-01-05 co toi da 5 ngay, da co 3, them 5 nua la 8 -> vuot
    r = toan_quyen.post(f'/nhansu/phan-cong/{ma_pc}/them-ngay-cong', data={'SoNgayThem': '5'},
                         follow_redirects=True)
    assert 'vượt quá số lượng tối đa' in r.data.decode('utf-8').lower()

    with app.app_context():
        from app.models import PhanCong
        pc = PhanCong.query.get(ma_pc)
        assert pc.SoNgayCong == 3  # không đổi


def test_them_ngay_cong_hop_le_cong_don(toan_quyen, app):
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/nhansu/them', data={'MaNV': 'NV01', 'TenNV': 'Văn A',
                                            'TrangThaiLamViec': 'Đang làm việc'}, follow_redirects=True)
    toan_quyen.post('/nhansu/NV01/phan-cong/them', data={'MaHangMuc': 'HM02', 'SoNgayCong': '3'},
                     follow_redirects=True)
    with app.app_context():
        from app.models import PhanCong
        ma_pc = PhanCong.query.filter_by(nhansu_MaNV='NV01').first().MaPhanCong

    toan_quyen.post(f'/nhansu/phan-cong/{ma_pc}/them-ngay-cong', data={'SoNgayThem': '2'},
                     follow_redirects=True)
    with app.app_context():
        from app.models import PhanCong
        pc = PhanCong.query.get(ma_pc)
        assert pc.SoNgayCong == 5


def test_thanh_tien_tinh_lai_sau_khi_them_ngay_cong(toan_quyen, app):
    """LỖI ĐÃ SỬA: trước đây Thành tiền luôn tính theo khoảng ngày bắt đầu -
    kết thúc, bỏ qua hẳn `SoNgayCong` - nên bấm "+ Công" không làm Thành
    tiền thay đổi chút nào. Giờ `SoNgayCong` là số liệu chính thức để tính
    tiền, nên Thành tiền phải tự cập nhật đúng sau mỗi lần cộng dồn."""
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/nhansu/them', data={'MaNV': 'NV01', 'TenNV': 'Văn A',
                                            'TrangThaiLamViec': 'Đang làm việc'}, follow_redirects=True)
    toan_quyen.post('/nhansu/NV01/phan-cong/them', data={
        'MaHangMuc': 'HM02', 'NgayBatDau': '2026-01-01', 'NgayKetThuc': '2026-01-10',
        'SoNgayCong': '3', 'ChiphiThue': '100000', 'DonViTinh': 'ngày',
    }, follow_redirects=True)
    with app.app_context():
        from app.models import PhanCong
        from app.modules.nhansu import service
        pc = PhanCong.query.filter_by(nhansu_MaNV='NV01').first()
        ma_pc = pc.MaPhanCong
        assert service.thanh_tien_phan_cong(pc) == 300000  # 3 ngày x 100.000

    toan_quyen.post(f'/nhansu/phan-cong/{ma_pc}/them-ngay-cong', data={'SoNgayThem': '2'},
                     follow_redirects=True)
    with app.app_context():
        from app.models import PhanCong
        from app.modules.nhansu import service
        pc = PhanCong.query.get(ma_pc)
        assert pc.SoNgayCong == 5
        assert service.thanh_tien_phan_cong(pc) == 500000  # phải tính lại: 5 ngày x 100.000


def test_thanh_tien_theo_don_vi_thang_khong_quy_doi_qua_ngay(toan_quyen, app):
    """Khi `DonViTinh` = 'tháng', `SoNgayCong` là số THÁNG công (không phải
    số ngày) - Thành tiền = SoNgayCong x đơn giá/tháng trực tiếp, không quy
    đổi qua ngày lịch (khoảng ngày chỉ dùng để giới hạn mức tối đa được
    phép cộng thêm ở `them_ngay_cong`, không dùng để tính tiền)."""
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/nhansu/them', data={'MaNV': 'NV02', 'TenNV': 'Thị B',
                                            'TrangThaiLamViec': 'Đang làm việc'}, follow_redirects=True)
    toan_quyen.post('/nhansu/NV02/phan-cong/them', data={
        'MaHangMuc': 'HM02', 'NgayBatDau': '2026-01-01', 'NgayKetThuc': '2026-06-30',
        'SoNgayCong': '2', 'ChiphiThue': '1000000', 'DonViTinh': 'tháng',
    }, follow_redirects=True)
    with app.app_context():
        from app.models import PhanCong
        from app.modules.nhansu import service
        pc = PhanCong.query.filter_by(nhansu_MaNV='NV02').first()
        # 2 tháng x 1.000.000 = 2.000.000 - KHÔNG phải quy đổi ~181 ngày lịch
        assert service.thanh_tien_phan_cong(pc) == 2000000


def test_them_ngay_cong_don_vi_thang_gioi_han_dung_theo_thang(toan_quyen, app):
    """Giới hạn "+Công" phải quy đổi đúng đơn vị: khoảng 2026-01-01 ->
    2026-03-02 (61 ngày) với đơn vị THÁNG tối đa quy đổi được là 3 tháng
    ((61+29)//30 = 3) - cộng thêm cho tổng vượt quá 3 tháng phải bị chặn,
    KHÔNG được so nhầm trực tiếp với 61 (số ngày lịch)."""
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/nhansu/them', data={'MaNV': 'NV03', 'TenNV': 'Văn C',
                                            'TrangThaiLamViec': 'Đang làm việc'}, follow_redirects=True)
    toan_quyen.post('/nhansu/NV03/phan-cong/them', data={
        'MaHangMuc': 'HM02', 'NgayBatDau': '2026-01-01', 'NgayKetThuc': '2026-03-02',
        'SoNgayCong': '2', 'DonViTinh': 'tháng',
    }, follow_redirects=True)
    with app.app_context():
        from app.models import PhanCong
        ma_pc = PhanCong.query.filter_by(nhansu_MaNV='NV03').first().MaPhanCong

    r = toan_quyen.post(f'/nhansu/phan-cong/{ma_pc}/them-ngay-cong', data={'SoNgayThem': '2'},
                         follow_redirects=True)
    assert 'vượt quá số lượng tối đa' in r.data.decode('utf-8').lower()
    with app.app_context():
        from app.models import PhanCong
        assert PhanCong.query.get(ma_pc).SoNgayCong == 2  # không đổi


def test_chan_tinh_tien_khi_thieu_mot_moc_thoi_gian(toan_quyen):
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/nhansu/them', data={'MaNV': 'NV01', 'TenNV': 'Văn A',
                                            'TrangThaiLamViec': 'Đang làm việc'}, follow_redirects=True)
    r = toan_quyen.post('/nhansu/NV01/phan-cong/them', data={
        'MaHangMuc': 'HM02', 'NgayBatDau': '2026-01-01', 'ChiphiThue': '150000',
        'DonViTinh': 'tháng'
    }, follow_redirects=True)
    assert 'đầy đủ cả ngày bắt đầu và ngày kết thúc' in r.data.decode('utf-8').lower()


def test_khong_nhap_so_ngay_cong_tu_dong_tinh_theo_ngay(toan_quyen, app):
    """Không nhập SoNgayCong nhưng có đủ NgayBatDau/NgayKetThuc -> hệ thống
    tự tính SoNgayCong từ khoảng ngày đó theo DonViTinh, thay vì để trống."""
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/nhansu/them', data={'MaNV': 'NV01', 'TenNV': 'Văn A',
                                            'TrangThaiLamViec': 'Đang làm việc'}, follow_redirects=True)
    toan_quyen.post('/nhansu/NV01/phan-cong/them', data={
        'MaHangMuc': 'HM02', 'NgayBatDau': '2026-01-01', 'NgayKetThuc': '2026-01-05',
        'DonViTinh': 'ngày',
    }, follow_redirects=True)
    with app.app_context():
        from app.models import PhanCong
        pc = PhanCong.query.filter_by(nhansu_MaNV='NV01').first()
        assert pc.SoNgayCong == 5  # 2026-01-01 -> 2026-01-05: 5 ngày


def test_khong_nhap_so_ngay_cong_tu_dong_tinh_theo_thang(toan_quyen, app):
    """Tương tự nhưng DonViTinh = 'tháng' - phải quy đổi đúng đơn vị tháng,
    không lấy thẳng số ngày lịch."""
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/nhansu/them', data={'MaNV': 'NV02', 'TenNV': 'Thị B',
                                            'TrangThaiLamViec': 'Đang làm việc'}, follow_redirects=True)
    toan_quyen.post('/nhansu/NV02/phan-cong/them', data={
        'MaHangMuc': 'HM02', 'NgayBatDau': '2026-01-01', 'NgayKetThuc': '2026-03-02',
        'DonViTinh': 'tháng',
    }, follow_redirects=True)
    with app.app_context():
        from app.models import PhanCong
        pc = PhanCong.query.filter_by(nhansu_MaNV='NV02').first()
        assert pc.SoNgayCong == 3  # (61 ngày + 29) // 30 = 3 tháng


def test_them_phan_cong_so_ngay_cong_vuot_khoang_ngay_bi_chan(toan_quyen):
    """Khác với test_them_ngay_cong_vuot_so_ngay_lich_bi_chan (chặn ở bước
    '+ Công'): đây là chặn ngay từ lúc THÊM MỚI phân công, nếu SoNgayCong
    nhập vào đã vượt quá mức tối đa quy đổi từ khoảng ngày ngay từ đầu."""
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/nhansu/them', data={'MaNV': 'NV01', 'TenNV': 'Văn A',
                                            'TrangThaiLamViec': 'Đang làm việc'}, follow_redirects=True)
    r = toan_quyen.post('/nhansu/NV01/phan-cong/them', data={
        'MaHangMuc': 'HM02', 'NgayBatDau': '2026-01-01', 'NgayKetThuc': '2026-01-05',
        'SoNgayCong': '10', 'DonViTinh': 'ngày',
    }, follow_redirects=True)
    assert 'vượt quá số lượng tối đa' in r.data.decode('utf-8').lower()


def test_chan_xoa_nhan_su_con_phan_cong(toan_quyen):
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/nhansu/them', data={'MaNV': 'NV01', 'TenNV': 'Văn A',
                                            'TrangThaiLamViec': 'Đang làm việc'}, follow_redirects=True)
    toan_quyen.post('/nhansu/NV01/phan-cong/them', data={'MaHangMuc': 'HM02'}, follow_redirects=True)
    r = toan_quyen.post('/nhansu/xoa/NV01', follow_redirects=True)
    assert 'không thể xóa' in r.data.decode('utf-8').lower()
