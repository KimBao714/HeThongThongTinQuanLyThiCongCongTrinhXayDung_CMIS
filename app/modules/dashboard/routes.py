"""LỚP PRESENTATION (Presentation Layer) - chỉ nhận request, gọi service, render template."""

from flask import Blueprint, make_response, render_template

from app.modules.dashboard import service

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


def _khong_cho_cache(response):
    """Cả trang đầy đủ lẫn fragment polling đều PHẢI luôn lấy số liệu MỚI
    NHẤT từ CSDL - không được để trình duyệt/proxy cache lại kết quả cũ,
    nếu không tính năng "cập nhật theo thời gian thực" sẽ vô nghĩa."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response


@bp.route('/')
def tong_quan():
    so_lieu = service.lay_so_lieu_tong_quan()
    response = make_response(render_template(
        'dashboard/index.html', so_lieu=so_lieu, active_module='dashboard'
    ))
    return _khong_cho_cache(response)


@bp.route('/lam-moi')
def lam_moi():
    """Trả về đúng 1 fragment HTML (dashboard/_body.html) chứa số liệu MỚI
    NHẤT truy vấn lại từ CSDL tại thời điểm gọi - dùng cho JS
    (static/js/dashboard.js) gọi định kỳ bằng fetch() để cập nhật KPI/cảnh
    báo/biểu đồ mà KHÔNG cần tải lại cả trang. Dùng LẠI đúng
    `dashboard/_body.html` mà trang chính cũng include, để tránh 2 nơi
    render 2 bản HTML khác nhau cho cùng 1 dữ liệu."""
    so_lieu = service.lay_so_lieu_tong_quan()
    response = make_response(render_template('dashboard/_body.html', so_lieu=so_lieu))
    return _khong_cho_cache(response)
