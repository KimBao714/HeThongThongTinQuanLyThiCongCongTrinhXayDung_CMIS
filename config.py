import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # KHÔNG hardcode tài khoản/mật khẩu CSDL thật vào source code (rủi ro
    # lộ thông tin khi đẩy code lên kho lưu trữ công khai). Bắt buộc người
    # chạy tự khai báo qua biến môi trường - xem README mục 3. Giá trị mặc
    # định để trống chỉ nhằm mục đích không làm crash lúc import module,
    # KHÔNG phải giá trị dùng được thật.
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'kimBao714/')
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'quanlythicong_ctdandung')

    SQLALCHEMY_DATABASE_URI = (
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Tương tự mật khẩu CSDL: không hardcode 1 chuỗi cố định vào source code
    # (ai đọc được code là biết luôn SECRET_KEY dùng để ký session). Đọc từ
    # biến môi trường; nếu chưa khai báo (VD: chạy thử cục bộ) thì tự sinh
    # 1 khóa ngẫu nhiên mỗi lần khởi động - đủ dùng cho MVP/demo, KHÔNG phù
    # hợp để deploy thật (sinh mới mỗi lần chạy sẽ làm mất session cũ).
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    # Nơi lưu file bản vẽ upload lên
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads', 'banve')
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'dwg'}
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # giới hạn 20MB / file
