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
from app.modules.hangmuc import service as hangmuc_service
from app.modules.nhansu.service import TRANG_THAI_LAM_VIEC
from app.modules.chiphi import service as chiphi_service
from app.modules.vatlieu import service as vatlieu_service

CHUA_XAC_DINH = 'Chưa xác định'
TRANG_THAI_HANG_MUC = ('Đang thi công', 'Quá hạn', 'Chưa khởi công', 'Chưa xác định')

# Mã đặc biệt (không trùng được với MaHangMuc thật - cột đó là mã do người
# dùng tự đặt cho 1 hạng mục cụ thể) đại diện cho lựa chọn "Tổng cộng (toàn
# dự án)" ở select box chọn hạng mục trên khối Ngân sách - xem
# `_ngan_sach_theo_hang_muc()` và `lay_so_lieu_tong_quan()`.
MA_TOAN_DU_AN = '__TOAN_DU_AN__'


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
    cạnh biểu đồ, không được trình bày như 1 trạng thái đã được xác nhận.

    THỨ TỰ KIỂM TRA (LỖI CŨ đã sửa): phải xét NGÀY KHỞI CÔNG so với HÔM NAY
    TRƯỚC TIÊN để biết hạng mục đã thật sự bắt đầu thi công hay chưa, rồi
    mới xét tiếp NGÀY DỰ KIẾN HOÀN THÀNH để kết luận "Quá hạn" - bản trước
    kiểm tra `ThoiGianHoanThanhDuKien < hôm nay` NGAY ĐẦU TIÊN, bất kể hạng
    mục đã khởi công hay chưa, nên 1 hạng mục CHƯA khởi công (NgayKhoiCong
    còn ở tương lai) nhưng lỡ có ngày dự kiến hoàn thành đã nằm trong quá
    khứ (VD: nhập kế hoạch cũ/sai) sẽ bị xếp NHẦM vào "Quá hạn" thay vì
    đúng ra phải là "Chưa khởi công". "Quá hạn" giờ chỉ được kết luận khi cả
    3 điều kiện cùng đúng: đã có ngày khởi công, ngày đó đã qua (đã bắt đầu
    thi công), VÀ ngày dự kiến hoàn thành cũng đã qua so với hôm nay."""
    hom_nay = date.today()
    da_khoi_cong = hang_muc.NgayKhoiCong is not None and hang_muc.NgayKhoiCong <= hom_nay
    chua_khoi_cong = hang_muc.NgayKhoiCong is not None and hang_muc.NgayKhoiCong > hom_nay

    if chua_khoi_cong:
        return 'Chưa khởi công'
    if da_khoi_cong:
        if hang_muc.ThoiGianHoanThanhDuKien and hang_muc.ThoiGianHoanThanhDuKien < hom_nay:
            return 'Quá hạn'
        return 'Đang thi công'
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


def _ngan_sach_theo_hang_muc():
    """[{MaHangMuc, TenHangMuc, Cap, LaGoc, NganSachDangCo, DaSuDungThucTe,
    DaSuDungUocTinh, ConLai, Vuot}, ...] cho TẤT CẢ hạng mục (cả gốc lẫn
    con/cháu - KHÔNG chỉ hạng mục gốc như bản trước) - phục vụ select box
    "Xem theo hạng mục" ở khối Ngân sách của Dashboard, để người dùng chọn
    ĐÚNG 1 hạng mục bất kỳ (không riêng cấp công trình) và xem ngân sách
    đang có/đã sử dụng của riêng hạng mục đó.

    Thứ tự trả về + `Cap` (cấp thụt lề) lấy ĐÚNG từ
    `hangmuc.service.lay_cay_hang_muc()` (hàm đã có sẵn, dùng để vẽ cây
    cha/con ở trang danh sách Hạng mục) - KHÔNG tự sắp xếp lại theo cách
    riêng, để select box hiển thị đúng thứ tự/thụt lề giống hệt module Hạng
    mục, tránh 2 nơi có 2 cách sắp xếp cây khác nhau.

    Số liệu ngân sách/đã dùng của TỪNG dòng lấy nguyên từ
    `chiphi.service.lay_tong_hop_theo_hang_muc()` (KHÔNG tính lại) - hàm đó
    đã tính đúng cho MỌI cấp hạng mục (không chỉ gốc), tự cộng dồn số liệu
    của hạng mục con/cháu vào hạng mục cha.

    Giữ nguyên đúng quy ước "2 con số tách biệt, không gộp" đã áp dụng toàn
    hệ thống (xem module Chi phí, mục 6b/6e ở README):
    - `DaSuDungThucTe`: tổng `SoTienChi` đã ghi nhận thủ công ở module Chi
      phí (giống hệt số dùng để tính `Vuot`/cảnh báo "Hạng mục vượt ngân
      sách" - xem `_hang_muc_vuot_ngan_sach` - để 2 khối này trên cùng 1
      trang luôn khớp nhau).
    - `DaSuDungUocTinh`: đơn giá x số lượng vật liệu đã dùng + chi phí thuê
      x ngày công nhân sự đã phân công, kể cả khi CHƯA ghi dòng chi phí
      chính thức nào.
    """
    theo_ma = {
        dong['item'].MaHangMuc: dong for dong in chiphi_service.lay_tong_hop_theo_hang_muc()
    }
    ket_qua = []
    for node in hangmuc_service.lay_cay_hang_muc():
        hang_muc = node['item']
        dong = theo_ma.get(hang_muc.MaHangMuc)
        if dong is None:
            continue
        ngan_sach = float(dong['ngan_sach'])
        da_su_dung_thuc_te = float(dong['chi_phi'])
        ket_qua.append({
            'MaHangMuc': hang_muc.MaHangMuc,
            'TenHangMuc': hang_muc.TenHangMuc,
            'Cap': node['cap'],
            'LaGoc': hang_muc.hangmuc_MaHangMuc == hang_muc.MaHangMuc,
            'NganSachDangCo': ngan_sach,
            'DaSuDungThucTe': da_su_dung_thuc_te,
            'DaSuDungUocTinh': float(dong['da_su_dung_uoc_tinh']),
            'ConLai': ngan_sach - da_su_dung_thuc_te,
            'Vuot': dong['vuot'],
        })
    return ket_qua


def _tong_da_su_dung_toan_bo(tong_quan_chi_phi):
    """'Đã sử dụng' cho thẻ KPI tổng quan "Ngân sách đang có" - CỘNG DỒN cả
    3 nguồn phát sinh chi phí của TẤT CẢ hạng mục: giá trị vật liệu đã dùng
    (`tong_vat_lieu`) + chi phí nhân công đã phân công (`tong_nhan_cong`) +
    chi phí đã ghi nhận thực tế (`tong_chi`, bảng `chiphi`). Đây LÀ con số
    khác với `tong_quan_chi_phi['tong_chi']` (chỉ tính riêng bảng `chiphi`)
    đang dùng ở thẻ KPI "Đã chi thực tế" cũng như ở khối Ngân sách theo hạng
    mục (`_ngan_sach_theo_hang_muc` - hàm đó tách riêng 2 con số ghi nhận
    thực tế/ước tính, không gộp) - ở ĐÂY, cho 1 con số tóm tắt DUY NHẤT ngay
    trên thẻ KPI, "đã sử dụng" phản ánh ĐẦY ĐỦ nguồn lực đã tiêu tốn, kể cả
    phần vật liệu/nhân công đã phân bổ nhưng có thể chưa được ghi thành 1
    dòng chi phí chính thức."""
    return float(
        tong_quan_chi_phi['tong_vat_lieu']
        + tong_quan_chi_phi['tong_nhan_cong']
        + tong_quan_chi_phi['tong_chi']
    )


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
    # "Đã sử dụng" tóm tắt cho thẻ KPI tổng quan Ngân sách - xem giải thích
    # đầy đủ ở docstring `_tong_da_su_dung_toan_bo` (khác với
    # `tong_chi_phi_thuc_te` ở thẻ KPI "Đã chi thực tế", vốn CHỈ tính riêng
    # bảng `chiphi`).
    da_su_dung = _tong_da_su_dung_toan_bo(tong_quan_chi_phi)

    # Dòng "Tổng cộng (toàn dự án)" - LUÔN đứng đầu danh sách/select box của
    # khối Ngân sách theo hạng mục (mã đặc biệt `MA_TOAN_DU_AN`, không thể
    # trùng với 1 MaHangMuc thật). Định nghĩa `Vuot`/`ConLai` dùng ĐÚNG cùng
    # 1 khái niệm "đã sử dụng" (ghi nhận thực tế - `tong_chi`) như từng dòng
    # hạng mục ở `_ngan_sach_theo_hang_muc()` bên dưới và như cảnh báo "Hạng
    # mục vượt ngân sách" (`_hang_muc_vuot_ngan_sach`) - KHÔNG dùng con số
    # `da_su_dung` gộp cả 3 nguồn ở trên (đó là con số CHỈ dành riêng cho 1
    # thẻ KPI tóm tắt), để tránh 2 khối cùng nói về "vượt ngân sách" trên
    # cùng 1 trang lại dựa trên 2 định nghĩa "đã sử dụng" khác nhau.
    tong_cong_ngan_sach = {
        'MaHangMuc': MA_TOAN_DU_AN,
        'TenHangMuc': 'Tổng cộng (toàn dự án)',
        'Cap': -1,
        'LaGoc': True,
        'NganSachDangCo': ngan_sach,
        'DaSuDungThucTe': float(tong_quan_chi_phi['tong_chi']),
        'DaSuDungUocTinh': float(tong_quan_chi_phi['tong_ngan_sach_su_dung']),
        'ConLai': ngan_sach - float(tong_quan_chi_phi['tong_chi']),
        'Vuot': float(tong_quan_chi_phi['tong_chi']) > ngan_sach,
    }

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
            'hang_muc_theo_trang_thai': trang_thai_hang_muc,
            'ngan_sach_theo_hang_muc': [tong_cong_ngan_sach] + _ngan_sach_theo_hang_muc(),
            'ma_toan_du_an': MA_TOAN_DU_AN,
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
