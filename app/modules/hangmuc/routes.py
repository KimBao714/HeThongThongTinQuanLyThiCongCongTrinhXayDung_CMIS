"""LỚP PRESENTATION (Presentation Layer) - chỉ nhận request, gọi service, render template."""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.modules.hangmuc import service
from app.auth import yeu_cau_toan_quyen

bp = Blueprint('hangmuc', __name__, url_prefix='/hangmuc')


def _hang_muc_lien_quan(item):
    return [item] + service.danh_sach_hang_muc_hau_due(item.MaHangMuc)


@bp.route('/')
def list_hangmuc():
    keyword = request.args.get('q', '').strip()
    cay_hang_muc = service.lay_cay_hang_muc(keyword)
    # Đọc thêm dữ liệu phân công (thuộc module Nhân sự) và sử dụng vật liệu
    # (thuộc module Vật liệu) chỉ để hiển thị ngược "hạng mục này đang có ai
    # làm, đang dùng vật liệu gì" - xem service.nhan_su_dang_lam_theo_hangmuc
    # và service.vat_lieu_dang_dung_theo_hangmuc.
    phan_cong_theo_hangmuc = service.nhan_su_dang_lam_theo_hangmuc()
    vat_lieu_theo_hangmuc = service.vat_lieu_dang_dung_theo_hangmuc()
    return render_template('hangmuc/list.html', cay_hang_muc=cay_hang_muc, keyword=keyword,
                            phan_cong_theo_hangmuc=phan_cong_theo_hangmuc,
                            vat_lieu_theo_hangmuc=vat_lieu_theo_hangmuc,
                            
                            active_module='hangmuc')


@bp.route('/<ma>')
def detail_hangmuc(ma):
    item = service.lay_theo_ma(ma)
    danh_sach_hau_due = service.danh_sach_hang_muc_hau_due(item.MaHangMuc)
    danh_sach_con = [h for h in danh_sach_hau_due if h.hangmuc_MaHangMuc == item.MaHangMuc]
    ma_lien_quan = {item.MaHangMuc} | {h.MaHangMuc for h in danh_sach_hau_due}
    phan_cong_theo_hangmuc = service.nhan_su_dang_lam_theo_hangmuc()
    vat_lieu_theo_hangmuc = service.vat_lieu_dang_dung_theo_hangmuc()
    phan_cong = [pc for ma_hm in ma_lien_quan for pc in phan_cong_theo_hangmuc.get(ma_hm, [])]
    vat_lieu = [sd for ma_hm in ma_lien_quan for sd in vat_lieu_theo_hangmuc.get(ma_hm, [])]
    ban_ve = item.danh_sach_banve
    chi_phi = item.danh_sach_chiphi
    return render_template(
        'hangmuc/detail.html', item=item, danh_sach_con=danh_sach_con,
        phan_cong=phan_cong, vat_lieu=vat_lieu, ban_ve=ban_ve, chi_phi=chi_phi,
        danh_sach_hau_due=danh_sach_hau_due,
        active_module='hangmuc'
    )


@bp.route('/<ma>/them-ngan-sach', methods=['POST'])
@yeu_cau_toan_quyen
def add_ngan_sach(ma):
    try:
        service.cong_ngan_sach(ma, request.form.get('SoTienNganSach'))
        flash('Đã cộng thêm ngân sách đang có.', 'success')
    except service.LoiNghiepVu as loi:
        flash(str(loi), 'danger')
    return redirect(url_for('hangmuc.detail_hangmuc', ma=ma))


@bp.route('/<ma>/ban-ve')
def related_banve(ma):
    item = service.lay_theo_ma(ma)
    danh_sach = [bv for hang_muc in _hang_muc_lien_quan(item) for bv in hang_muc.danh_sach_banve]
    return render_template(
        'hangmuc/related.html', item=item, loai='ban_ve',
        danh_sach=danh_sach, active_module='hangmuc'
    )


@bp.route('/<ma>/nhan-su')
def related_nhansu(ma):
    item = service.lay_theo_ma(ma)
    ma_lien_quan = {h.MaHangMuc for h in _hang_muc_lien_quan(item)}
    danh_sach = [
        pc for ma_hm, phan_congs in service.nhan_su_dang_lam_theo_hangmuc().items()
        if ma_hm in ma_lien_quan for pc in phan_congs
    ]
    return render_template(
        'hangmuc/related.html', item=item, loai='nhan_su',
        danh_sach=danh_sach, active_module='hangmuc'
    )


@bp.route('/<ma>/vat-lieu')
def related_vatlieu(ma):
    item = service.lay_theo_ma(ma)
    ma_lien_quan = {h.MaHangMuc for h in _hang_muc_lien_quan(item)}
    danh_sach = [
        sd for ma_hm, su_dungs in service.vat_lieu_dang_dung_theo_hangmuc().items()
        if ma_hm in ma_lien_quan for sd in su_dungs
    ]
    return render_template(
        'hangmuc/related.html', item=item, loai='vat_lieu',
        danh_sach=danh_sach, active_module='hangmuc'
    )


@bp.route('/them', methods=['GET', 'POST'])
@yeu_cau_toan_quyen
def add_hangmuc():
    danh_sach_cha = service.danh_sach_hang_muc_cha_de_chon()

    if request.method == 'POST':
        try:
            service.them_moi(request.form)
        except service.LoiNghiepVu as loi:
            flash(str(loi), 'danger')
            return render_template('hangmuc/form.html', item=None, form_data=request.form,
                                    danh_sach_cha=danh_sach_cha, active_module='hangmuc')

        flash('Thêm hạng mục thành công.', 'success')
        return redirect(url_for('hangmuc.list_hangmuc'))

    return render_template('hangmuc/form.html', item=None, form_data=None,
                            danh_sach_cha=danh_sach_cha, active_module='hangmuc')


@bp.route('/sua/<ma>', methods=['GET', 'POST'])
@yeu_cau_toan_quyen
def edit_hangmuc(ma):
    danh_sach_cha = service.danh_sach_hang_muc_cha_de_chon(ma_dang_sua=ma)

    if request.method == 'POST':
        try:
            service.cap_nhat(ma, request.form)
        except service.LoiNghiepVu as loi:
            item = service.lay_theo_ma(ma)
            flash(str(loi), 'danger')
            return render_template('hangmuc/form.html', item=item, form_data=request.form,
                                    danh_sach_cha=danh_sach_cha, active_module='hangmuc')

        flash('Cập nhật hạng mục thành công.', 'success')
        return redirect(url_for('hangmuc.list_hangmuc'))

    item = service.lay_theo_ma(ma)
    return render_template('hangmuc/form.html', item=item, form_data=None,
                            danh_sach_cha=danh_sach_cha, active_module='hangmuc')


@bp.route('/xoa/<ma>', methods=['POST'])
@yeu_cau_toan_quyen
def delete_hangmuc(ma):
    try:
        service.xoa(ma)
        flash('Đã xóa hạng mục.', 'success')
    except service.LoiNghiepVu as loi:
        flash(str(loi), 'danger')
    return redirect(url_for('hangmuc.list_hangmuc'))
