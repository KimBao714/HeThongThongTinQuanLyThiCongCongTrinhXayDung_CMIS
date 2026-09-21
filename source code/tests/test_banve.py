"""Test module Bản vẽ (đã gộp Phiên bản + Trạng thái phiên bản): tạo bản vẽ
bắt buộc kèm file (tự sinh v1), tối đa 1 phiên bản chờ duyệt, không duyệt
lại/xóa phiên bản đã duyệt, xóa phiên bản xóa luôn file vật lý."""

import io
import os

from conftest import tao_hang_muc_goc_va_con


def _them_ban_ve(client, ma_bv='BV01', ten_file='v1.pdf', noi_dung=b'noi dung file'):
    return client.post('/banve/them', data={
        'MaBV': ma_bv, 'TenBV': 'Bản vẽ móng', 'MaHangMuc': 'HM02',
        'HoNguoiTao': 'Nguyễn', 'TenNguoiTao': 'Văn A',
        'file_ban_ve': (io.BytesIO(noi_dung), ten_file),
    }, content_type='multipart/form-data', follow_redirects=True)


def test_tao_ban_ve_khong_file_bi_chan(toan_quyen, app):
    tao_hang_muc_goc_va_con(toan_quyen)
    r = toan_quyen.post('/banve/them', data={
        'MaBV': 'BV01', 'TenBV': 'Bản vẽ móng', 'MaHangMuc': 'HM02',
        'HoNguoiTao': 'Nguyễn', 'TenNguoiTao': 'Văn A',
    }, follow_redirects=True)
    assert 'vui lòng chọn file' in r.data.decode('utf-8').lower()
    with app.app_context():
        from app.models import BanVe
        assert BanVe.query.count() == 0


def test_tao_ban_ve_kem_file_tu_dong_tao_phien_ban_v1(toan_quyen, app):
    tao_hang_muc_goc_va_con(toan_quyen)
    _them_ban_ve(toan_quyen)
    with app.app_context():
        from app.models import BanVe, PhienBan
        assert BanVe.query.count() == 1
        pb = PhienBan.query.filter_by(banve_MaBV='BV01').first()
        assert pb is not None
        assert pb.SoPhienBan == '1'
        assert pb.trangthaiphienban_MaTrangThai == 'CHO_DUYET'


def test_dinh_dang_file_khong_hop_le_bi_chan(toan_quyen, app):
    tao_hang_muc_goc_va_con(toan_quyen)
    _them_ban_ve(toan_quyen, ten_file='virus.exe')
    with app.app_context():
        from app.models import BanVe
        assert BanVe.query.count() == 0  # không để lại bản vẽ mồ côi


def test_chan_tai_len_khi_con_phien_ban_cho_duyet(toan_quyen):
    tao_hang_muc_goc_va_con(toan_quyen)
    _them_ban_ve(toan_quyen)
    r = toan_quyen.post('/banve/BV01/phien-ban/them', data={
        'HoNguoiTao': 'Trần', 'TenNguoiTao': 'Thị B',
        'file_ban_ve': (io.BytesIO(b'v2'), 'v2.pdf'),
    }, content_type='multipart/form-data', follow_redirects=True)
    assert 'chờ duyệt' in r.data.decode('utf-8').lower()


def test_duyet_phien_ban_thanh_cong(toan_quyen, app):
    tao_hang_muc_goc_va_con(toan_quyen)
    _them_ban_ve(toan_quyen)
    with app.app_context():
        from app.models import PhienBan
        ma_pb = PhienBan.query.filter_by(banve_MaBV='BV01').first().MaPB

    toan_quyen.post(f'/banve/phien-ban/{ma_pb}/duyet', follow_redirects=True)
    with app.app_context():
        from app.models import PhienBan
        pb = PhienBan.query.get(ma_pb)
        assert pb.trangthaiphienban_MaTrangThai == 'DA_DUYET'
        assert pb.NgayDuyet is not None


def test_chan_duyet_lai_phien_ban_da_duyet(toan_quyen):
    tao_hang_muc_goc_va_con(toan_quyen)
    _them_ban_ve(toan_quyen)
    with toan_quyen.application.app_context():
        from app.models import PhienBan
        ma_pb = PhienBan.query.filter_by(banve_MaBV='BV01').first().MaPB
    toan_quyen.post(f'/banve/phien-ban/{ma_pb}/duyet', follow_redirects=True)
    r = toan_quyen.post(f'/banve/phien-ban/{ma_pb}/duyet', follow_redirects=True)
    assert 'chỉ có thể duyệt' in r.data.decode('utf-8').lower()


def test_chan_xoa_phien_ban_da_duyet(toan_quyen):
    tao_hang_muc_goc_va_con(toan_quyen)
    _them_ban_ve(toan_quyen)
    with toan_quyen.application.app_context():
        from app.models import PhienBan
        ma_pb = PhienBan.query.filter_by(banve_MaBV='BV01').first().MaPB
    toan_quyen.post(f'/banve/phien-ban/{ma_pb}/duyet', follow_redirects=True)
    r = toan_quyen.post(f'/banve/phien-ban/{ma_pb}/xoa', follow_redirects=True)
    assert 'không thể xóa' in r.data.decode('utf-8').lower()


def test_xoa_duoc_phien_ban_cu_da_duyet(toan_quyen, app):
    tao_hang_muc_goc_va_con(toan_quyen)
    _them_ban_ve(toan_quyen)
    with app.app_context():
        from app.models import PhienBan
        pb_v1 = PhienBan.query.filter_by(banve_MaBV='BV01').first()
        ma_v1 = pb_v1.MaPB
    toan_quyen.post(f'/banve/phien-ban/{ma_v1}/duyet', follow_redirects=True)

    toan_quyen.post('/banve/BV01/phien-ban/them', data={
        'HoNguoiTao': 'Trần', 'TenNguoiTao': 'Thị B',
        'file_ban_ve': (io.BytesIO(b'v2'), 'v2.pdf'),
    }, content_type='multipart/form-data', follow_redirects=True)
    with app.app_context():
        from app.models import PhienBan
        pb_v2 = PhienBan.query.filter_by(banve_MaBV='BV01', SoPhienBan='2').first()
        ma_v2 = pb_v2.MaPB
        file_v1 = pb_v1.HinhBV
    toan_quyen.post(f'/banve/phien-ban/{ma_v2}/duyet', follow_redirects=True)

    toan_quyen.post(f'/banve/phien-ban/{ma_v1}/xoa', follow_redirects=True)
    with app.app_context():
        from app.models import PhienBan
        assert PhienBan.query.get(ma_v1) is None
    assert not os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], file_v1))


def test_xoa_phien_ban_tu_choi_xoa_luon_file_vat_ly(toan_quyen, app):
    tao_hang_muc_goc_va_con(toan_quyen)
    _them_ban_ve(toan_quyen)
    with app.app_context():
        from app.models import PhienBan
        pb = PhienBan.query.filter_by(banve_MaBV='BV01').first()
        ma_pb = pb.MaPB
        duong_dan_file = os.path.join(app.config['UPLOAD_FOLDER'], pb.HinhBV)

    assert os.path.isfile(duong_dan_file)
    toan_quyen.post(f'/banve/phien-ban/{ma_pb}/tu-choi', follow_redirects=True)
    toan_quyen.post(f'/banve/phien-ban/{ma_pb}/xoa', follow_redirects=True)
    assert not os.path.isfile(duong_dan_file)


def test_xoa_ban_ve_xoa_toan_bo_phien_ban_va_file(toan_quyen, app):
    tao_hang_muc_goc_va_con(toan_quyen)
    _them_ban_ve(toan_quyen)
    with app.app_context():
        from app.models import BanVe, PhienBan
        pb = PhienBan.query.filter_by(banve_MaBV='BV01').first()
        ma_pb = pb.MaPB
        duong_dan_file = os.path.join(app.config['UPLOAD_FOLDER'], pb.HinhBV)

    assert os.path.isfile(duong_dan_file)
    toan_quyen.post('/banve/xoa/BV01', follow_redirects=True)
    with app.app_context():
        assert BanVe.query.get('BV01') is None
        assert PhienBan.query.get(ma_pb) is None
    assert not os.path.isfile(duong_dan_file)


def test_tai_xuong_phien_ban_dung_noi_dung(toan_quyen, app):
    tao_hang_muc_goc_va_con(toan_quyen)
    _them_ban_ve(toan_quyen, noi_dung=b'noi dung dac trung')
    with app.app_context():
        from app.models import PhienBan
        ma_pb = PhienBan.query.filter_by(banve_MaBV='BV01').first().MaPB
    r = toan_quyen.get(f'/banve/phien-ban/{ma_pb}/tai-xuong')
    assert r.data == b'noi dung dac trung'
