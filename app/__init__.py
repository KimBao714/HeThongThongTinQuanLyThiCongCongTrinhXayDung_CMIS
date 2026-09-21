import os
from decimal import Decimal, InvalidOperation
from flask import Flask, redirect, url_for, request
from app.extensions import db
from app.auth import da_chon_vai_tro, co_toan_quyen, vai_tro_hien_tai


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    @app.template_filter('so_gon')
    def so_gon(value):
        if value is None or value == '':
            return ''
        try:
            formatted = format(Decimal(str(value)), ',f')
        except (InvalidOperation, ValueError):
            return str(value)
        if '.' in formatted:
            formatted = formatted.rstrip('0').rstrip('.')
        return formatted

    @app.template_filter('ngay_vn')
    def ngay_vn(value):
        if not value:
            return ''
        return value.strftime('%d/%m/%Y') if hasattr(value, 'strftime') else str(value)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    from app.modules.vaitro.routes import bp as vaitro_bp
    from app.modules.dashboard.routes import bp as dashboard_bp
    from app.modules.hangmuc.routes import bp as hangmuc_bp
    from app.modules.vatlieu.routes import bp as vatlieu_bp
    from app.modules.nhansu.routes import bp as nhansu_bp
    from app.modules.banve.routes import bp as banve_bp
    from app.modules.chiphi.routes import bp as chiphi_bp

    app.register_blueprint(vaitro_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(hangmuc_bp)
    app.register_blueprint(vatlieu_bp)
    app.register_blueprint(nhansu_bp)
    app.register_blueprint(banve_bp)
    app.register_blueprint(chiphi_bp)

    # Bảng `trangthaiphienban` là bảng tra cứu (lookup) rỗng trong file SQL
    # gốc và không có route quản lý riêng - đảm bảo luôn có đủ 3 trạng thái
    # cố định (Chờ duyệt / Đã duyệt / Từ chối) mà module Bản vẽ cần dùng.
    with app.app_context():
        from app.modules.banve import repository as banve_repository
        banve_repository.dam_bao_trang_thai_mac_dinh()

    # Cho phép template gọi trực tiếp co_toan_quyen()/vai_tro_hien_tai() mà không cần
    # truyền biến thủ công ở từng route
    @app.context_processor
    def inject_auth_helpers():
        return dict(co_toan_quyen=co_toan_quyen, vai_tro_hien_tai=vai_tro_hien_tai)

    # Bắt buộc chọn vai trò trước khi vào bất kỳ trang nào khác trong hệ thống
    @app.before_request
    def kiem_tra_da_chon_vai_tro():
        endpoint_duoc_phep_bo_qua = {'vaitro.chon_vai_tro', 'vaitro.doi_vai_tro', 'vaitro.dang_xuat_route', 'static'}
        if request.endpoint in endpoint_duoc_phep_bo_qua:
            return
        if not da_chon_vai_tro():
            return redirect(url_for('vaitro.chon_vai_tro'))

    @app.route('/')
    def home():
        return redirect(url_for('dashboard.tong_quan'))

    return app
