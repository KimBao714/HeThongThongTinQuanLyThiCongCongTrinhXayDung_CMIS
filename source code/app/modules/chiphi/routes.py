"""LỚP PRESENTATION (Presentation Layer) - chỉ nhận request, gọi service, render template."""

from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.modules.chiphi import service
from app.auth import yeu_cau_toan_quyen

bp = Blueprint('chiphi', __name__, url_prefix='/chiphi')


@bp.route('/')
def list_chiphi():
    keyword = request.args.get('q', '').strip()
    ma_hangmuc = request.args.get('hangmuc', '').strip()
    loai_chi_phi = request.args.get('loai', '').strip()

    danh_sach = service.lay_danh_sach(keyword, ma_hangmuc or None, loai_chi_phi or None)
    # Chỉ tính so sánh ngân sách khi người dùng đã lọc theo đúng 1 hạng mục
    # cụ thể - so sánh ngân sách gộp nhiều hạng mục không có ý nghĩa nghiệp vụ.
    ngan_sach = service.tinh_ngan_sach(ma_hangmuc) if ma_hangmuc else None
    ngan_sach_su_dung = service.tinh_ngan_sach_su_dung(ma_hangmuc) if ma_hangmuc else None
    tong_quan = service.lay_tong_quan_chi_phi()
    chi_tiet_nguon = service.lay_chi_tiet_nguon_chi_phi(ma_hangmuc or None)
    tong_hop_theo_hang_muc = service.lay_tong_hop_theo_hang_muc()

    return render_template(
        'chiphi/list.html',
        danh_sach=danh_sach, keyword=keyword, ma_hangmuc=ma_hangmuc, loai_chi_phi=loai_chi_phi,
        ngan_sach=ngan_sach, ngan_sach_su_dung=ngan_sach_su_dung, tong_quan=tong_quan,
        chi_tiet_nguon=chi_tiet_nguon,
        tong_hop_theo_hang_muc=tong_hop_theo_hang_muc,
        danh_sach_hang_muc=service.danh_sach_hang_muc_de_chon(),
        danh_sach_loai=service.LOAI_CHI_PHI, active_module='chiphi'
    )


@bp.route('/them', methods=['GET', 'POST'])
@yeu_cau_toan_quyen
def add_chiphi():
    du_lieu_tham_chieu = _du_lieu_tham_chieu()

    if request.method == 'POST':
        try:
            service.them_moi(request.form)
        except service.LoiNghiepVu as loi:
            flash(str(loi), 'danger')
            return render_template('chiphi/form.html', item=None, form_data=request.form,
                                    active_module='chiphi', **du_lieu_tham_chieu)

        flash('Thêm chi phí thành công.', 'success')
        return redirect(url_for('chiphi.list_chiphi'))

    return render_template('chiphi/form.html', item=None, form_data=None,
                            active_module='chiphi', **du_lieu_tham_chieu)


@bp.route('/sua/<ma>', methods=['GET', 'POST'])
@yeu_cau_toan_quyen
def edit_chiphi(ma):
    du_lieu_tham_chieu = _du_lieu_tham_chieu()

    if request.method == 'POST':
        try:
            service.cap_nhat(ma, request.form)
        except service.LoiNghiepVu as loi:
            item = service.lay_theo_ma(ma)
            flash(str(loi), 'danger')
            return render_template('chiphi/form.html', item=item, form_data=request.form,
                                    active_module='chiphi', **du_lieu_tham_chieu)

        flash('Cập nhật chi phí thành công.', 'success')
        return redirect(url_for('chiphi.list_chiphi'))

    item = service.lay_theo_ma(ma)
    return render_template('chiphi/form.html', item=item, form_data=None,
                            active_module='chiphi', **du_lieu_tham_chieu)


@bp.route('/xoa/<ma>', methods=['POST'])
@yeu_cau_toan_quyen
def delete_chiphi(ma):
    try:
        service.xoa(ma)
        flash('Đã xóa chi phí.', 'success')
    except service.LoiNghiepVu as loi:
        flash(str(loi), 'danger')
    return redirect(url_for('chiphi.list_chiphi'))


def _du_lieu_tham_chieu():
    """Dữ liệu tham chiếu dùng chung cho form Thêm/Sửa (dropdown chọn hạng
    mục / phân công / sử dụng vật liệu, và ngày hôm nay để chặn chọn ngày
    chi trong tương lai ngay trên trình duyệt)."""
    return {
        'danh_sach_hang_muc': service.danh_sach_hang_muc_de_chon(),
        'danh_sach_phan_cong': service.danh_sach_phan_cong_de_chon(),
        'danh_sach_su_dung_vat_lieu': service.danh_sach_su_dung_vat_lieu_de_chon(),
        'danh_sach_loai': service.LOAI_CHI_PHI,
        'hom_nay': date.today().isoformat(),
    }
