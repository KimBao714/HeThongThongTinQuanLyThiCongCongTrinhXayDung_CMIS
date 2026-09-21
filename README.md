# Hệ thống Quản lý Thi công Công trình Dân dụng — MVP

## 1. Cài thư viện
```
pip install -r requirements.txt
```

## 2. Chuẩn bị database
Import file `mainDB_latest.sql`:
```
mysql -u root -p < "mainDB_latest.sql"
```

## 3. Cấu hình kết nối
Sửa `config.py` hoặc set biến môi trường:
```
export MYSQL_USER=root
export MYSQL_PASSWORD=matkhau_cua_ban
export MYSQL_DB=quanlythicong_ctdandung
```

## 4. Chạy chương trình
```
python run.py
```
Mở trình duyệt: http://127.0.0.1:5000

## 5. Module hiện có

| Module | Route | Ghi chú |
|---|---|---|
| Hạng mục | `/hangmuc` | Khớp bảng `hangmuc` (cây cha/con) |
| Vật liệu | `/vatlieu` | Khớp bảng `vatlieu` + `sudungvatlieu` — mỗi vật liệu có thể được ghi nhận sử dụng cho nhiều hạng mục con, kèm số lượng và so sánh với số lượng dự kiến (xem mục 6d) |
| Nhân sự | `/nhansu` | Khớp bảng `nhansu` (đã bỏ cột `ChiPhiThue` — không còn trong schema mới) |
| Bản vẽ | `/banve` | Khớp bảng `banve` + `phienban` + `trangthaiphienban` — mỗi bản vẽ có nhiều phiên bản, mỗi phiên bản có quy trình duyệt/từ chối riêng (xem mục 6) |
| Chi phí | `/chiphi` | Khớp bảng `chiphi` — mỗi dòng chi phí gắn với 1 hạng mục + 1 phân công + 1 lượt sử dụng vật liệu đã có sẵn, có so sánh với ngân sách dự kiến (xem mục 6b) |
| Dashboard tổng quan | `/dashboard` | Không có bảng riêng — chỉ đọc và tổng hợp lại số liệu/logic đã có ở các module trên, KHÔNG tính lại (xem mục 6e) |

Đăng nhập/phân quyền theo vai trò (`vaitro`) không phụ thuộc DB, vẫn giữ
nguyên như trước.

## 6. Logic nghiệp vụ module Bản vẽ

Bảng `phienban` không có ràng buộc nào tự đảm bảo được quy trình duyệt bản
vẽ, nên toàn bộ được xử lý ở tầng `service.py`:

- **Tạo bản vẽ mới bắt buộc phải tải file lên ngay** — hệ thống tự tạo
  luôn phiên bản v1 kèm file đó trong CÙNG 1 lần lưu (không tách 2 bước như
  trước). Không cho tạo 1 bản vẽ "rỗng" chưa có file nào, vì 1 bản vẽ không
  có file đính kèm thì không có giá trị sử dụng thực tế. Nếu việc lưu file
  thất bại (thiếu file, sai định dạng...) thì bản vẽ cũng KHÔNG được tạo —
  tránh để lại bản vẽ mồ côi không có phiên bản nào.
- Mỗi lần tải file bản vẽ lên là 1 **phiên bản** mới; `SoPhienBan` và
  `NgayTao` do hệ thống tự sinh, không cho nhập tay.
- Phiên bản mới luôn khởi tạo ở trạng thái **Chờ duyệt**; chỉ vai trò toàn
  quyền mới được **Duyệt** (gán `NgayDuyet`) hoặc **Từ chối**.
- Phiên bản đã ở trạng thái cuối (Đã duyệt/Từ chối) không được duyệt/từ
  chối lại — muốn sửa phải tải lên phiên bản mới, giữ nguyên lịch sử.
- Không xóa được phiên bản **Đã duyệt** (giữ toàn vẹn hồ sơ chính thức);
  các phiên bản khác khi xóa sẽ xóa luôn file vật lý trên đĩa.
- Không xóa được 1 bản vẽ khi vẫn còn phiên bản (vì luôn có sẵn v1 ngay từ
  lúc tạo, nên phải xóa hết phiên bản trước mới xóa được bản vẽ).
- Mỗi bản vẽ chỉ được có **tối đa 1 phiên bản đang Chờ duyệt** tại 1 thời
  điểm (áp dụng ngay từ v1) — phải duyệt/từ chối phiên bản đang chờ trước
  khi tải phiên bản kế tiếp (v2, v3, ... — vào trang "Phiên bản" của bản vẽ
  đó, không phải trang tạo mới).
- **Phiên bản hiện hành** = phiên bản Đã duyệt có số phiên bản lớn nhất.
- Bảng tra cứu `trangthaiphienban` (rỗng trong file SQL gốc) được hệ thống
  tự seed 3 dòng cố định (`CHO_DUYET`, `DA_DUYET`, `TU_CHOI`) khi khởi động
  app — xem `app/modules/banve/repository.py`.

## 6b. Logic nghiệp vụ module Chi phí

Bảng `chiphi` trong `mainDB_latest.sql` có 1 điểm đặc biệt cần lưu ý: ngoài
`hangmuc_MaHangMuc`, còn có 2 cột `phancong_MaPhanCong` và cặp
`sudungvatlieu_vatlieu_MaVL` + `sudungvatlieu_hangmuc_MaHangMuc` đều
**NOT NULL và có ràng buộc khóa ngoại thật**. Nghĩa là:

> Theo đúng CSDL, **mọi** dòng chi phí đều bắt buộc phải gắn với **đúng 1
> phân công nhân sự đã có sẵn** và **đúng 1 lượt sử dụng vật liệu đã có
> sẵn** — không phải kiểu "chi phí nhân công *hoặc* chi phí vật liệu" như
> cách hiểu thông thường. Cột `LoaiChiPhi` chỉ mang tính phân loại để báo
> cáo, không thay đổi được ràng buộc bắt buộc chọn cả 2 tham chiếu trên.

**Hệ quả quan trọng**: bảng `phancong` và `sudungvatlieu` phải có dữ liệu
từ trước thì mới thêm được chi phí. Việc thêm/sửa/xóa 2 bảng này thuộc về
module Nhân sự (`/nhansu/<mã>/phan-cong`, xem mục 6c) và module Vật liệu
(`/vatlieu/<mã>/su-dung`, xem mục 6d) — module Chi phí chỉ *đọc* dữ liệu có
sẵn ở 2 bảng đó để hiển thị lên dropdown chọn, không có quyền thêm/sửa/xóa
chúng. Nếu 2 bảng này còn trống, màn hình "Thêm chi phí" sẽ hiện cảnh báo
và không thể lưu được — cần tạo phân công/lượt sử dụng vật liệu trước ở 2
module tương ứng.

Các quy tắc nghiệp vụ khác được xử lý ở `service.py` (CSDL không tự đảm
bảo được):

- Số tiền chi (`SoTienChi`) phải > 0.
- Ngày chi (`NgayChi`) không được là ngày trong tương lai.
- `LoaiChiPhi` giới hạn theo danh sách cố định (`Nhân công` / `Vật liệu` /
  `Khác`) để đồng nhất khi tổng hợp báo cáo — cột này trong CSDL là
  `varchar(45)` tự do, không có ràng buộc `CHECK` hay bảng tra cứu riêng.
- **Nhất quán hạng mục**: phân công và lượt sử dụng vật liệu được chọn
  phải **cùng thuộc hạng mục** đã chọn cho dòng chi phí. CSDL không kiểm
  tra được việc này (3 cột hạng mục ở 3 bảng hoàn toàn độc lập nhau), nên
  nếu không chặn ở tầng Business, dữ liệu có thể ghi nhận vô lý — ví dụ chi
  phí khai báo cho "Hạng mục A" nhưng lại trỏ tới phân công/vật liệu thực
  tế đang dùng cho "Hạng mục B". Trên giao diện, việc chọn hạng mục trước
  sẽ tự động lọc bớt 2 dropdown còn lại (`static/js/chiphi.js`) để hỗ trợ
  nhập liệu, nhưng việc kiểm tra thật sự luôn nằm ở `service.py` — kể cả
  khi ai đó submit form theo cách khác bỏ qua JS.
- Xóa chi phí không bị giới hạn gì thêm — không có bảng nào khác trong
  schema đặt khóa ngoại trỏ tới `chiphi`.
- So sánh chi phí thực tế lũy kế của 1 hạng mục với `NganSachDangCo` khai
  báo ở bảng `hangmuc`, hiển thị ở trang danh sách khi lọc theo đúng 1
  hạng mục — cảnh báo khi tổng chi đã vượt ngân sách dự kiến. Hạng mục
  chưa khai báo ngân sách thì chỉ hiển thị số đã chi, không tính được tỉ lệ %.

## 6c. Logic nghiệp vụ module Nhân sự (đã gộp Phân công)

Module Nhân sự (`/nhansu`) giờ quản lý gộp cả `nhansu` và `phancong`
(Phân công), vì `phancong` là **thực thể kết hợp** (associative entity)
sinh ra từ quan hệ nhiều-nhiều giữa `hangmuc` và `nhansu` — mỗi phân công
gắn 1 nhân sự với 1 hạng mục trong 1 khoảng thời gian. Hướng thiết kế: xem
phân công **từ góc nhìn 1 nhân sự** ("người này đang/đã làm ở những hạng
mục nào") — trang `/nhansu/<mã>/phan-cong` để xem/thêm/sửa/xóa.

Khác với `sudungvatlieu` (khóa chính là khóa kép, không có mã riêng),
`phancong` có mã riêng (`MaPhanCong`, tự sinh) nên 1 cặp (nhân sự, hạng
mục) vẫn có thể lặp lại ở các đợt thời gian khác nhau — không đặt ràng
buộc unique theo cặp, mà kiểm soát bằng ràng buộc **chồng lịch** bên dưới.

Quy tắc nghiệp vụ:

- `TrangThaiLamViec` giới hạn 3 giá trị cố định (Đang làm việc / Tạm nghỉ /
  Đã nghỉ việc) — đồng nhất dữ liệu, cột CSDL là văn bản tự do.
- **Không xóa được nhân sự khi còn phân công** — phải xóa hết phân công
  của người đó trước (tương tự quy tắc chặn xóa hạng mục còn con).
- **Chỉ phân công vào hạng mục CON** (có hạng mục cha cụ thể, không phải
  hạng mục gốc/công trình) — hạng mục gốc là cấp quản lý tổng thể, công
  việc thực tế luôn diễn ra ở hạng mục con.
- **Chỉ nhân sự "Đang làm việc" mới nhận phân công mới** — nhân sự tạm
  nghỉ/đã nghỉ việc không hợp lý để giao việc mới (phân công cũ của họ vẫn
  giữ nguyên, chỉ chặn thêm mới).
- Ngày bắt đầu ≤ ngày kết thúc (nếu khai báo cả 2); số ngày công > 0; chi
  phí thuê không âm (nếu có nhập).
- **Không trùng lịch**: 1 nhân sự không thể có 2 phân công chồng lấn thời
  gian làm việc (không thể "làm 2 nơi cùng lúc"). CSDL không kiểm tra được
  việc này (mỗi phân công là 1 dòng độc lập), nên phải tự so sánh ở tầng
  Business — chỉ so sánh được khi cả 2 phân công đều có đủ ngày bắt
  đầu/kết thúc; phân công thiếu ngày thì bỏ qua kiểm tra.
- **Xóa phân công bị chặn nếu đã có chi phí** (`chiphi`) tham chiếu tới nó
  — khớp với ràng buộc khóa ngoại thật `fk_chiphi_phancong1` trong
  `mainDB_latest.sql`, chặn ở đây để báo lỗi thân thiện thay vì để CSDL tự
  chặn bằng `IntegrityError`.

**Hiển thị 2 chiều**: trang danh sách Nhân sự hiển thị badge mã hạng mục
mà từng người đang làm; ngược lại, trang danh sách Hạng mục (module
`hangmuc`) hiển thị số lượng + danh sách tên nhân sự đang phân công cho
từng hạng mục (đọc dữ liệu `phancong` trực tiếp, không có quyền
thêm/sửa/xóa — quyền đó chỉ thuộc module Nhân sự).

## 6d. Logic nghiệp vụ module Vật liệu (đã gộp Sử dụng vật liệu)

Module Vật liệu (`/vatlieu`) giờ quản lý gộp cả `vatlieu` và
`sudungvatlieu` (Sử dụng vật liệu), theo đúng tinh thần đã áp dụng cho
`phancong` ở module Nhân sự (mục 6c): `sudungvatlieu` là **thực thể kết
hợp** (associative entity) sinh ra từ quan hệ nhiều-nhiều giữa `vatlieu` và
`hangmuc` — mỗi dòng ghi nhận 1 loại vật liệu được dùng bao nhiêu cho 1
hạng mục cụ thể. Hướng thiết kế: xem việc sử dụng **từ góc nhìn 1 vật
liệu** ("vật liệu này đang dùng cho những hạng mục nào, số lượng bao
nhiêu") — trang `/vatlieu/<mã>/su-dung` để xem/thêm/sửa/xóa.

Khác với `phancong` (có mã riêng `MaPhanCong`, tự sinh, nên 1 cặp nhân
sự-hạng mục có thể lặp lại ở nhiều đợt thời gian khác nhau), khóa chính của
`sudungvatlieu` là **khóa kép** (`vatlieu_MaVL`, `hangmuc_MaHangMuc`) — tức
1 vật liệu chỉ có đúng 1 dòng cho mỗi hạng mục, không lặp lại theo thời
gian. Muốn ghi nhận thêm vật liệu dùng vào đợt sau cho cùng hạng mục đó,
phải **sửa (cộng dồn số lượng vào)** dòng đã có, không tạo dòng mới.

Quy tắc nghiệp vụ:

- **Không xóa được vật liệu khi còn hạng mục đang sử dụng** — phải xóa hết
  các lượt sử dụng của vật liệu đó trước (tương tự quy tắc chặn xóa nhân sự
  còn phân công / hạng mục còn con).
- **Chỉ ghi nhận sử dụng vào hạng mục CON** (có hạng mục cha cụ thể, không
  phải hạng mục gốc/công trình) — *logic nghiệp vụ bổ sung*, áp dụng lại
  đúng lý do đã dùng cho `phancong`: hạng mục gốc là cấp quản lý tổng thể,
  việc thi công thực tế (và do đó tiêu hao vật liệu) luôn diễn ra ở hạng
  mục con.
- Số lượng sử dụng (`SoLuongSD`) phải > 0.
- **Trùng cặp (vật liệu, hạng mục) thì tự cộng dồn** — vì khóa chính là
  khóa kép, nếu hạng mục đã có dòng ghi nhận vật liệu này rồi, form "Thêm"
  tự động cộng dồn số lượng mới vào dòng đã có (UPDATE), không tạo dòng
  mới — không cần người dùng tự tìm dòng cũ để sửa thủ công, và CSDL cũng
  không bao giờ tự chặn bằng `IntegrityError` ở thao tác này.
- **Không cho đổi vật liệu/hạng mục khi sửa** (2 cột này là khóa chính) —
  form Sửa chỉ cho phép đổi số lượng sử dụng, để tránh rủi ro đổi khóa
  chính của 1 dòng đang được `chiphi` tham chiếu tới.
- **Xóa 1 lượt sử dụng bị chặn nếu đã có chi phí** (`chiphi`) tham chiếu
  tới nó — khớp với ràng buộc khóa ngoại thật `fk_chiphi_sudungvatlieu1`
  trong `mainDB_latest.sql`, chặn ở đây để báo lỗi thân thiện thay vì để CSDL
  tự chặn bằng `IntegrityError`.
- **Cảnh báo (không chặn) khi tổng số lượng đã dùng vượt `SoLuongDangCo`** (số
  lượng dự kiến) khai báo ở bảng `vatlieu` — *logic nghiệp vụ bổ sung*, mô
  phỏng đúng cách module Chi phí so sánh chi phí thực tế với
  `NganSachDangCo` (mục 6b). Vật liệu chưa khai báo số lượng dự kiến thì
  chỉ hiển thị số đã dùng, không tính được tỉ lệ %.

**Hiển thị 2 chiều**: trang danh sách Vật liệu hiển thị badge mã hạng mục
mà từng vật liệu đang được dùng, kèm cảnh báo nếu đã dùng vượt số lượng dự
kiến; ngược lại, trang danh sách Hạng mục (module `hangmuc`) hiển thị số
loại + danh sách tên vật liệu đang dùng cho từng hạng mục kèm số lượng (đọc
dữ liệu `sudungvatlieu` trực tiếp, không có quyền thêm/sửa/xóa — quyền đó
chỉ thuộc module Vật liệu).

## 6e. Logic nghiệp vụ Dashboard tổng quan

Dashboard (`/dashboard`) là module CHỈ ĐỌC, không có bảng CSDL riêng, không
cho thêm/sửa/xóa gì. Nguyên tắc thiết kế quan trọng nhất: **tái sử dụng
đúng logic nghiệp vụ đã có ở từng module gốc, không tính lại**. Cụ thể gọi
lại `chiphi.service.lay_tong_quan_chi_phi()` / `lay_tong_hop_theo_hang_muc()`,
`vatlieu.service.danh_sach_vuot_du_kien()`, và
`banve.service.phien_ban_hien_hanh()` thay vì viết lại các phép so sánh
ngân sách/số lượng dự kiến theo công thức riêng — tránh tình trạng con số ở
Dashboard lệch với con số ở trang chi tiết của chính module đó.

- **2 con số chi phí tách biệt, không gộp làm 1**: "Đã chi thực tế" (tổng
  `SoTienChi` các dòng chi phí đã ghi nhận thủ công) và "Ước tính từ phân
  bổ" (đơn giá × số lượng vật liệu đã dùng + chi phí thuê × ngày công nhân
  sự đã phân công, kể cả khi CHƯA ghi dòng chi phí chính thức nào) là 2
  khái niệm khác nhau đã có sẵn ở module Chi phí (mục 6b) — Dashboard hiển
  thị cả hai kèm giải thích, thay vì gộp lại gây hiểu nhầm.
- **Hạng mục vượt ngân sách**: chỉ hiển thị ở cấp **hạng mục GỐC** (không
  hiển thị cả hạng mục con), vì số liệu "đã sử dụng" của Chi phí đã CỘNG
  DỒN sẵn toàn bộ hạng mục con/cháu vào hạng mục cha — hiển thị thêm hạng
  mục con sẽ trùng lặp cùng 1 khoản vượt.
- **Vật liệu vượt số lượng dự kiến** *(mới thêm vào Dashboard)*: tái sử
  dụng nguyên logic đã có ở module Vật liệu (mục 6d), chỉ thêm 1 hàm gộp
  truy vấn cho TOÀN BỘ vật liệu trong 1 lần (`danh_sach_vuot_du_kien()`)
  để tránh N+1 query, trước đây chưa hiển thị ở đâu khác ngoài trang chi
  tiết từng vật liệu.
- **Bản vẽ chưa có phiên bản chính thức** *(mới thêm vào Dashboard)*: bản
  vẽ chưa có phiên bản nào ở trạng thái Đã duyệt (dù có thể đang chờ hoặc
  đã bị từ chối) — nghĩa là hạng mục đó hiện KHÔNG có hồ sơ bản vẽ chính
  thức nào để thi công theo. Tái sử dụng đúng định nghĩa "phiên bản hiện
  hành" đã có ở module Bản vẽ (mục 6).
- **Hạng mục trễ tiến độ dự kiến** *(logic hoàn toàn mới, chưa module nào
  tính)*: hạng mục có `ThoiGianHoanThanhDuKien` đã qua ngày hôm nay. **Giới
  hạn quan trọng**: schema mới không còn cột nào lưu "đã hoàn thành hay
  chưa" (cột `TrangThaiHoanThanh` ở schema cũ đã bị bỏ — xem mục 7), nên
  cảnh báo này chỉ mang tính "cần kiểm tra thủ công", không khẳng định
  chắc chắn hạng mục đang trễ — giao diện có ghi rõ giới hạn này.
- **Biểu đồ cột "Ngân sách dự kiến / đã sử dụng theo công trình"**: chỉ vẽ
  ở cấp hạng mục gốc, cùng lý do với mục "hạng mục vượt ngân sách" ở trên
  (tránh trùng lặp giá trị cộng dồn giữa cha và con trên cùng 1 biểu đồ).

## 6f. Logic nghiệp vụ module Hạng mục (bổ sung)

Ngoài các quy tắc đã có từ trước (cây cha/con qua khóa tự tham chiếu, chặn
vòng lặp cha/con, chặn xóa khi còn hạng mục con hoặc còn bị tham chiếu bởi
bản vẽ/phân công/sử dụng vật liệu/chi phí — xem docstring đầu
`app/modules/hangmuc/service.py`), module này còn kiểm tra:

- **`ThoiGianHoanThanhDuKien` không được trước `NgayKhoiCong`** — cả 2
  trường đều tùy chọn (CSDL cho phép NULL) nên chỉ so sánh khi CẢ HAI đã
  được khai báo. Lý do cần chặn: nếu không, dữ liệu vô nghĩa kiểu "hạng mục
  dự kiến hoàn thành trước cả ngày khởi công" có thể lọt vào hệ thống, kéo
  theo cảnh báo "Hạng mục trễ tiến độ dự kiến" ở Dashboard (mục 6e) hiển
  thị sai ngay từ lúc nhập liệu.

## 7. Module đã gỡ bỏ / còn thiếu (chờ xây dựng theo schema mới)

| Module | Tình trạng |
|---|---|
| `congtrinh` | Đã gỡ — dựa trên `QlCongTrinh`, bảng này không còn tồn tại, đã bị thay bằng `hangmuc` (hạng mục phân cấp cha/con qua khóa tự tham chiếu). Chức năng "nhìn tổng quan" mà module này từng đảm nhiệm nay do module `dashboard` (mục 6e) phụ trách, xây dựng lại hoàn toàn theo schema mới. |
| `tiendo` | Đã gỡ — dựa trên `QlTienDo` với `TiLeHoanThanh`/`TrangThaiHoanThanh`, 2 cột này không còn tồn tại trong `hangmuc` mới. Đây cũng là lý do cảnh báo "trễ tiến độ" ở Dashboard (mục 6e) chỉ mang tính tham khảo, không khẳng định chắc chắn. |

`models.py` hiện đã có sẵn model cho toàn bộ bảng trong schema mới
(`HangMuc`, `BanVe`, `PhienBan`, `TrangThaiPhienBan`, `ChiPhi`, `PhanCong`,
`SuDungVatLieu`, `VatLieu`, `NhanSu`) — tất cả các bảng hiện đều đã có
module quản lý (`hangmuc`, `vatlieu`, `nhansu`, `banve`, `chiphi`), cộng
thêm module tổng hợp `dashboard` không có bảng riêng.

## 8. Cấu trúc thư mục
```
qlct_erp/
├── run.py
├── config.py
├── app/
│   ├── extensions.py
│   ├── models.py                <- khớp đúng tên bảng/cột trong mainDB_latest.sql
│   ├── utils.py                 <- hàm dùng chung (parse ngày tháng, xử lý file upload)
│   ├── modules/
│   │   ├── hangmuc/{routes,service,repository}.py
│   │   ├── vatlieu/{routes,service,repository}.py
│   │   ├── nhansu/{routes,service,repository}.py
│   │   ├── banve/{routes,service,repository}.py   <- bản vẽ + phiên bản + duyệt/từ chối
│   │   └── chiphi/{routes,service,repository}.py  <- chi phí (đọc thêm phancong + sudungvatlieu)
│   ├── templates/
│   │   └── base.html            <- layout sidebar bên phải, đóng/mở được
│   └── static/
│       ├── css/  (main.css dùng chung + 1 file css riêng cho mỗi module)
│       ├── js/   (main.js dùng chung + 1 file js riêng cho mỗi module)
│       └── uploads/banve/       <- file bản vẽ vật lý (tạo tự động khi chạy app)
```

## 9. Giao diện
- Sidebar nằm bên phải, bấm icon ☰ để đóng/mở, trạng thái được nhớ lại (localStorage)
- Màu chủ đạo: xanh navy đậm (#1b2a4a) + vàng nhạt (#f4c95d)
- Bootstrap 5 (CDN) làm nền, style riêng nằm trong `static/css/main.css`
