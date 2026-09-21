"""LỚP PRESENTATION (Presentation Layer) - chỉ nhận request, gọi service, render template."""

from flask import (Blueprint, render_template, request, redirect, url_for,
                    flash, current_app, send_from_directory, abort)

from app.modules.banve import service
from app.auth import yeu_cau_toan_quyen

bp = Blueprint('banve', __name__, url_prefix='/banve')


# ---------------------- Bản vẽ ----------------------

@bp.route('/')
def list_banve():
    keyword = request.args.get('q', '').strip()
    ma_hangmuc = request.args.get('hangmuc', '').strip()
    danh_sach = service.lay_danh_sach(keyword, ma_hangmuc or None)

    du_lieu = [
        {
            'item': bv,
            'hien_hanh': service.phien_ban_hien_hanh(bv.MaBV),
            'so_phien_ban': len(service.lay_phien_ban(bv.MaBV)),
        }
        for bv in danh_sach
    ]

    return render_template(
        'banve/list.html', du_lieu=du_lieu, keyword=keyword, ma_hangmuc=ma_hangmuc,
        danh_sach_hang_muc=service.danh_sach_hang_muc_de_chon(), active_module='banve'
    )


@bp.route('/them', methods=['GET', 'POST'])
@yeu_cau_toan_quyen
def add_banve():
    danh_sach_hang_muc = service.danh_sach_hang_muc_de_chon()

    if request.method == 'POST':
        file_storage = request.files.get('file_ban_ve')
        try:
            service.them_moi(
                request.form, file_storage,
                current_app.config['UPLOAD_FOLDER'],
                current_app.config['ALLOWED_EXTENSIONS'],
            )
        except service.LoiNghiepVu as loi:
            flash(str(loi), 'danger')
            return render_template('banve/form.html', item=None, form_data=request.form,
                                    danh_sach_hang_muc=danh_sach_hang_muc, active_module='banve')

        flash('Đã thêm bản vẽ và tải lên phiên bản đầu tiên (v1), đang chờ duyệt.', 'success')
        return redirect(url_for('banve.list_banve'))

    return render_template('banve/form.html', item=None, form_data=None,
                            danh_sach_hang_muc=danh_sach_hang_muc, active_module='banve')


@bp.route('/sua/<ma>', methods=['GET', 'POST'])
@yeu_cau_toan_quyen
def edit_banve(ma):
    danh_sach_hang_muc = service.danh_sach_hang_muc_de_chon()

    if request.method == 'POST':
        try:
            service.cap_nhat(ma, request.form)
        except service.LoiNghiepVu as loi:
            item = service.lay_theo_ma(ma)
            flash(str(loi), 'danger')
            return render_template('banve/form.html', item=item, form_data=request.form,
                                    danh_sach_hang_muc=danh_sach_hang_muc, active_module='banve')

        flash('Cập nhật bản vẽ thành công.', 'success')
        return redirect(url_for('banve.list_banve'))

    item = service.lay_theo_ma(ma)
    return render_template('banve/form.html', item=item, form_data=None,
                            danh_sach_hang_muc=danh_sach_hang_muc, active_module='banve')


@bp.route('/xoa/<ma>', methods=['POST'])
@yeu_cau_toan_quyen
def delete_banve(ma):
    try:
        service.xoa(ma, current_app.config['UPLOAD_FOLDER'])
        flash('Đã xóa bản vẽ và toàn bộ phiên bản.', 'success')
    except service.LoiNghiepVu as loi:
        flash(str(loi), 'danger')
    return redirect(url_for('banve.list_banve'))


# ---------------------- Phiên bản ----------------------

@bp.route('/<ma>/phien-ban')
def list_phien_ban(ma):
    item = service.lay_theo_ma(ma)
    danh_sach = service.lay_phien_ban(ma)
    hien_hanh = service.phien_ban_hien_hanh(ma)
    return render_template('banve/phienban.html', item=item, danh_sach=danh_sach,
                           hien_hanh=hien_hanh, active_module='banve')


@bp.route('/<ma>/phien-ban/them', methods=['POST'])
@yeu_cau_toan_quyen
def add_phien_ban(ma):
    file_storage = request.files.get('file_ban_ve')
    try:
        service.them_phien_ban(
            ma, request.form, file_storage,
            current_app.config['UPLOAD_FOLDER'],
            current_app.config['ALLOWED_EXTENSIONS'],
        )
        flash('Đã tải lên phiên bản mới, đang chờ duyệt.', 'success')
    except service.LoiNghiepVu as loi:
        flash(str(loi), 'danger')
    return redirect(url_for('banve.list_phien_ban', ma=ma))


@bp.route('/phien-ban/<ma_pb>/duyet', methods=['POST'])
@yeu_cau_toan_quyen
def duyet_phien_ban(ma_pb):
    pb = service.lay_phien_ban_theo_ma(ma_pb)
    ma_bv = pb.banve_MaBV
    try:
        service.duyet_phien_ban(ma_pb)
        flash('Đã duyệt phiên bản.', 'success')
    except service.LoiNghiepVu as loi:
        flash(str(loi), 'danger')
    return redirect(url_for('banve.list_phien_ban', ma=ma_bv))


@bp.route('/phien-ban/<ma_pb>/tu-choi', methods=['POST'])
@yeu_cau_toan_quyen
def tu_choi_phien_ban(ma_pb):
    pb = service.lay_phien_ban_theo_ma(ma_pb)
    ma_bv = pb.banve_MaBV
    try:
        service.tu_choi_phien_ban(ma_pb)
        flash('Đã từ chối phiên bản.', 'success')
    except service.LoiNghiepVu as loi:
        flash(str(loi), 'danger')
    return redirect(url_for('banve.list_phien_ban', ma=ma_bv))


@bp.route('/phien-ban/<ma_pb>/xoa', methods=['POST'])
@yeu_cau_toan_quyen
def delete_phien_ban(ma_pb):
    pb = service.lay_phien_ban_theo_ma(ma_pb)
    ma_bv = pb.banve_MaBV
    try:
        service.xoa_phien_ban(ma_pb, current_app.config['UPLOAD_FOLDER'])
        flash('Đã xóa phiên bản.', 'success')
    except service.LoiNghiepVu as loi:
        flash(str(loi), 'danger')
    return redirect(url_for('banve.list_phien_ban', ma=ma_bv))


@bp.route('/phien-ban/<ma_pb>/tai-xuong')
def tai_xuong_phien_ban(ma_pb):
    pb = service.lay_phien_ban_theo_ma(ma_pb)
    if not pb.HinhBV:
        abort(404)
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], pb.HinhBV, as_attachment=True)


@bp.route('/phien-ban/<ma_pb>/xem-hinh')
def xem_hinh_phien_ban(ma_pb):
    pb = service.lay_phien_ban_theo_ma(ma_pb)
    duoi_file = pb.HinhBV.rsplit('.', 1)[-1].lower() if pb.HinhBV and '.' in pb.HinhBV else ''
    if duoi_file not in {'pdf', 'png', 'jpg', 'jpeg', 'dwg'}:
        abort(404)
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], pb.HinhBV, as_attachment=False)
