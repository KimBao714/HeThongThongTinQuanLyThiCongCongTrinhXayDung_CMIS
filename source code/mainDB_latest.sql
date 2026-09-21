-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: quanlythicong_ctdandung
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `banve`
--

DROP TABLE IF EXISTS `banve`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `banve` (
  `MaBV` varchar(20) NOT NULL,
  `LoaiBV` varchar(100) DEFAULT NULL,
  `TenBV` varchar(100) DEFAULT NULL,
  `hangmuc_hangmuc_MaHangMuc` varchar(20) NOT NULL,
  `hangmuc_hangmuc_hangmuc_MaHangMuc` varchar(20) NOT NULL,
  PRIMARY KEY (`MaBV`),
  KEY `fk_banve_hangmuc1_idx` (`hangmuc_hangmuc_MaHangMuc`,`hangmuc_hangmuc_hangmuc_MaHangMuc`),
  CONSTRAINT `fk_banve_hangmuc1` FOREIGN KEY (`hangmuc_hangmuc_MaHangMuc`) REFERENCES `hangmuc` (`MaHangMuc`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `banve`
--

LOCK TABLES `banve` WRITE;
/*!40000 ALTER TABLE `banve` DISABLE KEYS */;
INSERT INTO `banve` VALUES ('BV01','Kiến trúc','Kiến trúc','HM02-01','HM02-01');
/*!40000 ALTER TABLE `banve` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `chiphi`
--

DROP TABLE IF EXISTS `chiphi`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chiphi` (
  `MaCP` varchar(20) NOT NULL,
  `LoaiChiPhi` varchar(45) DEFAULT NULL,
  `NgayChi` date DEFAULT NULL,
  `SoTienChi` decimal(15,2) DEFAULT NULL,
  `MoTa` text,
  `phancong_MaPhanCong` varchar(20) NOT NULL,
  `sudungvatlieu_vatlieu_MaVL` varchar(10) NOT NULL,
  `sudungvatlieu_hangmuc_MaHangMuc` varchar(20) NOT NULL,
  `hangmuc_MaHangMuc` varchar(20) NOT NULL,
  PRIMARY KEY (`MaCP`),
  KEY `fk_chiphi_phancong1_idx` (`phancong_MaPhanCong`),
  KEY `fk_chiphi_sudungvatlieu1_idx` (`sudungvatlieu_vatlieu_MaVL`,`sudungvatlieu_hangmuc_MaHangMuc`),
  KEY `fk_chiphi_hangmuc1_idx` (`hangmuc_MaHangMuc`),
  CONSTRAINT `fk_chiphi_hangmuc1` FOREIGN KEY (`hangmuc_MaHangMuc`) REFERENCES `hangmuc` (`MaHangMuc`),
  CONSTRAINT `fk_chiphi_phancong1` FOREIGN KEY (`phancong_MaPhanCong`) REFERENCES `phancong` (`MaPhanCong`),
  CONSTRAINT `fk_chiphi_sudungvatlieu1` FOREIGN KEY (`sudungvatlieu_vatlieu_MaVL`, `sudungvatlieu_hangmuc_MaHangMuc`) REFERENCES `sudungvatlieu` (`vatlieu_MaVL`, `hangmuc_MaHangMuc`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `chiphi`
--

LOCK TABLES `chiphi` WRITE;
/*!40000 ALTER TABLE `chiphi` DISABLE KEYS */;
INSERT INTO `chiphi` VALUES ('NS01','Nhân công','2026-09-04',1000.00,'Chi phí nhân công đợt 1','PC796CAB670B78','VL01','HM01.01','HM01.01');
/*!40000 ALTER TABLE `chiphi` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `hangmuc`
--

DROP TABLE IF EXISTS `hangmuc`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `hangmuc` (
  `MaHangMuc` varchar(20) NOT NULL,
  `NganSachDangCo` decimal(15,2) DEFAULT NULL,
  `TenHangMuc` varchar(100) DEFAULT NULL,
  `NgayKhoiCong` date DEFAULT NULL,
  `ThoiGianHoanThanhDuKien` date DEFAULT NULL,
  `hangmuc_MaHangMuc` varchar(20) NOT NULL,
  PRIMARY KEY (`MaHangMuc`),
  KEY `fk_hangmuc_hangmuc1_idx` (`hangmuc_MaHangMuc`),
  CONSTRAINT `fk_hangmuc_hangmuc1` FOREIGN KEY (`hangmuc_MaHangMuc`) REFERENCES `hangmuc` (`MaHangMuc`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `hangmuc`
--

LOCK TABLES `hangmuc` WRITE;
/*!40000 ALTER TABLE `hangmuc` DISABLE KEYS */;
INSERT INTO `hangmuc` VALUES ('HM01',NULL,'Đổ sàn','2026-08-13','2026-09-13','HM01'),('HM01.01',NULL,'Do san tang tret','2026-08-31','2026-09-30','HM01'),('HM01.02',NULL,'Do san tang thuong','2026-08-12','2026-08-13','HM01'),('HM02',NULL,'Xây tầng trệt','2026-09-04','2026-10-04','HM02'),('HM02-01',NULL,'Thô','2026-09-05','2026-11-11','HM02'),('HM02-01-01',NULL,'Xây nền nhà','2026-09-06','2026-11-05','HM02-01');
/*!40000 ALTER TABLE `hangmuc` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `nhansu`
--

DROP TABLE IF EXISTS `nhansu`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nhansu` (
  `MaNV` varchar(10) NOT NULL,
  `HoNV` varchar(50) DEFAULT NULL,
  `TenNV` varchar(50) DEFAULT NULL,
  `NgayThangNamSinh` date DEFAULT NULL,
  `ChucVu` varchar(50) DEFAULT NULL,
  `TrangThaiLamViec` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`MaNV`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `nhansu`
--

LOCK TABLES `nhansu` WRITE;
/*!40000 ALTER TABLE `nhansu` DISABLE KEYS */;
INSERT INTO `nhansu` VALUES ('NS02','Trần Kim','Bảo','2004-01-07','Chủ đầu tư','Đang làm việc'),('NS03','Vũ Trần','Phương Anh','2005-01-01','Sếp','Đang làm việc'),('NS04','Trần Kim','Bảo','2004-01-07','Chủ đầu tư','Đang làm việc'),('NS05','Lê Triệu Đăng','Khánh','2003-12-05','Kỹ sư trưởng','Đang làm việc'),('NS67','','BO','2006-06-21','chỉ huy trưởng','Tạm nghỉ');
/*!40000 ALTER TABLE `nhansu` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `phancong`
--

DROP TABLE IF EXISTS `phancong`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `phancong` (
  `MaPhanCong` varchar(20) NOT NULL,
  `DiaDiemLamViec` varchar(100) DEFAULT NULL,
  `SoNgayCong` int DEFAULT NULL,
  `NgayBatDau` date DEFAULT NULL,
  `NgayKetThuc` date DEFAULT NULL,
  `hangmuc_MaHangMuc` varchar(20) NOT NULL,
  `nhansu_MaNV` varchar(10) NOT NULL,
  `ChiphiThue` decimal(15,2) DEFAULT NULL,
  `DonViTinh` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`MaPhanCong`),
  KEY `fk_phancong_hangmuc1_idx` (`hangmuc_MaHangMuc`),
  KEY `fk_phancong_nhansu1_idx` (`nhansu_MaNV`),
  CONSTRAINT `fk_phancong_hangmuc1` FOREIGN KEY (`hangmuc_MaHangMuc`) REFERENCES `hangmuc` (`MaHangMuc`),
  CONSTRAINT `fk_phancong_nhansu1` FOREIGN KEY (`nhansu_MaNV`) REFERENCES `nhansu` (`MaNV`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `phancong`
--

LOCK TABLES `phancong` WRITE;
/*!40000 ALTER TABLE `phancong` DISABLE KEYS */;
INSERT INTO `phancong` VALUES ('PC28D6F47DF47B','',2,NULL,NULL,'HM01.02','NS02',NULL,NULL),('PC796CAB670B78','',NULL,NULL,NULL,'HM01.01','NS02',NULL,NULL),('PCE0D05E097DF6','Nhà Bè',10000,'2026-08-27','2026-08-31','HM01.01','NS03',1000000.00,NULL),('PP3161816','',22,'2026-09-04','2026-11-05','HM02-01','NS05',69000.00,NULL);
/*!40000 ALTER TABLE `phancong` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `phienban`
--

DROP TABLE IF EXISTS `phienban`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `phienban` (
  `MaPB` varchar(20) NOT NULL,
  `SoPhienBan` varchar(20) DEFAULT NULL,
  `NgayTao` date DEFAULT NULL,
  `HinhBV` varchar(45) DEFAULT NULL,
  `HoNguoiTao` varchar(100) DEFAULT NULL,
  `TenNguoiTao` varchar(100) DEFAULT NULL,
  `NgayDuyet` date DEFAULT NULL,
  `banve_MaBV` varchar(20) NOT NULL,
  `trangthaiphienban_MaTrangThai` varchar(20) NOT NULL,
  PRIMARY KEY (`MaPB`),
  KEY `fk_phienban_banve1_idx` (`banve_MaBV`),
  KEY `fk_phienban_trangthaiphienban1_idx` (`trangthaiphienban_MaTrangThai`),
  CONSTRAINT `fk_phienban_banve1` FOREIGN KEY (`banve_MaBV`) REFERENCES `banve` (`MaBV`),
  CONSTRAINT `fk_phienban_trangthaiphienban1` FOREIGN KEY (`trangthaiphienban_MaTrangThai`) REFERENCES `trangthaiphienban` (`MaTrangThai`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `phienban`
--

LOCK TABLES `phienban` WRITE;
/*!40000 ALTER TABLE `phienban` DISABLE KEYS */;
INSERT INTO `phienban` VALUES ('PB57ED2AD49CDE','1','2026-09-04','521439f913bd422c.jpg','Trần Kim','Bảo','2026-09-04','BV01','DA_DUYET'),('PB9C3CEA1B39B0','2','2026-09-04','1a7541ee21764c1e.jpg','Trần Kim','Bảo','2026-09-04','BV01','DA_DUYET');
/*!40000 ALTER TABLE `phienban` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sudungvatlieu`
--

DROP TABLE IF EXISTS `sudungvatlieu`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sudungvatlieu` (
  `SoLuongSD` decimal(10,2) DEFAULT NULL,
  `vatlieu_MaVL` varchar(10) NOT NULL,
  `hangmuc_MaHangMuc` varchar(20) NOT NULL,
  PRIMARY KEY (`vatlieu_MaVL`,`hangmuc_MaHangMuc`),
  KEY `fk_sudungvatlieu_vatlieu1_idx` (`vatlieu_MaVL`),
  KEY `fk_sudungvatlieu_hangmuc1_idx` (`hangmuc_MaHangMuc`),
  CONSTRAINT `fk_sudungvatlieu_hangmuc1` FOREIGN KEY (`hangmuc_MaHangMuc`) REFERENCES `hangmuc` (`MaHangMuc`),
  CONSTRAINT `fk_sudungvatlieu_vatlieu1` FOREIGN KEY (`vatlieu_MaVL`) REFERENCES `vatlieu` (`MaVL`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sudungvatlieu`
--

LOCK TABLES `sudungvatlieu` WRITE;
/*!40000 ALTER TABLE `sudungvatlieu` DISABLE KEYS */;
INSERT INTO `sudungvatlieu` VALUES (200.00,'VL01','HM01.01'),(10.00,'VL01','HM02-01-01'),(100000.00,'VL02','HM02-01-01');
/*!40000 ALTER TABLE `sudungvatlieu` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `trangthaiphienban`
--

DROP TABLE IF EXISTS `trangthaiphienban`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `trangthaiphienban` (
  `MaTrangThai` varchar(20) NOT NULL,
  `TenTrangThai` varchar(50) DEFAULT NULL,
  `MoTa` longtext,
  PRIMARY KEY (`MaTrangThai`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `trangthaiphienban`
--

LOCK TABLES `trangthaiphienban` WRITE;
/*!40000 ALTER TABLE `trangthaiphienban` DISABLE KEYS */;
INSERT INTO `trangthaiphienban` VALUES ('CHO_DUYET','Chờ duyệt','Phiên bản vừa tải lên, đang chờ phê duyệt.'),('DA_DUYET','Đã duyệt','Phiên bản đã được phê duyệt chính thức.'),('TU_CHOI','Từ chối','Phiên bản bị từ chối, cần tải lên phiên bản mới.');
/*!40000 ALTER TABLE `trangthaiphienban` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `vatlieu`
--

DROP TABLE IF EXISTS `vatlieu`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `vatlieu` (
  `MaVL` varchar(10) NOT NULL,
  `TenVL` varchar(100) DEFAULT NULL,
  `SoLuongDangCo` decimal(10,2) DEFAULT NULL,
  `DonViTinh` varchar(45) DEFAULT NULL,
  `DonGia` decimal(15,2) DEFAULT NULL,
  PRIMARY KEY (`MaVL`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `vatlieu`
--

LOCK TABLES `vatlieu` WRITE;
/*!40000 ALTER TABLE `vatlieu` DISABLE KEYS */;
INSERT INTO `vatlieu` VALUES ('VL01','Xi mang',NULL,'bao',10000000.00),('VL02','Thép',NULL,'Thép',100000000.00);
/*!40000 ALTER TABLE `vatlieu` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-04 20:18:53
