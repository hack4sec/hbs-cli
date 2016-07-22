SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";

CREATE TABLE `algs` (
  `id` smallint(5) UNSIGNED NOT NULL,
  `name` varchar(45) NOT NULL,
  `alg_id` int(10) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `dicts` (
  `id` int(10) UNSIGNED NOT NULL,
  `group_id` int(10) UNSIGNED NOT NULL,
  `name` varchar(100) NOT NULL,
  `hash` varchar(32) NOT NULL,
  `comment` text NOT NULL,
  `size` int(10) UNSIGNED NOT NULL,
  `count` varchar(45) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `dicts_groups` (
  `id` int(10) UNSIGNED NOT NULL,
  `name` varchar(150) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `hashes` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `hashlist_id` int(10) UNSIGNED NOT NULL,
  `hash` varchar(250) NOT NULL,
  `salt` varchar(50) NOT NULL,
  `password` varchar(500) NOT NULL,
  `cracked` tinyint(1) NOT NULL,
  `summ` varchar(32) NOT NULL DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `hashlists` (
  `id` int(10) UNSIGNED NOT NULL,
  `name` varchar(100) NOT NULL,
  `alg_id` smallint(5) UNSIGNED NOT NULL,
  `have_salts` tinyint(1) NOT NULL DEFAULT '0',
  `delimiter` varchar(50) NOT NULL DEFAULT ':',
  `errors` longtext NOT NULL,
  `parsed` tinyint(1) NOT NULL DEFAULT '0',
  `tmp_path` varchar(1000) NOT NULL DEFAULT '',
  `status` enum('wait','parsing','errpath','sorting','preparedb','putindb','searchfound','ready') NOT NULL,
  `when_loaded` int(10) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `rules` (
  `id` mediumint(5) UNSIGNED NOT NULL,
  `name` varchar(100) NOT NULL,
  `hash` varchar(32) NOT NULL,
  `count` int(10) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `tasks` (
  `id` int(10) UNSIGNED NOT NULL,
  `name` varchar(150) DEFAULT NULL,
  `group_id` int(10) UNSIGNED NOT NULL,
  `type` enum('dict','mask','dictmask','maskdict') NOT NULL,
  `source` varchar(500) DEFAULT NULL,
  `rule` mediumint(8) UNSIGNED NOT NULL,
  `custom_charset1` varchar(500) DEFAULT NULL,
  `custom_charset2` varchar(500) DEFAULT NULL,
  `custom_charset3` varchar(500) DEFAULT NULL,
  `custom_charset4` varchar(500) DEFAULT NULL,
  `order` tinyint(3) UNSIGNED NOT NULL,
  `increment` tinyint(1) NOT NULL DEFAULT '0',
  `increment_min` int(11) NOT NULL DEFAULT '0',
  `increment_max` int(11) NOT NULL DEFAULT '0',
  `additional_params` varchar(500) NOT NULL DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `tasks_groups` (
  `id` int(10) UNSIGNED NOT NULL,
  `name` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `task_works` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `hashlist_id` int(10) UNSIGNED NOT NULL,
  `status` enum('wait','work','done','go_stop','stop','waitoutparse','outparsing') NOT NULL DEFAULT 'stop',
  `task_id` int(10) UNSIGNED NOT NULL,
  `uncracked_before` bigint(20) UNSIGNED NOT NULL,
  `uncracked_after` bigint(20) UNSIGNED NOT NULL,
  `session_name` varchar(32) NOT NULL DEFAULT '',
  `hc_status` varchar(255) NOT NULL,
  `hc_speed` varchar(255) NOT NULL,
  `hc_curku` varchar(255) NOT NULL,
  `hc_progress` varchar(255) NOT NULL,
  `hc_rechash` varchar(255) NOT NULL,
  `hc_temp` varchar(255) NOT NULL,
  `priority` int(10) UNSIGNED NOT NULL DEFAULT '0',
  `hybride_dict` varchar(500) NOT NULL,
  `out_file` varchar(500) NOT NULL DEFAULT '',
  `err_output` longtext NOT NULL,
  `path_stdout` varchar(2000) NOT NULL DEFAULT '',
  `process_status` enum('starting','work','compilehybride','compilecommand','loadhashes','buildhashlist','preparedicts') DEFAULT NULL,
  `stderr` text NOT NULL,
  `work_time` int(10) UNSIGNED NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

ALTER TABLE `algs`
  ADD PRIMARY KEY (`id`);

ALTER TABLE `dicts`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `hash` (`hash`),
  ADD KEY `group_id` (`group_id`);

ALTER TABLE `dicts_groups`
  ADD PRIMARY KEY (`id`);

ALTER TABLE `hashes`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `hashlist_id` (`hashlist_id`,`hash`,`salt`),
  ADD KEY `index2` (`hashlist_id`),
  ADD KEY `index3` (`cracked`),
  ADD KEY `summ` (`summ`);

ALTER TABLE `hashlists`
  ADD PRIMARY KEY (`id`),
  ADD KEY `index2` (`alg_id`);

ALTER TABLE `rules`
  ADD PRIMARY KEY (`id`);

ALTER TABLE `tasks`
  ADD PRIMARY KEY (`id`);

ALTER TABLE `tasks_groups`
  ADD PRIMARY KEY (`id`);

ALTER TABLE `task_works`
  ADD PRIMARY KEY (`id`),
  ADD KEY `hashlist_id` (`hashlist_id`),
  ADD KEY `priority` (`priority`);

ALTER TABLE `algs`
  MODIFY `id` smallint(5) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=0;

ALTER TABLE `dicts`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=0;

ALTER TABLE `dicts_groups`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=0;

ALTER TABLE `hashes`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=0;

ALTER TABLE `hashlists`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=0;

ALTER TABLE `rules`
  MODIFY `id` mediumint(5) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=0;

ALTER TABLE `tasks`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=0;

ALTER TABLE `tasks_groups`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=0;

ALTER TABLE `task_works`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=0;

INSERT INTO `algs` (`id`, `name`, `alg_id`) VALUES
(3, 'MD4', 900),
(4, 'MD5', 0),
(5, 'Half MD5', 5100),
(6, 'SHA1', 100),
(7, 'SHA-384', 10800),
(8, 'SHA-256', 1400),
(9, 'SHA-512', 1700),
(10, 'SHA-3(Keccak)', 5000),
(11, 'SipHash', 10100),
(12, 'RipeMD160', 6000),
(13, 'Whirlpool', 6100),
(14, 'GOST R 34.11-94', 6900),
(15, 'GOST R 34.11-2012 (Streebog) 256-bit', 11700),
(16, 'GOST R 34.11-2012 (Streebog) 512-bit', 11800),
(17, 'md5($pass.$salt)', 10),
(18, 'md5($salt.$pass)', 20),
(19, 'md5(unicode($pass).$salt)', 30),
(20, 'md5($salt.unicode($pass))', 40),
(21, 'md5($salt.$pass.$salt)', 3800),
(22, 'md5($salt.md5($pass))', 3710),
(23, 'md5(md5($pass)', 2600),
(24, 'md5(strtoupper(md5($pass)))', 4300),
(25, 'md5(sha1($pass))', 4400),
(26, 'sha1($pass.$salt)', 110),
(27, 'sha1($salt.$pass)', 120),
(28, 'sha1(unicode($pass).$salt)', 130),
(29, 'sha1($salt.unicode($pass))', 140),
(30, 'sha1(sha1($pass)', 4500),
(31, 'sha1(md5($pass))', 4700),
(32, 'sha1($salt.$pass.$salt)', 4900),
(33, 'sha256($pass.$salt)', 1410),
(34, 'sha256($salt.$pass)', 1420),
(35, 'sha256(unicode($pass).$salt)', 1430),
(36, 'sha256($salt.unicode($pass))', 1440),
(37, 'sha512($pass.$salt)', 1710),
(38, 'sha512($salt.$pass)', 1720),
(39, 'sha512(unicode($pass).$salt)', 1730),
(40, 'sha512($salt.unicode($pass))', 1740),
(41, 'HMAC-MD5 (key', 50),
(42, 'HMAC-MD5 (key', 60),
(43, 'HMAC-SHA1 (key', 150),
(44, 'HMAC-SHA1 (key', 160),
(45, 'HMAC-SHA256 (key', 1450),
(46, 'HMAC-SHA256 (key', 1460),
(47, 'HMAC-SHA512 (key', 1750),
(48, 'HMAC-SHA512 (key', 1760),
(49, 'phpass', 400),
(50, 'scrypt', 8900),
(51, 'PBKDF2-HMAC-MD5', 11900),
(52, 'PBKDF2-HMAC-SHA1', 12000),
(53, 'PBKDF2-HMAC-SHA256', 10900),
(54, 'PBKDF2-HMAC-SHA512', 12100),
(55, 'Skype', 23),
(56, 'WPA/WPA2', 2500),
(57, 'iSCSI CHAP authentication, MD5(Chap)', 4800),
(58, 'IKE-PSK MD5', 5300),
(59, 'IKE-PSK SHA1', 5400),
(60, 'NetNTLMv1', 5500),
(61, 'NetNTLMv1 + ESS', 5500),
(62, 'NetNTLMv2', 5600),
(63, 'IPMI2 RAKP HMAC-SHA1', 7300),
(64, 'Kerberos 5 AS-REQ Pre-Auth etype 23', 7500),
(65, 'DNSSEC (NSEC3)', 8300),
(66, 'Cram MD5', 10200),
(67, 'PostgreSQL Challenge-Response Authentication ', 11100),
(68, 'MySQL Challenge-Response Authentication (SHA1', 11200),
(69, 'SIP digest authentication (MD5)', 11400),
(70, 'SMF (Simple Machines Forum)', 121),
(71, 'phpBB3', 400),
(72, 'vBulletin < v3.8.5', 2611),
(73, 'vBulletin > v3.8.5', 2711),
(74, 'MyBB', 2811),
(75, 'IPB (Invison Power Board)', 2811),
(76, 'WBB3 (Woltlab Burning Board)', 8400),
(77, 'Joomla < 2.5.18', 11),
(78, 'Joomla > 2.5.18', 400),
(79, 'Wordpress', 400),
(80, 'PHPS', 2612),
(81, 'Drupal7', 7900),
(82, 'osCommerce', 21),
(83, 'xt:Commerce', 21),
(84, 'PrestaShop', 11000),
(85, 'Django (SHA-1)', 124),
(86, 'Django (PBKDF2-SHA256)', 10000),
(87, 'Mediawiki B type', 3711),
(88, 'Redmine', 7600),
(89, 'PostgreSQL', 12),
(90, 'MSSQL(2000)', 131),
(91, 'MSSQL(2005)', 132),
(92, 'MSSQL(2012)', 1731),
(93, 'MSSQL(2014)', 1731),
(94, 'MySQL323', 200),
(95, 'MySQL4.1/MySQL5', 300),
(96, 'Oracle H: Type (Oracle 7+)', 3100),
(97, 'Oracle S: Type (Oracle 11+)', 112),
(98, 'Oracle T: Type (Oracle 12+)', 12300),
(99, 'Sybase ASE', 8000),
(100, 'EPiServer 6.x < v4', 141),
(101, 'EPiServer 6.x > v4', 1441),
(102, 'Apache $apr1$', 1600),
(103, 'ColdFusion 10+', 12600),
(104, 'hMailServer', 1421),
(105, 'nsldap, SHA-1(Base64), Netscape LDAP SHA', 101),
(106, 'nsldaps, SSHA-1(Base64), Netscape LDAP SSHA', 111),
(107, 'SSHA-512(Base64), LDAP {SSHA512}', 1711),
(108, 'CRC32', 11500),
(109, 'LM', 3000),
(110, 'NTLM', 1000),
(111, 'Domain Cached Credentials (DCC), MS Cache', 1100),
(112, 'Domain Cached Credentials 2 (DCC2), MS Cache ', 2100),
(113, 'MS-AzureSync PBKDF2-HMAC-SHA256', 12800),
(114, 'descrypt, DES(Unix), Traditional DES', 1500),
(115, 'BSDiCrypt, Extended DES', 12400),
(116, 'md5crypt $1$, MD5(Unix)', 500),
(117, 'bcrypt $2*$, Blowfish(Unix)', 3200),
(118, 'sha256crypt $5$, SHA256(Unix)', 7400),
(119, 'sha512crypt $6$, SHA512(Unix)', 1800),
(120, 'OSX v10.4', 122),
(121, 'OSX v10.5', 122),
(122, 'OSX v10.6', 122),
(123, 'OSX v10.7', 1722),
(124, 'OSX v10.8', 7100),
(125, 'OSX v10.9', 7100),
(126, 'OSX v10.10', 7100),
(127, 'AIX {smd5}', 6300),
(128, 'AIX {ssha1}', 6700),
(129, 'AIX {ssha256}', 6400),
(130, 'AIX {ssha512}', 6500),
(131, 'Cisco-PIX', 2400),
(132, 'Cisco-ASA', 2410),
(133, 'Cisco-IOS $1$', 500),
(134, 'Cisco-IOS $4$', 5700),
(135, 'Cisco-IOS $8$', 9200),
(136, 'Cisco-IOS $9$', 9300),
(137, 'Juniper Netscreen/SSG (ScreenOS)', 22),
(138, 'Juniper IVE', 501),
(139, 'Android PIN', 5800),
(140, 'Citrix Netscaler', 8100),
(141, 'RACF', 8500),
(142, 'GRUB 2', 7200),
(143, 'Radmin2', 9900),
(144, 'SAP CODVN B (BCODE)', 7700),
(145, 'SAP CODVN F/G (PASSCODE)', 7800),
(146, 'SAP CODVN H (PWDSALTEDHASH) iSSHA-1', 10300),
(147, 'Lotus Notes/Domino 5', 8600),
(148, 'Lotus Notes/Domino 6', 8700),
(149, 'Lotus Notes/Domino 8', 9100),
(150, 'PeopleSoft', 133),
(151, '7-Zip', 11600),
(152, 'RAR3-hp', 12500),
(153, 'Android FDE < v4.3', 8800),
(154, 'eCryptfs', 12200),
(155, 'MS Office <', 9700),
(156, 'MS Office <', 9710),
(157, 'MS Office <', 9720),
(158, 'MS Office <', 9800),
(159, 'MS Office <', 9810),
(160, 'MS Office <', 9820),
(161, 'MS Office 2007', 9400),
(162, 'MS Office 2010', 9500),
(163, 'MS Office 2013', 9600),
(164, 'PDF 1.1 - 1.3 (Acrobat 2 - 4)', 10400),
(165, 'PDF 1.1 - 1.3 (Acrobat 2 - 4) + collider-mode', 10410),
(166, 'PDF 1.1 - 1.3 (Acrobat 2 - 4) + collider-mode', 10420),
(167, 'PDF 1.4 - 1.6 (Acrobat 5 - 8)', 10500),
(168, 'PDF 1.7 Level 3 (Acrobat 9)', 10600),
(169, 'PDF 1.7 Level 8 (Acrobat 10 - 11)', 10700),
(170, 'Password Safe v2', 9000),
(171, 'Password Safe v3', 5200),
(172, 'Lastpass', 6800),
(173, '1Password, agilekeychain', 6600),
(174, '1Password, cloudkeychain', 8200),
(175, 'Bitcoin/Litecoin wallet.dat', 11300),
(176, 'Blockchain, My Wallet', 12700);
