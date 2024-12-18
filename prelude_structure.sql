/*M!999999\- enable the sandbox mode */ 

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


DROP TABLE IF EXISTS `Prelude_Action`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Action` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_index` tinyint(4) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `category` enum('block-installed','notification-sent','taken-offline','other') NOT NULL,
  PRIMARY KEY (`_message_ident`,`_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_AdditionalData`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_AdditionalData` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent_type` enum('A','H') NOT NULL,
  `_index` tinyint(4) NOT NULL,
  `type` enum('boolean','byte','character','date-time','integer','ntpstamp','portlist','real','string','byte-string','xml') NOT NULL,
  `meaning` varchar(255) DEFAULT NULL,
  `data` blob NOT NULL,
  PRIMARY KEY (`_parent_type`,`_message_ident`,`_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Address`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Address` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent_type` enum('A','H','S','T') NOT NULL,
  `_parent0_index` smallint(6) NOT NULL,
  `_index` tinyint(4) NOT NULL,
  `ident` varchar(255) DEFAULT NULL,
  `category` enum('unknown','atm','e-mail','lotus-notes','mac','sna','vm','ipv4-addr','ipv4-addr-hex','ipv4-net','ipv4-net-mask','ipv6-addr','ipv6-addr-hex','ipv6-net','ipv6-net-mask') NOT NULL,
  `vlan_name` varchar(255) DEFAULT NULL,
  `vlan_num` int(10) unsigned DEFAULT NULL,
  `address` varchar(255) NOT NULL,
  `netmask` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`_parent_type`,`_message_ident`,`_parent0_index`,`_index`),
  KEY `prelude_address_index_address` (`_parent_type`,`_parent0_index`,`_index`,`address`(10))
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Alert`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Alert` (
  `_ident` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `messageid` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`_ident`),
  KEY `prelude_alert_messageid` (`messageid`)
) ENGINE=InnoDB AUTO_INCREMENT=11648 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Alertident`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Alertident` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_index` int(11) NOT NULL,
  `_parent_type` enum('T','C') NOT NULL,
  `alertident` varchar(255) NOT NULL,
  `analyzerid` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`_parent_type`,`_message_ident`,`_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Analyzer`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Analyzer` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent_type` enum('A','H') NOT NULL,
  `_index` tinyint(4) NOT NULL,
  `analyzerid` varchar(255) DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `manufacturer` varchar(255) DEFAULT NULL,
  `model` varchar(255) DEFAULT NULL,
  `version` varchar(255) DEFAULT NULL,
  `class` varchar(255) DEFAULT NULL,
  `ostype` varchar(255) DEFAULT NULL,
  `osversion` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`_parent_type`,`_message_ident`,`_index`),
  KEY `prelude_analyzer_analyzerid` (`_parent_type`,`_index`,`analyzerid`),
  KEY `prelude_analyzer_index_model` (`_parent_type`,`_index`,`model`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_AnalyzerTime`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_AnalyzerTime` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent_type` enum('A','H') NOT NULL,
  `time` datetime NOT NULL,
  `usec` int(10) unsigned NOT NULL,
  `gmtoff` int(11) NOT NULL,
  PRIMARY KEY (`_parent_type`,`_message_ident`),
  KEY `prelude_analyzertime_index` (`_parent_type`,`time`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Assessment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Assessment` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  PRIMARY KEY (`_message_ident`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Checksum`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Checksum` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent0_index` smallint(6) NOT NULL,
  `_parent1_index` tinyint(4) NOT NULL,
  `_index` tinyint(4) NOT NULL,
  `algorithm` enum('MD4','MD5','SHA1','SHA2-256','SHA2-384','SHA2-512','CRC-32','Haval','Tiger','Gost') NOT NULL,
  `value` varchar(255) NOT NULL,
  `checksum_key` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`_message_ident`,`_parent0_index`,`_parent1_index`,`_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Classification`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Classification` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `ident` varchar(255) DEFAULT NULL,
  `text` varchar(255) NOT NULL,
  PRIMARY KEY (`_message_ident`),
  KEY `prelude_classification_index_text` (`text`(40))
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Confidence`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Confidence` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `confidence` float DEFAULT NULL,
  `rating` enum('low','medium','high','numeric') NOT NULL,
  PRIMARY KEY (`_message_ident`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_CorrelationAlert`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_CorrelationAlert` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `name` varchar(255) NOT NULL,
  PRIMARY KEY (`_message_ident`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_CreateTime`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_CreateTime` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent_type` enum('A','H') NOT NULL,
  `time` datetime NOT NULL,
  `usec` int(10) unsigned NOT NULL,
  `gmtoff` int(11) NOT NULL,
  PRIMARY KEY (`_parent_type`,`_message_ident`),
  KEY `prelude_createtime_index` (`_parent_type`,`time`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_DetectTime`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_DetectTime` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `time` datetime NOT NULL,
  `usec` int(10) unsigned NOT NULL,
  `gmtoff` int(11) NOT NULL,
  PRIMARY KEY (`_message_ident`),
  KEY `prelude_detecttime_index` (`time`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_File`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_File` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent0_index` smallint(6) NOT NULL,
  `_index` tinyint(4) NOT NULL,
  `ident` varchar(255) DEFAULT NULL,
  `path` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `category` enum('current','original') DEFAULT NULL,
  `create_time` datetime DEFAULT NULL,
  `create_time_gmtoff` int(11) DEFAULT NULL,
  `modify_time` datetime DEFAULT NULL,
  `modify_time_gmtoff` int(11) DEFAULT NULL,
  `access_time` datetime DEFAULT NULL,
  `access_time_gmtoff` int(11) DEFAULT NULL,
  `data_size` int(10) unsigned DEFAULT NULL,
  `disk_size` int(10) unsigned DEFAULT NULL,
  `fstype` enum('ufs','efs','nfs','afs','ntfs','fat16','fat32','pcfs','joliet','iso9660') DEFAULT NULL,
  `file_type` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`_message_ident`,`_parent0_index`,`_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_FileAccess`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_FileAccess` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent0_index` smallint(6) NOT NULL,
  `_parent1_index` tinyint(4) NOT NULL,
  `_index` tinyint(4) NOT NULL,
  PRIMARY KEY (`_message_ident`,`_parent0_index`,`_parent1_index`,`_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_FileAccess_Permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_FileAccess_Permission` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent0_index` smallint(6) NOT NULL,
  `_parent1_index` tinyint(4) NOT NULL,
  `_parent2_index` tinyint(4) NOT NULL,
  `_index` tinyint(4) NOT NULL,
  `permission` varchar(255) NOT NULL,
  PRIMARY KEY (`_message_ident`,`_parent0_index`,`_parent1_index`,`_parent2_index`,`_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Heartbeat`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Heartbeat` (
  `_ident` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `messageid` varchar(255) DEFAULT NULL,
  `heartbeat_interval` int(11) DEFAULT NULL,
  PRIMARY KEY (`_ident`)
) ENGINE=InnoDB AUTO_INCREMENT=112293 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Impact`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Impact` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `description` text DEFAULT NULL,
  `severity` enum('info','low','medium','high') DEFAULT NULL,
  `completion` enum('failed','succeeded') DEFAULT NULL,
  `type` enum('admin','dos','file','recon','user','other') NOT NULL,
  PRIMARY KEY (`_message_ident`),
  KEY `prelude_impact_index_severity` (`severity`),
  KEY `prelude_impact_index_completion` (`completion`),
  KEY `prelude_impact_index_type` (`type`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Inode`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Inode` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent0_index` smallint(6) NOT NULL,
  `_parent1_index` tinyint(4) NOT NULL,
  `change_time` datetime DEFAULT NULL,
  `change_time_gmtoff` int(11) DEFAULT NULL,
  `number` int(10) unsigned DEFAULT NULL,
  `major_device` int(10) unsigned DEFAULT NULL,
  `minor_device` int(10) unsigned DEFAULT NULL,
  `c_major_device` int(10) unsigned DEFAULT NULL,
  `c_minor_device` int(10) unsigned DEFAULT NULL,
  PRIMARY KEY (`_message_ident`,`_parent0_index`,`_parent1_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Linkage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Linkage` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent0_index` smallint(6) NOT NULL,
  `_parent1_index` tinyint(4) NOT NULL,
  `_index` tinyint(4) NOT NULL,
  `category` enum('hard-link','mount-point','reparse-point','shortcut','stream','symbolic-link') NOT NULL,
  `name` varchar(255) NOT NULL,
  `path` varchar(255) NOT NULL,
  PRIMARY KEY (`_message_ident`,`_parent0_index`,`_parent1_index`,`_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Node`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Node` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent_type` enum('A','H','S','T') NOT NULL,
  `_parent0_index` smallint(6) NOT NULL,
  `ident` varchar(255) DEFAULT NULL,
  `category` enum('unknown','ads','afs','coda','dfs','dns','hosts','kerberos','nds','nis','nisplus','nt','wfw') DEFAULT NULL,
  `location` varchar(255) DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`_parent_type`,`_message_ident`,`_parent0_index`),
  KEY `prelude_node_index_location` (`_parent_type`,`_parent0_index`,`location`(20)),
  KEY `prelude_node_index_name` (`_parent_type`,`_parent0_index`,`name`(20))
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_OverflowAlert`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_OverflowAlert` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `program` varchar(255) NOT NULL,
  `size` int(10) unsigned DEFAULT NULL,
  `buffer` blob DEFAULT NULL,
  PRIMARY KEY (`_message_ident`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Process`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Process` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent_type` enum('A','H','S','T') NOT NULL,
  `_parent0_index` smallint(6) NOT NULL,
  `ident` varchar(255) DEFAULT NULL,
  `name` varchar(255) NOT NULL,
  `pid` int(10) unsigned DEFAULT NULL,
  `path` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`_parent_type`,`_message_ident`,`_parent0_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_ProcessArg`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_ProcessArg` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent_type` enum('A','H','S','T') NOT NULL DEFAULT 'A',
  `_parent0_index` smallint(6) NOT NULL,
  `_index` tinyint(4) NOT NULL,
  `arg` varchar(255) NOT NULL,
  PRIMARY KEY (`_parent_type`,`_message_ident`,`_parent0_index`,`_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_ProcessEnv`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_ProcessEnv` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent_type` enum('A','H','S','T') NOT NULL,
  `_parent0_index` smallint(6) NOT NULL,
  `_index` tinyint(4) NOT NULL,
  `env` varchar(255) NOT NULL,
  PRIMARY KEY (`_parent_type`,`_message_ident`,`_parent0_index`,`_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Reference`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Reference` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_index` tinyint(4) NOT NULL,
  `origin` enum('unknown','vendor-specific','user-specific','bugtraqid','cve','osvdb') NOT NULL,
  `name` varchar(255) NOT NULL,
  `url` varchar(255) NOT NULL,
  `meaning` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`_message_ident`,`_index`),
  KEY `prelude_reference_index_name` (`name`(40))
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Service`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Service` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent_type` enum('S','T') NOT NULL,
  `_parent0_index` smallint(6) NOT NULL,
  `ident` varchar(255) DEFAULT NULL,
  `ip_version` tinyint(3) unsigned DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `port` smallint(5) unsigned DEFAULT NULL,
  `iana_protocol_number` tinyint(3) unsigned DEFAULT NULL,
  `iana_protocol_name` varchar(255) DEFAULT NULL,
  `portlist` varchar(255) DEFAULT NULL,
  `protocol` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`_parent_type`,`_message_ident`,`_parent0_index`),
  KEY `prelude_service_index_protocol_port` (`_parent_type`,`_parent0_index`,`protocol`(10),`port`),
  KEY `prelude_service_index_protocol_name` (`_parent_type`,`_parent0_index`,`protocol`(10),`name`(10))
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_SnmpService`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_SnmpService` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent_type` enum('S','T') NOT NULL,
  `_parent0_index` smallint(6) NOT NULL,
  `snmp_oid` varchar(255) DEFAULT NULL,
  `message_processing_model` int(10) unsigned DEFAULT NULL,
  `security_model` int(10) unsigned DEFAULT NULL,
  `security_name` varchar(255) DEFAULT NULL,
  `security_level` int(10) unsigned DEFAULT NULL,
  `context_name` varchar(255) DEFAULT NULL,
  `context_engine_id` varchar(255) DEFAULT NULL,
  `command` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`_parent_type`,`_message_ident`,`_parent0_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Source`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Source` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_index` smallint(6) NOT NULL,
  `ident` varchar(255) DEFAULT NULL,
  `spoofed` enum('unknown','yes','no') NOT NULL,
  `interface` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`_message_ident`,`_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_Target`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_Target` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_index` smallint(6) NOT NULL,
  `ident` varchar(255) DEFAULT NULL,
  `decoy` enum('unknown','yes','no') NOT NULL,
  `interface` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`_message_ident`,`_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_ToolAlert`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_ToolAlert` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `name` varchar(255) NOT NULL,
  `command` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`_message_ident`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_User`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_User` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent_type` enum('S','T') NOT NULL,
  `_parent0_index` smallint(6) NOT NULL,
  `ident` varchar(255) DEFAULT NULL,
  `category` enum('unknown','application','os-device') NOT NULL,
  PRIMARY KEY (`_parent_type`,`_message_ident`,`_parent0_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_UserId`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_UserId` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent_type` enum('S','T','F') NOT NULL,
  `_parent0_index` smallint(6) NOT NULL,
  `_parent1_index` tinyint(4) NOT NULL,
  `_parent2_index` tinyint(4) NOT NULL,
  `_index` tinyint(4) NOT NULL,
  `ident` varchar(255) DEFAULT NULL,
  `type` enum('current-user','original-user','target-user','user-privs','current-group','group-privs','other-privs') NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `tty` varchar(255) DEFAULT NULL,
  `number` int(10) unsigned DEFAULT NULL,
  PRIMARY KEY (`_parent_type`,`_message_ident`,`_parent0_index`,`_parent1_index`,`_parent2_index`,`_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_WebService`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_WebService` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent_type` enum('S','T') NOT NULL,
  `_parent0_index` smallint(6) NOT NULL,
  `url` varchar(255) NOT NULL,
  `cgi` varchar(255) DEFAULT NULL,
  `http_method` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`_parent_type`,`_message_ident`,`_parent0_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `Prelude_WebServiceArg`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Prelude_WebServiceArg` (
  `_message_ident` bigint(20) unsigned NOT NULL,
  `_parent_type` enum('S','T') NOT NULL,
  `_parent0_index` smallint(6) NOT NULL,
  `_index` tinyint(4) NOT NULL,
  `arg` varchar(255) NOT NULL,
  PRIMARY KEY (`_parent_type`,`_message_ident`,`_parent0_index`,`_index`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


DROP TABLE IF EXISTS `_format`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `_format` (
  `name` varchar(255) NOT NULL,
  `version` varchar(255) NOT NULL,
  `uuid` varchar(23) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_AdditionalData`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_AdditionalData` WRITE;
/*!40000 ALTER TABLE `Prelude_AdditionalData` DISABLE KEYS */;
INSERT INTO `Prelude_AdditionalData` VALUES
(146,'A',-1,'byte-string','payload','GET /CFIDE/administrator/ HTTP/1.1\r\nHost: migration-test.example-org.de\r\nPragma: no-cache\r\nUser-Agent: Mozilla/5.0; EXAMPLE-ORG OpenVAS-VT 23.3.1\r\nAccept: image/gif, image/x-xbitmap, image/jpeg, image/pjpeg, image/png, */*\r\nAccept-Language: en\r\nAccept-Charset: iso-8859-1,*,utf-8\r\nVia: 1.1 __ZIT_BB__ (squid), 1.1 proxy-001.dmz\.example\.internal, 1.1 api.internal\.example\.internal\r\nSurrogate-Capability: __ZIT_BB__=\"Surrogate/1.0\"\r\nX-Forwarded-For: 49.13.153.188, 192.168.232.21, 127.0.0.1\r\nCache-Control: no-cache\r\nX-Forwarded-Host: migration-test.example-org.de, migration-test.example-org.de\r\nX-Forwarded-Server: proxy-001.dmz\.example\.internal, api.internal\.example\.internal\r\nConnection: Keep-Alive\r\n\r\n'),
(146,'A',0,'integer','snort_rule_sid','25975'),
(146,'A',1,'integer','snort_rule_rev','3'),
(146,'A',2,'integer','ip_ver','4'),
(146,'A',3,'integer','ip_hlen','5');
/*!40000 ALTER TABLE `Prelude_AdditionalData` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:13:19
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_Address`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_Address` WRITE;
/*!40000 ALTER TABLE `Prelude_Address` DISABLE KEYS */;
INSERT INTO `Prelude_Address` VALUES
(146,'A',-1,-1,NULL,'ipv4-addr',NULL,NULL,'10.129.9.50',NULL),
(146,'A',-1,0,NULL,'ipv4-addr',NULL,NULL,'10.129.9.50',NULL),
(146,'A',0,-1,NULL,'ipv4-addr',NULL,NULL,'10.129.9.60',NULL),
(146,'A',0,0,NULL,'ipv4-addr',NULL,NULL,'10.129.9.60',NULL),
(146,'A',1,-1,NULL,'ipv4-addr',NULL,NULL,'10.129.9.50',NULL);
/*!40000 ALTER TABLE `Prelude_Address` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:13:21
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_Alert`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_Alert` WRITE;
/*!40000 ALTER TABLE `Prelude_Alert` DISABLE KEYS */;
INSERT INTO `Prelude_Alert` VALUES
(343,'00010b60-bd21-11ef-80fe'),
(299,'008d1160-bbc7-11ef-9b0c'),
(300,'008d512a-bbc7-11ef-9b0c'),
(301,'008d8b72-bbc7-11ef-9b0c'),
(302,'03c126b4-bbc7-11ef-af21');
/*!40000 ALTER TABLE `Prelude_Alert` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:13:23
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_Alertident`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_Alertident` WRITE;
/*!40000 ALTER TABLE `Prelude_Alertident` DISABLE KEYS */;
INSERT INTO `Prelude_Alertident` VALUES
(1440,-1,'C','3bb2665e-bd3f-11ef-999c','591886882278660'),
(1440,0,'C','3adb77d4-bd3f-11ef-85c4','591886882278660'),
(1440,1,'C','3b04d70a-bd3f-11ef-9501','591886882278660'),
(1440,2,'C','3b4ea1b4-bd3f-11ef-af36','591886882278660'),
(1440,3,'C','3b951cac-bd3f-11ef-965f','591886882278660');
/*!40000 ALTER TABLE `Prelude_Alertident` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:13:25
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_Analyzer`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_Analyzer` WRITE;
/*!40000 ALTER TABLE `Prelude_Analyzer` DISABLE KEYS */;
INSERT INTO `Prelude_Analyzer` VALUES
(146,'A',-1,'1759967662935316','snort-eno6','http://www.snort.org','Snort','1.14','NIDS','Linux','5.14.0-503.15.1.el9_5.x86_64'),
(146,'A',0,'951891028586482','prelude-manager','https://www.prelude-siem.com','Prelude Manager','5.2.0','Concentrator','Linux','5.14.0-503.15.1.el9_5.x86_64'),
(146,'A',1,'1759967662935316','snort-eno6','http://www.snort.org','Snort','1.14','NIDS','Linux','5.14.0-503.15.1.el9_5.x86_64'),
(147,'A',-1,'591886882278660','snort-eno5','http://www.snort.org','Snort','1.14','NIDS','Linux','5.14.0-503.15.1.el9_5.x86_64'),
(147,'A',0,'951891028586482','prelude-manager','https://www.prelude-siem.com','Prelude Manager','5.2.0','Concentrator','Linux','5.14.0-503.15.1.el9_5.x86_64');
/*!40000 ALTER TABLE `Prelude_Analyzer` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:13:27
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_AnalyzerTime`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_AnalyzerTime` WRITE;
/*!40000 ALTER TABLE `Prelude_AnalyzerTime` DISABLE KEYS */;
INSERT INTO `Prelude_AnalyzerTime` VALUES
(146,'A','2024-12-15 02:52:57',39031,3600),
(147,'A','2024-12-15 02:52:57',771372,3600),
(148,'A','2024-12-15 02:52:57',771918,3600),
(149,'A','2024-12-15 02:52:58',40648,3600),
(150,'A','2024-12-15 02:52:58',156209,3600);
/*!40000 ALTER TABLE `Prelude_AnalyzerTime` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:13:32
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_Assessment`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_Assessment` WRITE;
/*!40000 ALTER TABLE `Prelude_Assessment` DISABLE KEYS */;
INSERT INTO `Prelude_Assessment` VALUES
(146),
(147),
(148),
(149),
(150);
/*!40000 ALTER TABLE `Prelude_Assessment` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:13:34
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_Classification`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_Classification` WRITE;
/*!40000 ALTER TABLE `Prelude_Classification` DISABLE KEYS */;
INSERT INTO `Prelude_Classification` VALUES
(146,'1:25975','POLICY-OTHER Adobe ColdFusion admin interface access attempt'),
(147,'1:25975','POLICY-OTHER Adobe ColdFusion admin interface access attempt'),
(148,'1:25975','POLICY-OTHER Adobe ColdFusion admin interface access attempt'),
(149,'1:25975','POLICY-OTHER Adobe ColdFusion admin interface access attempt'),
(150,'1:25975','POLICY-OTHER Adobe ColdFusion admin interface access attempt');
/*!40000 ALTER TABLE `Prelude_Classification` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:13:36
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_CreateTime`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_CreateTime` WRITE;
/*!40000 ALTER TABLE `Prelude_CreateTime` DISABLE KEYS */;
INSERT INTO `Prelude_CreateTime` VALUES
(146,'A','2024-12-15 02:52:57',39005,3600),
(147,'A','2024-12-15 02:52:57',771330,3600),
(148,'A','2024-12-15 02:52:57',771904,3600),
(149,'A','2024-12-15 02:52:58',40624,3600),
(150,'A','2024-12-15 02:52:58',156145,3600);
/*!40000 ALTER TABLE `Prelude_CreateTime` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:13:38
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_DetectTime`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_DetectTime` WRITE;
/*!40000 ALTER TABLE `Prelude_DetectTime` DISABLE KEYS */;
INSERT INTO `Prelude_DetectTime` VALUES
(146,'2024-12-15 02:52:56',805633,3600),
(147,'2024-12-15 02:52:56',805583,3600),
(148,'2024-12-15 02:52:57',406391,3600),
(149,'2024-12-15 02:52:57',406326,3600),
(150,'2024-12-15 02:52:58',1131,3600);
/*!40000 ALTER TABLE `Prelude_DetectTime` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:13:40
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_Impact`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_Impact` WRITE;
/*!40000 ALTER TABLE `Prelude_Impact` DISABLE KEYS */;
INSERT INTO `Prelude_Impact` VALUES
(146,'Potential Corporate Privacy Violation','high',NULL,'other'),
(147,'Potential Corporate Privacy Violation','high',NULL,'other'),
(148,'Potential Corporate Privacy Violation','high',NULL,'other'),
(149,'Potential Corporate Privacy Violation','high',NULL,'other'),
(150,'Potential Corporate Privacy Violation','high',NULL,'other');
/*!40000 ALTER TABLE `Prelude_Impact` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:13:48
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_Node`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_Node` WRITE;
/*!40000 ALTER TABLE `Prelude_Node` DISABLE KEYS */;
INSERT INTO `Prelude_Node` VALUES
(146,'A',-1,NULL,'unknown',NULL,'server-001\.example\.internal'),
(146,'A',0,NULL,'unknown',NULL,'server-001\.example\.internal'),
(146,'A',1,NULL,'unknown',NULL,'server-001\.example\.internal'),
(147,'A',-1,NULL,'unknown',NULL,'server-001\.example\.internal'),
(147,'A',0,NULL,'unknown',NULL,'server-001\.example\.internal');
/*!40000 ALTER TABLE `Prelude_Node` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:13:50
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_Process`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_Process` WRITE;
/*!40000 ALTER TABLE `Prelude_Process` DISABLE KEYS */;
INSERT INTO `Prelude_Process` VALUES
(146,'A',-1,NULL,'',1203289,NULL),
(146,'A',0,NULL,'prelude-manager',3142182,'/usr/sbin/prelude-manager'),
(146,'A',1,NULL,'',1203289,NULL),
(147,'A',-1,NULL,'',1203319,NULL),
(147,'A',0,NULL,'prelude-manager',3142182,'/usr/sbin/prelude-manager');
/*!40000 ALTER TABLE `Prelude_Process` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:13:53
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_Reference`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_Reference` WRITE;
/*!40000 ALTER TABLE `Prelude_Reference` DISABLE KEYS */;
INSERT INTO `Prelude_Reference` VALUES
(146,-1,'vendor-specific','url','http://www.adobe.com/support/security/advisories/apsa13-01.html',NULL),
(146,0,'vendor-specific','1:25975','http://www.snort.org/pub-bin/sigs.cgi?sid=1:25975','Snort Signature ID'),
(146,1,'bugtraqid','57330','http://www.securityfocus.com/bid/57330',NULL),
(146,2,'cve','2013-0632','http://cve.mitre.org/cgi-bin/cvename.cgi?name=2013-0632',NULL),
(146,3,'vendor-specific','url','http://www.adobe.com/support/security/advisories/apsa13-01.html',NULL);
/*!40000 ALTER TABLE `Prelude_Reference` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:13:55
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_Service`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_Service` WRITE;
/*!40000 ALTER TABLE `Prelude_Service` DISABLE KEYS */;
INSERT INTO `Prelude_Service` VALUES
(146,'S',-1,NULL,4,NULL,59684,6,'tcp',NULL,NULL),
(146,'S',0,NULL,4,NULL,59684,6,'tcp',NULL,NULL),
(147,'S',-1,NULL,4,NULL,59684,6,'tcp',NULL,NULL),
(147,'S',0,NULL,4,NULL,59684,6,'tcp',NULL,NULL),
(148,'S',-1,NULL,4,NULL,54650,6,'tcp',NULL,NULL);
/*!40000 ALTER TABLE `Prelude_Service` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:13:57
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_Source`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_Source` WRITE;
/*!40000 ALTER TABLE `Prelude_Source` DISABLE KEYS */;
INSERT INTO `Prelude_Source` VALUES
(146,-1,NULL,'unknown','eno6'),
(146,0,NULL,'unknown','eno6'),
(147,-1,NULL,'unknown','eno5'),
(147,0,NULL,'unknown','eno5'),
(148,-1,NULL,'unknown','eno5');
/*!40000 ALTER TABLE `Prelude_Source` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:14:00
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.10-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: prelude
-- ------------------------------------------------------
-- Server version	10.11.10-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `Prelude_Target`
--
-- WHERE:  1 LIMIT 5

LOCK TABLES `Prelude_Target` WRITE;
/*!40000 ALTER TABLE `Prelude_Target` DISABLE KEYS */;
INSERT INTO `Prelude_Target` VALUES
(146,-1,NULL,'unknown','eno6'),
(146,0,NULL,'unknown','eno6'),
(147,-1,NULL,'unknown','eno5'),
(147,0,NULL,'unknown','eno5'),
(148,-1,NULL,'unknown','eno5');
/*!40000 ALTER TABLE `Prelude_Target` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-18 16:14:02
