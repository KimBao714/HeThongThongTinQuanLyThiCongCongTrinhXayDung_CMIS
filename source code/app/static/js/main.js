document.addEventListener('DOMContentLoaded', function () {
  var sidebar = document.getElementById('appSidebar');
  var toggleBtn = document.getElementById('sidebarToggleBtn');

  if (!sidebar || !toggleBtn) return;

  // Khôi phục trạng thái đóng/mở đã lưu lần trước
  var saved = localStorage.getItem('sidebar_collapsed');
  if (saved === 'true') {
    sidebar.classList.add('collapsed');
  }

  toggleBtn.addEventListener('click', function () {
    sidebar.classList.toggle('collapsed');
    localStorage.setItem('sidebar_collapsed', sidebar.classList.contains('collapsed'));
  });

  // Hiện ngày hôm nay ở topbar
  var dateEl = document.getElementById('topbarDate');
  if (dateEl) {
    var now = new Date();
    dateEl.textContent = now.toLocaleDateString('vi-VN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  }

  // Bấm vào menu cha (VD: "Công trình") để xổ/thu menu con
  document.querySelectorAll('.sidebar-nav-parent').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var group = btn.closest('.sidebar-nav-group');
      if (group) {
        group.classList.toggle('open');
      }
    });
  });

  // Các ô chọn ngày: hiện lịch popup nhưng hiển thị/nhập theo đúng dd/mm/yyyy
  // (input vẫn gửi lên server dạng yyyy-mm-dd để tương thích với route/DB cũ)
  if (typeof flatpickr !== 'undefined') {
    document.querySelectorAll('input.js-datepicker').forEach(function (el) {
      var tuyChon = {
        dateFormat: 'Y-m-d',
        altInput: true,
        altFormat: 'd/m/Y',
        allowInput: true,
        locale: (typeof flatpickr.l10ns !== 'undefined' && flatpickr.l10ns.vn) ? 'vn' : undefined
      };
      if (el.getAttribute('max')) { tuyChon.maxDate = el.getAttribute('max'); }
      if (el.getAttribute('min')) { tuyChon.minDate = el.getAttribute('min'); }
      flatpickr(el, tuyChon);
    });
  }
});
