ALTER TABLE `hashlists` CHANGE `common_by_alg` `common_by_alg` SMALLINT UNSIGNED NOT NULL DEFAULT '0';
ALTER TABLE `hashlists` ADD `last_finder_checked` INT NOT NULL DEFAULT '0' AFTER `common_by_alg`;
ALTER TABLE `algs` ADD `finder_insidepro_allowed` BOOLEAN NOT NULL DEFAULT FALSE AFTER `alg_id`;
