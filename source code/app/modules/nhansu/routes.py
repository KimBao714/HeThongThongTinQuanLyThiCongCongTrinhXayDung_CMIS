"""LỚP PRESENTATION (Presentation Layer) - chỉ nhận request, gọi service, render template."""

from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.modules.nhansu import service
from app.auth import yeu_cau_toan_quyen

bp = Blueprint('nhansu', __name__, url_prefix='/nhansu')


# ==================== NHÂN SỰ ====================

@bp.route('/')
def list_nhansu():
    keyword = request.args.get('q', '').strip()
    ma_hangmuc = request.args.get('hangmuc', '').strip()
    danh_sach = service.lay_danh_sach(keyword, ma_hangmuc or None)
    # Kèm theo danh sách mã hạng mục đang phân công của từng người, để hiển
    # thị ngay trên danh sách "ai đang làm hạng mục gì" mà không cần mở
    # trang chi tiết (giống cách banve/routes.py gộp item + hien_hanh).
    du_lieu = [
        {'item': ns, 'hang_muc_dang_lam': service.danh_sach_hang_muc_dang_lam(ns.MaNV)}
        for ns in danh_sach
    ]
    return render_template('nhansu/list.html', du_lieu=du_lieu, keyword=keyword,
                           ma_hangmuc=ma_hangmuc, active_module='nhansu')


@bp.route('/them', methods=['GET', 'POST'])
@yeu_cau_toan_quyen
def add_nhansu():
    if request.method == 'POST':
        try:
            service.them_moi(request.form)
        except service.LoiNghiepVu as loi:
            flash(str(loi), 'danger')
            return render_template('nhansu/form.html', item=None, form_data=request.form, active_module='nhansu')

        flash('Thêm nhân sự thành công.', 'success')
        return redirect(url_for('nhansu.list_nhansu'))

    return render_template('nhansu/form.html', item=None, form_data=None, active_module='nhansu')


@bp.route('/sua/<ma>', methods=['GET', 'POST'])
@yeu_cau_toan_quyen
def edit_nhansu(ma):
    if request.method == 'POST':
        try:
            service.cap_nhat(ma, request.form)
        except service.LoiNghiepVu as loi:
            item = service.lay_theo_ma(ma)
            flash(str(loi), 'danger')
            return render_template('nhansu/form.html', item=item, form_data=request.form, active_module='nhansu')

        flash('Cập nhật nhân sự thành công.', 'success')
        return redirect(url_for('nhansu.list_nhansu'))

    item = service.lay_theo_ma(ma)
    return render_template('nhansu/form.html', item=item, form_data=None, active_module='nhansu')


@bp.route('/xoa/<ma>', methods=['POST'])
@yeu_cau_toan_quyen
def delete_nhansu(ma):
    try:
        service.xoa(ma)
        flash('Đã xóa nhân sự.', 'success')
    except service.LoiNghiepVu as loi:
        flash(str(loi), 'danger')
    return redirect(url_for('nhansu.list_nhansu'))


# ==================== PHÂN CÔNG (thực thể kết hợp nhansu x hangmuc) ====================

@bp.route('/<ma>/phan-cong')
def list_phan_cong(ma):
    nhan_vien = service.lay_theo_ma(ma)
    danh_sach = service.danh_sach_phan_cong(ma)
    du_lieu = [{'item': pc, 'thanh_tien': service.thanh_tien_phan_cong(pc)} for pc in danh_sach]
    return render_template(
        'nhansu/phancong.html', item=nhan_vien, danh_sach=du_lieu,
        danh_sach_hang_muc_con=service.danh_sach_hang_muc_con_de_chon(),
        active_module='nhansu'
    )


@bp.route('/<ma>/phan-cong/them', methods=['POST'])
@yeu_cau_toan_quyen
def add_phan_cong(ma):
    try:
        service.them_phan_cong(ma, request.form)
        flash('Thêm phân công thành công.', 'success')
    except service.LoiNghiepVu as loi:
        flash(str(loi), 'danger')
    return redirect(url_for('nhansu.list_phan_cong', ma=ma))


@bp.route('/phan-cong/<ma_pc>/sua', methods=['GET', 'POST'])
@yeu_cau_toan_quyen
def edit_phan_cong(ma_pc):
    item = service.lay_phan_cong_theo_ma(ma_pc)

    if request.method == 'POST':
        try:
            service.sua_phan_cong(ma_pc, request.form)
            flash('Cập nhật phân công thành công.', 'success')
            return redirect(url_for('nhansu.list_phan_cong', ma=item.nhansu_MaNV))
        except service.LoiNghiepVu as loi:
            flash(str(loi), 'danger')
            return render_template(
                'nhansu/phancong_form.html', item=item, form_data=request.form,
                danh_sach_hang_muc_con=service.danh_sach_hang_muc_con_de_chon(),
                active_module='nhansu'
            )

    return render_template(
        'nhansu/phancong_form.html', item=item, form_data=None,
        danh_sach_hang_muc_con=service.danh_sach_hang_muc_con_de_chon(),
        active_module='nhansu'
    )


@bp.route('/phan-cong/<ma_pc>/them-ngay-cong', methods=['POST'])
@yeu_cau_toan_quyen
def add_ngay_cong(ma_pc):
    item = service.lay_phan_cong_theo_ma(ma_pc)
    ma_nv = item.nhansu_MaNV
    try:
        service.them_ngay_cong(ma_pc, request.form.get('SoNgayThem'))
        flash('Đã cộng thêm ngày công.', 'success')
    except service.LoiNghiepVu as loi:
        flash(str(loi), 'danger')
    return redirect(url_for('nhansu.list_phan_cong', ma=ma_nv))


@bp.route('/phan-cong/<ma_pc>/xoa', methods=['POST'])
@yeu_cau_toan_quyen
def delete_phan_cong(ma_pc):
    item = service.lay_phan_cong_theo_ma(ma_pc)
    ma_nv = item.nhansu_MaNV
    try:
        service.xoa_phan_cong(ma_pc)
        flash('Đã xóa phân công.', 'success')
    except service.LoiNghiepVu as loi:
        flash(str(loi), 'danger')
    return redirect(url_for('nhansu.list_phan_cong', ma=ma_nv))
