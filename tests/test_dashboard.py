"""Test module Dashboard tổng quan: chỉ đọc, tái sử dụng logic module gốc
(không tính lại), hoạt động đúng kể cả khi CSDL rỗng."""

import io
from datetime import date, timedelta

from conftest import tao_hang_muc_goc_va_con


def test_dashboard_rong_khong_loi(toan_quyen):
    r = toan_quyen.get('/dashboard/')
    assert r.status_code == 200


def test_dashboard_hien_thi_hang_muc_vuot_ngan_sach(toan_quyen):
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/hangmuc/sua/HM01', data={'TenHangMuc': 'Công trình A', 'NganSachDangCo': '100'},
                     follow_redirects=True)
    toan_quyen.post('/nhansu/them', data={'MaNV': 'NV01', 'TenNV': 'Văn A',
                                            'TrangThaiLamViec': 'Đang làm việc'}, follow_redirects=True)
    toan_quyen.post('/nhansu/NV01/phan-cong/them', data={'MaHangMuc': 'HM02', 'SoNgayCong': '5',
                                                            'ChiphiThue': '1000000'}, follow_redirects=True)
    toan_quyen.post('/vatlieu/them', data={'MaVL': 'VL01', 'TenVL': 'Xi măng', 'DonGia': '1'},
                    follow_redirects=True)
    toan_quyen.post('/vatlieu/VL01/su-dung/them', data={'MaHangMuc': 'HM02', 'SoLuongSD': '1'},
                    follow_redirects=True)
    with toan_quyen.application.app_context():
        from app.models import PhanCong
        ma_pc = PhanCong.query.filter_by(nhansu_MaNV='NV01').first().MaPhanCong
    toan_quyen.post('/chiphi/them', data={
        'MaCP': 'CP01', 'LoaiChiPhi': 'Khác', 'NgayChi': date.today().isoformat(),
        'SoTienChi': '101', 'MaHangMuc': 'HM02', 'MaPhanCong': ma_pc, 'MaVatLieu': 'VL01',
    }, follow_redirects=True)
    r = toan_quyen.get('/dashboard/')
    text = r.data.decode('utf-8')
    assert 'Công trình A' in text
    assert 'Hạng mục vượt ngân sách' in text


def test_dashboard_hien_thi_vat_lieu_vuot_du_kien(toan_quyen):
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/vatlieu/them', data={'MaVL': 'VL01', 'TenVL': 'Xi măng', 'SoLuongDangCo': '50'},
                     follow_redirects=True)
    toan_quyen.post('/vatlieu/VL01/su-dung/them', data={'MaHangMuc': 'HM02', 'SoLuongSD': '80'},
                     follow_redirects=True)
    r = toan_quyen.get('/dashboard/')
    text = r.data.decode('utf-8')
    assert 'Xi măng' in text
    assert 'vượt số lượng đang có' in text.lower()


def test_dashboard_hien_thi_ban_ve_chua_co_phien_ban_chinh_thuc(toan_quyen):
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/banve/them', data={
        'MaBV': 'BV01', 'TenBV': 'Bản vẽ móng', 'MaHangMuc': 'HM02',
        'HoNguoiTao': 'Nguyễn', 'TenNguoiTao': 'Văn A',
        'file_ban_ve': (io.BytesIO(b'noi dung'), 'v1.pdf'),
    }, content_type='multipart/form-data', follow_redirects=True)
    r = toan_quyen.get('/dashboard/')
    text = r.data.decode('utf-8')
    assert 'Bản vẽ móng' in text
    assert 'chưa có phiên bản chính thức' in text.lower()


def test_dashboard_hien_thi_hang_muc_tre_tien_do(toan_quyen):
    qua_han = (date.today() - timedelta(days=3)).isoformat()
    toan_quyen.post('/hangmuc/them', data={'MaHangMuc': 'HM01', 'TenHangMuc': 'Công trình A',
                                             'ThoiGianHoanThanhDuKien': qua_han}, follow_redirects=True)
    r = toan_quyen.get('/dashboard/')
    text = r.data.decode('utf-8')
    assert 'Công trình A' in text
    assert 'trễ tiến độ' in text.lower()


def test_dashboard_khong_hien_thi_canh_bao_khi_du_lieu_binh_thuong(toan_quyen):
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/hangmuc/sua/HM01', data={'TenHangMuc': 'Công trình A', 'NganSachDangCo': '1000000'},
                     follow_redirects=True)
    r = toan_quyen.get('/dashboard/')
    text = r.data.decode('utf-8')
    assert 'chưa có hạng mục nào vượt ngân sách' in text.lower()


def test_dashboard_lam_moi_tra_ve_fragment_hop_le(toan_quyen):
    """Route /dashboard/lam-moi (dùng cho JS polling) phải trả về đúng 1
    fragment HTML - có đủ khối dữ liệu biểu đồ nhúng kèm (script
    #dashboard-live-data) để static/js/dashboard.js đọc lại vẽ Chart.js,
    và KHÔNG bọc trong layout đầy đủ (không có thẻ <html>/sidebar)."""
    r = toan_quyen.get('/dashboard/lam-moi')
    text = r.data.decode('utf-8')
    assert r.status_code == 200
    assert 'id="dashboard-live-data"' in text
    assert '<html' not in text.lower()


def test_dashboard_lam_moi_phan_anh_du_lieu_moi_nhat(toan_quyen):
    """Gọi /dashboard/lam-moi PHẢI thấy được dữ liệu vừa mới tạo (mô phỏng
    đúng luồng polling thật: JS gọi lại route này định kỳ để lấy số liệu
    MỚI từ CSDL, không phải số liệu đã cache từ lần tải trang trước đó)."""
    text_truoc = toan_quyen.get('/dashboard/lam-moi').data.decode('utf-8')
    assert 'Công trình trễ tiến độ demo' not in text_truoc

    qua_han = (date.today() - timedelta(days=3)).isoformat()
    toan_quyen.post('/hangmuc/them', data={
        'MaHangMuc': 'HM09', 'TenHangMuc': 'Công trình trễ tiến độ demo',
        'ThoiGianHoanThanhDuKien': qua_han,
    }, follow_redirects=True)

    text_sau = toan_quyen.get('/dashboard/lam-moi').data.decode('utf-8')
    assert 'Công trình trễ tiến độ demo' in text_sau


def test_dashboard_lam_moi_khong_bi_cache(toan_quyen):
    """Cả trang chính lẫn fragment polling đều phải có header chống cache -
    nếu không, trình duyệt/proxy có thể trả lại 1 bản HTML cũ và tính năng
    cập nhật thời gian thực sẽ không có tác dụng thật sự."""
    r = toan_quyen.get('/dashboard/lam-moi')
    assert 'no-store' in r.headers.get('Cache-Control', '')


def test_dashboard_chu_thich_phien_ban_du_ca_4_trang_thai(toan_quyen, app):
    """LỖI ĐÃ SỬA: bảng tra cứu `trangthaiphienban` có 4 trạng thái cố định
    (Chờ duyệt/Đã duyệt/Từ chối/Cũ - xem banve/repository.py), không phải 3.
    Khi 1 phiên bản mới được duyệt, phiên bản Đã duyệt trước đó tự chuyển
    sang "Cũ" - nên chú thích màu trên Dashboard PHẢI có đủ nhãn "Cũ",
    nếu không người xem sẽ thấy 1 lát cắt màu xám trong biểu đồ mà không
    biết nó đại diện cho trạng thái gì."""
    toan_quyen.post('/hangmuc/them', data={'MaHangMuc': 'HM10', 'TenHangMuc': 'Công trình test phiên bản'},
                     follow_redirects=True)
    toan_quyen.post('/banve/them', data={
        'MaBV': 'BV10', 'TenBV': 'Bản vẽ test', 'MaHangMuc': 'HM10',
        'HoNguoiTao': 'Nguyễn', 'TenNguoiTao': 'Văn A',
        'file_ban_ve': (io.BytesIO(b'v1'), 'v1.pdf'),
    }, content_type='multipart/form-data', follow_redirects=True)
    with app.app_context():
        from app.models import PhienBan
        pb_v1 = PhienBan.query.filter_by(banve_MaBV='BV10').first()
        ma_v1 = pb_v1.MaPB
    toan_quyen.post(f'/banve/phien-ban/{ma_v1}/duyet', follow_redirects=True)

    toan_quyen.post('/banve/BV10/phien-ban/them', data={
        'HoNguoiTao': 'Trần', 'TenNguoiTao': 'Thị B',
        'file_ban_ve': (io.BytesIO(b'v2'), 'v2.pdf'),
    }, content_type='multipart/form-data', follow_redirects=True)
    with app.app_context():
        from app.models import PhienBan
        pb_v2 = PhienBan.query.filter_by(banve_MaBV='BV10', SoPhienBan='2').first()
        ma_v2 = pb_v2.MaPB
    toan_quyen.post(f'/banve/phien-ban/{ma_v2}/duyet', follow_redirects=True)

    with app.app_context():
        from app.models import PhienBan
        assert PhienBan.query.get(ma_v1).trangthaiphienban_MaTrangThai == 'CU'

    text = toan_quyen.get('/dashboard/').data.decode('utf-8')
    assert '>Cũ<' in text  # chú thích màu phải liệt kê đủ, không chỉ 3/4 trạng thái
