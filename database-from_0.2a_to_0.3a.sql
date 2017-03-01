ALTER TABLE `hashlists` CHANGE `common_by_alg` `common_by_alg` SMALLINT UNSIGNED NOT NULL DEFAULT '0';
ALTER TABLE `hashlists` ADD `last_finder_checked` INT NOT NULL DEFAULT '0' AFTER `common_by_alg`;
ALTER TABLE `algs` ADD `finder_insidepro_allowed` BOOLEAN NOT NULL DEFAULT FALSE AFTER `alg_id`;
UPDATE algs SET `finder_insidepro_allowed`=1;
CREATE TABLE `logs` (
  `id` int(10) UNSIGNED NOT NULL,
  `module` enum('main','worker','database','finderinsidepro','hashlist_common_loader','hashlist_loader','result_parser') NOT NULL,
  `timestamp` int(10) UNSIGNED NOT NULL DEFAULT '0',
  `message` varchar(5000) NOT NULL DEFAULT ''
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
ALTER TABLE `logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `timestamp` (`timestamp`),
  ADD KEY `source` (`module`);
ALTER TABLE `logs`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT;