// JS riêng cho module Chi phí: lọc dropdown "Phân công" và "Sử dụng vật
// liệu" theo Hạng mục đã chọn, vì mỗi phân công / lượt sử dụng vật liệu chỉ
// thuộc đúng 1 hạng mục (xem quy tắc "nhất quán hạng mục" ở service.py).
//
// Đây CHỈ là hỗ trợ trải nghiệm nhập liệu (đỡ phải dò trong danh sách dài),
// KHÔNG thay thế việc kiểm tra ở tầng Business - nếu ai đó submit thẳng
// form bằng cách khác (bỏ qua JS), service.py vẫn chặn lại nếu dữ liệu
// không nhất quán.
document.addEventListener('DOMContentLoaded', function () {
  var chonHangMuc = document.getElementById('chonHangMuc');
  var chonPhanCong = document.getElementById('chonPhanCong');
  var chonVatLieu = document.getElementById('chonVatLieu');

  if (!chonHangMuc || !chonPhanCong || !chonVatLieu) return;

  function locTheoHangMuc(select, maHangMuc) {
    var giuNguyenLuaChon = false;
    Array.prototype.forEach.call(select.options, function (opt) {
      if (!opt.value) {
        opt.hidden = false;
        return;
      }
      var thuocHangMucDangChon = opt.getAttribute('data-hangmuc') === maHangMuc;
      opt.hidden = !thuocHangMucDangChon;
      if (thuocHangMucDangChon && opt.selected) {
        giuNguyenLuaChon = true;
      }
    });
    // Nếu lựa chọn cũ không còn thuộc hạng mục mới chọn thì reset về rỗng,
    // tránh gửi lên server 1 tổ hợp chắc chắn sẽ bị service.py từ chối.
    if (!giuNguyenLuaChon) {
      select.value = '';
    }
  }

  function capNhatBoLoc() {
    var maHangMuc = chonHangMuc.value;
    locTheoHangMuc(chonPhanCong, maHangMuc);
    locTheoHangMuc(chonVatLieu, maHangMuc);
  }

  chonHangMuc.addEventListener('change', capNhatBoLoc);
  capNhatBoLoc(); // áp dụng ngay khi tải trang (VD: khi Sửa đã có sẵn hạng mục)
});
