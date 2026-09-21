"""
Toàn bộ model khớp đúng tên bảng/cột trong file SQL gốc `mainDB_latest.sql`
(database `quanlythicong_ctdandung`).

Ghi chú quan trọng về bảng `hangmuc`:
- `hangmuc` thay thế hoàn toàn khái niệm "công trình" cũ (không còn bảng
  `ql_congtrinh`). Một hạng mục có thể là hạng mục gốc (công trình) hoặc
  hạng mục con của một hạng mục khác, thông qua khóa ngoại tự tham chiếu
  `hangmuc_MaHangMuc`.
- Cột `hangmuc_MaHangMuc` được khai báo NOT NULL trong file SQL gốc, tức
  MỌI hạng mục đều bắt buộc phải có "hạng mục cha" — kể cả hạng mục gốc
  (thường được quy ước tự trỏ vào chính nó, `hangmuc_MaHangMuc = MaHangMuc`).
  Đây là điểm cần lưu ý khi viết logic thêm mới ở tầng service sau này.

Ghi chú về bảng `banve`:
- Bảng gốc từng có 1 cột dư `hangmuc_hangmuc_hangmuc_MaHangMuc` sinh ra do công
  cụ dựng ERD tự suy luận từ khóa tự tham chiếu của `hangmuc` (không có ràng
  buộc FK nào, không phục vụ nghiệp vụ gì). Cột này đã được bỏ hẳn khỏi
  database thật đang dùng - model KHÔNG khai báo lại cột đó nữa để tránh lỗi
  "Unknown column" khi truy vấn.
"""

from app.extensions import db


class HangMuc(db.Model):
    __tablename__ = 'hangmuc'

    MaHangMuc = db.Column(db.String(20), primary_key=True)
    NganSachDangCo = db.Column(db.Numeric(15, 2))
    TenHangMuc = db.Column(db.String(100))
    NgayKhoiCong = db.Column(db.Date)
    ThoiGianHoanThanhDuKien = db.Column(db.Date)
    hangmuc_MaHangMuc = db.Column(db.String(20), db.ForeignKey('hangmuc.MaHangMuc'), nullable=False)

    # Quan hệ cha - con (self-referencing)
    hang_muc_con = db.relationship(
        'HangMuc',
        backref=db.backref('hang_muc_cha', remote_side=[MaHangMuc]),
        lazy=True
    )


class VatLieu(db.Model):
    __tablename__ = 'vatlieu'

    MaVL = db.Column(db.String(10), primary_key=True)
    TenVL = db.Column(db.String(100))
    SoLuongDangCo = db.Column(db.Numeric(10, 2))
    DonViTinh = db.Column(db.String(45))
    DonGia = db.Column(db.Numeric(15, 2))


class NhanSu(db.Model):
    __tablename__ = 'nhansu'

    MaNV = db.Column(db.String(10), primary_key=True)
    HoNV = db.Column(db.String(50))
    TenNV = db.Column(db.String(50))
    NgayThangNamSinh = db.Column(db.Date)
    ChucVu = db.Column(db.String(50))
    TrangThaiLamViec = db.Column(db.String(50))


class PhanCong(db.Model):
    __tablename__ = 'phancong'

    MaPhanCong = db.Column(db.String(20), primary_key=True)
    DiaDiemLamViec = db.Column(db.String(100))
    SoNgayCong = db.Column(db.Integer)
    NgayBatDau = db.Column(db.Date)
    NgayKetThuc = db.Column(db.Date)
    hangmuc_MaHangMuc = db.Column(db.String(20), db.ForeignKey('hangmuc.MaHangMuc'), nullable=False)
    nhansu_MaNV = db.Column(db.String(10), db.ForeignKey('nhansu.MaNV'), nullable=False)
    # Đơn giá thuê áp dụng riêng cho lần phân công này (khác nhân viên/hạng
    # mục có thể có đơn giá khác nhau). Dùng để tính chi phí nhân sự:
    # Số lượng công x đơn giá thuê; đơn vị nằm ở DonViTinh (ngày/tháng).
    ChiphiThue = db.Column(db.Numeric(15, 2))
    # Đơn vị tính của khối lượng công việc trong lần phân công này (vd:
    # Đơn vị tính của số lượng công (ngày hoặc tháng).
    DonViTinh = db.Column(db.String(45))

    hangmuc = db.relationship('HangMuc', backref='danh_sach_phancong', lazy=True)
    nhansu = db.relationship('NhanSu', backref='danh_sach_phancong', lazy=True)


class SuDungVatLieu(db.Model):
    __tablename__ = 'sudungvatlieu'

    SoLuongSD = db.Column(db.Numeric(10, 2))
    vatlieu_MaVL = db.Column(db.String(10), db.ForeignKey('vatlieu.MaVL'), primary_key=True)
    hangmuc_MaHangMuc = db.Column(db.String(20), db.ForeignKey('hangmuc.MaHangMuc'), primary_key=True)

    vatlieu = db.relationship('VatLieu', backref='danh_sach_su_dung', lazy=True)
    hangmuc = db.relationship('HangMuc', backref='danh_sach_vat_lieu_su_dung', lazy=True)


class ChiPhi(db.Model):
    __tablename__ = 'chiphi'

    MaCP = db.Column(db.String(20), primary_key=True)
    LoaiChiPhi = db.Column(db.String(45))
    NgayChi = db.Column(db.Date)
    SoTienChi = db.Column(db.Numeric(15, 2))
    MoTa = db.Column(db.Text)
    phancong_MaPhanCong = db.Column(db.String(20), db.ForeignKey('phancong.MaPhanCong'), nullable=False)
    sudungvatlieu_vatlieu_MaVL = db.Column(db.String(10), nullable=False)
    sudungvatlieu_hangmuc_MaHangMuc = db.Column(db.String(20), nullable=False)
    hangmuc_MaHangMuc = db.Column(db.String(20), db.ForeignKey('hangmuc.MaHangMuc'), nullable=False)

    __table_args__ = (
        db.ForeignKeyConstraint(
            ['sudungvatlieu_vatlieu_MaVL', 'sudungvatlieu_hangmuc_MaHangMuc'],
            ['sudungvatlieu.vatlieu_MaVL', 'sudungvatlieu.hangmuc_MaHangMuc']
        ),
    )

    phancong = db.relationship('PhanCong', backref='danh_sach_chiphi', lazy=True)
    hangmuc = db.relationship('HangMuc', backref='danh_sach_chiphi', lazy=True)
    su_dung_vat_lieu = db.relationship(
        'SuDungVatLieu',
        backref='danh_sach_chiphi',
        lazy=True,
        foreign_keys=[sudungvatlieu_vatlieu_MaVL, sudungvatlieu_hangmuc_MaHangMuc]
    )


class BanVe(db.Model):
    __tablename__ = 'banve'

    MaBV = db.Column(db.String(20), primary_key=True)
    LoaiBV = db.Column(db.String(100))
    TenBV = db.Column(db.String(100))
    hangmuc_hangmuc_MaHangMuc = db.Column(db.String(20), db.ForeignKey('hangmuc.MaHangMuc'), nullable=False)

    hangmuc = db.relationship('HangMuc', backref='danh_sach_banve', lazy=True)


class TrangThaiPhienBan(db.Model):
    __tablename__ = 'trangthaiphienban'

    MaTrangThai = db.Column(db.String(20), primary_key=True)
    TenTrangThai = db.Column(db.String(50))
    MoTa = db.Column(db.Text)


class PhienBan(db.Model):
    __tablename__ = 'phienban'

    MaPB = db.Column(db.String(20), primary_key=True)
    SoPhienBan = db.Column(db.String(20))
    NgayTao = db.Column(db.Date)
    HinhBV = db.Column(db.String(45))
    HoNguoiTao = db.Column(db.String(100))
    TenNguoiTao = db.Column(db.String(100))
    NgayDuyet = db.Column(db.Date)
    banve_MaBV = db.Column(db.String(20), db.ForeignKey('banve.MaBV'), nullable=False)
    trangthaiphienban_MaTrangThai = db.Column(db.String(20), db.ForeignKey('trangthaiphienban.MaTrangThai'), nullable=False)

    banve = db.relationship('BanVe', backref='danh_sach_phienban', lazy=True)
    trang_thai = db.relationship('TrangThaiPhienBan', backref='danh_sach_phienban', lazy=True)
