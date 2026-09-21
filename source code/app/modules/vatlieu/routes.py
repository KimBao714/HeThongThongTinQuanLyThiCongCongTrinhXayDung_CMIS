"""LỚP PRESENTATION (Presentation Layer) - chỉ nhận request, gọi service, render template."""

from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.modules.vatlieu import service
from app.auth import yeu_cau_toan_quyen

bp = Blueprint('vatlieu', __name__, url_prefix='/vatlieu')


# ==================== VẬT LIỆU ====================

@bp.route('/')
def list_vatlieu():
    keyword = request.args.get('q', '').strip()
    ma_hangmuc = request.args.get('hangmuc', '').strip()
    danh_sach = service.lay_danh_sach(keyword, ma_hangmuc or None)
    # Kèm theo danh sách mã hạng mục đang dùng + so sánh với số lượng dự
    # kiến của từng vật liệu, để hiển thị ngay trên danh sách mà không cần
    # mở trang chi tiết (giống cách banve/nhansu gộp item + dữ liệu liên quan).
    du_lieu = [
        {
            'item': vl,
            'hang_muc_dang_dung': service.danh_sach_hang_muc_dang_dung(vl.MaVL),
            'su_dung': service.tinh_su_dung(vl.MaVL),
        }
        for vl in danh_sach
    ]
    return render_template('vatlieu/list.html', du_lieu=du_lieu, keyword=keyword,
                           ma_hangmuc=ma_hangmuc, active_module='vatlieu')


@bp.route('/them', methods=['GET', 'POST'])
@yeu_cau_toan_quyen
def add_vatlieu():
    if request.method == 'POST':
        try:
            service.them_moi(request.form)
        except service.LoiNghiepVu as loi:
            flash(str(loi), 'danger')
            return render_template('vatlieu/form.html', item=None, form_data=request.form, active_module='vatlieu')

        flash('Thêm vật liệu thành công.', 'success')
        return redirect(url_for('vatlieu.list_vatlieu'))

    return render_template('vatlieu/form.html', item=None, form_data=None, active_module='vatlieu')


@bp.route('/sua/<ma>', methods=['GET', 'POST'])
@yeu_cau_toan_quyen
def edit_vatlieu(ma):
    if request.method == 'POST':
        try:
            service.cap_nhat(ma, request.form)
        except service.LoiNghiepVu as loi:
            item = service.lay_theo_ma(ma)
            flash(str(loi), 'danger')
            return render_template('vatlieu/form.html', item=item, form_data=request.form, active_module='vatlieu')

        flash('Cập nhật vật liệu thành công.', 'success')
        return redirect(url_for('vatlieu.list_vatlieu'))

    item = service.lay_theo_ma(ma)
    return render_template('vatlieu/form.html', item=item, form_data=None, active_module='vatlieu')


@bp.route('/xoa/<ma>', methods=['POST'])
@yeu_cau_toan_quyen
def delete_vatlieu(ma):
    try:
        service.xoa(ma)
        flash('Đã xóa vật liệu.', 'success')
    except service.LoiNghiepVu as loi:
        flash(str(loi), 'danger')
    return redirect(url_for('vatlieu.list_vatlieu'))


# ==================== SỬ DỤNG VẬT LIỆU (thực thể kết hợp vatlieu x hangmuc) ====================

@bp.route('/<ma>/su-dung')
def list_su_dung(ma):
    vat_lieu = service.lay_theo_ma(ma)
    danh_sach = service.danh_sach_su_dung(ma)
    return render_template(
        'vatlieu/sudung.html', item=vat_lieu, danh_sach=danh_sach,
        su_dung=service.tinh_su_dung(ma),
        danh_sach_hang_muc_con=service.danh_sach_hang_muc_con_de_chon(),
        active_module='vatlieu'
    )


@bp.route('/<ma>/su-dung/them', methods=['POST'])
@yeu_cau_toan_quyen
def add_su_dung(ma):
    try:
        service.them_su_dung(ma, request.form)
        flash('Ghi nhận sử dụng vật liệu thành công.', 'success')
    except service.LoiNghiepVu as loi:
        flash(str(loi), 'danger')
    return redirect(url_for('vatlieu.list_su_dung', ma=ma))


@bp.route('/<ma>/su-dung/<ma_hangmuc>/sua', methods=['GET', 'POST'])
@yeu_cau_toan_quyen
def edit_su_dung(ma, ma_hangmuc):
    item = service.lay_su_dung_theo_khoa(ma, ma_hangmuc)

    if request.method == 'POST':
        try:
            service.sua_su_dung(ma, ma_hangmuc, request.form)
            flash('Cập nhật số lượng sử dụng thành công.', 'success')
            return redirect(url_for('vatlieu.list_su_dung', ma=ma))
        except service.LoiNghiepVu as loi:
            flash(str(loi), 'danger')
            return render_template('vatlieu/sudung_form.html', item=item, form_data=request.form, active_module='vatlieu')

    return render_template('vatlieu/sudung_form.html', item=item, form_data=None, active_module='vatlieu')


@bp.route('/<ma>/su-dung/<ma_hangmuc>/xoa', methods=['POST'])
@yeu_cau_toan_quyen
def delete_su_dung(ma, ma_hangmuc):
    try:
        service.xoa_su_dung(ma, ma_hangmuc)
        flash('Đã xóa lượt sử dụng.', 'success')
    except service.LoiNghiepVu as loi:
        flash(str(loi), 'danger')
    return redirect(url_for('vatlieu.list_su_dung', ma=ma))
