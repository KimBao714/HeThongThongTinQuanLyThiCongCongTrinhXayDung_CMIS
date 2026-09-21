"""
Xử lý "đăng nhập" đơn giản bằng cách chọn vai trò (không mật khẩu) - phù hợp
với MVP định hướng BA: mục tiêu là minh họa khái niệm phân quyền theo vai trò
trong nghiệp vụ xây dựng, không phải xây dựng cơ chế bảo mật đầy đủ.
"""

from functools import wraps
from flask import session, flash, redirect, url_for, request

# Toàn bộ vai trò tham gia hệ thống theo đúng các bên liên quan trong đồ án
VAI_TRO_TOAN_QUYEN = ['Chủ đầu tư', 'Tư vấn thiết kế']
VAI_TRO_TRA_CUU = ['Tổng thầu', 'Nhà thầu chính', 'Nhà thầu phụ', 'Quản lý dự án', 'Tư vấn giám sát']
TAT_CA_VAI_TRO = VAI_TRO_TOAN_QUYEN + VAI_TRO_TRA_CUU


def dang_nhap(vai_tro):
    session['vai_tro'] = vai_tro


def dang_xuat():
    session.pop('vai_tro', None)


def vai_tro_hien_tai():
    return session.get('vai_tro')


def da_chon_vai_tro():
    return 'vai_tro' in session


def co_toan_quyen():
    return session.get('vai_tro') in VAI_TRO_TOAN_QUYEN


def yeu_cau_toan_quyen(f):
    """Decorator gắn vào route Thêm/Sửa/Xóa - chặn nếu vai trò chỉ ở mức tra cứu.
    Chặn ở tầng route (không chỉ ẩn nút trên giao diện) để tránh người dùng
    tra cứu tự gõ thẳng URL để bỏ qua giao diện."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not co_toan_quyen():
            flash('Vai trò của bạn chỉ có quyền tra cứu, không thể thực hiện thao tác này.', 'danger')
            return redirect(request.referrer or url_for('dashboard.tong_quan'))
        return f(*args, **kwargs)
    return wrapper
