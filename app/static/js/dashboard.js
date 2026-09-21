// JS riêng cho Dashboard tổng quan - vẽ các biểu đồ tròn bằng Chart.js
// (thư viện được tải qua CDN ngay trong template dashboard/index.html),
// và tự động fetch lại dữ liệu mới từ CSDL định kỳ (polling) để dashboard
// luôn phản ánh đúng số liệu hiện tại mà không cần người dùng tự F5.

const KHOANG_CACH_CAP_NHAT_MS = 20000; // 20 giây - đủ gần thời gian thực, không dội quá nhiều request lên server MVP.

// Bảng màu cố định theo Ý NGHĨA nhãn (không theo thứ tự ngẫu nhiên), để
// cùng 1 trạng thái luôn hiển thị cùng 1 màu ở mọi lần tải trang.
const MAU_THEO_NHAN = {
    'Đang làm việc': '#2e9e5b',
    'Tạm nghỉ': '#d4af4a',
    'Đã nghỉ việc': '#9aa1ab',
    'Chưa xác định': '#c9cdd3',
    'Chờ duyệt': '#d4af4a',
    'Đã duyệt': '#2e9e5b',
    'Cũ': '#9aa1ab',
    'Từ chối': '#d9534f',
    'Ngân sách đang có': '#0f766e',
    'Nhân công': '#093498',
    'Vật liệu': '#d4af4a',
    'Khác': '#9aa1ab',
};

const MAU_DU_PHONG = ['#093498', '#2d52a7', '#d4af4a', '#2e9e5b', '#d9534f', '#9aa1ab'];

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

function veBieuDoNganSach(canvasId, duLieu) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    if (typeof Chart === 'undefined') {
        const nhan = Object.keys(duLieu);
        veBieuDoFallback(canvas, nhan, Object.values(duLieu), ['#2e9e5b', '#093498', '#d9534f']);
        return;
    }

    const chart = new Chart(canvas, {
        type: 'pie',
        data: {
            labels: Object.keys(duLieu),
            datasets: [
                { data: Object.values(duLieu), backgroundColor: ['#2e9e5b', '#093498', '#d9534f'] },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (ctx) { return `${ctx.label}: ${Number(ctx.parsed).toLocaleString('vi-VN')} đ`; },
                    },
                },
            },
        },
    });
    dangKyBieuDo(canvasId, chart);
}

function veBieuDoTrangThaiHangMuc(canvasId, duLieu) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;
    const chart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: Object.keys(duLieu),
            datasets: [{
                label: 'Số hạng mục',
                data: Object.values(duLieu),
                backgroundColor: ['#2e9e5b', '#d9534f', '#d4af4a', '#9aa1ab'],
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

function veBieuDoNganSachTheoHangMuc(canvasId, danhSach) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined' || !danhSach || !danhSach.length) return;

    const chart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: danhSach.map((hm) => hm.TenHangMuc),
            datasets: [
                {
                    label: 'Ngân sách đang có',
                    data: danhSach.map((hm) => hm.NganSachDangCo),
                    backgroundColor: '#0f766e',
                    borderRadius: 4,
                },
                {
                    label: 'Đã sử dụng',
                    data: danhSach.map((hm) => hm.DaSuDung),
                    backgroundColor: '#093498',
                    borderRadius: 4,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            return `${ctx.dataset.label}: ${Number(ctx.parsed.y).toLocaleString('vi-VN')} đ`;
                        },
                    },
                },
            },
            scales: { y: { beginAtZero: true, ticks: { callback: (v) => Number(v).toLocaleString('vi-VN') } } },
        },
    });
    dangKyBieuDo(canvasId, chart);
}

function initDashboardCharts(data) {
    veBieuDoNganSach('chartNganSach', data.nganSachVsDaSuDung || {});
    veBieuDoTrangThaiHangMuc('chartTrangThaiHangMuc', data.hangMucTheoTrangThai || {});
    // 3 biểu đồ tròn dưới đây tái sử dụng đúng dữ liệu tổng hợp đã tính sẵn ở
    // từng module gốc (Nhân sự, Bản vẽ, Chi phí) - dashboard KHÔNG tính lại,
    // chỉ vẽ ra để đồng bộ với những gì các module đó đang quản lý.
    veBieuDoTron('chartNhanSu', data.nhanSuTheoTrangThai || {});
    veBieuDoTron('chartPhienBan', data.phienBanTheoTrangThai || {});
    veBieuDoTron('chartChiPhiTheoLoai', data.chiPhiTheoLoai || {}, 'tien');
    veBieuDoNganSachTheoHangMuc('chartNganSachTheoHangMuc', data.nganSachTheoHangMucGoc || []);
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
