ALTER TABLE `hashlists` ADD `parsed` BOOLEAN NOT NULL DEFAULT FALSE AFTER `errors`;
ALTER TABLE `hashlists` ADD `tmp_path` VARCHAR(1000) NOT NULL AFTER `parsed`;
ALTER TABLE `hashlists` CHANGE `tmp_path` `tmp_path` VARCHAR(1000) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL DEFAULT '';
ALTER TABLE `hashlists` ADD `status` ENUM('wait','parsing','errpath','sorting','preparedb','putindb','searchfound','ready') NOT NULL AFTER `tmp_path`, ADD `when_loaded` INT UNSIGNED NOT NULL AFTER `status`;
ALTER TABLE `task_works` CHANGE `status` `status` ENUM('wait','work','done','go_stop','stop','waitoutparse','outparsing') CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL DEFAULT 'stop';