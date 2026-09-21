"""
Cấu hình chung cho toàn bộ bộ test (pytest tự động nạp file này).

CHIẾN LƯỢC: mỗi test chạy trên 1 CSDL SQLite TẠM RIÊNG (không đụng tới
MySQL thật khai báo trong config.py) - cô lập hoàn toàn giữa các test, và
không đòi hỏi người chạy test phải có sẵn MySQL/import `mainDB_latest.sql`
trước. SQLite hiểu tương đương các kiểu cột dùng trong models.py (Decimal,
Date, Text...) nên không cần sửa gì ở models.py để test chạy được.

Chạy bộ test:
    pip install -r requirements-dev.txt
    pytest
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from flask import Flask  # noqa: E402
from app.extensions import db  # noqa: E402
import app.models  # noqa: E402,F401  (import để đăng ký toàn bộ model lên metadata)


@pytest.fixture()
def app(tmp_path):
    """1 Flask app + 1 CSDL SQLite tạm, tạo mới hoàn toàn cho MỖI test."""
    db_path = tmp_path / 'test.db'
    config.Config.SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
    config.Config.SECRET_KEY = 'test-secret-key'
    config.Config.UPLOAD_FOLDER = str(tmp_path / 'uploads')

    # Phải tạo bảng TRƯỚC khi gọi create_app(): create_app() seed sẵn 3
    # dòng cố định cho bảng `trangthaiphienban` ngay lúc khởi tạo (xem
    # app/__init__.py), đòi hỏi bảng đó đã tồn tại từ trước.
    pre_app = Flask(__name__)
    pre_app.config.from_object(config.Config)
    db.init_app(pre_app)
    with pre_app.app_context():
        db.create_all()

    from app import create_app
    flask_app = create_app()
    flask_app.config['TESTING'] = True

    yield flask_app

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def toan_quyen(client):
    """Client đã "đăng nhập" với 1 vai trò toàn quyền (Chủ đầu tư)."""
    client.post('/vai-tro/', data={'vai_tro': 'Chủ đầu tư'}, follow_redirects=True)
    return client


@pytest.fixture()
def tra_cuu(client):
    """Client đã "đăng nhập" với 1 vai trò chỉ tra cứu (Nhà thầu chính)."""
    client.post('/vai-tro/', data={'vai_tro': 'Nhà thầu chính'}, follow_redirects=True)
    return client


def tao_hang_muc_goc_va_con(client, ma_goc='HM01', ma_con='HM02'):
    """Helper dùng chung nhiều test: tạo sẵn 1 hạng mục gốc + 1 hạng mục
    con của nó, vì rất nhiều quy tắc nghiệp vụ (phân công, sử dụng vật
    liệu, chi phí...) chỉ áp dụng được cho hạng mục con."""
    client.post('/hangmuc/them', data={'MaHangMuc': ma_goc, 'TenHangMuc': 'Công trình A'},
                follow_redirects=True)
    client.post('/hangmuc/them', data={'MaHangMuc': ma_con, 'TenHangMuc': 'Hạng mục con',
                                        'HangMucCha': ma_goc}, follow_redirects=True)
