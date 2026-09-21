"""Test module Hạng mục: cây cha/con, chặn vòng lặp, chặn xóa khi còn phụ
thuộc, validate ngân sách đang có (bug đã sửa: nhập chữ/số âm từng gây lỗi
500 thô thay vì thông báo thân thiện)."""

from conftest import tao_hang_muc_goc_va_con


def test_tao_hang_muc_goc_tu_tro_vao_chinh_no(toan_quyen, app):
    toan_quyen.post('/hangmuc/them', data={'MaHangMuc': 'HM01', 'TenHangMuc': 'Công trình A'},
                     follow_redirects=True)
    with app.app_context():
        from app.models import HangMuc
        hm = HangMuc.query.get('HM01')
        assert hm is not None
        assert hm.hangmuc_MaHangMuc == 'HM01'  # tự trỏ vào chính nó = hạng mục gốc


def test_tao_hang_muc_con(toan_quyen, app):
    tao_hang_muc_goc_va_con(toan_quyen)
    with app.app_context():
        from app.models import HangMuc
        con = HangMuc.query.get('HM02')
        assert con.hangmuc_MaHangMuc == 'HM01'


def test_chan_vong_lap_cha_con(toan_quyen):
    tao_hang_muc_goc_va_con(toan_quyen)
    # thử chọn HM02 (con) làm cha của chính HM01 (cha của nó) -> vòng lặp
    r = toan_quyen.post('/hangmuc/sua/HM01', data={'TenHangMuc': 'Công trình A', 'HangMucCha': 'HM02'})
    assert 'vòng lặp' in r.data.decode('utf-8').lower()


def test_chan_xoa_hang_muc_con_hang_muc_con(toan_quyen):
    tao_hang_muc_goc_va_con(toan_quyen)
    r = toan_quyen.post('/hangmuc/xoa/HM01', follow_redirects=True)
    assert 'không thể xóa' in r.data.decode('utf-8').lower()


def test_xoa_hang_muc_khong_con_phu_thuoc_thanh_cong(toan_quyen, app):
    toan_quyen.post('/hangmuc/them', data={'MaHangMuc': 'HM01', 'TenHangMuc': 'Công trình A'},
                     follow_redirects=True)
    toan_quyen.post('/hangmuc/xoa/HM01', follow_redirects=True)
    with app.app_context():
        from app.models import HangMuc
        assert HangMuc.query.get('HM01') is None


# ---- Validate ngân sách đang có (bug đã sửa) ----

def test_ngan_sach_khong_phai_so_bi_chan_khong_crash(toan_quyen):
    r = toan_quyen.post('/hangmuc/them',
                         data={'MaHangMuc': 'HMX', 'TenHangMuc': 'Test', 'NganSachDangCo': 'abc'})
    assert r.status_code == 200  # không phải 500
    assert 'không hợp lệ' in r.data.decode('utf-8').lower()


def test_ngan_sach_am_bi_chan(toan_quyen):
    r = toan_quyen.post('/hangmuc/them',
                         data={'MaHangMuc': 'HMX', 'TenHangMuc': 'Test', 'NganSachDangCo': '-500'})
    assert 'không được âm' in r.data.decode('utf-8').lower()


def test_ngan_sach_bo_trong_van_tao_duoc(toan_quyen, app):
    toan_quyen.post('/hangmuc/them', data={'MaHangMuc': 'HM01', 'TenHangMuc': 'Công trình A'},
                     follow_redirects=True)
    with app.app_context():
        from app.models import HangMuc
        hm = HangMuc.query.get('HM01')
        assert hm.NganSachDangCo is None


def test_ngan_sach_hop_le_luu_dung_gia_tri(toan_quyen, app):
    toan_quyen.post('/hangmuc/them', data={'MaHangMuc': 'HM01', 'TenHangMuc': 'Công trình A',
                                             'NganSachDangCo': '1000000'}, follow_redirects=True)
    with app.app_context():
        from app.models import HangMuc
        hm = HangMuc.query.get('HM01')
        assert float(hm.NganSachDangCo) == 1000000.0

    def test_cong_ngan_sach_dang_co(toan_quyen, app):
        toan_quyen.post('/hangmuc/them', data={
            'MaHangMuc': 'HM01', 'TenHangMuc': 'Công trình A', 'NganSachDangCo': '500000'
        }, follow_redirects=True)
        r = toan_quyen.post('/hangmuc/HM01/them-ngan-sach', data={
            'SoTienNganSach': '200000'
        }, follow_redirects=True)
        assert 'cộng thêm ngân sách' in r.data.decode('utf-8').lower()
        with app.app_context():
            from app.models import HangMuc
            assert float(HangMuc.query.get('HM01').NganSachDangCo) == 700000.0


def test_sua_hang_muc_voi_ngan_sach_sai_khong_lam_hong_du_lieu_cu(toan_quyen, app):
    toan_quyen.post('/hangmuc/them', data={'MaHangMuc': 'HM01', 'TenHangMuc': 'Công trình A',
                                             'NganSachDangCo': '1000000'}, follow_redirects=True)
    toan_quyen.post('/hangmuc/sua/HM01', data={'TenHangMuc': 'Công trình A', 'NganSachDangCo': 'xyz'})
    with app.app_context():
        from app.models import HangMuc
        hm = HangMuc.query.get('HM01')
        # LoiNghiepVu raise TRƯỚC khi gán vào entity -> giá trị cũ không đổi
        assert float(hm.NganSachDangCo) == 1000000.0


# ---- Ngày khởi công / ngày dự kiến hoàn thành ----

def test_ngay_hoan_thanh_du_kien_truoc_ngay_khoi_cong_bi_chan(toan_quyen):
    r = toan_quyen.post('/hangmuc/them', data={
        'MaHangMuc': 'HM01', 'TenHangMuc': 'Công trình A',
        'NgayKhoiCong': '2026-09-04', 'ThoiGianHoanThanhDuKien': '2026-08-11',
    })
    assert 'không được trước ngày khởi công' in r.data.decode('utf-8').lower()


def test_ngay_hoan_thanh_du_kien_hop_le_luu_duoc(toan_quyen, app):
    toan_quyen.post('/hangmuc/them', data={
        'MaHangMuc': 'HM01', 'TenHangMuc': 'Công trình A',
        'NgayKhoiCong': '2026-08-11', 'ThoiGianHoanThanhDuKien': '2026-09-04',
    }, follow_redirects=True)
    with app.app_context():
        from app.models import HangMuc
        hm = HangMuc.query.get('HM01')
        assert hm.NgayKhoiCong.isoformat() == '2026-08-11'
        assert hm.ThoiGianHoanThanhDuKien.isoformat() == '2026-09-04'


def test_chi_1_trong_2_ngay_khong_bi_chan(toan_quyen, app):
    """Chỉ khai báo 1 trong 2 ngày (cột kia còn để trống) thì không có gì để
    so sánh - không bị chặn."""
    toan_quyen.post('/hangmuc/them', data={
        'MaHangMuc': 'HM01', 'TenHangMuc': 'Công trình A',
        'NgayKhoiCong': '2026-09-04',
    }, follow_redirects=True)
    with app.app_context():
        from app.models import HangMuc
        hm = HangMuc.query.get('HM01')
        assert hm.NgayKhoiCong.isoformat() == '2026-09-04'
        assert hm.ThoiGianHoanThanhDuKien is None


def test_sua_ngay_hoan_thanh_du_kien_truoc_ngay_khoi_cong_bi_chan(toan_quyen, app):
    toan_quyen.post('/hangmuc/them', data={
        'MaHangMuc': 'HM01', 'TenHangMuc': 'Công trình A',
        'NgayKhoiCong': '2026-08-11', 'ThoiGianHoanThanhDuKien': '2026-09-04',
    }, follow_redirects=True)
    r = toan_quyen.post('/hangmuc/sua/HM01', data={
        'TenHangMuc': 'Công trình A',
        'NgayKhoiCong': '2026-09-04', 'ThoiGianHoanThanhDuKien': '2026-08-11',
    })
    assert 'không được trước ngày khởi công' in r.data.decode('utf-8').lower()
    with app.app_context():
        from app.models import HangMuc
        hm = HangMuc.query.get('HM01')
        # LoiNghiepVu raise TRƯỚC khi gán vào entity -> giá trị cũ không đổi
        assert hm.NgayKhoiCong.isoformat() == '2026-08-11'
        assert hm.ThoiGianHoanThanhDuKien.isoformat() == '2026-09-04'


# ---- Phân quyền ----

def test_vai_tro_tra_cuu_khong_them_duoc(tra_cuu):
    r = tra_cuu.post('/hangmuc/them', data={'MaHangMuc': 'HM01', 'TenHangMuc': 'Công trình A'},
                      follow_redirects=True)
    assert 'chỉ có quyền tra cứu' in r.data.decode('utf-8').lower()


def test_chua_chon_vai_tro_bi_chuyen_huong(client):
    r = client.get('/hangmuc/')
    assert r.status_code == 302
    assert '/vai-tro' in r.headers['Location']
