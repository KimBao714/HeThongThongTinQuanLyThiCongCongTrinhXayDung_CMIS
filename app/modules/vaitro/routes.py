from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.auth import dang_nhap, dang_xuat, VAI_TRO_TOAN_QUYEN, VAI_TRO_TRA_CUU

bp = Blueprint('vaitro', __name__, url_prefix='/vai-tro')


@bp.route('/', methods=['GET', 'POST'])
def chon_vai_tro():
    if request.method == 'POST':
        vai_tro = request.form.get('vai_tro', '').strip()
        if vai_tro in VAI_TRO_TOAN_QUYEN + VAI_TRO_TRA_CUU:
            dang_nhap(vai_tro)
            return redirect(url_for('dashboard.tong_quan'))

    return render_template('vaitro/chon_vai_tro.html',
                            vai_tro_toan_quyen=VAI_TRO_TOAN_QUYEN,
                            vai_tro_tra_cuu=VAI_TRO_TRA_CUU)


@bp.route('/doi-vai-tro')
def doi_vai_tro():
    dang_xuat()
    return redirect(url_for('vaitro.chon_vai_tro'))


@bp.route('/dang-xuat')
def dang_xuat_route():
    dang_xuat()
    flash('Bạn đã đăng xuất khỏi hệ thống.', 'success')
    return redirect(url_for('vaitro.chon_vai_tro'))
