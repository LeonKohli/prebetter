-- Test seed data for prelude_test database
-- Populates all tables needed for the test suite with realistic IDS data.
-- Timestamps use NOW() so data is always "recent" relative to test execution.

-- Format table (required by schema)
INSERT IGNORE INTO _format (name, version) VALUES ('classic', '14.8');

-- Pair accelerator table for grouped alerts
CREATE TABLE IF NOT EXISTS Prebetter_Pair (
  _message_ident BIGINT PRIMARY KEY,
  source_ip INT UNSIGNED NOT NULL,
  target_ip INT UNSIGNED NOT NULL,
  pair_key BIGINT UNSIGNED AS (source_ip * 4294967296 + target_ip) PERSISTENT,
  KEY idx_pair_key (pair_key),
  KEY idx_source (source_ip),
  KEY idx_target (target_ip)
) ENGINE=InnoDB;

-- ==========================================================================
-- ALERTS (10 alerts)
-- ==========================================================================
INSERT INTO Prelude_Alert (_ident, messageid) VALUES
  (1, 'msg-001'), (2, 'msg-002'), (3, 'msg-003'), (4, 'msg-004'), (5, 'msg-005'),
  (6, 'msg-006'), (7, 'msg-007'), (8, 'msg-008'), (9, 'msg-009'), (10, 'msg-010');

-- Detect times (spread across last 12 hours)
INSERT INTO Prelude_DetectTime (_message_ident, time, usec, gmtoff) VALUES
  (1,  DATE_SUB(NOW(), INTERVAL 1 HOUR),   0, 0),
  (2,  DATE_SUB(NOW(), INTERVAL 2 HOUR),   0, 0),
  (3,  DATE_SUB(NOW(), INTERVAL 3 HOUR),   0, 0),
  (4,  DATE_SUB(NOW(), INTERVAL 4 HOUR),   0, 0),
  (5,  DATE_SUB(NOW(), INTERVAL 5 HOUR),   0, 0),
  (6,  DATE_SUB(NOW(), INTERVAL 6 HOUR),   0, 0),
  (7,  DATE_SUB(NOW(), INTERVAL 7 HOUR),   0, 0),
  (8,  DATE_SUB(NOW(), INTERVAL 8 HOUR),   0, 0),
  (9,  DATE_SUB(NOW(), INTERVAL 10 HOUR),  0, 0),
  (10, DATE_SUB(NOW(), INTERVAL 12 HOUR),  0, 0);

-- Create times for alerts
INSERT INTO Prelude_CreateTime (_message_ident, _parent_type, time, usec, gmtoff) VALUES
  (1,  'A', DATE_SUB(NOW(), INTERVAL 1 HOUR),   0, 0),
  (2,  'A', DATE_SUB(NOW(), INTERVAL 2 HOUR),   0, 0),
  (3,  'A', DATE_SUB(NOW(), INTERVAL 3 HOUR),   0, 0),
  (4,  'A', DATE_SUB(NOW(), INTERVAL 4 HOUR),   0, 0),
  (5,  'A', DATE_SUB(NOW(), INTERVAL 5 HOUR),   0, 0),
  (6,  'A', DATE_SUB(NOW(), INTERVAL 6 HOUR),   0, 0),
  (7,  'A', DATE_SUB(NOW(), INTERVAL 7 HOUR),   0, 0),
  (8,  'A', DATE_SUB(NOW(), INTERVAL 8 HOUR),   0, 0),
  (9,  'A', DATE_SUB(NOW(), INTERVAL 10 HOUR),  0, 0),
  (10, 'A', DATE_SUB(NOW(), INTERVAL 12 HOUR),  0, 0);

-- Analyzer times for alerts (subset, for detail view)
INSERT INTO Prelude_AnalyzerTime (_message_ident, _parent_type, time, usec, gmtoff) VALUES
  (1,  'A', DATE_SUB(NOW(), INTERVAL 1 HOUR),  0, 0),
  (2,  'A', DATE_SUB(NOW(), INTERVAL 2 HOUR),  0, 0),
  (3,  'A', DATE_SUB(NOW(), INTERVAL 3 HOUR),  0, 0),
  (7,  'A', DATE_SUB(NOW(), INTERVAL 7 HOUR),  0, 0);

-- Classifications (7 distinct, one contains "scan")
INSERT INTO Prelude_Classification (_message_ident, ident, text) VALUES
  (1,  'CVE-2024-0001', 'Attempted Information Leak'),
  (2,  'CVE-2024-0002', 'Misc Attack'),
  (3,  'CVE-2024-0003', 'Network Scan Detection'),
  (4,  'CVE-2024-0004', 'Potential Corporate Privacy Violation'),
  (5,  'CVE-2024-0005', 'Attempted Information Leak'),
  (6,  'CVE-2024-0006', 'Misc Attack'),
  (7,  'CVE-2024-0007', 'Web Application Attack'),
  (8,  'CVE-2024-0008', 'Network Scan Detection'),
  (9,  'CVE-2024-0009', 'Attempted Denial of Service'),
  (10, 'CVE-2024-0010', 'Suspicious Login Attempt');

-- Impact / severity (includes high, medium, low, info)
INSERT INTO Prelude_Impact (_message_ident, severity, completion, type, description) VALUES
  (1,  'high',   'succeeded', 'recon',  'Information leak detected'),
  (2,  'high',   'failed',    'other',  'Attack attempt blocked'),
  (3,  'high',   'succeeded', 'recon',  'Port scan from external host'),
  (4,  'medium', 'failed',    'other',  'Privacy policy violation'),
  (5,  'medium', 'succeeded', 'recon',  'Information gathering attempt'),
  (6,  'low',    'failed',    'other',  'Benign anomaly detected'),
  (7,  'high',   'succeeded', 'user',   'SQL injection attempt'),
  (8,  'info',   NULL,        'recon',  'Routine scan activity'),
  (9,  'medium', 'failed',    'dos',    'DoS attempt mitigated'),
  (10, 'low',    'failed',    'admin',  'Brute force login attempt');

-- Assessment (required for detail queries)
INSERT INTO Prelude_Assessment (_message_ident) VALUES
  (1), (2), (3), (4), (5), (6), (7), (8), (9), (10);

-- ==========================================================================
-- SOURCE / TARGET entities
-- ==========================================================================
INSERT INTO Prelude_Source (_message_ident, _index, ident, spoofed, interface) VALUES
  (1,  0, NULL, 'no', 'eth0'), (2,  0, NULL, 'no', 'eth0'),
  (3,  0, NULL, 'no', 'eth0'), (4,  0, NULL, 'no', 'eth0'),
  (5,  0, NULL, 'no', 'eth1'), (6,  0, NULL, 'no', 'eth1'),
  (7,  0, NULL, 'no', 'eth0'), (8,  0, NULL, 'no', 'eth0'),
  (9,  0, NULL, 'no', 'eth0'), (10, 0, NULL, 'no', 'eth0');

INSERT INTO Prelude_Target (_message_ident, _index, ident, decoy, interface) VALUES
  (1,  0, NULL, 'no', 'eth0'), (2,  0, NULL, 'no', 'eth0'),
  (3,  0, NULL, 'no', 'eth0'), (4,  0, NULL, 'no', 'eth0'),
  (5,  0, NULL, 'no', 'eth1'), (6,  0, NULL, 'no', 'eth1'),
  (7,  0, NULL, 'no', 'eth0'), (8,  0, NULL, 'no', 'eth0'),
  (9,  0, NULL, 'no', 'eth0'), (10, 0, NULL, 'no', 'eth0');

-- Source addresses (IPv4)
INSERT INTO Prelude_Address (_message_ident, _parent_type, _parent0_index, _index, ident, category, address, netmask) VALUES
  (1,  'S', 0, 0, NULL, 'ipv4-addr', '192.168.1.100', NULL),
  (2,  'S', 0, 0, NULL, 'ipv4-addr', '192.168.1.100', NULL),
  (3,  'S', 0, 0, NULL, 'ipv4-addr', '10.0.0.50',     NULL),
  (4,  'S', 0, 0, NULL, 'ipv4-addr', '10.0.0.50',     NULL),
  (5,  'S', 0, 0, NULL, 'ipv4-addr', '172.16.0.10',   NULL),
  (6,  'S', 0, 0, NULL, 'ipv4-addr', '172.16.0.10',   NULL),
  (7,  'S', 0, 0, NULL, 'ipv4-addr', '192.168.1.100', NULL),
  (8,  'S', 0, 0, NULL, 'ipv4-addr', '10.0.0.50',     NULL),
  (9,  'S', 0, 0, NULL, 'ipv4-addr', '192.168.1.200', NULL),
  (10, 'S', 0, 0, NULL, 'ipv4-addr', '192.168.1.200', NULL);

-- Target addresses (IPv4)
INSERT INTO Prelude_Address (_message_ident, _parent_type, _parent0_index, _index, ident, category, address, netmask) VALUES
  (1,  'T', 0, 0, NULL, 'ipv4-addr', '10.0.0.1', NULL),
  (2,  'T', 0, 0, NULL, 'ipv4-addr', '10.0.0.1', NULL),
  (3,  'T', 0, 0, NULL, 'ipv4-addr', '10.0.0.2', NULL),
  (4,  'T', 0, 0, NULL, 'ipv4-addr', '10.0.0.2', NULL),
  (5,  'T', 0, 0, NULL, 'ipv4-addr', '10.0.0.3', NULL),
  (6,  'T', 0, 0, NULL, 'ipv4-addr', '10.0.0.3', NULL),
  (7,  'T', 0, 0, NULL, 'ipv4-addr', '10.0.0.1', NULL),
  (8,  'T', 0, 0, NULL, 'ipv4-addr', '10.0.0.2', NULL),
  (9,  'T', 0, 0, NULL, 'ipv4-addr', '10.0.0.4', NULL),
  (10, 'T', 0, 0, NULL, 'ipv4-addr', '10.0.0.4', NULL);

-- ==========================================================================
-- ANALYZERS for alerts (_parent_type='A', _index=-1 = primary)
-- ==========================================================================
INSERT INTO Prelude_Analyzer (_message_ident, _parent_type, _index, analyzerid, name, manufacturer, model, version, class, ostype, osversion) VALUES
  (1,  'A', -1, 'analyzer-001', 'snort',    'Snort Project', 'Snort IDS',    '3.1.0', 'NIDS', 'Linux', '6.1'),
  (2,  'A', -1, 'analyzer-001', 'snort',    'Snort Project', 'Snort IDS',    '3.1.0', 'NIDS', 'Linux', '6.1'),
  (3,  'A', -1, 'analyzer-002', 'suricata', 'OISF',          'Suricata IDS', '7.0.0', 'NIDS', 'Linux', '6.1'),
  (4,  'A', -1, 'analyzer-002', 'suricata', 'OISF',          'Suricata IDS', '7.0.0', 'NIDS', 'Linux', '6.1'),
  (5,  'A', -1, 'analyzer-003', 'ossec',    'OSSEC Project', 'OSSEC HIDS',   '3.7.0', 'HIDS', 'Linux', '6.1'),
  (6,  'A', -1, 'analyzer-003', 'ossec',    'OSSEC Project', 'OSSEC HIDS',   '3.7.0', 'HIDS', 'Linux', '6.1'),
  (7,  'A', -1, 'analyzer-001', 'snort',    'Snort Project', 'Snort IDS',    '3.1.0', 'NIDS', 'Linux', '6.1'),
  (8,  'A', -1, 'analyzer-002', 'suricata', 'OISF',          'Suricata IDS', '7.0.0', 'NIDS', 'Linux', '6.1'),
  (9,  'A', -1, 'analyzer-001', 'snort',    'Snort Project', 'Snort IDS',    '3.1.0', 'NIDS', 'Linux', '6.1'),
  (10, 'A', -1, 'analyzer-003', 'ossec',    'OSSEC Project', 'OSSEC HIDS',   '3.7.0', 'HIDS', 'Linux', '6.1');

-- Nodes for alert analyzers (FQDN names for server extraction)
INSERT INTO Prelude_Node (_message_ident, _parent_type, _parent0_index, ident, category, location, name) VALUES
  (1,  'A', -1, NULL, NULL, 'datacenter-1', 'server-001.example.com'),
  (2,  'A', -1, NULL, NULL, 'datacenter-1', 'server-001.example.com'),
  (3,  'A', -1, NULL, NULL, 'datacenter-2', 'server-002.example.com'),
  (4,  'A', -1, NULL, NULL, 'datacenter-2', 'server-002.example.com'),
  (5,  'A', -1, NULL, NULL, 'datacenter-1', 'server-001.example.com'),
  (6,  'A', -1, NULL, NULL, 'datacenter-1', 'server-001.example.com'),
  (7,  'A', -1, NULL, NULL, 'datacenter-2', 'server-002.example.com'),
  (8,  'A', -1, NULL, NULL, 'datacenter-2', 'server-002.example.com'),
  (9,  'A', -1, NULL, NULL, 'datacenter-1', 'server-001.example.com'),
  (10, 'A', -1, NULL, NULL, 'datacenter-1', 'server-001.example.com');

-- ==========================================================================
-- REFERENCES, SERVICES, ADDITIONAL DATA (for detail view)
-- ==========================================================================
INSERT INTO Prelude_Reference (_message_ident, _index, origin, name, url, meaning) VALUES
  (1, 0, 'cve',             'CVE-2024-0001', 'https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2024-0001', 'CVE reference'),
  (1, 1, 'vendor-specific', 'SNORT-001',     'https://snort.org/rule_docs/1-001',                            'Snort rule reference'),
  (3, 0, 'cve',             'CVE-2024-0003', 'https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2024-0003', 'CVE reference'),
  (7, 0, 'cve',             'CVE-2024-0007', 'https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2024-0007', 'CVE reference');

INSERT INTO Prelude_Service (_message_ident, _parent_type, _parent0_index, ident, ip_version, name, port, iana_protocol_number, iana_protocol_name, protocol) VALUES
  (1, 'S', 0, NULL, 4, 'ephemeral', 49152, 6, 'tcp', 'tcp'),
  (1, 'T', 0, NULL, 4, 'http',      80,    6, 'tcp', 'tcp'),
  (3, 'S', 0, NULL, 4, 'ephemeral', 51234, 6, 'tcp', 'tcp'),
  (3, 'T', 0, NULL, 4, 'ssh',       22,    6, 'tcp', 'tcp'),
  (7, 'S', 0, NULL, 4, 'ephemeral', 55000, 6, 'tcp', 'tcp'),
  (7, 'T', 0, NULL, 4, 'https',     443,   6, 'tcp', 'tcp');

INSERT INTO Prelude_AdditionalData (_message_ident, _parent_type, _index, type, meaning, data) VALUES
  (1, 'A', 0, 'integer', 'ip_ver',    '4'),
  (1, 'A', 1, 'integer', 'ip_hlen',   '5'),
  (1, 'A', 2, 'string',  'snort_rule', 'alert tcp any any -> any 80 (msg:"HTTP attack"; sid:100001; rev:1;)'),
  (3, 'A', 0, 'integer', 'ip_ver',    '4'),
  (3, 'A', 1, 'string',  'scan_type', 'SYN scan'),
  (7, 'A', 0, 'string',  'http_uri',  '/admin/login.php?id=1 OR 1=1');

-- ==========================================================================
-- HEARTBEATS (5 heartbeats across 2 nodes)
-- ==========================================================================
INSERT INTO Prelude_Heartbeat (_ident, messageid, heartbeat_interval) VALUES
  (1, 'hb-001', 600), (2, 'hb-002', 600), (3, 'hb-003', 600),
  (4, 'hb-004', 300), (5, 'hb-005', 300);

-- Analyzer times for heartbeats (recent, within last 24h)
INSERT INTO Prelude_AnalyzerTime (_message_ident, _parent_type, time, usec, gmtoff) VALUES
  (1, 'H', DATE_SUB(NOW(), INTERVAL 10 MINUTE),  0, 0),
  (2, 'H', DATE_SUB(NOW(), INTERVAL 30 MINUTE),  0, 0),
  (3, 'H', DATE_SUB(NOW(), INTERVAL 1 HOUR),     0, 0),
  (4, 'H', DATE_SUB(NOW(), INTERVAL 2 HOUR),     0, 0),
  (5, 'H', DATE_SUB(NOW(), INTERVAL 5 HOUR),     0, 0);

-- Create times for heartbeats
INSERT INTO Prelude_CreateTime (_message_ident, _parent_type, time, usec, gmtoff) VALUES
  (1, 'H', DATE_SUB(NOW(), INTERVAL 10 MINUTE),  0, 0),
  (2, 'H', DATE_SUB(NOW(), INTERVAL 30 MINUTE),  0, 0),
  (3, 'H', DATE_SUB(NOW(), INTERVAL 1 HOUR),     0, 0),
  (4, 'H', DATE_SUB(NOW(), INTERVAL 2 HOUR),     0, 0),
  (5, 'H', DATE_SUB(NOW(), INTERVAL 5 HOUR),     0, 0);

-- Analyzers for heartbeats
INSERT INTO Prelude_Analyzer (_message_ident, _parent_type, _index, analyzerid, name, manufacturer, model, version, class, ostype, osversion) VALUES
  (1, 'H', -1, 'hb-analyzer-001', 'snort',       'Snort Project', 'Snort IDS',    '3.1.0', 'NIDS', 'Linux', '6.1'),
  (2, 'H', -1, 'hb-analyzer-002', 'suricata',    'OISF',          'Suricata IDS', '7.0.0', 'NIDS', 'Linux', '6.1'),
  (3, 'H', -1, 'hb-analyzer-003', 'ossec',       'OSSEC Project', 'OSSEC HIDS',   '3.7.0', 'HIDS', 'Linux', '6.1'),
  (4, 'H', -1, 'hb-analyzer-004', 'samhain',     'Samhain Labs',  'Samhain FIM',  '4.4.0', 'HIDS', 'Linux', '6.1'),
  (5, 'H', -1, 'hb-analyzer-005', 'prelude-lml', 'CS Group',      'Prelude LML',  '5.2.0', 'LML',  'Linux', '6.1');

-- Nodes for heartbeats
INSERT INTO Prelude_Node (_message_ident, _parent_type, _parent0_index, ident, category, location, name) VALUES
  (1, 'H', -1, NULL, NULL, 'datacenter-1', 'server-001.example.com'),
  (2, 'H', -1, NULL, NULL, 'datacenter-1', 'server-001.example.com'),
  (3, 'H', -1, NULL, NULL, 'datacenter-2', 'server-002.example.com'),
  (4, 'H', -1, NULL, NULL, 'datacenter-2', 'server-002.example.com'),
  (5, 'H', -1, NULL, NULL, 'datacenter-1', 'server-001.example.com');

-- Heartbeat addresses
INSERT INTO Prelude_Address (_message_ident, _parent_type, _parent0_index, _index, ident, category, address, netmask) VALUES
  (1, 'H', -1, 0, NULL, 'ipv4-addr', '192.168.1.10', NULL),
  (2, 'H', -1, 0, NULL, 'ipv4-addr', '192.168.1.10', NULL),
  (3, 'H', -1, 0, NULL, 'ipv4-addr', '192.168.2.10', NULL),
  (4, 'H', -1, 0, NULL, 'ipv4-addr', '192.168.2.10', NULL),
  (5, 'H', -1, 0, NULL, 'ipv4-addr', '192.168.1.10', NULL);

-- ==========================================================================
-- PAIR TABLE (grouped alerts accelerator)
-- ==========================================================================
INSERT INTO Prebetter_Pair (_message_ident, source_ip, target_ip) VALUES
  (1,  INET_ATON('192.168.1.100'), INET_ATON('10.0.0.1')),
  (2,  INET_ATON('192.168.1.100'), INET_ATON('10.0.0.1')),
  (3,  INET_ATON('10.0.0.50'),     INET_ATON('10.0.0.2')),
  (4,  INET_ATON('10.0.0.50'),     INET_ATON('10.0.0.2')),
  (5,  INET_ATON('172.16.0.10'),   INET_ATON('10.0.0.3')),
  (6,  INET_ATON('172.16.0.10'),   INET_ATON('10.0.0.3')),
  (7,  INET_ATON('192.168.1.100'), INET_ATON('10.0.0.1')),
  (8,  INET_ATON('10.0.0.50'),     INET_ATON('10.0.0.2')),
  (9,  INET_ATON('192.168.1.200'), INET_ATON('10.0.0.4')),
  (10, INET_ATON('192.168.1.200'), INET_ATON('10.0.0.4'));
