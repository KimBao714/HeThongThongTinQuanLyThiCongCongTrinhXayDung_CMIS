"""Test module Vật liệu (đã gộp Sử dụng vật liệu): chỉ ghi nhận vào hạng
mục con, chặn trùng cặp khóa, chặn xóa khi còn phụ thuộc, validate số lượng
đang có/đơn giá (bug đã sửa)."""

from conftest import tao_hang_muc_goc_va_con


def test_them_vat_lieu(toan_quyen, app):
    toan_quyen.post('/vatlieu/them', data={'MaVL': 'VL01', 'TenVL': 'Xi măng',
                                             'SoLuongDangCo': '100', 'DonGia': '90000'},
                     follow_redirects=True)
    with app.app_context():
        from app.models import VatLieu
        vl = VatLieu.query.get('VL01')
        assert vl is not None
        assert float(vl.SoLuongDangCo) == 100.0


def test_chan_ghi_nhan_su_dung_vao_hang_muc_goc(toan_quyen, app):
    toan_quyen.post('/hangmuc/them', data={'MaHangMuc': 'HM01', 'TenHangMuc': 'Công trình A'},
                     follow_redirects=True)
    toan_quyen.post('/vatlieu/them', data={'MaVL': 'VL01', 'TenVL': 'Xi măng'}, follow_redirects=True)

    r = toan_quyen.post('/vatlieu/VL01/su-dung/them', data={'MaHangMuc': 'HM01', 'SoLuongSD': '10'},
                         follow_redirects=True)
    assert 'hạng mục con' in r.data.decode('utf-8').lower()
    with app.app_context():
        from app.models import SuDungVatLieu
        assert SuDungVatLieu.query.count() == 0


def test_ghi_nhan_su_dung_vao_hang_muc_con_thanh_cong(toan_quyen, app):
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/vatlieu/them', data={'MaVL': 'VL01', 'TenVL': 'Xi măng'}, follow_redirects=True)
    r = toan_quyen.post('/vatlieu/VL01/su-dung/them', data={'MaHangMuc': 'HM02', 'SoLuongSD': '10'},
                         follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        from app.models import SuDungVatLieu
        assert SuDungVatLieu.query.count() == 1


def test_trung_cap_vat_lieu_hang_muc_tu_cong_don(toan_quyen, app):
    """Gửi lại đúng cặp (vật liệu, hạng mục) đã có sẵn -> TỰ CỘNG DỒN số
    lượng vào dòng cũ (UPDATE), không tạo dòng mới - đúng theo README mục
    6d và docstring của service.them_su_dung."""
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/vatlieu/them', data={'MaVL': 'VL01', 'TenVL': 'Xi măng'}, follow_redirects=True)
    toan_quyen.post('/vatlieu/VL01/su-dung/them', data={'MaHangMuc': 'HM02', 'SoLuongSD': '10'},
                     follow_redirects=True)
    toan_quyen.post('/vatlieu/VL01/su-dung/them', data={'MaHangMuc': 'HM02', 'SoLuongSD': '5'},
                     follow_redirects=True)
    with app.app_context():
        from app.models import SuDungVatLieu
        sd = SuDungVatLieu.query.get(('VL01', 'HM02'))
        assert float(sd.SoLuongSD) == 15.0  # 10 + 5 cộng dồn, không tạo dòng mới
        assert SuDungVatLieu.query.count() == 1


def test_sua_so_luong_su_dung_cong_don(toan_quyen, app):
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/vatlieu/them', data={'MaVL': 'VL01', 'TenVL': 'Xi măng'}, follow_redirects=True)
    toan_quyen.post('/vatlieu/VL01/su-dung/them', data={'MaHangMuc': 'HM02', 'SoLuongSD': '10'},
                     follow_redirects=True)
    toan_quyen.post('/vatlieu/VL01/su-dung/HM02/sua', data={'SoLuongSD': '25'}, follow_redirects=True)
    with app.app_context():
        from app.models import SuDungVatLieu
        sd = SuDungVatLieu.query.get(('VL01', 'HM02'))
        assert float(sd.SoLuongSD) == 25.0


def test_chan_xoa_vat_lieu_con_dang_su_dung(toan_quyen):
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/vatlieu/them', data={'MaVL': 'VL01', 'TenVL': 'Xi măng'}, follow_redirects=True)
    toan_quyen.post('/vatlieu/VL01/su-dung/them', data={'MaHangMuc': 'HM02', 'SoLuongSD': '10'},
                     follow_redirects=True)
    r = toan_quyen.post('/vatlieu/xoa/VL01', follow_redirects=True)
    assert 'không thể xóa' in r.data.decode('utf-8').lower()


def test_danh_sach_vuot_du_kien(toan_quyen, app):
    tao_hang_muc_goc_va_con(toan_quyen)
    toan_quyen.post('/vatlieu/them', data={'MaVL': 'VL01', 'TenVL': 'Xi măng', 'SoLuongDangCo': '50'},
                     follow_redirects=True)
    toan_quyen.post('/vatlieu/VL01/su-dung/them', data={'MaHangMuc': 'HM02', 'SoLuongSD': '80'},
                     follow_redirects=True)
    with app.app_context():
        from app.modules.vatlieu import service
        ket_qua = service.danh_sach_vuot_du_kien()
        assert len(ket_qua) == 1
        assert ket_qua[0]['item'].MaVL == 'VL01'
        assert ket_qua[0]['phan_tram'] == 160.0


# ---- Validate số lượng đang có / đơn giá (bug đã sửa) ----

def test_so_luong_du_kien_khong_phai_so_bi_chan(toan_quyen):
    r = toan_quyen.post('/vatlieu/them', data={'MaVL': 'VLX', 'TenVL': 'Test', 'SoLuongDangCo': 'xyz'})
    assert r.status_code == 200
    assert 'không hợp lệ' in r.data.decode('utf-8').lower()


def test_don_gia_am_bi_chan(toan_quyen):
    r = toan_quyen.post('/vatlieu/them', data={'MaVL': 'VLX', 'TenVL': 'Test', 'DonGia': '-100'})
    assert 'không được âm' in r.data.decode('utf-8').lower()
