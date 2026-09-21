"""Test module Chi phí: bắt buộc chọn phân công + sử dụng vật liệu đã có
sẵn, nhất quán hạng mục giữa 3 nơi, ngày chi không ở tương lai, so sánh
ngân sách đang có vs đã sử dụng."""

from datetime import date, timedelta

from conftest import tao_hang_muc_goc_va_con


def _chuan_bi_phan_cong_va_su_dung_vat_lieu(client):
    tao_hang_muc_goc_va_con(client)
    client.post('/nhansu/them', data={'MaNV': 'NV01', 'TenNV': 'Văn A',
                                        'TrangThaiLamViec': 'Đang làm việc'}, follow_redirects=True)
    client.post('/nhansu/NV01/phan-cong/them', data={'MaHangMuc': 'HM02', 'SoNgayCong': '5',
                                                        'ChiphiThue': '100000'}, follow_redirects=True)
    client.post('/vatlieu/them', data={'MaVL': 'VL01', 'TenVL': 'Xi măng', 'DonGia': '90000'},
                follow_redirects=True)
    client.post('/vatlieu/VL01/su-dung/them', data={'MaHangMuc': 'HM02', 'SoLuongSD': '10'},
                follow_redirects=True)


def test_them_chi_phi_hop_le(toan_quyen, app):
    _chuan_bi_phan_cong_va_su_dung_vat_lieu(toan_quyen)
    with app.app_context():
        from app.models import PhanCong
        ma_pc = PhanCong.query.filter_by(nhansu_MaNV='NV01').first().MaPhanCong

    r = toan_quyen.post('/chiphi/them', data={
        'MaCP': 'CP01', 'LoaiChiPhi': 'Vật liệu', 'NgayChi': date.today().isoformat(),
        'SoTienChi': '500000', 'MaHangMuc': 'HM02', 'MaPhanCong': ma_pc, 'MaVatLieu': 'VL01',
    }, follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        from app.models import ChiPhi
        assert ChiPhi.query.count() == 1


def test_chan_ngay_chi_trong_tuong_lai(toan_quyen, app):
    _chuan_bi_phan_cong_va_su_dung_vat_lieu(toan_quyen)
    with app.app_context():
        from app.models import PhanCong
        ma_pc = PhanCong.query.filter_by(nhansu_MaNV='NV01').first().MaPhanCong

    ngay_mai = (date.today() + timedelta(days=1)).isoformat()
    r = toan_quyen.post('/chiphi/them', data={
        'MaCP': 'CP01', 'LoaiChiPhi': 'Vật liệu', 'NgayChi': ngay_mai,
        'SoTienChi': '500000', 'MaHangMuc': 'HM02', 'MaPhanCong': ma_pc, 'MaVatLieu': 'VL01',
    }, follow_redirects=True)
    assert 'tương lai' in r.data.decode('utf-8').lower()


def test_chan_so_tien_khong_hop_le(toan_quyen, app):
    _chuan_bi_phan_cong_va_su_dung_vat_lieu(toan_quyen)
    with app.app_context():
        from app.models import PhanCong
        ma_pc = PhanCong.query.filter_by(nhansu_MaNV='NV01').first().MaPhanCong

    r = toan_quyen.post('/chiphi/them', data={
        'MaCP': 'CP01', 'LoaiChiPhi': 'Vật liệu', 'NgayChi': date.today().isoformat(),
        'SoTienChi': '0', 'MaHangMuc': 'HM02', 'MaPhanCong': ma_pc, 'MaVatLieu': 'VL01',
    }, follow_redirects=True)
    assert 'phải lớn hơn 0' in r.data.decode('utf-8').lower()


def test_tinh_ngan_sach_su_dung(toan_quyen, app):
    _chuan_bi_phan_cong_va_su_dung_vat_lieu(toan_quyen)
    with app.app_context():
        from app.modules.chiphi import service
        ket_qua = service.tinh_ngan_sach_su_dung('HM01')
        # vat lieu: 90000*10=900000; nhan cong: 100000*5=500000 -> tong 1400000
        assert float(ket_qua['da_su_dung']) == 1_400_000.0
