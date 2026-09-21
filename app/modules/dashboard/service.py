"""
LỚP BUSINESS (Business Logic Layer)
------------------------------------
Dashboard tổng quan là module CHỈ ĐỌC (không thêm/sửa/xóa gì) - không có
bảng CSDL riêng, chỉ tổng hợp số liệu từ các module khác để hiển thị 1
trang nhìn nhanh toàn hệ thống.

NGUYÊN TẮC THIẾT KẾ QUAN TRỌNG NHẤT của module này: TÁI SỬ DỤNG đúng logic
nghiệp vụ đã có ở TỪNG MODULE gốc, thay vì tự tính lại. Cụ thể module này
gọi lại:
- `chiphi.service.lay_tong_quan_chi_phi()` / `lay_tong_hop_theo_hang_muc()`
  - để lấy tổng chi phí, chi phí theo loại, và hạng mục nào vượt ngân sách.
- `vatlieu.service.danh_sach_vuot_du_kien()` - để lấy vật liệu nào đã dùng
  vượt số lượng đang có.
- `banve.service.phien_ban_hien_hanh()` - để biết bản vẽ nào đã có phiên
  bản chính thức (Đã duyệt) hay chưa.
- `nhansu.service.TRANG_THAI_LAM_VIEC` - để đảm bảo biểu đồ trạng thái nhân
  sự luôn đủ mặt cả 3 trạng thái cố định, không lấy từ 1 danh sách khai báo
  trùng lặp riêng ở đây.

Lý do: nếu Dashboard tự tính lại các phép so sánh ngân sách/số lượng dự
kiến theo cách RIÊNG của nó, rất dễ xảy ra tình trạng con số ở Dashboard
LỆCH với con số hiển thị ở trang chi tiết của chính module đó (2 nơi tính
cùng 1 khái niệm nghiệp vụ theo 2 công thức khác nhau, ai sửa 1 nơi quên
sửa nơi kia là dữ liệu sai lệch ngay). Bản thân module Chi phí đã minh họa
rõ việc này: nó phân biệt "chi phí đã GHI NHẬN thực tế" (tổng `SoTienChi`
trong bảng `chiphi`) và "chi phí ƯỚC TÍNH từ khối lượng đã phân bổ" (tổng
đơn giá x số lượng vật liệu + chi phí thuê x ngày công nhân sự) - đây LÀ 2
con số khác nhau về ý nghĩa (số đã trả tiền thật vs. số phát sinh từ việc
đã phân bổ tài nguyên nhưng có thể chưa ghi nhận thành 1 dòng chi phí chính
thức) - Dashboard hiển thị CẢ HAI để người dùng thấy rõ sự khác biệt, thay
vì gộp lại thành 1 con số duy nhất gây hiểu nhầm.

Ngoài việc tổng hợp lại, module này bổ sung 2 logic nghiệp vụ MỚI (chưa
module nào tính) - mỗi cái đều được giải thích rõ tại hàm tương ứng bên
dưới:
1. HẠNG MỤC TRỄ TIẾN ĐỘ DỰ KIẾN (`_hang_muc_tre_tien_do`).
2. BẢN VẼ CHƯA CÓ PHIÊN BẢN CHÍNH THỨC (`_ban_ve_chua_co_phien_ban_chinh_thuc`).
"""

from datetime import date

from app.modules.dashboard import repository
from app.modules.banve import repository as banve_repository
from app.modules.banve import service as banve_service
from app.modules.nhansu.service import TRANG_THAI_LAM_VIEC
from app.modules.chiphi import service as chiphi_service
from app.modules.vatlieu import service as vatlieu_service

CHUA_XAC_DINH = 'Chưa xác định'
TRANG_THAI_HANG_MUC = ('Đang thi công', 'Quá hạn', 'Chưa khởi công', 'Chưa xác định')


def _phan_loai_hang_muc(hang_muc):
    """QUAN TRỌNG - đây KHÔNG phải 1 cột trạng thái có thật trong bảng
    `hangmuc` (bảng này không có cột nào lưu "trạng thái thi công" - xem
    README mục 7: cột `TrangThaiHoanThanh` ở schema cũ đã bị bỏ hẳn). 4 nhãn
    dưới đây chỉ là 1 cách PHÂN LOẠI TẠM THỜI do Dashboard tự suy ra từ 2
    cột ngày tháng CÓ THẬT (`NgayKhoiCong`, `ThoiGianHoanThanhDuKien`) để có
    cái nhìn nhanh, cùng chung giới hạn với cảnh báo `_hang_muc_tre_tien_do`
    bên dưới: KHÔNG khẳng định chắc chắn hạng mục có đang thi công/quá hạn
    thật hay không (VD: đã hoàn thành xong nhưng chưa cập nhật lại ngày vẫn
    sẽ bị xếp nhầm vào "Quá hạn"). Giao diện PHẢI ghi rõ giới hạn này ngay
    cạnh biểu đồ, không được trình bày như 1 trạng thái đã được xác nhận."""
    hom_nay = date.today()
    if hang_muc.ThoiGianHoanThanhDuKien and hang_muc.ThoiGianHoanThanhDuKien < hom_nay:
        return 'Quá hạn'
    if hang_muc.NgayKhoiCong and hang_muc.NgayKhoiCong <= hom_nay:
        return 'Đang thi công'
    if hang_muc.NgayKhoiCong and hang_muc.NgayKhoiCong > hom_nay:
        return 'Chưa khởi công'
    return 'Chưa xác định'


def _trang_thai_hang_muc():
    """Xem giới hạn quan trọng ở docstring của `_phan_loai_hang_muc` - đây
    là số liệu suy ra từ ngày tháng, không phải đếm theo 1 cột trạng thái
    có thật trong CSDL."""
    dem = {trang_thai: 0 for trang_thai in TRANG_THAI_HANG_MUC}
    for hang_muc in repository.danh_sach_hang_muc():
        dem[_phan_loai_hang_muc(hang_muc)] += 1
    return dem


def _nhan_su_theo_trang_thai_day_du():
    """Đảm bảo đủ mặt cả 3 trạng thái cố định (kể cả khi đang có 0 người ở
    trạng thái đó) + gộp riêng 1 nhóm "Chưa xác định" cho nhân sự chưa khai
    trạng thái (cột này không bắt buộc nhập) - để biểu đồ tròn luôn phản
    ánh đúng 100% số nhân sự, không bị "mất" người thiếu dữ liệu."""
    dem = {trang_thai: 0 for trang_thai in TRANG_THAI_LAM_VIEC}
    dem[CHUA_XAC_DINH] = 0
    for trang_thai, so_luong in repository.nhan_su_theo_trang_thai():
        khoa = trang_thai if trang_thai in TRANG_THAI_LAM_VIEC else CHUA_XAC_DINH
        dem[khoa] += so_luong
    return dem


def _phien_ban_theo_trang_thai_day_du():
    """dict {TenTrangThai: so_luong} - đã bảo đảm đủ 3 trạng thái nhờ LEFT
    JOIN từ phía bảng tra cứu ở repository."""
    return {ten: so_luong for _, ten, so_luong in repository.phien_ban_theo_trang_thai()}


def _hang_muc_vuot_ngan_sach():
    """Danh sách hạng mục GỐC có chi phí thực tế đã ghi nhận vượt ngân sách,
    xem module Chi phí) VƯỢT ngân sách đang có, sắp xếp vượt nhiều nhất lên
    đầu. Chỉ lấy hạng mục GỐC từ kết quả của
    `chiphi.service.lay_tong_hop_theo_hang_muc()` (hàm đó trả về TẤT CẢ
    hạng mục, cha lẫn con) vì số liệu của 1 hạng mục gốc đã CỘNG DỒN sẵn
    toàn bộ hạng mục con/cháu của nó - hiển thị luôn cả hạng mục con sẽ bị
    trùng lặp cảnh báo cho cùng 1 khoản vượt (con vượt thì cha chứa nó chắc
    chắn cũng vượt theo, không phải 2 sự việc độc lập)."""
    ma_hang_muc_goc = {hm.MaHangMuc for hm in repository.danh_sach_hang_muc_goc()}
    ket_qua = []
    for dong in chiphi_service.lay_tong_hop_theo_hang_muc():
        if dong['item'].MaHangMuc not in ma_hang_muc_goc or not dong['vuot']:
            continue
        ngan_sach = float(dong['ngan_sach'])
        da_su_dung = float(dong['chi_phi'])
        ket_qua.append({
            'MaHangMuc': dong['item'].MaHangMuc,
            'TenHangMuc': dong['item'].TenHangMuc,
            'NganSachDangCo': ngan_sach,
            'DaSuDung': da_su_dung,
            'ChiPhiThucTe': float(dong['chi_phi']),
            'PhanTramVuot': round((da_su_dung - ngan_sach) / ngan_sach * 100, 1) if ngan_sach > 0 else 0,
        })
    ket_qua.sort(key=lambda x: x['PhanTramVuot'], reverse=True)
    return ket_qua


def _ngan_sach_theo_hang_muc_goc():
    """[{MaHangMuc, TenHangMuc, NganSachDangCo, DaSuDung}, ...] cho TẤT CẢ
    hạng mục gốc (không chỉ hạng mục vượt) - dùng vẽ biểu đồ cột so sánh
    ngân sách đang có / đã sử dụng theo từng công trình. Lý do chỉ lấy cấp
    gốc: xem giải thích ở `_hang_muc_vuot_ngan_sach`."""
    ma_hang_muc_goc = {hm.MaHangMuc for hm in repository.danh_sach_hang_muc_goc()}
    ket_qua = []
    for dong in chiphi_service.lay_tong_hop_theo_hang_muc():
        if dong['item'].MaHangMuc not in ma_hang_muc_goc:
            continue
        ket_qua.append({
            'MaHangMuc': dong['item'].MaHangMuc,
            'TenHangMuc': dong['item'].TenHangMuc,
            'NganSachDangCo': float(dong['ngan_sach']),
            'DaSuDung': float(dong['chi_phi']),
        })
    ket_qua.sort(key=lambda x: x['MaHangMuc'])
    return ket_qua


def _hang_muc_tre_tien_do():
    """CẢNH BÁO MỚI (chưa module nào tính): hạng mục có `ThoiGianHoanThanhDuKien`
    đã qua ngày hôm nay, sắp xếp trễ lâu nhất lên đầu.

    GIỚI HẠN QUAN TRỌNG cần hiểu rõ: schema `mainDB_latest.sql` hiện KHÔNG còn
    cột nào lưu "hạng mục đã hoàn thành hay chưa" (cột `TrangThaiHoanThanh`
    ở schema cũ đã bị bỏ khi chuyển sang bảng `hangmuc` mới - xem README,
    mục "Module đã gỡ bỏ"). Vì vậy cảnh báo này CHỈ có thể dựa trên "đã qua
    ngày dự kiến hoàn thành" chứ KHÔNG thể khẳng định chắc chắn hạng mục đó
    có thật sự đang bị trễ hay đã hoàn thành xong nhưng chưa cập nhật lại
    ngày - đây là cảnh báo mang tính "cần người quản lý kiểm tra thủ công",
    không phải 1 khẳng định chắc chắn. Giao diện phải nói rõ giới hạn này
    (xem chú thích ở template)."""
    ket_qua = []
    for hm in repository.hang_muc_tre_tien_do():
        so_ngay_tre = (date.today() - hm.ThoiGianHoanThanhDuKien).days
        ket_qua.append({'item': hm, 'so_ngay_tre': so_ngay_tre})
    return ket_qua


def _ban_ve_chua_co_phien_ban_chinh_thuc():
    """CẢNH BÁO MỚI (chưa module nào tính): bản vẽ chưa có phiên bản nào ở
    trạng thái "Đã duyệt" - nghĩa là công trình hiện KHÔNG có hồ sơ bản vẽ
    chính thức nào cho hạng mục đó để thi công theo, dù có thể đã có phiên
    bản đang "Chờ duyệt" hoặc đã bị "Từ chối". Tái sử dụng đúng hàm
    `banve.service.phien_ban_hien_hanh()` (định nghĩa "phiên bản hiện hành"
    đã có sẵn ở module Bản vẽ) cho từng bản vẽ - giống cách
    `banve/routes.py` đã làm ở trang danh sách bản vẽ (chấp nhận lặp truy
    vấn nhỏ theo từng bản vẽ, vì đây là quy mô MVP và đã là tiền lệ có sẵn
    trong chính module Bản vẽ, không phải logic mới tự nghĩ ra thêm)."""
    ket_qua = []
    for bv in repository.danh_sach_ban_ve():
        if banve_service.phien_ban_hien_hanh(bv.MaBV) is None:
            ket_qua.append(bv)
    return ket_qua


def lay_so_lieu_tong_quan():
    tong_hang_muc = repository.dem_hang_muc()
    hang_muc_goc = repository.dem_hang_muc_goc()

    nhan_su_theo_trang_thai = _nhan_su_theo_trang_thai_day_du()
    phien_ban_theo_trang_thai = _phien_ban_theo_trang_thai_day_du()

    # Tái sử dụng nguyên hàm tổng hợp đã có ở module Chi phí (KHÔNG tính
    # lại) - xem giải thích ở docstring đầu file.
    tong_quan_chi_phi = chiphi_service.lay_tong_quan_chi_phi()
    trang_thai_hang_muc = _trang_thai_hang_muc()
    ngan_sach = float(tong_quan_chi_phi['tong_ngan_sach'])
    da_su_dung = float(tong_quan_chi_phi['tong_chi'])

    return {
        'the_so_lieu': {
            'so_hang_muc': tong_hang_muc,
            'so_hang_muc_goc': hang_muc_goc,
            'so_hang_muc_con': tong_hang_muc - hang_muc_goc,
            'so_vat_lieu': repository.dem_vat_lieu(),
            'so_nhan_su': repository.dem_nhan_su(),
            'so_phan_cong': repository.dem_phan_cong(),
            'so_ban_ve': repository.dem_ban_ve(),
            'so_phien_ban': repository.dem_phien_ban(),
            'so_chi_phi': tong_quan_chi_phi['so_dong_chi_phi'],
            'tong_chi_phi_thuc_te': float(tong_quan_chi_phi['tong_chi']),
            'tong_ngan_sach': ngan_sach,
            'tong_da_su_dung': da_su_dung,
            'so_hang_muc_dang_thi_cong': trang_thai_hang_muc['Đang thi công'],
            'so_hang_muc_qua_han': trang_thai_hang_muc['Quá hạn'],
        },
        'bieu_do': {
            'nhan_su_theo_trang_thai': nhan_su_theo_trang_thai,
            'phien_ban_theo_trang_thai': phien_ban_theo_trang_thai,
            'chi_phi_theo_loai': {loai: float(tien) for loai, tien in tong_quan_chi_phi['theo_loai'].items()},
            'ngan_sach_vs_da_su_dung': {
                'Đã sử dụng': da_su_dung,
                'Còn lại': max(ngan_sach - da_su_dung, 0),
                'Vượt ngân sách': max(da_su_dung - ngan_sach, 0),
            },
            'hang_muc_theo_trang_thai': trang_thai_hang_muc,
            'ngan_sach_theo_hang_muc_goc': _ngan_sach_theo_hang_muc_goc(),
        },
        'canh_bao': {
            'hang_muc_vuot_ngan_sach': _hang_muc_vuot_ngan_sach(),
            'vat_lieu_vuot_du_kien': vatlieu_service.danh_sach_vuot_du_kien(),
            'ban_ve_chua_co_phien_ban_chinh_thuc': _ban_ve_chua_co_phien_ban_chinh_thuc(),
            'hang_muc_tre_tien_do': _hang_muc_tre_tien_do(),
            'hang_muc_tien_do_thap': {
                'co_du_lieu': False,
                'thong_bao': 'Database hiện chưa có trường phần trăm tiến độ để đánh giá.',
            },
            'phien_ban_cho_duyet_lau_nhat': repository.phien_ban_dang_cho_duyet(
                banve_repository.CHO_DUYET
            ),
        },
    }
