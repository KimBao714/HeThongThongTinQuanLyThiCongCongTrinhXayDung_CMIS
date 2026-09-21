// JS riêng cho Dashboard tổng quan - vẽ các biểu đồ tròn bằng Chart.js
// (thư viện được tải qua CDN ngay trong template dashboard/index.html),
// và tự động fetch lại dữ liệu mới từ CSDL định kỳ (polling) để dashboard
// luôn phản ánh đúng số liệu hiện tại mà không cần người dùng tự F5.

const KHOANG_CACH_CAP_NHAT_MS = 20000; // 20 giây - đủ gần thời gian thực, không dội quá nhiều request lên server MVP.

// Bảng màu cố định theo Ý NGHĨA nhãn (không theo thứ tự ngẫu nhiên), để
// cùng 1 trạng thái luôn hiển thị cùng 1 màu ở mọi lần tải trang.
const MAU_THEO_NHAN = {
    // Nhân sự theo trạng thái: đổi sang bảng màu tương phản mạnh hơn để 4
    // trạng thái tách bạch rõ ràng trên biểu đồ tròn (trước đây "Tạm nghỉ"
    // và "Đã nghỉ việc" khá gần tông nhau, còn "Chưa xác định" quá nhạt,
    // gần như biến mất trên nền trắng).
    'Đang làm việc': '#16a34a',
    'Tạm nghỉ': '#f97316',
    'Đã nghỉ việc': '#ef4444',
    'Chưa xác định': '#a855f7',
    // Các thuộc tính còn lại (Hạng mục, Phiên bản, Chi phí, Ngân sách) - đổi
    // sang bảng màu rực và tương phản cao hơn so với bản cũ (navy/mù tạt
    // trầm) để nổi bật rõ trên nền trắng của biểu đồ, đồng bộ với các class
    // legend-* tương ứng trong dashboard.css.
    'Chờ duyệt': '#eab308',
    'Đã duyệt': '#22c55e',
    'Cũ': '#64748b',
    'Từ chối': '#dc2626',
    'Ngân sách đang có': '#14b8a6',
    'Nhân công': '#2563eb',
    'Vật liệu': '#eab308',
    'Khác': '#64748b',
};

const MAU_DU_PHONG = ['#2563eb', '#3b82f6', '#eab308', '#22c55e', '#dc2626', '#64748b'];

// Mỗi lần fragment được thay mới (polling), canvas cũ bị xóa khỏi DOM và
// canvas MỚI được tạo lại với cùng id - phải hủy Chart instance CŨ trước
// khi vẽ lên canvas mới, nếu không Chart.js sẽ giữ tham chiếu "rác" và có
// thể báo lỗi "Canvas is already in use".
const cacBieuDoDangVe = {};

function dangKyBieuDo(canvasId, chart) {
    cacBieuDoDangVe[canvasId] = chart;
}

function huyTatCaBieuDoCu() {
    Object.keys(cacBieuDoDangVe).forEach((id) => {
        try {
            cacBieuDoDangVe[id].destroy();
        } catch (err) {
            // Chart đã bị hủy hoặc canvas không còn trong DOM - bỏ qua.
        }
        delete cacBieuDoDangVe[id];
    });
}

function mauChoNhan(nhan, chiSo) {
    return MAU_THEO_NHAN[nhan] || MAU_DU_PHONG[chiSo % MAU_DU_PHONG.length];
}

function veBieuDoFallback(canvas, nhan, gtri, mau) {
    const width = canvas.clientWidth || 420;
    const height = canvas.height || 220;
    const tiLe = window.devicePixelRatio || 1;
    canvas.width = width * tiLe;
    canvas.height = height * tiLe;
    const context = canvas.getContext('2d');
    context.scale(tiLe, tiLe);
    const tong = gtri.reduce((tongHienTai, giaTri) => tongHienTai + giaTri, 0);
    const banKinh = Math.min(width, height) * 0.34;
    const tamX = width / 2;
    const tamY = height / 2;
    let gocBatDau = -Math.PI / 2;
    const giaTriVe = tong > 0 ? gtri : [1];
    const mauVe = tong > 0 ? mau : ['#c9cdd3'];
    giaTriVe.forEach((giaTri, chiSo) => {
        const gocKetThuc = gocBatDau + (giaTri / (tong || 1)) * Math.PI * 2;
        context.beginPath();
        context.moveTo(tamX, tamY);
        context.arc(tamX, tamY, banKinh, gocBatDau, gocKetThuc);
        context.closePath();
        context.fillStyle = mauVe[chiSo];
        context.fill();
        context.strokeStyle = '#fff';
        context.lineWidth = 2;
        context.stroke();
        gocBatDau = gocKetThuc;
    });
}

// Dự phòng cho biểu đồ CỘT khi Chart.js chưa tải được (CDN chậm/bị chặn) -
// tương tự veBieuDoFallback() ở trên nhưng vẽ cột thay vì hình tròn, để
// không có canvas nào bị bỏ trắng hoàn toàn chỉ vì thư viện ngoài chưa kịp
// load. Không cần trục/nhãn chi tiết - chỉ cần thấy được hình dạng số liệu,
// vì đây chỉ là phương án tạm trong lúc chờ Chart.js, không thay thế hẳn.
function veBieuDoFallbackCot(canvas, nhan, gtri, mau) {
    const width = canvas.clientWidth || 420;
    const height = canvas.height || 220;
    const tiLe = window.devicePixelRatio || 1;
    canvas.width = width * tiLe;
    canvas.height = height * tiLe;
    const context = canvas.getContext('2d');
    context.scale(tiLe, tiLe);

    const leTren = 12;
    const leDuoi = 28;
    const caoVe = height - leTren - leDuoi;
    const soCot = gtri.length || 1;
    const khoangCach = width / soCot;
    const beRongCot = Math.min(khoangCach * 0.5, 64);
    const gtriMax = Math.max(...gtri, 1);

    context.font = '11px sans-serif';
    context.textAlign = 'center';
    context.fillStyle = '#5b6472';

    gtri.forEach((giaTri, chiSo) => {
        const caoCot = gtriMax > 0 ? (giaTri / gtriMax) * caoVe : 0;
        const x = chiSo * khoangCach + (khoangCach - beRongCot) / 2;
        const y = leTren + (caoVe - caoCot);
        context.fillStyle = mau[chiSo % mau.length];
        context.beginPath();
        context.roundRect ? context.roundRect(x, y, beRongCot, caoCot, 4) : context.rect(x, y, beRongCot, caoCot);
        context.fill();

        context.fillStyle = '#093498';
        context.fillText(String(giaTri), x + beRongCot / 2, y - 4 >= 10 ? y - 4 : 10);

        context.fillStyle = '#5b6472';
        context.fillText(nhan[chiSo] || '', x + beRongCot / 2, height - leDuoi + 14);
    });
}

function veBieuDoTron(canvasId, duLieuDict, dinhDangSoLieu) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const nhan = Object.keys(duLieuDict);
    const gtri = nhan.map((k) => duLieuDict[k]);
    const mau = nhan.map((n, i) => mauChoNhan(n, i));
    if (typeof Chart === 'undefined') {
        veBieuDoFallback(canvas, nhan, gtri, mau);
        return;
    }

    // Nếu toàn bộ giá trị đều bằng 0 (chưa có dữ liệu), vẫn vẽ để không bị
    // trống trơn khó hiểu, kèm chú thích rõ ràng.
    const tongTatCa = gtri.reduce((a, b) => a + b, 0);

    const chart = new Chart(canvas, {
        type: 'pie',
        data: {
            labels: nhan,
            datasets: [{
                data: gtri,
                backgroundColor: mau,
                borderColor: '#fff',
                borderWidth: 2,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                // Đã có chú thích màu tĩnh (.chart-legend) render sẵn trong HTML ngay dưới
                // canvas - tắt legend riêng của Chart.js để tránh 2 chú thích trùng lặp.
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            const gt = ctx.parsed;
                            const phanTram = tongTatCa > 0 ? ((gt / tongTatCa) * 100).toFixed(1) : 0;
                            const soHienThi = dinhDangSoLieu === 'tien'
                                ? Number(gt).toLocaleString('vi-VN') + ' đ'
                                : gt;
                            return `${ctx.label}: ${soHienThi} (${phanTram}%)`;
                        },
                    },
                },
            },
        },
    });
    dangKyBieuDo(canvasId, chart);
}

// Biểu đồ CỘT đếm số hạng mục theo từng trạng thái suy ra từ ngày tháng
// (Đang thi công/Quá hạn/Chưa khởi công/Chưa xác định - xem
// `dashboard/service.py`, hàm `_phan_loai_hang_muc`).
function veBieuDoTrangThaiHangMuc(canvasId, duLieu) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const nhan = Object.keys(duLieu);
    const gtri = Object.values(duLieu);

    // QUAN TRỌNG: không được gán màu theo VỊ TRÍ index (mảng cố định) như
    // bản trước - vì `duLieu` đi qua Jinja `| tojson` ở _body.html, và
    // Flask mặc định sort_keys=True khi serialize dict sang JSON, nên thứ
    // tự khóa trả về bị xáo trộn theo alphabet (VD: "Chưa khởi công" luôn
    // đứng trước "Đang thi công" dù backend tạo dict theo thứ tự khác).
    // Nếu tô màu theo index, cột sẽ lệch màu so với chú thích cố định ở
    // _body.html (Đang thi công=xanh, Quá hạn=đỏ, Chưa khởi công=vàng,
    // Chưa xác định=xám) - đây chính là lỗi người dùng báo. Phải ánh xạ
    // màu theo TÊN nhãn để luôn khớp bất kể thứ tự khóa từ backend.
    const mauTheoNhan = {
        'Đang thi công': '#22c55e',
        'Quá hạn': '#dc2626',
        'Chưa khởi công': '#eab308',
        'Chưa xác định': '#64748b',
    };
    const mauMacDinh = '#64748b';
    const mauCoDinh = nhan.map((n) => mauTheoNhan[n] || mauMacDinh);

    // Chart.js tải qua CDN ngoài (xem index.html) - nếu chưa kịp tải xong
    // hoặc bị chặn mạng, KHÔNG được để canvas trống trơn như trước đây (đây
    // chính là lỗi đã gặp): vẽ tạm bằng Canvas thô, giống cách các biểu đồ
    // tròn khác (veBieuDoTron/veBieuDoNganSach) đã xử lý.
    if (typeof Chart === 'undefined') {
        veBieuDoFallbackCot(canvas, nhan, gtri, mauCoDinh);
        return;
    }

    const chart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: nhan,
            datasets: [{
                label: 'Số hạng mục',
                data: gtri,
                backgroundColor: mauCoDinh,
                borderRadius: 4,
            }],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
        },
    });
    dangKyBieuDo(canvasId, chart);
}

// Biểu đồ CỘT cho khối "Ngân sách đang có so với đã sử dụng theo hạng mục":
// thay vì vẽ TẤT CẢ hạng mục cạnh nhau trên 1 biểu đồ (bản trước, chỉ vẽ
// được cấp GỐC vì quá nhiều hạng mục con sẽ không đọc nổi trên 1 trục X),
// giờ người dùng CHỌN đúng 1 hạng mục bất kỳ (mọi cấp, qua select box
// #dashboard-chon-hang-muc) và biểu đồ chỉ vẽ 3 cột cho riêng hạng mục đó:
// Ngân sách đang có / Đã sử dụng (ghi nhận thực tế) / Đã sử dụng (ước tính
// từ phân bổ) - giữ đúng quy ước "2 con số đã sử dụng tách biệt, không gộp"
// đã áp dụng ở module Chi phí. Cột "Đã sử dụng (ghi nhận thực tế)" tô ĐỎ khi
// hạng mục đã vượt ngân sách (`dong.Vuot`), khớp với cảnh báo "Hạng mục vượt
// ngân sách" ở khối phía trên.
function veBieuDoNganSachHangMucDonLe(canvasId, dong) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !dong) return;

    const nhan = ['Ngân sách đang có', 'Đã sử dụng (ghi nhận thực tế)', 'Đã sử dụng (ước tính)'];
    const gtri = [dong.NganSachDangCo || 0, dong.DaSuDungThucTe || 0, dong.DaSuDungUocTinh || 0];
    const mau = ['#14b8a6', dong.Vuot ? '#dc2626' : '#2563eb', '#eab308'];

    if (typeof Chart === 'undefined') {
        veBieuDoFallbackCot(canvas, nhan, gtri, mau);
        return;
    }

    const chart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: nhan,
            datasets: [{
                data: gtri,
                backgroundColor: mau,
                borderRadius: 4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            const suffix = ctx.dataIndex === 1 && dong.Vuot ? ' (VƯỢT NGÂN SÁCH)' : '';
                            return `${Number(ctx.parsed.y).toLocaleString('vi-VN')} đ${suffix}`;
                        },
                    },
                },
            },
            scales: {
                y: { beginAtZero: true, ticks: { callback: (v) => Number(v).toLocaleString('vi-VN') } },
                x: { ticks: { autoSkip: false, maxRotation: 20, minRotation: 0 } },
            },
        },
    });
    dangKyBieuDo(canvasId, chart);
}

// Mã hạng mục hiện đang được chọn ở select box Ngân sách - giữ ở biến mức
// module (không phải trong DOM) để LƯU LẠI đúng lựa chọn của người dùng
// qua mỗi lần fragment bị thay mới lúc tự động cập nhật (polling) - nếu
// không, mỗi lần polling sẽ làm select box tự nhảy về lựa chọn đầu tiên
// ("Tổng cộng"), rất khó chịu khi người dùng đang xem 1 hạng mục cụ thể.
let maHangMucNganSachDangChon = null;

// Vẽ lại KPI (3 con số) + biểu đồ cột cho ĐÚNG hạng mục đang chọn ở select
// box. Nếu mã đang chọn không còn tồn tại trong danh sách mới (VD: hạng mục
// vừa bị xóa ở module Hạng mục) thì rơi về lựa chọn đầu tiên ("Tổng cộng").
function capNhatKhoiNganSachHangMuc(danhSach) {
    const select = document.getElementById('dashboard-chon-hang-muc');
    const khungKpi = document.getElementById('dashboard-hangmuc-ngansach-kpi');
    if (!danhSach || !danhSach.length) return;

    let ma = maHangMucNganSachDangChon;
    if (!ma || !danhSach.some((hm) => hm.MaHangMuc === ma)) {
        ma = danhSach[0].MaHangMuc;
    }
    maHangMucNganSachDangChon = ma;
    if (select) select.value = ma;

    const dong = danhSach.find((hm) => hm.MaHangMuc === ma) || danhSach[0];

    if (khungKpi) {
        const conLai = dong.ConLai || 0;
        const the_vuot = dong.Vuot
            ? `<span class="badge bg-danger">Vượt ${Number(-conLai).toLocaleString('vi-VN')} đ</span>`
            : `<span class="badge bg-success">Còn lại ${Number(conLai).toLocaleString('vi-VN')} đ</span>`;
        khungKpi.innerHTML = `
            <div class="budget-kpi-item">
                <span class="budget-kpi-label">Ngân sách đang có</span>
                <strong>${Number(dong.NganSachDangCo || 0).toLocaleString('vi-VN')} đ</strong>
            </div>
            <div class="budget-kpi-item">
                <span class="budget-kpi-label">Đã sử dụng (ghi nhận thực tế)</span>
                <strong class="${dong.Vuot ? 'text-danger' : ''}">${Number(dong.DaSuDungThucTe || 0).toLocaleString('vi-VN')} đ</strong>
            </div>
            <div class="budget-kpi-item">
                <span class="budget-kpi-label">Đã sử dụng (ước tính từ phân bổ)</span>
                <strong>${Number(dong.DaSuDungUocTinh || 0).toLocaleString('vi-VN')} đ</strong>
            </div>
            <div class="budget-kpi-item budget-kpi-item-badge">${the_vuot}</div>
        `;
    }

    veBieuDoNganSachHangMucDonLe('chartNganSachHangMuc', dong);
}

function ganSuKienChonHangMucNganSach(data) {
    const select = document.getElementById('dashboard-chon-hang-muc');
    if (!select) return;
    // Fragment (kể cả select bên trong) bị thay MỚI HOÀN TOÀN mỗi lần
    // polling - phải gắn lại sự kiện mỗi lần, listener cũ (nếu có) đã bị
    // xóa theo cùng phần tử DOM cũ nên không lo gắn trùng nhiều lần.
    select.addEventListener('change', function () {
        maHangMucNganSachDangChon = select.value;
        capNhatKhoiNganSachHangMuc(data.nganSachTheoHangMuc || []);
    });
}

function initDashboardCharts(data) {
    veBieuDoTrangThaiHangMuc('chartTrangThaiHangMuc', data.hangMucTheoTrangThai || {});
    // 3 biểu đồ tròn dưới đây tái sử dụng đúng dữ liệu tổng hợp đã tính sẵn ở
    // từng module gốc (Nhân sự, Bản vẽ, Chi phí) - dashboard KHÔNG tính lại,
    // chỉ vẽ ra để đồng bộ với những gì các module đó đang quản lý.
    veBieuDoTron('chartNhanSu', data.nhanSuTheoTrangThai || {});
    veBieuDoTron('chartPhienBan', data.phienBanTheoTrangThai || {});
    veBieuDoTron('chartChiPhiTheoLoai', data.chiPhiTheoLoai || {}, 'tien');
    capNhatKhoiNganSachHangMuc(data.nganSachTheoHangMuc || []);
    ganSuKienChonHangMucNganSach(data);
}

// ---------------------------------------------------------------------
// Cập nhật theo thời gian thực (polling định kỳ qua fetch)
// ---------------------------------------------------------------------

function docDuLieuBieuDoTuTrang() {
    const the = document.getElementById('dashboard-live-data');
    if (!the) return null;
    try {
        return JSON.parse(the.textContent);
    } catch (err) {
        console.error('Không đọc được dữ liệu biểu đồ Dashboard:', err);
        return null;
    }
}

function capNhatDongHoLamMoi(thanhCong) {
    const nhanThoiGian = document.getElementById('dashboard-refresh-time');
    const cham = document.getElementById('dashboard-refresh-indicator');
    if (nhanThoiGian) {
        nhanThoiGian.textContent = thanhCong
            ? new Date().toLocaleTimeString('vi-VN')
            : `${new Date().toLocaleTimeString('vi-VN')} (lỗi - đang hiển thị dữ liệu cũ)`;
    }
    if (cham) cham.classList.toggle('dashboard-refresh-dot-error', !thanhCong);
}

let dashboardTimerId = null;

function dungTuDongCapNhat() {
    if (dashboardTimerId) {
        clearInterval(dashboardTimerId);
        dashboardTimerId = null;
    }
}

async function capNhatDashboardTheoThoiGianThuc() {
    const root = document.getElementById('dashboard-live-root');
    const url = root ? root.dataset.refreshUrl : null;
    if (!root || !url) return;

    try {
        const res = await fetch(url, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            cache: 'no-store',
        });
        // res.redirected = true nghĩa là phiên làm việc đã hết hạn (server
        // chuyển hướng về trang chọn vai trò) - dừng tự động cập nhật, vì
        // fragment nhận được lúc này KHÔNG còn là dữ liệu Dashboard nữa.
        if (!res.ok || res.redirected) {
            capNhatDongHoLamMoi(false);
            dungTuDongCapNhat();
            return;
        }
        const html = await res.text();
        huyTatCaBieuDoCu();
        root.innerHTML = html;
        const duLieuMoi = docDuLieuBieuDoTuTrang();
        if (duLieuMoi) initDashboardCharts(duLieuMoi);
        capNhatDongHoLamMoi(true);
    } catch (err) {
        console.error('Lỗi khi tự động cập nhật Dashboard:', err);
        capNhatDongHoLamMoi(false);
    }
}

function batDauTuDongCapNhat() {
    dungTuDongCapNhat();
    dashboardTimerId = setInterval(capNhatDashboardTheoThoiGianThuc, KHOANG_CACH_CAP_NHAT_MS);
}

document.addEventListener('DOMContentLoaded', function () {
    const duLieuBanDau = docDuLieuBieuDoTuTrang();
    if (duLieuBanDau) initDashboardCharts(duLieuBanDau);

    const root = document.getElementById('dashboard-live-root');
    if (!root) return; // Không phải trang Dashboard - script vẫn được tải chung, không làm gì thêm.

    batDauTuDongCapNhat();

    const nutLamMoi = document.getElementById('dashboard-refresh-btn');
    if (nutLamMoi) {
        nutLamMoi.addEventListener('click', function () {
            capNhatDashboardTheoThoiGianThuc();
            batDauTuDongCapNhat(); // bấm thủ công thì tính lại chu kỳ 20s từ đầu, tránh cập nhật kép sát nhau.
        });
    }

    // Tạm dừng polling khi tab không hiển thị (đỡ tốn request vô ích), và
    // cập nhật ngay + chạy lại khi người dùng quay lại tab.
    document.addEventListener('visibilitychange', function () {
        if (document.hidden) {
            dungTuDongCapNhat();
        } else {
            capNhatDashboardTheoThoiGianThuc();
            batDauTuDongCapNhat();
        }
    });
});
