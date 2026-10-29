-- phpMyAdmin SQL Dump
-- version 5.2.0
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Aug 31, 2026 at 02:39 PM
-- Server version: 8.0.30
-- PHP Version: 8.1.10

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `db_darurat_112`
--
CREATE DATABASE IF NOT EXISTS `db_darurat_112` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `db_darurat_112`;

-- --------------------------------------------------------

--
-- Table structure for table `laporan_darurat`
--

CREATE TABLE IF NOT EXISTS `laporan_darurat` (
  `id_laporan` int NOT NULL AUTO_INCREMENT,
  `waktu_panggilan` datetime DEFAULT CURRENT_TIMESTAMP,
  `path_file_audio` varchar(255) DEFAULT NULL,
  `teks_transkrip` text,
  `kategori_darurat` varchar(100) DEFAULT NULL,
  `lokasi` varchar(255) DEFAULT NULL,
  `skala_bahaya` varchar(50) DEFAULT NULL,
  `status_penanganan` enum('Menunggu','Diproses','Selesai') DEFAULT 'Menunggu',
  PRIMARY KEY (`id_laporan`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `laporan_darurat`
--

INSERT INTO `laporan_darurat` (`id_laporan`, `waktu_panggilan`, `path_file_audio`, `teks_transkrip`, `kategori_darurat`, `lokasi`, `skala_bahaya`, `status_penanganan`) VALUES
(8, '2026-08-27 19:19:42', 'rekaman_darurat_1.mp3', 'Tolong ada kecelakaan besar disimpang 5 banyak korban.', 'Kecelakaan', 'Simpang 5', 'Tinggi', 'Menunggu'),
(9, '2026-08-28 17:06:09', 'streaming_sementara.webm', 'Halo satu satu dua tolong cepat Ada kebakaran besar di pasar atas bukti tinggi', 'Kebakaran', 'Pasar atas', 'Tinggi', 'Menunggu'),
(10, '2026-08-28 17:07:36', 'streaming_sementara.webm', 'Halo, satu-satu dua. Tolong disini ada kecelakaan yang melibatkan dua pengendara di pasar bawah begitu tinggi.', 'Kecelakaan', 'Pasar bawah', 'Tinggi', 'Menunggu'),
(11, '2026-08-28 17:32:11', 'streaming_sementara.webm', 'Halo, satu-satuh dua, terlalu cepat di sini ada maling', 'Kriminal', 'Di sini', 'Rendah', 'Menunggu'),
(12, '2026-08-29 14:17:41', 'streaming_sementara.webm', '1-1-2 tolong sini cepat ada kebakaran di pasar atas.', 'Kebakaran', 'Pasar atas', 'Tinggi', 'Menunggu'),
(13, '2026-08-31 08:54:24', 'streaming_sementara.webm', 'Alam, alam, alam, alam, alam, alam, alam.', 'Lainnya', 'Alam', 'Tinggi', 'Menunggu'),
(14, '2026-08-31 08:54:28', 'streaming_sementara.webm', '1-2, tolong cepat ke simpeng turku, kunding ada kebakaran tokoh, apinya mulai membesar', 'Kebakaran', 'Turku', 'Tinggi', 'Menunggu'),
(15, '2026-08-31 08:55:13', 'streaming_sementara.webm', 'Halo, satu-satuh dua tolong cepat kesingpang aur kuning ada kebakaran tokol, apinya mulai membesaran.', 'Kebakaran', 'Tokol', 'Tinggi', 'Menunggu'),
(16, '2026-08-31 09:26:58', 'streaming_sementara.webm', 'Halo, 1-1-2, tolong cepat ke aur kuning ada kebakaran tokoh, apinya mulai membasar.', 'Kebakaran', 'Aur Kuning', 'Tinggi', 'Menunggu'),
(17, '2026-08-31 09:35:15', 'streaming_sementara.webm', 'Halo, satu-satuh dua, tolong cepat ke simpang awr mening ada kecila kean besar.', 'Lainnya', 'Simpang Awr Mening', 'Rendah', 'Menunggu');

COMMIT;