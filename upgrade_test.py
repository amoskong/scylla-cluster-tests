#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright (c) 2016 ScyllaDB


import random
from avocado import main
from cassandra import InvalidRequest
from cassandra.util import sortedset
from collections import OrderedDict
from uuid import UUID

#from sdcm.nemesis import RollbackNemesis
#from sdcm.nemesis import UpgradeNemesis
from sdcm.nemesis import UpgradeNemesisOneNode
from sdcm.tester import ClusterTester


class UpgradeTest(ClusterTester):
    """
    Test a Scylla cluster upgrade.

    :avocado: enable
    """

    default_params = {'timeout': 650000}

    def test_upgrade_cql_queries(self):
        """
        Run a set of different cql queries against various types/tables before
        and after upgrade of every node to check the consistency of data
        """
        all_verification_items = [
            # order_by_with_in_test: Check that order-by works with IN
            {
                'create_tables': ["""
                      CREATE TABLE order_by_with_in_test(
                          my_id varchar,
                          col1 int,
                          value varchar,
                          PRIMARY KEY (my_id, col1)
                      )"""],
                'truncates': ['TRUNCATE order_by_with_in_test'],
                'inserts': ["INSERT INTO order_by_with_in_test(my_id, col1, value) VALUES ( 'key1', 1, 'a')",
                            "INSERT INTO order_by_with_in_test(my_id, col1, value) VALUES ( 'key2', 3, 'c')",
                            "INSERT INTO order_by_with_in_test(my_id, col1, value) VALUES ( 'key3', 2, 'b')",
                            "INSERT INTO order_by_with_in_test(my_id, col1, value) VALUES ( 'key4', 4, 'd')"],
                'queries': [
                    "SELECT col1 FROM order_by_with_in_test WHERE my_id in('key1', 'key2', 'key3') ORDER BY col1",
                    "SELECT col1, my_id FROM order_by_with_in_test WHERE my_id in('key1', 'key2', 'key3') ORDER BY col1",
                    "SELECT my_id, col1 FROM order_by_with_in_test WHERE my_id in('key1', 'key2', 'key3') ORDER BY col1"],
                'results': [[[1], [2], [3]],
                            [[1, 'key1'], [2, 'key3'], [3, 'key2']],
                            [['key1', 1], ['key3', 2], ['key2', 3]]],
                'min_version': '2.0',
                'max_version': '',
                'skip': '',
                'disable_paging': True},
            # static_cf_test: Test static CF syntax
            {
                'create_tables': ["""CREATE TABLE static_cf_test (
                        userid uuid PRIMARY KEY,
                        firstname text,
                        lastname text,
                        age int
                    );"""],
                'truncates': ['TRUNCATE static_cf_test'],
                'inserts': [
                    "INSERT INTO static_cf_test (userid, firstname, lastname, age) VALUES (550e8400-e29b-41d4-a716-446655440000, 'Frodo', 'Baggins', 32)",
                    "UPDATE static_cf_test SET firstname = 'Samwise', lastname = 'Gamgee', age = 33 WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479"],
                'queries': [
                    "SELECT firstname, lastname FROM static_cf_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000",
                    "SELECT * FROM static_cf_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000",
                    "SELECT * FROM static_cf_test"],
                'results': [[['Frodo', 'Baggins']],
                            [[UUID('550e8400-e29b-41d4-a716-446655440000'), 32, 'Frodo', 'Baggins']],
                            [[UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479'), 33, 'Samwise', 'Gamgee'],
                             [UUID('550e8400-e29b-41d4-a716-446655440000'), 32, 'Frodo', 'Baggins']]],
                'min_version': '1.0',
                'max_version': '',
                'skip': ''},
            # static_cf_test_batch: Test static CF syntax with batch
            {
                'create_tables': ["""CREATE TABLE static_cf_test_batch (
                    userid uuid PRIMARY KEY,
                    firstname text,
                    lastname text,
                    age int
                );"""],
                'truncates': ['TRUNCATE static_cf_test_batch'],
                'inserts': [
                    "INSERT INTO static_cf_test_batch (userid, firstname, lastname, age) VALUES (550e8400-e29b-41d4-a716-446655440000, 'Frodo', 'Baggins', 32)",
                    "UPDATE static_cf_test_batch SET firstname = 'Samwise', lastname = 'Gamgee', age = 33 WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479",
                    """BEGIN BATCH
                        INSERT INTO static_cf_test_batch (userid, age) VALUES (550e8400-e29b-41d4-a716-446655440000, 36)
                        UPDATE static_cf_test_batch SET age = 37 WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479
                        DELETE firstname, lastname FROM static_cf_test_batch WHERE userid = 550e8400-e29b-41d4-a716-446655440000
                        DELETE firstname, lastname FROM static_cf_test_batch WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479
                       APPLY BATCH"""
                ],
                'queries': [
                    "SELECT * FROM static_cf_test_batch"],
                'results': [[[UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479'), 37, None, None],
                             [UUID('550e8400-e29b-41d4-a716-446655440000'), 36, None, None]]],
                'min_version': '1.0',
                'max_version': '',
                'skip': ''},
            # noncomposite_static_cf_test: Test non-composite static CF syntax
            {
                'create_tables': ["""CREATE TABLE noncomposite_static_cf_test (
                        userid uuid PRIMARY KEY,
                        firstname ascii,
                        lastname ascii,
                        age int
                    ) WITH COMPACT STORAGE;"""],
                'truncates': ['TRUNCATE noncomposite_static_cf_test'],
                'inserts': [
                    "INSERT INTO noncomposite_static_cf_test (userid, firstname, lastname, age) VALUES (550e8400-e29b-41d4-a716-446655440000, 'Frodo', 'Baggins', 32)",
                    "UPDATE noncomposite_static_cf_test SET firstname = 'Samwise', lastname = 'Gamgee', age = 33 WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479"],
                'queries': [
                    "SELECT firstname, lastname FROM noncomposite_static_cf_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000",
                    "SELECT * FROM noncomposite_static_cf_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000",
                    "SELECT * FROM noncomposite_static_cf_test WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479",
                    "SELECT * FROM noncomposite_static_cf_test"],
                'results': [[['Frodo', 'Baggins']],
                            [[UUID('550e8400-e29b-41d4-a716-446655440000'), 32, 'Frodo', 'Baggins']],
                            [[UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479'), 33, 'Samwise', 'Gamgee']],
                            [[UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479'), 33, 'Samwise', 'Gamgee'],
                             [UUID('550e8400-e29b-41d4-a716-446655440000'), 32, 'Frodo', 'Baggins']]],
                'min_version': '1.0',
                'max_version': '',
                'skip': ''},
            # noncomposite_static_cf_test_batch: Test non-composite static CF syntax with batch
            {
                'create_tables': ["""CREATE TABLE noncomposite_static_cf_test_batch (
                        userid uuid PRIMARY KEY,
                        firstname ascii,
                        lastname ascii,
                        age int
                    ) WITH COMPACT STORAGE;"""],
                'truncates': ['TRUNCATE noncomposite_static_cf_test_batch'],
                'inserts': [
                    "INSERT INTO noncomposite_static_cf_test_batch (userid, firstname, lastname, age) VALUES (550e8400-e29b-41d4-a716-446655440000, 'Frodo', 'Baggins', 32)",
                    "UPDATE noncomposite_static_cf_test_batch SET firstname = 'Samwise', lastname = 'Gamgee', age = 33 WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479",
                    """BEGIN BATCH
                        INSERT INTO noncomposite_static_cf_test_batch (userid, age) VALUES (550e8400-e29b-41d4-a716-446655440000, 36)
                        UPDATE noncomposite_static_cf_test_batch SET age = 37 WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479
                        DELETE firstname, lastname FROM noncomposite_static_cf_test_batch WHERE userid = 550e8400-e29b-41d4-a716-446655440000
                        DELETE firstname, lastname FROM noncomposite_static_cf_test_batch WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479
                        APPLY BATCH"""],
                'queries': [
                    "SELECT * FROM noncomposite_static_cf_test_batch"],
                'results': [[[UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479'), 37, None, None],
                             [UUID('550e8400-e29b-41d4-a716-446655440000'), 36, None, None]]],
                'min_version': '1.0',
                'max_version': '',
                'skip': ''},
            # dynamic_cf_test: Test non-composite dynamic CF syntax
            {
                'create_tables': ["""CREATE TABLE dynamic_cf_test (
                        userid uuid,
                        url text,
                        time bigint,
                        PRIMARY KEY (userid, url)
                    ) WITH COMPACT STORAGE;"""],
                'truncates': ['TRUNCATE dynamic_cf_test'],
                'inserts': [
                    "INSERT INTO dynamic_cf_test (userid, url, time) VALUES (550e8400-e29b-41d4-a716-446655440000, 'http://foo.bar', 42)",
                    "INSERT INTO dynamic_cf_test (userid, url, time) VALUES (550e8400-e29b-41d4-a716-446655440000, 'http://foo-2.bar', 24)",
                    "INSERT INTO dynamic_cf_test (userid, url, time) VALUES (550e8400-e29b-41d4-a716-446655440000, 'http://bar.bar', 128)",
                    "UPDATE dynamic_cf_test SET time = 24 WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479 and url = 'http://bar.foo'",
                    "UPDATE dynamic_cf_test SET time = 12 WHERE userid IN (f47ac10b-58cc-4372-a567-0e02b2c3d479, 550e8400-e29b-41d4-a716-446655440000) and url = 'http://foo-3'"],
                'queries': [
                    "SELECT url, time FROM dynamic_cf_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000",
                    "SELECT * FROM dynamic_cf_test WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479",
                    "SELECT time FROM dynamic_cf_test"],
                'results': [
                    [['http://bar.bar', 128], ['http://foo-2.bar', 24], ['http://foo-3', 12], ['http://foo.bar', 42]],
                    [[UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479'), 'http://bar.foo', 24],
                     [UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479'), 'http://foo-3', 12]],
                    [[24], [12], [128], [24], [12], [42]]],
                'invalid_queries': [
                    # Error from server: code=2200 [Invalid query] message="Missing PRIMARY KEY part url"
                    "INSERT INTO dynamic_cf_test (userid, url, time) VALUES (810e8500-e29b-41d4-a716-446655440000, '', 42)"],
                'min_version': '1.0',
                'max_version': '',
                'skip': ''},
            # dense_cf_test: Test composite 'dense' CF syntax
            {
                'create_tables': ["""CREATE TABLE dense_cf_test (
                              userid uuid,
                              ip text,
                              port int,
                              time bigint,
                              PRIMARY KEY (userid, ip, port)
                                ) WITH COMPACT STORAGE;"""],
                'truncates': ['TRUNCATE dense_cf_test'],
                'inserts': [
                    "INSERT INTO dense_cf_test (userid, ip, port, time) VALUES (550e8400-e29b-41d4-a716-446655440000, '192.168.0.1', 80, 42)",
                    "INSERT INTO dense_cf_test (userid, ip, port, time) VALUES (550e8400-e29b-41d4-a716-446655440000, '192.168.0.2', 80, 24)",
                    "INSERT INTO dense_cf_test (userid, ip, port, time) VALUES (550e8400-e29b-41d4-a716-446655440000, '192.168.0.2', 90, 42)",
                    "UPDATE dense_cf_test SET time = 24 WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479 AND ip = '192.168.0.2' AND port = 80",
                    "INSERT INTO dense_cf_test (userid, ip, time) VALUES (f47ac10b-58cc-4372-a567-0e02b2c3d479, '192.168.0.3', 42)",
                    "UPDATE dense_cf_test SET time = 42 WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479 AND ip = '192.168.0.4'"],
                'queries': [
                    "SELECT ip, port, time FROM dense_cf_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000",
                    "SELECT ip, port, time FROM dense_cf_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000 and ip >= '192.168.0.2'",
                    "SELECT ip, port, time FROM dense_cf_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000 and ip = '192.168.0.2'",
                    "SELECT ip, port, time FROM dense_cf_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000 and ip > '192.168.0.2'",
                    "SELECT ip, port, time FROM dense_cf_test WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479 AND ip = '192.168.0.3'",
                    "SELECT ip, port, time FROM dense_cf_test WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479 AND ip = '192.168.0.4'",
                    "DELETE time FROM dense_cf_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000 AND ip = '192.168.0.2' AND port = 80",
                    "SELECT * FROM dense_cf_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000",
                    "DELETE FROM dense_cf_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000",
                    "SELECT * FROM dense_cf_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000",
                    "DELETE FROM dense_cf_test WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479 AND ip = '192.168.0.3'",
                    "SELECT * FROM dense_cf_test WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479 AND ip = '192.168.0.3'"
                ],
                'results': [[['192.168.0.1', 80, 42], ['192.168.0.2', 80, 24], ['192.168.0.2', 90, 42]],
                            [['192.168.0.2', 80, 24], ['192.168.0.2', 90, 42]],
                            [['192.168.0.2', 80, 24], ['192.168.0.2', 90, 42]],
                            [],
                            [['192.168.0.3', None, 42]],
                            [['192.168.0.4', None, 42]],
                            [],
                            [[UUID('550e8400-e29b-41d4-a716-446655440000'), '192.168.0.1', 80, 42],
                             [UUID('550e8400-e29b-41d4-a716-446655440000'), '192.168.0.2', 90, 42]],
                            [],
                            [],
                            [],
                            [],
                            ],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # sparse_cf_test: Test composite 'sparse' CF syntax
            {
                'create_tables': ["""CREATE TABLE sparse_cf_test (
                        userid uuid,
                        posted_month int,
                        posted_day int,
                        body ascii,
                        posted_by ascii,
                        PRIMARY KEY (userid, posted_month, posted_day)
                    );"""],
                'truncates': ['TRUNCATE sparse_cf_test'],
                'inserts': [
                    "INSERT INTO sparse_cf_test (userid, posted_month, posted_day, body, posted_by) VALUES (550e8400-e29b-41d4-a716-446655440000, 1, 12, 'Something else', 'Frodo Baggins')",
                    "INSERT INTO sparse_cf_test (userid, posted_month, posted_day, body, posted_by) VALUES (550e8400-e29b-41d4-a716-446655440000, 1, 24, 'Something something', 'Frodo Baggins')",
                    "UPDATE sparse_cf_test SET body = 'Yo Froddo', posted_by = 'Samwise Gamgee' WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479 AND posted_month = 1 AND posted_day = 3",
                    "UPDATE sparse_cf_test SET body = 'Yet one more message' WHERE userid = 550e8400-e29b-41d4-a716-446655440000 AND posted_month = 1 and posted_day = 30"],
                'queries': [
                    "SELECT body, posted_by FROM sparse_cf_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000 AND posted_month = 1 AND posted_day = 24",
                    "SELECT posted_day, body, posted_by FROM sparse_cf_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000 AND posted_month = 1 AND posted_day > 12",
                    "SELECT posted_day, body, posted_by FROM sparse_cf_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000 AND posted_month = 1"],
                'results': [
                    [['Something something', 'Frodo Baggins']],
                    [[24, 'Something something', 'Frodo Baggins'],
                     [30, 'Yet one more message', None]],
                    [[12, 'Something else', 'Frodo Baggins'],
                     [24, 'Something something', 'Frodo Baggins'],
                     [30, 'Yet one more message', None]]
                ],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # limit_ranges_test: Validate LIMIT option for 'range queries' in SELECT statements
            {
                'create_tables': ["""CREATE TABLE limit_ranges_test (
                        userid int,
                        url text,
                        time bigint,
                        PRIMARY KEY (userid, url)
                    ) WITH COMPACT STORAGE;"""],
                'truncates': ['TRUNCATE limit_ranges_test'],
                'inserts': [
                    "INSERT INTO limit_ranges_test (userid, url, time) VALUES ({}, 'http://foo.{}', 42)".format(id, tld)
                    for id in xrange(0, 100) for tld in ['com', 'org', 'net']],
                'queries': [
                    "SELECT * FROM limit_ranges_test WHERE token(userid) >= token(2) LIMIT 1",
                    "SELECT * FROM limit_ranges_test WHERE token(userid) > token(2) LIMIT 1"],
                'results': [
                    [[2, 'http://foo.com', 42]],
                    [[3, 'http://foo.com', 42]]],
                'min_version': '',
                'max_version': '',
                'skip': '#2029'},
            # limit_multiget_test: Validate LIMIT option for 'multiget' in SELECT statements
            {
                'create_tables': ["""CREATE TABLE limit_multiget_test (
                        userid int,
                        url text,
                        time bigint,
                        PRIMARY KEY (userid, url)
                    ) WITH COMPACT STORAGE;"""],
                'truncates': ['TRUNCATE limit_multiget_test'],
                'inserts': [
                    "INSERT INTO limit_multiget_test (userid, url, time) VALUES ({}, 'http://foo.{}', 42)".format(id,
                                                                                                                  tld)
                    for id in xrange(0, 100) for tld in ['com', 'org', 'net']],
                'queries': [
                    "SELECT * FROM limit_multiget_test WHERE userid IN (48, 2) LIMIT 1"],
                'results': [
                    [[2, 'http://foo.com', 42]]
                ],
                'min_version': '',
                'max_version': '',
                'skip': '#2029 order of keys is not applied with LIMIT for multiget IN'},
            # simple_tuple_query_test: CASSANDRA-8613
            {
                'create_tables': [
                    "create table simple_tuple_query_test (a int, b int, c int, d int , e int, PRIMARY KEY (a, b, c, d, e))"],
                'truncates': ['TRUNCATE simple_tuple_query_test'],
                'inserts': [
                    "INSERT INTO simple_tuple_query_test (a, b, c, d, e) VALUES (0, 2, 0, 0, 0)",
                    "INSERT INTO simple_tuple_query_test (a, b, c, d, e) VALUES (0, 1, 0, 0, 0)",
                    "INSERT INTO simple_tuple_query_test (a, b, c, d, e) VALUES (0, 0, 0, 0, 0)",
                    "INSERT INTO simple_tuple_query_test (a, b, c, d, e) VALUES (0, 0, 1, 1, 1)",
                    "INSERT INTO simple_tuple_query_test (a, b, c, d, e) VALUES (0, 0, 2, 2, 2)",
                    "INSERT INTO simple_tuple_query_test (a, b, c, d, e) VALUES (0, 0, 3, 3, 3)",
                    "INSERT INTO simple_tuple_query_test (a, b, c, d, e) VALUES (0, 0, 1, 1, 1)"
                ],
                'queries': [
                    "SELECT * FROM simple_tuple_query_test WHERE b=0 AND (c, d, e) > (1, 1, 1) ALLOW FILTERING"],
                'results': [
                    [[0, 0, 2, 2, 2], [0, 0, 3, 3, 3]]
                ],
                'min_version': '',
                'max_version': '',
                'skip': '#64 Clustering columns may not be skipped in multi-column relations. They should appear in the PRIMARY KEY order. Got (c, d, e) > (1, 1, 1)'},
            # limit_sparse_test: Validate LIMIT option for sparse table in SELECT statements
            {
                'create_tables': [
                    """CREATE TABLE limit_sparse_test (
                userid int,
                url text,
                day int,
                month text,
                year int,
                PRIMARY KEY (userid, url)
            );"""],
                'truncates': ['TRUNCATE limit_sparse_test'],
                'inserts': [
                    "INSERT INTO limit_sparse_test (userid, url, day, month, year) VALUES ({}, 'http://foo.{}', 1, 'jan', 2012)".format(
                        id, tld) for id in xrange(0, 100) for tld in ['com', 'org', 'net']],
                'queries': [
                    "SELECT * FROM limit_sparse_test LIMIT 4"],
                'results': [
                    [[23, u'http://foo.com', 1, u'jan', 2012], [23, u'http://foo.net', 1, u'jan', 2012],
                     [23, u'http://foo.org', 1, u'jan', 2012], [53, u'http://foo.com', 1, u'jan', 2012]]
                ],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # counters_test: Validate counter support
            {
                'create_tables': [
                    """CREATE TABLE counters_test (
                userid int,
                url text,
                total counter,
                PRIMARY KEY (userid, url)
            ) WITH COMPACT STORAGE;"""],
                'truncates': ['TRUNCATE counters_test'],
                'inserts': [
                    "UPDATE counters_test SET total = 0 WHERE userid = 1 AND url = 'http://foo.com'",
                    "UPDATE counters_test SET total = total + 1 WHERE userid = 1 AND url = 'http://foo.com'",
                ],
                'queries': [
                    "SELECT total FROM counters_test WHERE userid = 1 AND url = 'http://foo.com'",
                    "UPDATE counters_test SET total = total - 4 WHERE userid = 1 AND url = 'http://foo.com'",
                    "SELECT total FROM counters_test WHERE userid = 1 AND url = 'http://foo.com'",
                    "UPDATE counters_test SET total = total+1 WHERE userid = 1 AND url = 'http://foo.com'",
                    "SELECT total FROM counters_test WHERE userid = 1 AND url = 'http://foo.com'",
                    "UPDATE counters_test SET total = total -2 WHERE userid = 1 AND url = 'http://foo.com'",
                    "SELECT total FROM counters_test WHERE userid = 1 AND url = 'http://foo.com'"],
                'results': [
                    [[1]],
                    None,
                    [[-3]],
                    None,
                    [[-2]],
                    None,
                    [[-4]]
                ],
                'min_version': '1.7',
                'max_version': '',
                'skip': 'Counter support is not enabled'},
            # indexed_with_eq_test: Check that you can query for an indexed column even with a key EQ clause
            {
                'create_tables': ["""
                        CREATE TABLE indexed_with_eq_test (
                          userid uuid PRIMARY KEY,
                          firstname text,
                          lastname text,
                          age int);"""],
                'truncates': ['CREATE INDEX byAge ON indexed_with_eq_test(age);'],
                'inserts': [
                    "INSERT INTO indexed_with_eq_test (userid, firstname, lastname, age) VALUES (550e8400-e29b-41d4-a716-446655440000, 'Frodo', 'Baggins', 32)",
                    "UPDATE indexed_with_eq_test SET firstname = 'Samwise', lastname = 'Gamgee', age = 33 WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479",
                ],
                'queries': [
                    "SELECT firstname FROM indexed_with_eq_test WHERE userid = 550e8400-e29b-41d4-a716-446655440000 AND age = 33",
                    "SELECT firstname FROM indexed_with_eq_test WHERE userid = f47ac10b-58cc-4372-a567-0e02b2c3d479 AND age = 33"],
                'results': [
                    [],
                    [['Samwise']]
                ],
                'min_version': '2.0',
                'max_version': '',
                'skip': 'Index support is not enabled'},
            # select_key_in_test: Query for KEY IN (...)
            {
                'create_tables': ["""CREATE TABLE select_key_in_test (
                          userid uuid PRIMARY KEY,
                          firstname text,
                          lastname text,
                          age int);"""],
                'truncates': ['TRUNCATE select_key_in_test'],
                'inserts': [
                    "INSERT INTO select_key_in_test (userid, firstname, lastname, age) VALUES (550e8400-e29b-41d4-a716-446655440000, 'Frodo', 'Baggins', 32)",
                    "INSERT INTO select_key_in_test (userid, firstname, lastname, age) VALUES (f47ac10b-58cc-4372-a567-0e02b2c3d479, 'Samwise', 'Gamgee', 33)",
                ],
                'queries': [
                    "SELECT firstname, lastname FROM select_key_in_test WHERE userid IN (550e8400-e29b-41d4-a716-446655440000, f47ac10b-58cc-4372-a567-0e02b2c3d479)"],
                'results': [
                    [['Frodo', 'Baggins'], ['Samwise', 'Gamgee']]
                ],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # exclusive_slice_test: Test SELECT respects inclusive and exclusive bounds
            {
                'create_tables': ["""CREATE TABLE exclusive_slice_test (
                          k int,
                          c int,
                          v int,
                          PRIMARY KEY (k, c)
                            ) WITH COMPACT STORAGE;"""],
                'truncates': ['TRUNCATE exclusive_slice_test'],
                'inserts': [
                    """BEGIN BATCH
                        INSERT INTO exclusive_slice_test (k, c, v) VALUES (0, 0, 0)
                        INSERT INTO exclusive_slice_test (k, c, v) VALUES (0, 1, 1)
                        INSERT INTO exclusive_slice_test (k, c, v) VALUES (0, 2, 2)
                        INSERT INTO exclusive_slice_test (k, c, v) VALUES (0, 3, 3)
                        INSERT INTO exclusive_slice_test (k, c, v) VALUES (0, 4, 4)
                        INSERT INTO exclusive_slice_test (k, c, v) VALUES (0, 5, 5)
                        INSERT INTO exclusive_slice_test (k, c, v) VALUES (0, 6, 6)
                        INSERT INTO exclusive_slice_test (k, c, v) VALUES (0, 7, 7)
                        INSERT INTO exclusive_slice_test (k, c, v) VALUES (0, 8, 8)
                        INSERT INTO exclusive_slice_test (k, c, v) VALUES (0, 9, 9)
                       APPLY BATCH"""
                ],
                'queries': [
                    "SELECT v FROM exclusive_slice_test WHERE k = 0",
                    "SELECT v FROM exclusive_slice_test WHERE k = 0 AND c >= 2 AND c <= 6",
                    "SELECT v FROM exclusive_slice_test WHERE k = 0 AND c > 2 AND c <= 6",
                    "SELECT v FROM exclusive_slice_test WHERE k = 0 AND c >= 2 AND c < 6",
                    "SELECT v FROM exclusive_slice_test WHERE k = 0 AND c > 2 AND c < 6",
                    "SELECT v FROM exclusive_slice_test WHERE k = 0 AND c > 2 AND c <= 6 LIMIT 2",
                    "SELECT v FROM exclusive_slice_test WHERE k = 0 AND c >= 2 AND c < 6 ORDER BY c DESC LIMIT 2"
                ],
                'results': [
                    [[x] for x in range(10)],
                    [[x] for x in range(2, 7)],
                    [[x] for x in range(3, 7)],
                    [[x] for x in range(2, 6)],
                    [[x] for x in range(3, 6)],
                    [[3], [4]],
                    [[5], [4]]
                ],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # in_clause_wide_rows_test: Check IN support for 'wide rows' in SELECT statement
            {
                'create_tables': ["""CREATE TABLE in_clause_wide_rows_test1 (
                                                k int,
                                                c int,
                                                v int,
                                                PRIMARY KEY (k, c)) WITH COMPACT STORAGE;""",
                                  """CREATE TABLE in_clause_wide_rows_test2 (
                                        k int,
                                        c1 int,
                                        c2 int,
                                        v int,
                                        PRIMARY KEY (k, c1, c2)) WITH COMPACT STORAGE;"""
                                  ],
                'truncates': ['TRUNCATE in_clause_wide_rows_test1', 'TRUNCATE in_clause_wide_rows_test2'],
                'inserts': [
                    """BEGIN BATCH
                        INSERT INTO in_clause_wide_rows_test1 (k, c, v) VALUES (0, 0, 0)
                        INSERT INTO in_clause_wide_rows_test1 (k, c, v) VALUES (0, 1, 1)
                        INSERT INTO in_clause_wide_rows_test1 (k, c, v) VALUES (0, 2, 2)
                        INSERT INTO in_clause_wide_rows_test1 (k, c, v) VALUES (0, 3, 3)
                        INSERT INTO in_clause_wide_rows_test1 (k, c, v) VALUES (0, 4, 4)
                        INSERT INTO in_clause_wide_rows_test1 (k, c, v) VALUES (0, 5, 5)
                        INSERT INTO in_clause_wide_rows_test1 (k, c, v) VALUES (0, 6, 6)
                        INSERT INTO in_clause_wide_rows_test1 (k, c, v) VALUES (0, 7, 7)
                        INSERT INTO in_clause_wide_rows_test1 (k, c, v) VALUES (0, 8, 8)
                        INSERT INTO in_clause_wide_rows_test1 (k, c, v) VALUES (0, 9, 9)
                        INSERT INTO in_clause_wide_rows_test2 (k, c1, c2, v) VALUES (0, 0, 0, 0)
                        INSERT INTO in_clause_wide_rows_test2 (k, c1, c2, v) VALUES (0, 0, 1, 1)
                        INSERT INTO in_clause_wide_rows_test2 (k, c1, c2, v) VALUES (0, 0, 2, 2)
                        INSERT INTO in_clause_wide_rows_test2 (k, c1, c2, v) VALUES (0, 0, 3, 3)
                        INSERT INTO in_clause_wide_rows_test2 (k, c1, c2, v) VALUES (0, 0, 4, 4)
                        INSERT INTO in_clause_wide_rows_test2 (k, c1, c2, v) VALUES (0, 0, 5, 5)
                        INSERT INTO in_clause_wide_rows_test2 (k, c1, c2, v) VALUES (0, 0, 6, 6)
                        INSERT INTO in_clause_wide_rows_test2 (k, c1, c2, v) VALUES (0, 0, 7, 7)
                        INSERT INTO in_clause_wide_rows_test2 (k, c1, c2, v) VALUES (0, 0, 8, 8)
                        INSERT INTO in_clause_wide_rows_test2 (k, c1, c2, v) VALUES (0, 0, 9, 9)
                    APPLY BATCH"""
                ],
                'queries': [
                    "SELECT v FROM in_clause_wide_rows_test1 WHERE k = 0 AND c IN (5, 2, 8)",
                    "SELECT v FROM in_clause_wide_rows_test2 WHERE k = 0 AND c1 IN (5, 2, 8) AND c2 = 3"
                    ""
                ],
                'results': [
                    [[2], [5], [8]],
                    []],
                'min_version': '',
                'max_version': '',
                'skip': '#2566 Clustering column "c2" cannot be restricted by an IN relation'},
            # order_by_test: Check ORDER BY support in SELECT statement
            {
                'create_tables': ["""CREATE TABLE order_by_test1 (
                        k int,
                        c int,
                        v int,
                        PRIMARY KEY (k, c)
                    ) WITH COMPACT STORAGE;""",
                                  """CREATE TABLE order_by_test2 (
                k int,
                c1 int,
                c2 int,
                v int,
                PRIMARY KEY (k, c1, c2)
            );"""
                                  ],
                'truncates': ['TRUNCATE order_by_test1', 'TRUNCATE order_by_test2'],
                'inserts': [
                    """BEGIN BATCH
                        INSERT INTO order_by_test1 (k, c, v) VALUES (0, 0, 0)
                        INSERT INTO order_by_test1 (k, c, v) VALUES (0, 1, 1)
                        INSERT INTO order_by_test1 (k, c, v) VALUES (0, 2, 2)
                        INSERT INTO order_by_test1 (k, c, v) VALUES (0, 3, 3)
                        INSERT INTO order_by_test1 (k, c, v) VALUES (0, 4, 4)
                        INSERT INTO order_by_test1 (k, c, v) VALUES (0, 5, 5)
                        INSERT INTO order_by_test1 (k, c, v) VALUES (0, 6, 6)
                        INSERT INTO order_by_test1 (k, c, v) VALUES (0, 7, 7)
                        INSERT INTO order_by_test1 (k, c, v) VALUES (0, 8, 8)
                        INSERT INTO order_by_test1 (k, c, v) VALUES (0, 9, 9)
                        INSERT INTO order_by_test2 (k, c1, c2, v) VALUES (0, 0, 0, 0)
                        INSERT INTO order_by_test2 (k, c1, c2, v) VALUES (0, 0, 1, 1)
                        INSERT INTO order_by_test2 (k, c1, c2, v) VALUES (0, 1, 0, 2)
                        INSERT INTO order_by_test2 (k, c1, c2, v) VALUES (0, 1, 1, 3)
                        INSERT INTO order_by_test2 (k, c1, c2, v) VALUES (0, 2, 0, 4)
                        INSERT INTO order_by_test2 (k, c1, c2, v) VALUES (0, 2, 1, 5)
                        INSERT INTO order_by_test2 (k, c1, c2, v) VALUES (0, 3, 0, 6)
                        INSERT INTO order_by_test2 (k, c1, c2, v) VALUES (0, 3, 1, 7)
                    APPLY BATCH"""
                ],
                'queries': [
                    "SELECT v FROM order_by_test1 WHERE k = 0 ORDER BY c DESC",
                    "SELECT v FROM order_by_test2 WHERE k = 0 ORDER BY c1 DESC",
                    "SELECT v FROM order_by_test2 WHERE k = 0 ORDER BY c1"
                ],
                'results': [
                    [[x] for x in reversed(range(10))],
                    [[x] for x in reversed(range(8))],
                    [[x] for x in range(8)]],
                'invalid_queries': [
                    "SELECT v FROM order_by_test2 WHERE k = 0 ORDER BY c DESC",
                    "SELECT v FROM order_by_test2 WHERE k = 0 ORDER BY c2 DESC",
                    "SELECT v FROM order_by_test2 WHERE k = 0 ORDER BY k DESC"],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # more_order_by_test: More ORDER BY checks CASSANDRA-4160
            {
                'create_tables': ["""CREATE COLUMNFAMILY more_order_by_test1 (
                        row text,
                        number int,
                        string text,
                        PRIMARY KEY (row, number)
                    ) WITH COMPACT STORAGE""",
                                  """CREATE COLUMNFAMILY more_order_by_test2 (
                row text,
                number int,
                number2 int,
                string text,
                PRIMARY KEY (row, number, number2)
            ) WITH COMPACT STORAGE"""],
                'truncates': ['TRUNCATE more_order_by_test1'],
                'inserts': [
                    "INSERT INTO more_order_by_test1 (row, number, string) VALUES ('row', 1, 'one');",
                    "INSERT INTO more_order_by_test1 (row, number, string) VALUES ('row', 2, 'two');",
                    "INSERT INTO more_order_by_test1 (row, number, string) VALUES ('row', 3, 'three');",
                    "INSERT INTO more_order_by_test1 (row, number, string) VALUES ('row', 4, 'four');",
                    "INSERT INTO more_order_by_test2 (row, number, number2, string) VALUES ('a', 1, 0, 'a')",
                    "INSERT INTO more_order_by_test2 (row, number, number2, string) VALUES ('a', 2, 0, 'a')",
                    "INSERT INTO more_order_by_test2 (row, number, number2, string) VALUES ('a', 2, 1, 'a')",
                    "INSERT INTO more_order_by_test2 (row, number, number2, string) VALUES ('a', 3, 0, 'a')",
                    "INSERT INTO more_order_by_test2 (row, number, number2, string) VALUES ('a', 3, 1, 'a')",
                    "INSERT INTO more_order_by_test2 (row, number, number2, string) VALUES ('a', 4, 0, 'a')",

                ],
                'queries': [
                    "SELECT number FROM more_order_by_test1 WHERE row='row' AND number < 3 ORDER BY number ASC",
                    "SELECT number FROM more_order_by_test1 WHERE row='row' AND number >= 3 ORDER BY number ASC",
                    "SELECT number FROM more_order_by_test1 WHERE row='row' AND number < 3 ORDER BY number DESC",
                    "SELECT number FROM more_order_by_test1 WHERE row='row' AND number >= 3 ORDER BY number DESC",
                    "SELECT number FROM more_order_by_test1 WHERE row='row' AND number > 3 ORDER BY number DESC",
                    "SELECT number FROM more_order_by_test1 WHERE row='row' AND number <= 3 ORDER BY number DESC",
                    "SELECT number, number2 FROM more_order_by_test2 WHERE row='a' AND number < 3 ORDER BY number ASC",
                    "SELECT number, number2 FROM more_order_by_test2 WHERE row='a' AND number >= 3 ORDER BY number ASC",
                    "SELECT number, number2 FROM more_order_by_test2 WHERE row='a' AND number < 3 ORDER BY number DESC",
                    "SELECT number, number2 FROM more_order_by_test2 WHERE row='a' AND number >= 3 ORDER BY number DESC",
                    "SELECT number, number2 FROM more_order_by_test2 WHERE row='a' AND number > 3 ORDER BY number DESC",
                    "SELECT number, number2 FROM more_order_by_test2 WHERE row='a' AND number <= 3 ORDER BY number DESC"
                ],
                'results': [
                    [[1], [2]],
                    [[3], [4]],
                    [[2], [1]],
                    [[4], [3]],
                    [[4]],
                    [[3], [2], [1]],
                    [[1, 0], [2, 0], [2, 1]],
                    [[3, 0], [3, 1], [4, 0]],
                    [[2, 1], [2, 0], [1, 0]],
                    [[4, 0], [3, 1], [3, 0]],
                    [[4, 0]],
                    [[3, 1], [3, 0], [2, 1], [2, 0], [1, 0]]],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # order_by_validation_test:  Check we don't allow order by on row key CASSANDRA-4246
            {
                'create_tables': ["""CREATE TABLE order_by_validation_test (
                        k1 int,
                        k2 int,
                        v int,
                        PRIMARY KEY (k1, k2)
                    )"""],
                'truncates': ['TRUNCATE order_by_validation_test'],
                'inserts': [
                    "INSERT INTO order_by_validation_test (k1, k2, v) VALUES (0, 0, 0)",
                    "INSERT INTO order_by_validation_test (k1, k2, v) VALUES (1, 1, 1)",
                    "INSERT INTO order_by_validation_test (k1, k2, v) VALUES (2, 2, 2)"
                ],
                'queries': [],
                'results': [],
                'invalid_queries': [
                    "SELECT * FROM order_by_validation_test ORDER BY k2"],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # reversed_comparator_test
            {
                'create_tables': ["""CREATE TABLE reversed_comparator_test1 (
                        k int,
                        c int,
                        v int,
                        PRIMARY KEY (k, c)
                    ) WITH CLUSTERING ORDER BY (c DESC);""",
                                  """CREATE TABLE reversed_comparator_test2 (
                k int,
                c1 int,
                c2 int,
                v text,
                PRIMARY KEY (k, c1, c2)
            ) WITH CLUSTERING ORDER BY (c1 ASC, c2 DESC);"""],
                'truncates': ['TRUNCATE reversed_comparator_test1', 'TRUNCATE reversed_comparator_test2'],
                'inserts': ["INSERT INTO reversed_comparator_test1 (k, c, v) VALUES (0, {}, {})".format(x, x) for x in
                            range(0, 10)] + [
                                "INSERT INTO reversed_comparator_test2 (k, c1, c2, v) VALUES (0, {}, {}, '{}{}')".format(x,
                                                                                                                         y,
                                                                                                                         x,
                                                                                                                         y)
                                for x in range(0, 10) for y in range(0, 10)],
                'queries': [
                    "SELECT c, v FROM reversed_comparator_test1 WHERE k = 0 ORDER BY c ASC",
                    "SELECT c, v FROM reversed_comparator_test1 WHERE k = 0 ORDER BY c DESC",
                    "SELECT c1, c2, v FROM reversed_comparator_test2 WHERE k = 0 ORDER BY c1 ASC",
                    "SELECT c1, c2, v FROM reversed_comparator_test2 WHERE k = 0 ORDER BY c1 ASC, c2 DESC",
                    "SELECT c1, c2, v FROM reversed_comparator_test2 WHERE k = 0 ORDER BY c1 DESC, c2 ASC"
                ],
                'results': [
                    [[x, x] for x in range(0, 10)],
                    [[x, x] for x in range(9, -1, -1)],
                    [[x, y, '{}{}'.format(x, y)] for x in range(0, 10) for y in range(9, -1, -1)],
                    [[x, y, '{}{}'.format(x, y)] for x in range(0, 10) for y in range(9, -1, -1)],
                    [[x, y, '{}{}'.format(x, y)] for x in range(9, -1, -1) for y in range(0, 10)]],
                'invalid_queries': [
                    "SELECT c1, c2, v FROM reversed_comparator_test2 WHERE k = 0 ORDER BY c1 ASC, c2 ASC",
                    "SELECT c1, c2, v FROM reversed_comparator_test2 WHERE k = 0 ORDER BY c1 DESC, c2 DESC",
                    "SELECT c1, c2, v FROM reversed_comparator_test2 WHERE k = 0 ORDER BY c2 DESC, c1 ASC"],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # null_support_test:  Test support for nulls
            {
                'create_tables': ["""CREATE TABLE null_support_test (
                        k int,
                        c int,
                        v1 int,
                        v2 set<text>,
                        PRIMARY KEY (k, c));"""],
                'truncates': ['TRUNCATE order_by_validation_test'],
                'inserts': [
                    "INSERT INTO null_support_test (k, c, v1, v2) VALUES (0, 0, null, {'1', '2'})",
                    "INSERT INTO null_support_test (k, c, v1) VALUES (0, 1, 1)"],
                'queries': ["SELECT * FROM null_support_test",
                            "INSERT INTO null_support_test (k, c, v1) VALUES (0, 1, null)",
                            "INSERT INTO null_support_test (k, c, v2) VALUES(0, 0, null)",
                            "SELECT * FROM null_support_test"],
                'results': [
                    [[0, 0, None, set(['1', '2'])], [0, 1, 1, None]],
                    [],
                    [],
                    [[0, 0, None, None], [0, 1, None, None]]],
                'invalid_queries': [
                    "INSERT INTO null_support_test (k, c, v2) VALUES (0, 2, {1, null})",
                    "SELECT * FROM null_support_test WHERE k = null",
                    "INSERT INTO null_support_test (k, c, v2) VALUES (0, 0, { 'foo', 'bar', null })"],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # nameless_index_test:  Test CREATE INDEX without name and validate the index can be dropped
            {
                'create_tables': ["""CREATE TABLE nameless_index_test (
                        id text PRIMARY KEY,
                        birth_year int,
                    )"""],
                'truncates': ['TRUNCATE nameless_index_test'],
                'inserts': [
                    "INSERT INTO users (id, birth_year) VALUES ('Tom', 42)",
                    "INSERT INTO users (id, birth_year) VALUES ('Paul', 24)",
                    "INSERT INTO users (id, birth_year) VALUES ('Bob', 42)"],
                'queries': ["SELECT id FROM users WHERE birth_year = 42"],
                'results': [[['Tom'], ['Bob']]],
                'min_version': '',
                'max_version': '',
                'skip': 'INDEX'},
            # deletion_test: Test simple deletion and in particular check for CASSANDRA-4193 bug
            {
                'create_tables': ["""CREATE TABLE deletion_test1 (
                        username varchar,
                        id int,
                        name varchar,
                        stuff varchar,
                        PRIMARY KEY(username, id)
                    );""",
                                  """CREATE TABLE deletion_test2 (
                username varchar,
                id int,
                name varchar,
                stuff varchar,
                PRIMARY KEY(username, id, name)
            ) WITH COMPACT STORAGE;"""],
                'truncates': ['TRUNCATE deletion_test1', 'TRUNCATE deletion_test2'],
                'inserts': [
                    "INSERT INTO deletion_test1 (username, id, name, stuff) VALUES ('abc', 2, 'rst', 'some value')",
                    "INSERT INTO deletion_test1 (username, id, name, stuff) VALUES ('abc', 4, 'xyz', 'some other value')"],
                'queries': [
                    "SELECT * FROM deletion_test1",
                    "DELETE FROM deletion_test1 WHERE username='abc' AND id=2",
                    "SELECT * FROM deletion_test1",
                    "INSERT INTO deletion_test2 (username, id, name, stuff) VALUES ('abc', 2, 'rst', 'some value')",
                    "INSERT INTO deletion_test2 (username, id, name, stuff) VALUES ('abc', 4, 'xyz', 'some other value')",
                    "SELECT * FROM deletion_test2",
                    "DELETE FROM deletion_test2 WHERE username='abc' AND id=2",
                    "SELECT * FROM deletion_test1"
                ],
                'results': [
                    [list(('abc', 2, 'rst', 'some value')), list(('abc', 4, 'xyz', 'some other value'))],
                    [],
                    [list(('abc', 4, 'xyz', 'some other value'))],
                    [],
                    [],
                    [list(('abc', 2, 'rst', 'some value')), list(('abc', 4, 'xyz', 'some other value'))],
                    [],
                    [list(('abc', 4, 'xyz', 'some other value'))]],
                'invalid_queries': [
                    "SELECT c1, c2, v FROM test2 WHERE k = 0 ORDER BY c1 ASC, c2 ASC",
                    "SELECT c1, c2, v FROM test2 WHERE k = 0 ORDER BY c1 DESC, c2 DESC",
                    "SELECT c1, c2, v FROM reversed_comparator_test2 WHERE k = 0 ORDER BY c2 DESC, c1 ASC"],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # count_test
            {
                'create_tables': ["""CREATE TABLE count_test (
                        kind text,
                        time int,
                        value1 int,
                        value2 int,
                        PRIMARY KEY(kind, time)
                    )"""],
                'truncates': ['TRUNCATE count_test'],
                'inserts': [
                    "INSERT INTO count_test (kind, time, value1, value2) VALUES ('ev1', 0, 0, 0)",
                    "INSERT INTO count_test (kind, time, value1, value2) VALUES ('ev1', 1, 1, 1)",
                    "INSERT INTO count_test (kind, time, value1) VALUES ('ev1', 2, 2)",
                    "INSERT INTO count_test (kind, time, value1, value2) VALUES ('ev1', 3, 3, 3)",
                    "INSERT INTO count_test (kind, time, value1) VALUES ('ev1', 4, 4)",
                    "INSERT INTO count_test (kind, time, value1, value2) VALUES ('ev2', 0, 0, 0)"],
                'queries': ["SELECT COUNT(*) FROM count_test WHERE kind = 'ev1'",
                            "SELECT COUNT(1) FROM count_test WHERE kind IN ('ev1', 'ev2') AND time=0"],
                'results': [
                    [[5]],
                    [[2]]],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # batch_test
            {
                'create_tables': ["""CREATE TABLE batch_test (
                        userid text PRIMARY KEY,
                        name text,
                        password text
                    )"""],
                'truncates': ['TRUNCATE batch_test'],
                'inserts': [
                    """BEGIN BATCH
                    INSERT INTO batch_test (userid, password, name) VALUES ('user2', 'ch@ngem3b', 'second user');
                    UPDATE batch_test SET password = 'ps22dhds' WHERE userid = 'user3';
                    INSERT INTO batch_test (userid, password) VALUES ('user4', 'ch@ngem3c');
                    DELETE name FROM batch_test WHERE userid = 'user1';
                APPLY BATCH;"""],
                'queries': [],
                'results': [],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # table_options_test
            {
                'create_tables': ["""CREATE TABLE table_options_test (
                        k int PRIMARY KEY,
                        c int
                    ) WITH comment = 'My comment'
                       AND read_repair_chance = 0.5
                       AND dclocal_read_repair_chance = 0.5
                       AND gc_grace_seconds = 4
                       AND bloom_filter_fp_chance = 0.01
                       AND compaction = { 'class' : 'LeveledCompactionStrategy',
                                          'sstable_size_in_mb' : 10 }
                       AND compression = { 'sstable_compression' : '' }
                       AND caching = 'all'"""],
                'truncates': ['TRUNCATE table_options_test'],
                'inserts': [],
                'queries': ["""
                    ALTER TABLE table_options_test
                    WITH comment = 'other comment'
                     AND read_repair_chance = 0.3
                     AND dclocal_read_repair_chance = 0.3
                     AND gc_grace_seconds = 100
                     AND bloom_filter_fp_chance = 0.1
                     AND compaction = { 'class' : 'SizeTieredCompactionStrategy',
                                        'min_sstable_size' : 42 }
                     AND compression = { 'sstable_compression' : 'SnappyCompressor' }
                     AND caching = 'rows_only'
                """],
                'results': [[]],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # timestamp_and_ttl_test
            {
                'create_tables': ["""CREATE TABLE timestamp_and_ttl_test(
                        k int PRIMARY KEY,
                        c text,
                        d text
                    )"""],
                'truncates': ['TRUNCATE timestamp_and_ttl_test'],
                'inserts': ["INSERT INTO timestamp_and_ttl_test (k, c) VALUES (1, 'test')",
                            "INSERT INTO timestamp_and_ttl_test (k, c) VALUES (2, 'test') USING TTL 400",
                            "SELECT k, c, writetime(c), ttl(c) FROM timestamp_and_ttl_test",
                            "SELECT k, c, blobAsBigint(bigintAsBlob(writetime(c))), ttl(c) FROM timestamp_and_ttl_test",
                            "SELECT k, c, writetime(c), blobAsInt(intAsBlob(ttl(c))) FROM timestamp_and_ttl_test"],
                'queries': ["SELECT k, d, writetime(d) FROM timestamp_and_ttl_test WHERE k = 1"],
                'results': [[[1, None, None]]],
                'invalid_queries': ["SELECT k, c, writetime(k) FROM timestamp_and_ttl_test"],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # no_range_ghost_test
            {
                'create_tables': ["CREATE TABLE no_range_ghost_test (k int PRIMARY KEY, v int)",
                                  "CREATE KEYSPACE ks_no_range_ghost_test with replication = { 'class' : 'SimpleStrategy', 'replication_factor' : 1 };",
                                  """CREATE COLUMNFAMILY ks_no_range_ghost_test.users (
                                                                              KEY varchar PRIMARY KEY,
                                                                              password varchar,
                                                                              gender varchar,
                                                                              birth_year bigint)"""
                                  ],
                'truncates': ['TRUNCATE no_range_ghost_test'],
                'inserts': ["INSERT INTO no_range_ghost_test (k, v) VALUES (%d, 0)" % k for k in range(0, 5)],
                'queries': ["#SORTED SELECT k FROM no_range_ghost_test",
                            "DELETE FROM no_range_ghost_test WHERE k = 2",
                            "#SORTED SELECT k FROM no_range_ghost_test",
                            "USE ks_no_range_ghost_test",
                            "INSERT INTO ks_no_range_ghost_test.users (KEY, password) VALUES ('user1', 'ch@ngem3a')",
                            "UPDATE ks_no_range_ghost_test.users SET gender = 'm', birth_year = 1980 WHERE KEY = 'user1'",
                            "TRUNCATE ks_no_range_ghost_test.users",
                            "SELECT * FROM ks_no_range_ghost_test.users",
                            "SELECT * FROM ks_no_range_ghost_test.users WHERE KEY='user1'"
                            ],
                'results': [[[k] for k in range(0, 5)],
                            [],
                            [[k] for k in range(0, 5) if k is not 2],
                            [],
                            [],
                            [],
                            [],
                            [],
                            []
                            ],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # undefined_column_handling_test
            {
                'create_tables': ["""CREATE TABLE undefined_column_handling_test (
                        k int PRIMARY KEY,
                        v1 int,
                        v2 int,
                    )"""],
                'truncates': ['TRUNCATE undefined_column_handling_test'],
                'inserts': ["INSERT INTO undefined_column_handling_test (k, v1, v2) VALUES (0, 0, 0)",
                            "INSERT INTO undefined_column_handling_test (k, v1) VALUES (1, 1)",
                            "INSERT INTO undefined_column_handling_test (k, v1, v2) VALUES (2, 2, 2)"],
                'queries': ["SELECT v2 FROM undefined_column_handling_test",
                            "SELECT v2 FROM undefined_column_handling_test WHERE k = 1"],
                'results': [[[None], [0], [2]],
                            [[None]]],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # range_tombstones_test: Test deletion by 'composite prefix' (range tombstones)
            {
                'create_tables': ["""CREATE TABLE range_tombstones_test (
                    k int,
                    c1 int,
                    c2 int,
                    v1 int,
                    v2 int,
                    PRIMARY KEY (k, c1, c2)
                );"""],
                'truncates': [],
                'inserts': ["INSERT INTO range_tombstones_test (k, c1, c2, v1, v2) VALUES (%d, %d, %d, %d, %d)" % (
                    i, j, k, (i * 4) + (j * 2) + k, (i * 4) + (j * 2) + k) for i in xrange(0, 5) for j in xrange(0, 2)
                            for k
                            in xrange(0, 2)],
                'queries': ["SELECT v1, v2 FROM range_tombstones_test where k = %d" % 0,
                            "SELECT v1, v2 FROM range_tombstones_test where k = %d" % 1,
                            "SELECT v1, v2 FROM range_tombstones_test where k = %d" % 2,
                            "SELECT v1, v2 FROM range_tombstones_test where k = %d" % 3,
                            "SELECT v1, v2 FROM range_tombstones_test where k = %d" % 4,
                            "DELETE FROM range_tombstones_test WHERE k = %d AND c1 = 0" % 0,
                            "DELETE FROM range_tombstones_test WHERE k = %d AND c1 = 0" % 1,
                            "DELETE FROM range_tombstones_test WHERE k = %d AND c1 = 0" % 2,
                            "DELETE FROM range_tombstones_test WHERE k = %d AND c1 = 0" % 3,
                            "DELETE FROM range_tombstones_test WHERE k = %d AND c1 = 0" % 4,
                            "SELECT v1, v2 FROM range_tombstones_test WHERE k = %d" % 0,
                            "SELECT v1, v2 FROM range_tombstones_test WHERE k = %d" % 1,
                            "SELECT v1, v2 FROM range_tombstones_test WHERE k = %d" % 2,
                            "SELECT v1, v2 FROM range_tombstones_test WHERE k = %d" % 3,
                            "SELECT v1, v2 FROM range_tombstones_test WHERE k = %d" % 4,
                            "#REMOTER_RUN sudo nodetool flush",
                            "SELECT v1, v2 FROM range_tombstones_test WHERE k = %d" % 0,
                            "SELECT v1, v2 FROM range_tombstones_test WHERE k = %d" % 1,
                            "SELECT v1, v2 FROM range_tombstones_test WHERE k = %d" % 2,
                            "SELECT v1, v2 FROM range_tombstones_test WHERE k = %d" % 3,
                            "SELECT v1, v2 FROM range_tombstones_test WHERE k = %d" % 4],
                'results': [[[x, x] for x in xrange(0 * 4, (0 + 1) * 4)],
                            [[x, x] for x in xrange(1 * 4, (1 + 1) * 4)],
                            [[x, x] for x in xrange(2 * 4, (2 + 1) * 4)],
                            [[x, x] for x in xrange(3 * 4, (3 + 1) * 4)],
                            [[x, x] for x in xrange(4 * 4, (4 + 1) * 4)],
                            [],
                            [],
                            [],
                            [],
                            [],
                            [[x, x] for x in xrange(0 * 4 + 2, (0 + 1) * 4)],
                            [[x, x] for x in xrange(1 * 4 + 2, (1 + 1) * 4)],
                            [[x, x] for x in xrange(2 * 4 + 2, (2 + 1) * 4)],
                            [[x, x] for x in xrange(3 * 4 + 2, (3 + 1) * 4)],
                            [[x, x] for x in xrange(4 * 4 + 2, (4 + 1) * 4)],
                            None,
                            [[x, x] for x in xrange(0 * 4 + 2, (0 + 1) * 4)],
                            [[x, x] for x in xrange(1 * 4 + 2, (1 + 1) * 4)],
                            [[x, x] for x in xrange(2 * 4 + 2, (2 + 1) * 4)],
                            [[x, x] for x in xrange(3 * 4 + 2, (3 + 1) * 4)],
                            [[x, x] for x in xrange(4 * 4 + 2, (4 + 1) * 4)]],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # range_tombstones_compaction_test: Test deletion by 'composite prefix' (range tombstones) with compaction
            {
                'create_tables': ["""CREATE TABLE range_tombstones_compaction_test (
                    k int,
                    c1 int,
                    c2 int,
                    v1 text,
                    PRIMARY KEY (k, c1, c2)
                );"""],
                'truncates': [],
                'inserts': ["INSERT INTO range_tombstones_compaction_test (k, c1, c2, v1) VALUES (0, %d, %d, '%s')" % (
                    c1, c2, '%i%i' % (c1, c2)) for c1 in range(0, 4) for c2 in range(0, 2)],
                'queries': ["#REMOTER_RUN sudo nodetool flush",
                            "DELETE FROM range_tombstones_compaction_test WHERE k = 0 AND c1 = 1",
                            "#REMOTER_RUN sudo nodetool flush",
                            "#REMOTER_RUN sudo nodetool compact",
                            "SELECT v1 FROM range_tombstones_compaction_test WHERE k = 0"],
                'results': [None,
                            [],
                            None,
                            None,
                            [['%i%i' % (c1, c2)] for c1 in xrange(0, 4) for c2 in xrange(0, 2) if c1 != 1]],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # delete_row_test: Test deletion of rows
            {
                'create_tables': ["""CREATE TABLE delete_row_test (
                     k int,
                     c1 int,
                     c2 int,
                     v1 int,
                     v2 int,
                     PRIMARY KEY (k, c1, c2)
                );"""],
                'truncates': ["TRUNCATE delete_row_test"],
                'inserts': [
                    "INSERT INTO delete_row_test(k, c1, c2, v1, v2) VALUES (%d, %d, %d, %d, %d)" % (0, 0, 0, 0, 0),
                    "INSERT INTO delete_row_test(k, c1, c2, v1, v2) VALUES (%d, %d, %d, %d, %d)" % (0, 0, 1, 1, 1),
                    "INSERT INTO delete_row_test(k, c1, c2, v1, v2) VALUES( %d, %d, %d, %d, %d)" % (0, 0, 2, 2, 2),
                    "INSERT INTO delete_row_test(k, c1, c2, v1, v2) VALUES( %d, %d, %d, %d, %d)" % (0, 1, 0, 3, 3),
                    "DELETE FROM delete_row_test WHERE k = 0 AND c1 = 0 AND c2 = 0"],
                'queries': ["SELECT * FROM delete_row_test"],
                'results': [[[0, 0, 1, 1, 1], [0, 0, 2, 2, 2], [0, 1, 0, 3, 3]]],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # range_query_2ndary_test: Test range queries with 2ndary indexes CASSANDRA-4257
            {
                'create_tables': ["CREATE TABLE range_query_2ndary_test (id int primary key, row int, setid int);",
                                  "CREATE INDEX indextest_setid_idx ON range_query_2ndary_test (setid)"],
                'truncates': ["TRUNCATE range_query_2ndary_test"],
                'inserts': [
                    "INSERT INTO range_query_2ndary_test (id, row, setid) VALUES (%d, %d, %d);" % (0, 0, 0),
                    "INSERT INTO range_query_2ndary_test (id, row, setid) VALUES (%d, %d, %d);" % (0, 0, 0),
                    "INSERT INTO range_query_2ndary_test (id, row, setid) VALUES (%d, %d, %d);" % (1, 1, 0),
                    "INSERT INTO range_query_2ndary_test (id, row, setid) VALUES (%d, %d, %d);" % (3, 3, 0)],
                'queries': ["SELECT * FROM range_query_2ndary_test WHERE setid = 0 AND row < 1 ALLOW FILTERING;"],
                'results': [[[0, 0, 0]]],
                'invalid_queries': ["SELECT * FROM range_query_2ndary_test WHERE setid = 0 AND row < 1;"],
                'min_version': '',
                'max_version': '',
                'skip': 'Index support is not enabled'},
            # set_test
            {
                'create_tables': ["""CREATE TABLE set_test (
                    fn text,
                    ln text,
                    tags set<text>,
                    PRIMARY KEY (fn, ln)
                )"""],
                'truncates': ["TRUNCATE set_test"],
                'inserts': ["UPDATE set_test SET %s WHERE fn='Tom' AND ln='Bombadil'" % "tags = tags + { 'foo' }",
                            "UPDATE set_test SET %s WHERE fn='Tom' AND ln='Bombadil'" % "tags = tags + { 'bar' }",
                            "UPDATE set_test SET %s WHERE fn='Tom' AND ln='Bombadil'" % "tags = tags + { 'foo' }",
                            "UPDATE set_test SET %s WHERE fn='Tom' AND ln='Bombadil'" % "tags = tags + { 'foobar' }",
                            "UPDATE set_test SET %s WHERE fn='Tom' AND ln='Bombadil'" % "tags = tags - { 'bar' }"],
                'queries': ["SELECT tags FROM set_test",
                            "UPDATE set_test SET {} WHERE fn='Bilbo' AND ln='Baggins'".format(
                                "tags = { 'a', 'c', 'b' }"),
                            "SELECT tags FROM set_test WHERE fn='Bilbo' AND ln='Baggins'",
                            "UPDATE set_test SET {} WHERE fn='Bilbo' AND ln='Baggins'".format("tags = { 'm', 'n' }"),
                            "SELECT tags FROM set_test WHERE fn='Bilbo' AND ln='Baggins'",
                            "DELETE tags['m'] FROM set_test WHERE fn='Bilbo' AND ln='Baggins'",
                            "SELECT tags FROM set_test WHERE fn='Bilbo' AND ln='Baggins'",
                            "DELETE tags FROM set_test WHERE fn='Bilbo' AND ln='Baggins'",
                            "SELECT tags FROM set_test WHERE fn='Bilbo' AND ln='Baggins'"],
                'results': [[[set(['foo', 'foobar'])]],
                            [],
                            [[set(['a', 'b', 'c'])]],
                            [],
                            [[set(['m', 'n'])]],
                            [],
                            [[set(['n'])]],
                            [], []],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # map_test
            {
                'create_tables': ["""CREATE TABLE map_test (
                fn text,
                ln text,
                m map<text, int>,
                PRIMARY KEY (fn, ln)
            )"""],
                'truncates': ["TRUNCATE map_test"],
                'inserts': ["UPDATE map_test SET %s WHERE fn='Tom' AND ln='Bombadil'" % "m['foo'] = 3",
                            "UPDATE map_test SET %s WHERE fn='Tom' AND ln='Bombadil'" % "m['bar'] = 4",
                            "UPDATE map_test SET %s WHERE fn='Tom' AND ln='Bombadil'" % "m['woot'] = 5",
                            "UPDATE map_test SET %s WHERE fn='Tom' AND ln='Bombadil'" % "m['bar'] = 6",
                            "DELETE m['foo'] FROM map_test WHERE fn='Tom' AND ln='Bombadil'"],
                'queries': ["SELECT m FROM map_test",
                            "UPDATE map_test SET %s WHERE fn='Bilbo' AND ln='Baggins'" % "m = { 'a' : 4 , 'c' : 3, 'b' : 2 }",
                            "SELECT m FROM map_test WHERE fn='Bilbo' AND ln='Baggins'",
                            "UPDATE map_test SET %s WHERE fn='Bilbo' AND ln='Baggins'" % "m = { 'm' : 4 , 'n' : 1, 'o' : 2 }",
                            "SELECT m FROM map_test WHERE fn='Bilbo' AND ln='Baggins'",
                            "UPDATE map_test SET %s WHERE fn='Bilbo' AND ln='Baggins'" % "m = {}",
                            "SELECT m FROM map_test WHERE fn='Bilbo' AND ln='Baggins'"
                            ],
                'results': [[[{'woot': 5, 'bar': 6}]],
                            [],
                            [[{'a': 4, 'b': 2, 'c': 3}]],
                            [],
                            [[{'m': 4, 'n': 1, 'o': 2}]],
                            [],
                            []
                            ],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # list_test
            {
                'create_tables': ["""CREATE TABLE list_test (
                    fn text,
                    ln text,
                    tags list<text>,
                    PRIMARY KEY (fn, ln)
                )"""],
                'truncates': ["TRUNCATE list_test"],
                'inserts': ["UPDATE list_test SET %s WHERE fn='Tom' AND ln='Bombadil'" % "tags = tags + [ 'foo' ]",
                            "UPDATE list_test SET %s WHERE fn='Tom' AND ln='Bombadil'" % "tags = tags + [ 'bar' ]",
                            "UPDATE list_test SET %s WHERE fn='Tom' AND ln='Bombadil'" % "tags = tags + [ 'foo' ]",
                            "UPDATE list_test SET %s WHERE fn='Tom' AND ln='Bombadil'" % "tags = tags + [ 'foobar' ]"],
                'queries': ["SELECT tags FROM list_test",
                            "UPDATE list_test SET %s WHERE fn='Bilbo' AND ln='Baggins'" % "tags = [ 'a', 'c', 'b', 'c' ]",
                            "SELECT tags FROM list_test WHERE fn='Bilbo' AND ln='Baggins'",
                            "UPDATE list_test SET %s WHERE fn='Bilbo' AND ln='Baggins'" % "tags = [ 'm', 'n' ] + tags",
                            "SELECT tags FROM list_test WHERE fn='Bilbo' AND ln='Baggins'",
                            "UPDATE list_test SET %s WHERE fn='Bilbo' AND ln='Baggins'" % "tags[2] = 'foo', tags[4] = 'bar'",
                            "SELECT tags FROM list_test WHERE fn='Bilbo' AND ln='Baggins'",
                            "DELETE tags[2] FROM list_test WHERE fn='Bilbo' AND ln='Baggins'",
                            "SELECT tags FROM list_test WHERE fn='Bilbo' AND ln='Baggins'",
                            "UPDATE list_test SET %s WHERE fn='Bilbo' AND ln='Baggins'" % "tags = tags - [ 'bar' ]",
                            "SELECT tags FROM list_test WHERE fn='Bilbo' AND ln='Baggins'"
                            ],
                'results': [[[[u'foo', u'bar', u'foo', u'foobar']]],
                            [],
                            [[[u'a', u'c', u'b', u'c']]],
                            [],
                            [[[u'm', u'n', u'a', u'c', u'b', u'c']]],
                            [],
                            [[[u'm', u'n', u'foo', u'c', u'bar', u'c']]],
                            [],
                            [[[u'm', u'n', u'c', u'bar', u'c']]],
                            [],
                            [[[u'm', u'n', u'c', u'c']]]
                            ],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # multi_collection_test
            {
                'create_tables': ["""CREATE TABLE multi_collection_test(
                    k uuid PRIMARY KEY,
                    L list<int>,
                    M map<text, int>,
                    S set<int>
                );"""],
                'truncates': ["TRUNCATE multi_collection_test"],
                'inserts': [
                    "UPDATE multi_collection_test SET L = [1, 3, 5] WHERE k = b017f48f-ae67-11e1-9096-005056c00008;",
                    "UPDATE multi_collection_test SET L = L + [7, 11, 13] WHERE k = b017f48f-ae67-11e1-9096-005056c00008;",
                    "UPDATE multi_collection_test SET S = {1, 3, 5} WHERE k = b017f48f-ae67-11e1-9096-005056c00008;",
                    "UPDATE multi_collection_test SET S = S + {7, 11, 13} WHERE k = b017f48f-ae67-11e1-9096-005056c00008;",
                    "UPDATE multi_collection_test SET M = {'foo': 1, 'bar' : 3} WHERE k = b017f48f-ae67-11e1-9096-005056c00008;",
                    "UPDATE multi_collection_test SET M = M + {'foobar' : 4} WHERE k = b017f48f-ae67-11e1-9096-005056c00008;"],
                'queries': ["SELECT L, M, S FROM multi_collection_test WHERE k = b017f48f-ae67-11e1-9096-005056c00008"
                            ],
                'results': [[[[1, 3, 5, 7, 11, 13], OrderedDict([('bar', 3), ('foo', 1), ('foobar', 4)]),
                              sortedset([1, 3, 5, 7, 11, 13])
                              ]]
                            ],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # range_query_test : Range test query from CASSANDRA-4372
            {
                'create_tables': [
                    "CREATE TABLE range_query_test (a int, b int, c int, d int, e int, f text, PRIMARY KEY (a, b, c, d, e) )"],
                'truncates': ["TRUNCATE range_query_test"],
                'inserts': [
                    "INSERT INTO range_query_test (a, b, c, d, e, f) VALUES (1, 1, 1, 1, 2, '2');",
                    "INSERT INTO range_query_test (a, b, c, d, e, f) VALUES (1, 1, 1, 1, 1, '1');",
                    "INSERT INTO range_query_test (a, b, c, d, e, f) VALUES (1, 1, 1, 2, 1, '1');",
                    "INSERT INTO range_query_test (a, b, c, d, e, f) VALUES (1, 1, 1, 1, 3, '3');",
                    "INSERT INTO range_query_test (a, b, c, d, e, f) VALUES (1, 1, 1, 1, 5, '5');"
                ],
                'queries': [
                    "SELECT a, b, c, d, e, f FROM range_query_test WHERE a = 1 AND b = 1 AND c = 1 AND d = 1 AND e >= 2;"
                ],
                'results': [[[1, 1, 1, 1, 2, u'2'], [1, 1, 1, 1, 3, u'3'], [1, 1, 1, 1, 5, u'5']]
                            ],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # composite_row_key_test
            {
                'create_tables': [
                    """CREATE TABLE composite_row_key_test (
                k1 int,
                k2 int,
                c int,
                v int,
                PRIMARY KEY ((k1, k2), c)
            )
        """],
                'truncates': ["TRUNCATE composite_row_key_test"],
                'inserts': [
                    "INSERT INTO composite_row_key_test (k1, k2, c, v) VALUES ({}, {}, {}, {})".format(0, i, i, i) for i
                    in range(0, 4)
                    ],
                'queries': [
                    "SELECT * FROM composite_row_key_test",
                    "SELECT * FROM composite_row_key_test WHERE k1 = 0 and k2 IN (1, 3)",
                    "SELECT * FROM composite_row_key_test WHERE token(k1, k2) = token(0, 1)",
                    "SELECT * FROM composite_row_key_test WHERE token(k1, k2) > " + str(-((2 ** 63) - 1))
                ],
                'results': [[[0, 2, 2, 2], [0, 3, 3, 3], [0, 0, 0, 0], [0, 1, 1, 1]],
                            [[0, 1, 1, 1], [0, 3, 3, 3]],
                            [[0, 1, 1, 1]],
                            [[0, 2, 2, 2], [0, 3, 3, 3], [0, 0, 0, 0], [0, 1, 1, 1]]],
                'invalid_queries': ["SELECT * FROM test WHERE k2 = 3"],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # row_existence_test: Check the semantic of CQL row existence CASSANDRA-4361
            {
                'create_tables': [
                    """CREATE TABLE row_existence_test (
                k int,
                c int,
                v1 int,
                v2 int,
                PRIMARY KEY (k, c)
            )"""],
                'truncates': ["TRUNCATE row_existence_test"],
                'inserts': ["INSERT INTO row_existence_test (k, c, v1, v2) VALUES (1, 1, 1, 1)"],
                'queries': [
                    "SELECT * FROM row_existence_test",
                    "DELETE v2 FROM row_existence_test WHERE k = 1 AND c = 1",
                    "SELECT * FROM row_existence_test",
                    "DELETE v1 FROM row_existence_test WHERE k = 1 AND c = 1",
                    "SELECT * FROM row_existence_test",
                    "DELETE FROM row_existence_test WHERE k = 1 AND c = 1",
                    "SELECT * FROM row_existence_test",
                    "INSERT INTO row_existence_test (k, c) VALUES (2, 2)",
                    "SELECT * FROM row_existence_test"
                ],
                'results': [[[1, 1, 1, 1]],
                            [],
                            [[1, 1, 1, None]],
                            [],
                            [[1, 1, None, None]],
                            [],
                            [],
                            [],
                            [[2, 2, None, None]]],
                'invalid_queries': ["DELETE c FROM row_existence_test WHERE k = 1 AND c = 1"],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # only_pk_test
            {
                'create_tables': [
                    """CREATE TABLE only_pk_test1 (
                k int,
                c int,
                PRIMARY KEY (k, c)
            )""", """
                CREATE TABLE only_pk_test2 (
                    k int,
                    c int,
                    PRIMARY KEY (k, c)
                ) WITH COMPACT STORAGE
            """],
                'truncates': ["TRUNCATE only_pk_test1", "TRUNCATE only_pk_test2"],
                'inserts': ["INSERT INTO only_pk_test1 (k, c) VALUES (%s, %s)" % (k, c) for k in range(0, 2) for c in
                            range(0, 2)],
                'queries': ["#SORTED SELECT * FROM only_pk_test1",
                            "INSERT INTO only_pk_test2(k, c) VALUES(0, 0)",
                            "INSERT INTO only_pk_test2(k, c) VALUES(0, 1)",
                            "INSERT INTO only_pk_test2(k, c) VALUES(1, 0)",
                            "INSERT INTO only_pk_test2(k, c) VALUES(1, 1)",
                            "#SORTED SELECT * FROM only_pk_test2"
                            ],
                'results': [[[x, y] for x in range(0, 2) for y in range(0, 2)],
                            [],
                            [],
                            [],
                            [],
                            [[x, y] for x in range(0, 2) for y in range(0, 2)]],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # no_clustering_test
            {
                'create_tables': ["CREATE TABLE no_clustering_test (k int PRIMARY KEY, v int)"],
                'truncates': [],
                'inserts': ["INSERT INTO no_clustering_test (k, v) VALUES (%s, %s)" % (i, i) for i in range(10)],
                'queries': ["#SORTED SELECT * FROM no_clustering_test"],
                'results': [[[i, i] for i in range(10)]],
                'disable_paging': True,
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # date_test
            {
                'create_tables': ["CREATE TABLE date_test (k int PRIMARY KEY, t timestamp)"],
                'truncates': ["TRUNCATE date_test"],
                'inserts': ["INSERT INTO date_test (k, t) VALUES (0, '2011-02-03')"],
                'queries': [],
                'results': [],
                'invalid_queries': ["INSERT INTO date_test (k, t) VALUES (0, '2011-42-42')"],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # range_slice_test: Test a regression from CASSANDRA-1337
            {
                'create_tables': ["""
            CREATE TABLE range_slice_test (
                k text PRIMARY KEY,
                v int
            );
        """],
                'truncates': ["TRUNCATE range_slice_test"],
                'inserts': ["INSERT INTO range_slice_test (k, v) VALUES ('foo', 0)",
                            "INSERT INTO range_slice_test (k, v) VALUES ('bar', 1)"],
                'queries': ["SELECT * FROM range_slice_test"],
                'results': [[['bar', 1], ['foo', 0]]],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # composite_index_with_pk_test
            {
                'create_tables': ["""CREATE TABLE composite_index_with_pk_test (
                blog_id int,
                time1 int,
                time2 int,
                author text,
                content text,
                PRIMARY KEY (blog_id, time1, time2))"""],
                'truncates': ["TRUNCATE composite_index_with_pk_test"],
                'inserts': [
                    "INSERT INTO blogs (blog_id, time1, time2, author, content) VALUES (%d, %d, %d, '%s', '%s')" % (
                        1, 0, 0, 'foo', 'bar1'),
                    "INSERT INTO blogs (blog_id, time1, time2, author, content) VALUES (%d, %d, %d, '%s', '%s')" % (
                        1, 0, 1, 'foo', 'bar2'),
                    "INSERT INTO blogs (blog_id, time1, time2, author, content) VALUES (%d, %d, %d, '%s', '%s')" % (
                        2, 1, 0, 'foo', 'baz'),
                    "INSERT INTO blogs (blog_id, time1, time2, author, content) VALUES (%d, %d, %d, '%s', '%s')" % (
                        3, 0, 1, 'gux', 'qux')],
                'queries': ["SELECT blog_id, content FROM blogs WHERE author='foo'",
                            "SELECT blog_id, content FROM blogs WHERE time1 > 0 AND author='foo' ALLOW FILTERING",
                            "SELECT blog_id, content FROM blogs WHERE time1 = 1 AND author='foo' ALLOW FILTERING",
                            "SELECT blog_id, content FROM blogs WHERE time1 = 1 AND time2 = 0 AND author='foo' ALLOW FILTERING",
                            "SELECT content FROM blogs WHERE time1 = 1 AND time2 = 1 AND author='foo' ALLOW FILTERING",
                            "SELECT content FROM blogs WHERE time1 = 1 AND time2 > 0 AND author='foo' ALLOW FILTERING",
                            ],
                'results': [[[1, 'bar1'], [1, 'bar2'], [2, 'baz']],
                            [[2, 'baz']],
                            [[2, 'baz']],
                            [[2, 'baz']],
                            None,
                            None
                            ],
                'invalid_queries': ["SELECT content FROM blogs WHERE time2 >= 0 AND author='foo'",
                                    "SELECT blog_id, content FROM blogs WHERE time1 > 0 AND author='foo'",
                                    "SELECT blog_id, content FROM blogs WHERE time1 = 1 AND author='foo'",
                                    "SELECT blog_id, content FROM blogs WHERE time1 = 1 AND time2 = 0 AND author='foo'",
                                    "SELECT content FROM blogs WHERE time1 = 1 AND time2 = 1 AND author='foo'",
                                    "SELECT content FROM blogs WHERE time1 = 1 AND time2 > 0 AND author='foo'"
                                    ],
                'min_version': '',
                'max_version': '',
                'skip': 'Index support is not enabled'},
            # limit_bugs_test: Test for LIMIT bugs from CASSANDRA-4579
            {
                'create_tables': ["""CREATE TABLE limit_bugs_test1 (
                a int,
                b int,
                c int,
                d int,
                e int,
                PRIMARY KEY (a, b)
            );""", """
            CREATE TABLE limit_bugs_test2 (
                a int primary key,
                b int,
                c int,
            );
        """],
                'truncates': ["TRUNCATE limit_bugs_test1", "TRUNCATE limit_bugs_test2"],
                'inserts': ["INSERT INTO limit_bugs_test1 (a, b, c, d, e) VALUES (1, 1, 1, 1, 1);",
                            "INSERT INTO limit_bugs_test1 (a, b, c, d, e) VALUES (2, 2, 2, 2, 2);",
                            "INSERT INTO limit_bugs_test1 (a, b, c, d, e) VALUES (3, 3, 3, 3, 3);",
                            "INSERT INTO limit_bugs_test1 (a, b, c, d, e) VALUES (4, 4, 4, 4, 4);",
                            "INSERT INTO limit_bugs_test2 (a, b, c) VALUES (1, 1, 1);",
                            "INSERT INTO limit_bugs_test2 (a, b, c) VALUES (2, 2, 2);",
                            "INSERT INTO limit_bugs_test2 (a, b, c) VALUES (3, 3, 3);",
                            "INSERT INTO limit_bugs_test2 (a, b, c) VALUES (4, 4, 4);"
                            ],
                'queries': ["#SORTED SELECT * FROM limit_bugs_test1",
                            "SELECT * FROM limit_bugs_test1 LIMIT 1;",
                            "#SORTED SELECT * FROM limit_bugs_test1 LIMIT 2;",
                            "#SORTED SELECT * FROM limit_bugs_test2;",
                            "SELECT * FROM limit_bugs_test2 LIMIT 1;",
                            "#SORTED SELECT * FROM limit_bugs_test2 LIMIT 2;",
                            "#SORTED SELECT * FROM limit_bugs_test2 LIMIT 3;",
                            "#SORTED SELECT * FROM limit_bugs_test2 LIMIT 4;",
                            "#SORTED SELECT * FROM limit_bugs_test2 LIMIT 5;",
                            ],
                'results': [[[1, 1, 1, 1, 1], [2, 2, 2, 2, 2], [3, 3, 3, 3, 3], [4, 4, 4, 4, 4]],
                            [[1, 1, 1, 1, 1]],
                            [[1, 1, 1, 1, 1], [2, 2, 2, 2, 2]],
                            [[1, 1, 1], [2, 2, 2], [3, 3, 3], [4, 4, 4]],
                            [[1, 1, 1]],
                            [[1, 1, 1], [2, 2, 2]],
                            [[1, 1, 1], [2, 2, 2], [3, 3, 3]],
                            [[1, 1, 1], [2, 2, 2], [3, 3, 3], [4, 4, 4]],
                            [[1, 1, 1], [2, 2, 2], [3, 3, 3], [4, 4, 4]]
                            ],
                'min_version': '',
                'max_version': '',
                'skip': 'limit_bugs_test'},
            # npe_composite_table_slice_test: Test for NPE when trying to select a slice from a composite table CASSANDRA-4532
            {
                'create_tables': ["""CREATE TABLE npe_composite_table_slice_test(
                status ascii,
                ctime bigint,
                key ascii,
                nil ascii,
                PRIMARY KEY (status, ctime, key)
            )"""],
                'truncates': ["TRUNCATE npe_composite_table_slice_test"],
                'inserts': [
                    "INSERT INTO npe_composite_table_slice_test(status,ctime,key,nil) VALUES ('C',12345678,'key1','')",
                    "INSERT INTO npe_composite_table_slice_test(status,ctime,key,nil) VALUES ('C',12345678,'key2','')",
                    "INSERT INTO npe_composite_table_slice_test(status,ctime,key,nil) VALUES ('C',12345679,'key3','')",
                    "INSERT INTO npe_composite_table_slice_test(status,ctime,key,nil) VALUES ('C',12345679,'key4','')",
                    "INSERT INTO npe_composite_table_slice_test(status,ctime,key,nil) VALUES ('C',12345679,'key5','')",
                    "INSERT INTO npe_composite_table_slice_test(status,ctime,key,nil) VALUES ('C',12345680,'key6','')"],
                'queries': [],
                'results': [],
                'invalid_queries': [
                    "SELECT * FROM npe_composite_table_slice_test WHERE ctime>=12345679 AND key='key3' AND ctime<=12345680 LIMIT 3;",
                    "SELECT * FROM npe_composite_table_slice_test WHERE ctime=12345679  AND key='key3' AND ctime<=12345680 LIMIT 3;"],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # order_by_multikey_test: Test for #CASSANDRA-4612 bug and more generally order by when multiple C* rows are queried
            {
                'create_tables': ["""CREATE TABLE order_by_multikey_test(
                my_id varchar,
                col1 int,
                col2 int,
                value varchar,
                PRIMARY KEY (my_id, col1, col2)
            );"""],
                'truncates': ["TRUNCATE order_by_multikey_test"],
                'inserts': [
                    "INSERT INTO order_by_multikey_test(my_id, col1, col2, value) VALUES ( 'key1', 1, 1, 'a');",
                    "INSERT INTO order_by_multikey_test(my_id, col1, col2, value) VALUES ( 'key2', 3, 3, 'a');",
                    "INSERT INTO order_by_multikey_test(my_id, col1, col2, value) VALUES ( 'key3', 2, 2, 'b');",
                    "INSERT INTO order_by_multikey_test(my_id, col1, col2, value) VALUES ( 'key4', 2, 1, 'b');"
                ],
                'queries': [
                    "SELECT col1 FROM order_by_multikey_test WHERE my_id in('key1', 'key2', 'key3') ORDER BY col1;",
                    "SELECT col1, value, my_id, col2 FROM order_by_multikey_test WHERE my_id in('key3', 'key4') ORDER BY col1, col2;"],
                'results': [[[1], [2], [3]],
                            [[2, 'b', 'key4', 1], [2, 'b', 'key3', 2]]],
                'invalid_queries': [
                    "SELECT col1 FROM order_by_multikey_test ORDER BY col1;",
                    "SELECT col1 FROM order_by_multikey_test WHERE my_id > 'key1' ORDER BY col1;"],
                'min_version': '',
                'max_version': '',
                'disable_paging': True,
                'skip': ''},
            # remove_range_slice_test
            {
                'create_tables': ["""CREATE TABLE remove_range_slice_test (
                k int PRIMARY KEY,
                v int
            )"""],
                'truncates': ["TRUNCATE remove_range_slice_test"],
                'inserts': ["INSERT INTO remove_range_slice_test (k, v) VALUES ({}, {})".format(i, i) for i in
                            range(0, 3)] + [
                               "DELETE FROM remove_range_slice_test WHERE k = 1"],
                'queries': ["SELECT * FROM remove_range_slice_test"],
                'results': [[[0, 0], [2, 2]]],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # indexes_composite_test
            {
                'create_tables': ["""CREATE TABLE indexes_composite_test (
                blog_id int,
                timestamp int,
                author text,
                content text,
                PRIMARY KEY (blog_id, timestamp)
            )""", "CREATE INDEX ON indexes_composite_test(author)"],
                'truncates': ["TRUNCATE indexes_composite_test"],
                'inserts': [
                    "INSERT INTO indexes_composite_test (blog_id, timestamp, author, content) VALUES (%d, %d, '%s', '%s')" % (
                        0, 0, "bob", "1st post"),
                    "INSERT INTO indexes_composite_test (blog_id, timestamp, author, content) VALUES (%d, %d, '%s', '%s')" % (
                        0, 1, "tom", "2nd post"),
                    "INSERT INTO indexes_composite_test (blog_id, timestamp, author, content) VALUES (%d, %d, '%s', '%s')" % (
                        0, 2, "bob", "3rd post"),
                    "INSERT INTO indexes_composite_test (blog_id, timestamp, author, content) VALUES (%d, %d, '%s', '%s')" % (
                        0, 3, "tom", "4nd post"),
                    "INSERT INTO indexes_composite_test (blog_id, timestamp, author, content) VALUES (%d, %d, '%s', '%s')" % (
                        1, 0, "bob", "5th post")],
                'queries': ["SELECT blog_id, timestamp FROM indexes_composite_test WHERE author = 'bob'",
                            "INSERT INTO indexes_composite_test (blog_id, timestamp, author, content) VALUES (%d, %d, '%s', '%s')" % (
                                1, 1, "tom", "6th post"),
                            "INSERT INTO indexes_composite_test (blog_id, timestamp, author, content) VALUES (%d, %d, '%s', '%s')" % (
                                1, 2, "tom", "7th post"),
                            "INSERT INTO indexes_composite_test (blog_id, timestamp, author, content) VALUES (%d, %d, '%s', '%s')" % (
                                1, 3, "bob", "8th post"),
                            "SELECT blog_id, timestamp FROM indexes_composite_test WHERE author = 'bob'",
                            "DELETE FROM indexes_composite_test WHERE blog_id = 0 AND timestamp = 2",
                            "SELECT blog_id, timestamp FROM indexes_composite_test WHERE author = 'bob'"
                            ],
                'results': [[[1, 0], [0, 0], [0, 2]],
                            [],
                            [],
                            [],
                            [],
                            [[1, 0], [1, 3], [0, 0], [0, 2]],
                            [],
                            [[1, 0], [1, 3], [0, 0]]],
                'min_version': '',
                'max_version': '',
                'skip': 'Index support is not enabled'},
            # refuse_in_with_indexes_test: Test for the validation bug of CASSANDRA-4709
            {
                'create_tables': [
                    """create table refuse_in_with_indexes_test (pk varchar primary key, col1 varchar, col2 varchar);""",
                    "create index_refuse_in_with_indexes_test1 on t1(col1);",
                    "create index refuse_in_with_indexes_test2 on t1(col2);"],
                'truncates': ["TRUNCATE refuse_in_with_indexes_test"],
                'inserts': [
                    "insert into refuse_in_with_indexes_test (pk, col1, col2) values ('pk1','foo1','bar1');",
                    "insert into refuse_in_with_indexes_test (pk, col1, col2) values ('pk1a','foo1','bar1');",
                    "insert into refuse_in_with_indexes_test (pk, col1, col2) values ('pk1b','foo1','bar1');",
                    "insert into refuse_in_with_indexes_test (pk, col1, col2) values ('pk1c','foo1','bar1');",
                    "insert into refuse_in_with_indexes_test (pk, col1, col2) values ('pk2','foo2','bar2');",
                    "insert into refuse_in_with_indexes_test (pk, col1, col2) values ('pk3','foo3','bar3');"
                ],
                'queries': [],
                'results': [],
                'invalid_queries': ["select * from t1 where col2 in ('bar1', 'bar2');"],
                'min_version': '',
                'max_version': '',
                'skip': 'Index support is not enabled'},
            # reversed_compact_test: Test for CASSANDRA-4716 bug and more generally for good behavior of ordering
            {
                'create_tables': [
                    """ CREATE TABLE reversed_compact_test1 (
                k text,
                c int,
                v int,
                PRIMARY KEY (k, c)
            ) WITH COMPACT STORAGE
              AND CLUSTERING ORDER BY (c DESC);""", """
            CREATE TABLE reversed_compact_test2 (
                k text,
                c int,
                v int,
                PRIMARY KEY (k, c)
            ) WITH COMPACT STORAGE;
        """],
                'truncates': ["TRUNCATE reversed_compact_test1", "TRUNCATE reversed_compact_test2"],
                'inserts': [
                    "INSERT INTO %s(k, c, v) VALUES ('foo', %s, %s)" % (k, i, i) for i in range(0, 10) for k in
                    ['reversed_compact_test1', 'reversed_compact_test2']
                    ],
                'queries': ["SELECT c FROM reversed_compact_test1 WHERE c > 2 AND c < 6 AND k = 'foo'",
                            "SELECT c FROM reversed_compact_test1 WHERE c >= 2 AND c <= 6 AND k = 'foo'",
                            "SELECT c FROM reversed_compact_test1 WHERE c > 2 AND c < 6 AND k = 'foo' ORDER BY c ASC",
                            "SELECT c FROM reversed_compact_test1 WHERE c >= 2 AND c <= 6 AND k = 'foo' ORDER BY c ASC",
                            "SELECT c FROM reversed_compact_test1 WHERE c > 2 AND c < 6 AND k = 'foo' ORDER BY c DESC",
                            "SELECT c FROM reversed_compact_test1 WHERE c >= 2 AND c <= 6 AND k = 'foo' ORDER BY c DESC",
                            "SELECT c FROM reversed_compact_test2 WHERE c > 2 AND c < 6 AND k = 'foo'",
                            "SELECT c FROM reversed_compact_test2 WHERE c >= 2 AND c <= 6 AND k = 'foo'",
                            "SELECT c FROM reversed_compact_test2 WHERE c > 2 AND c < 6 AND k = 'foo' ORDER BY c ASC",
                            "SELECT c FROM reversed_compact_test2 WHERE c >= 2 AND c <= 6 AND k = 'foo' ORDER BY c ASC",
                            "SELECT c FROM reversed_compact_test2 WHERE c > 2 AND c < 6 AND k = 'foo' ORDER BY c DESC",
                            "SELECT c FROM reversed_compact_test1 WHERE c >= 2 AND c <= 6 AND k = 'foo' ORDER BY c DESC"],
                'results': [[[5], [4], [3]],
                            [[6], [5], [4], [3], [2]],
                            [[3], [4], [5]],
                            [[2], [3], [4], [5], [6]],
                            [[5], [4], [3]],
                            [[6], [5], [4], [3], [2]],
                            [[3], [4], [5]],
                            [[2], [3], [4], [5], [6]],
                            [[3], [4], [5]],
                            [[2], [3], [4], [5], [6]],
                            [[5], [4], [3]],
                            [[6], [5], [4], [3], [2]]
                            ],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # reversed_compact_multikey_test: Test for the bug from CASSANDRA-4760 and CASSANDRA-4759
            {
                'create_tables': [
                    """CREATE TABLE reversed_compact_multikey_test (
                key text,
                c1 int,
                c2 int,
                value text,
                PRIMARY KEY(key, c1, c2)
                ) WITH COMPACT STORAGE
                  AND CLUSTERING ORDER BY(c1 DESC, c2 DESC);
        """],
                'truncates': ["TRUNCATE reversed_compact_multikey_test"],
                'inserts': [
                    "INSERT INTO reversed_compact_multikey_test(key, c1, c2, value) VALUES ('foo', %i, %i, 'bar');" % (
                        i, j) for i in range(0, 3)
                    for j in range(0, 3)
                    ],
                'queries': ["SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 = 1",
                            "SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 = 1 ORDER BY c1 ASC, c2 ASC",
                            "SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 = 1 ORDER BY c1 DESC, c2 DESC",
                            "SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 > 1",
                            "SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 > 1 ORDER BY c1 ASC, c2 ASC",
                            "SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 > 1 ORDER BY c1 DESC, c2 DESC",
                            "SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 >= 1",
                            "SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 >= 1 ORDER BY c1 ASC, c2 ASC",
                            "SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 >= 1 ORDER BY c1 ASC",
                            "SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 >= 1 ORDER BY c1 DESC, c2 DESC",
                            "SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 < 1",
                            "SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 < 1 ORDER BY c1 ASC, c2 ASC",
                            "SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 < 1 ORDER BY c1 DESC, c2 DESC",
                            "SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 <= 1",
                            "SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 <= 1 ORDER BY c1 ASC, c2 ASC",
                            "SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 <= 1 ORDER BY c1 ASC",
                            "SELECT c1, c2 FROM reversed_compact_multikey_test WHERE key='foo' AND c1 <= 1 ORDER BY c1 DESC, c2 DESC"],
                'results': [[[1, 2], [1, 1], [1, 0]],
                            [[1, 0], [1, 1], [1, 2]],
                            [[1, 2], [1, 1], [1, 0]],
                            [[2, 2], [2, 1], [2, 0]],
                            [[2, 0], [2, 1], [2, 2]],
                            [[2, 2], [2, 1], [2, 0]],
                            [[2, 2], [2, 1], [2, 0], [1, 2], [1, 1], [1, 0]],
                            [[1, 0], [1, 1], [1, 2], [2, 0], [2, 1], [2, 2]],
                            [[1, 0], [1, 1], [1, 2], [2, 0], [2, 1], [2, 2]],
                            [[2, 2], [2, 1], [2, 0], [1, 2], [1, 1], [1, 0]],
                            [[0, 2], [0, 1], [0, 0]],
                            [[0, 0], [0, 1], [0, 2]],
                            [[0, 2], [0, 1], [0, 0]],
                            [[1, 2], [1, 1], [1, 0], [0, 2], [0, 1], [0, 0]],
                            [[0, 0], [0, 1], [0, 2], [1, 0], [1, 1], [1, 2]],
                            [[0, 0], [0, 1], [0, 2], [1, 0], [1, 1], [1, 2]],
                            [[1, 2], [1, 1], [1, 0], [0, 2], [0, 1], [0, 0]]],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # collection_and_regular_test
            {
                'create_tables': [
                    """CREATE TABLE collection_and_regular_test (
            k int PRIMARY KEY,
            l list<int>,
            c int
          )"""],
                'truncates': ["TRUNCATE collection_and_regular_test"],
                'inserts': [
                    "INSERT INTO collection_and_regular_test(k, l, c) VALUES(3, [0, 1, 2], 4)",
                    "UPDATE collection_and_regular_test SET l[0] = 1, c = 42 WHERE k = 3"],
                'queries': ["SELECT l, c FROM collection_and_regular_test WHERE k = 3"],
                'results': [[[[1, 1, 2], 42]]],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # batch_and_list_test
            {
                'create_tables': ["""
          CREATE TABLE batch_and_list_test (
            k int PRIMARY KEY,
            l list<int>
          )
        """],
                'truncates': ["TRUNCATE batch_and_list_test"],
                'inserts': ["""
              BEGIN BATCH
                UPDATE batch_and_list_test SET l = l + [ 1 ] WHERE k = 0;
                UPDATE batch_and_list_test SET l = l + [ 2 ] WHERE k = 0;
                UPDATE batch_and_list_test SET l = l + [ 3 ] WHERE k = 0;
              APPLY BATCH
            """],
                'queries': ["SELECT l FROM batch_and_list_test WHERE k = 0",
                            """          BEGIN BATCH
                                            UPDATE batch_and_list_test SET l = [ 1 ] + l WHERE k = 1;
                                            UPDATE batch_and_list_test SET l = [ 2 ] + l WHERE k = 1;
                                            UPDATE batch_and_list_test SET l = [ 3 ] + l WHERE k = 1;
                                          APPLY BATCH
                                        """,
                            "SELECT l FROM batch_and_list_test WHERE k = 1"
                            ],
                'results': [[[[1, 2, 3]]],
                            [],
                            [[[3, 2, 1]]]],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # boolean_test
            {
                'create_tables': [
                    """
          CREATE TABLE boolean_test (
            k boolean PRIMARY KEY,
            b boolean
          )
        """],
                'truncates': ["TRUNCATE boolean_test"],
                'inserts': [
                    "INSERT INTO boolean_test (k, b) VALUES (true, false)"],
                'queries': ["SELECT * FROM boolean_test WHERE k = true"],
                'results': [[[True, False]]],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # multiordering_test
            {
                'create_tables': [
                    """CREATE TABLE multiordering_test (
                k text,
                c1 int,
                c2 int,
                PRIMARY KEY (k, c1, c2)
            ) WITH CLUSTERING ORDER BY (c1 ASC, c2 DESC);"""],
                'truncates': ["TRUNCATE multiordering_test"],
                'inserts': ["INSERT INTO multiordering_test(k, c1, c2) VALUES ('foo', %i, %i)" % (i, j) for i in
                            range(0, 2) for j in
                            range(0, 2)],
                'queries': ["SELECT c1, c2 FROM multiordering_test WHERE k = 'foo'",
                            "SELECT c1, c2 FROM multiordering_test WHERE k = 'foo' ORDER BY c1 ASC, c2 DESC",
                            "SELECT c1, c2 FROM multiordering_test WHERE k = 'foo' ORDER BY c1 DESC, c2 ASC"
                            ],
                'results': [[[0, 1], [0, 0], [1, 1], [1, 0]],
                            [[0, 1], [0, 0], [1, 1], [1, 0]],
                            [[1, 0], [1, 1], [0, 0], [0, 1]]
                            ],
                'invalid_queries': ["SELECT c1, c2 FROM multiordering_test WHERE k = 'foo' ORDER BY c2 DESC",
                                    "SELECT c1, c2 FROM multiordering_test WHERE k = 'foo' ORDER BY c2 ASC",
                                    "SELECT c1, c2 FROM multiordering_test WHERE k = 'foo' ORDER BY c1 ASC, c2 ASC"],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # returned_null_test
            # Test for returned null.
            # StorageProxy short read protection hadn't been updated after the changes made by CASSANDRA-3647,
            # namely the fact that SliceQueryFilter groups columns by prefix before counting them. CASSANDRA-4882
            {
                'create_tables': [
                    """CREATE TABLE returned_null_test (
                k int,
                c1 int,
                c2 int,
                v int,
                PRIMARY KEY (k, c1, c2)
            ) WITH CLUSTERING ORDER BY (c1 ASC, c2 DESC);"""],
                'truncates': ["TRUNCATE returned_null_test"],
                'inserts': ["INSERT INTO returned_null_test (k, c1, c2, v) VALUES (0, 0, 0, 0);",
                            "INSERT INTO returned_null_test (k, c1, c2, v) VALUES (0, 1, 1, 1);",
                            "INSERT INTO returned_null_test (k, c1, c2, v) VALUES (0, 0, 2, 2);",
                            "INSERT INTO returned_null_test (k, c1, c2, v) VALUES (0, 1, 3, 3);"
                            ],
                'queries': ["SELECT * FROM returned_null_test WHERE k = 0 LIMIT 1;"],
                'results': [[[0, 0, 2, 2]]],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # multi_list_set_test
            {
                'create_tables': [
                    """ CREATE TABLE multi_list_set_test (
                k int PRIMARY KEY,
                l1 list<int>,
                l2 list<int>
            )"""],
                'truncates': ["TRUNCATE multi_list_set_test"],
                'inserts': ["INSERT INTO multi_list_set_test (k, l1, l2) VALUES (0, [1, 2, 3], [4, 5, 6])",
                            "UPDATE multi_list_set_test SET l2[1] = 42, l1[1] = 24  WHERE k = 0"],
                'queries': ["SELECT l1, l2 FROM multi_list_set_test WHERE k = 0"],
                'results': [[[[1, 24, 3], [4, 42, 6]]]],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # composite_index_collections_test
            {
                'create_tables': [
                    """
            CREATE TABLE composite_index_collections_test (
                blog_id int,
                time1 int,
                time2 int,
                author text,
                content set<text>,
                PRIMARY KEY (blog_id, time1, time2)
            )""", "CREATE INDEX ON composite_index_collections_test(author)"],
                'truncates': ["TRUNCATE composite_index_collections_test"],
                'inserts': [
                    "INSERT INTO composite_index_collections_test (blog_id, time1, time2, author, content) VALUES (%d, %d, %d, '%s', %s)" % (
                        1, 0, 0, 'foo', "{ 'bar1', 'bar2' }"),
                    "INSERT INTO composite_index_collections_test (blog_id, time1, time2, author, content) VALUES (%d, %d, %d, '%s', %s)" % (
                        1, 0, 1, 'foo', "{ 'bar2', 'bar3' }"),
                    "INSERT INTO composite_index_collections_test (blog_id, time1, time2, author, content) VALUES (%d, %d, %d, '%s', %s)" % (
                        2, 1, 0, 'foo', "{ 'baz' }"),
                    "INSERT INTO composite_index_collections_test (blog_id, time1, time2, author, content) VALUES (%d, %d, %d, '%s', %s)" % (
                        3, 0, 1, 'gux', "{ 'qux' }")
                ],
                'queries': ["SELECT composite_index_collections_test, content FROM blogs WHERE author='foo'"],
                'results': [[[[1, set(['bar1', 'bar2'])], [1, set(['bar2', 'bar3'])], [2, set(['baz'])]]]],
                'min_version': '',
                'max_version': '',
                'skip': 'Index support is not enabled'},
            # truncate_clean_cache_test
            {
                'create_tables': [
                    """CREATE TABLE truncate_clean_cache_test (
                    k int PRIMARY KEY,
                    v1 int,
                    v2 int,
                ) WITH caching = {'keys': 'NONE', 'rows_per_partition': 'ALL'};
            """],
                'truncates': ["TRUNCATE truncate_clean_cache_test"],
                'inserts': ["INSERT INTO truncate_clean_cache_test(k, v1, v2) VALUES (%d, %d, %d)" % (i, i, i * 2) for i
                            in range(0, 3)
                            ],
                'queries': ["SELECT v1, v2 FROM truncate_clean_cache_test WHERE k IN (0, 1, 2)",
                            "TRUNCATE truncate_clean_cache_test",
                            "SELECT v1, v2 FROM truncate_clean_cache_test WHERE k IN (0, 1, 2)"],
                'results': [[[0, 0], [1, 2], [2, 4]],
                            [],
                            []],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # range_with_deletes_test
            {
                'create_tables': [
                    """CREATE TABLE range_with_deletes_test (
                k int PRIMARY KEY,
                v int,
            )
            """],
                'truncates': ["TRUNCATE range_with_deletes_test"],
                'inserts': ["INSERT INTO range_with_deletes_test(k, v) VALUES ({}, {})".format(i, i) for i in
                            range(0, 30)] + [
                               "DELETE FROM range_with_deletes_test WHERE k = {}".format(i) for i in
                               random.sample(xrange(30), 5)],
                'queries': ["#LENGTH SELECT * FROM range_with_deletes_test LIMIT {}".format(15)],
                'results': [15],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # collection_function_test
            {
                'create_tables': [
                    """CREATE TABLE collection_function_test (
                k int PRIMARY KEY,
                l set<int>)
            """],
                'truncates': ["TRUNCATE collection_function_test"],
                'inserts': [],
                'queries': [],
                'results': [],
                'invalid_queries': ["SELECT ttl(l) FROM collection_function_test WHERE k = 0",
                                    "SELECT writetime(l) FROM collection_function_test WHERE k = 0"],
                'min_version': '',
                'max_version': '',
                'skip': ''},
            # composite_partition_key_validation_test: Test for bug from CASSANDRA-5122
            {
                'create_tables': [
                    "CREATE TABLE composite_partition_key_validation_test (a int, b text, c uuid, PRIMARY KEY ((a, b)));"],
                'truncates': ["TRUNCATE composite_partition_key_validation_test"],
                'inserts': [
                    "INSERT INTO composite_partition_key_validation_test (a, b, c) VALUES (1, 'aze', 4d481800-4c5f-11e1-82e0-3f484de45426)",
                    "INSERT INTO composite_partition_key_validation_test (a, b, c) VALUES (1, 'ert', 693f5800-8acb-11e3-82e0-3f484de45426)",
                    "INSERT INTO composite_partition_key_validation_test (a, b, c) VALUES (1, 'opl', d4815800-2d8d-11e0-82e0-3f484de45426)"],
                'queries': ["#LENGTH SELECT * FROM composite_partition_key_validation_test WHERE a=1"],
                'results': [3],
                'invalid_queries': ["SELECT * FROM composite_partition_key_validation_test WHERE a=1"],
                'min_version': '',
                'max_version': '',
                'skip': 'bug? Partition key parts: b must be restricted as other parts are'},

        ]

        node = self.db_cluster.nodes[0]
        session = self.cql_connection_patient(node)
        default_fetch_size = session.default_fetch_size
        session.execute("""
            CREATE KEYSPACE IF NOT EXISTS keyspace1
            WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '2'} AND durable_writes = true;
        """)
        session.execute("USE keyspace1;")
        for a in all_verification_items:
            if not a['skip']:
                for create_table in a['create_tables']:
                    session.execute(create_table)
                for truncate in a['truncates']:
                    session.execute(truncate)

        for a in all_verification_items:
            session.execute("USE keyspace1;")
            if not a['skip']:
                if 'disable_paging' in a and a['disable_paging']:
                    session.default_fetch_size = 0
                else:
                    session.default_fetch_size = default_fetch_size
                for insert in a['inserts']:
                    session.execute(insert)
                for i in range(len(a['queries'])):
                    try:
                        if a['queries'][i].startswith("#SORTED"):
                            res = session.execute(a['queries'][i].replace('#SORTED', ''))
                            self.assertEqual(sorted([list(row) for row in res]), a['results'][i])
                        elif a['queries'][i].startswith("#REMOTER_RUN"):
                            for node in self.db_cluster.nodes:
                                node.remoter.run(a['queries'][i].replace('#REMOTER_RUN', ''))
                        elif a['queries'][i].startswith("#LENGTH"):
                            res = session.execute(a['queries'][i].replace('#LENGTH', ''))
                            self.assertEqual(len([list(row) for row in res]), a['results'][i])
                        else:
                            res = session.execute(a['queries'][i])
                            self.assertEqual([list(row) for row in res], a['results'][i])
                    except Exception as e:
                        print a['queries'][i], e
                        raise e
                if 'invalid_queries' in a:
                    for i in range(len(a['invalid_queries'])):
                        try:
                            session.execute(a['invalid_queries'][i])
                            self.fail("query '%s' is not valid" % a['invalid_queries'][i])
                        except InvalidRequest as e:
                            print "Found error '%s' as expected" % e

        duration = 15 * len(self.db_cluster.nodes)

        stress_cmd = self._cs_add_node_flag(self.params.get('stress_cmd'))
        stress_queue = self.run_stress_thread(stress_cmd=stress_cmd,
                                              duration=duration)

        nodes_num = len(self.db_cluster.nodes)
        # prepare an array containing the indexes
        indexes = [x for x in range(nodes_num)]
        # shuffle it so we will upgrade the nodes in a
        # random order
        random.shuffle(indexes)

        # upgrade all the nodes in random order
        for i in indexes:
            self.db_cluster.node_to_upgrade = self.db_cluster.nodes[i]
            self.db_cluster.add_nemesis(nemesis=UpgradeNemesisOneNode,
                                        loaders=self.loaders,
                                        monitoring_set=self.monitors)
            self.db_cluster.start_nemesis(interval=15)
            # 10 minutes to upgrade 1 node
            self.db_cluster.stop_nemesis(timeout=15 * 60)
            session = self.cql_connection_patient(self.db_cluster.node_to_upgrade)
            session.execute("USE keyspace1;")

            for a in all_verification_items:
                if not a['skip']:
                    for truncate in a['truncates']:
                        session.execute(truncate)
            for a in all_verification_items:
                session.execute("USE keyspace1;")
                if not a['skip']:
                    if 'disable_paging' in a and a['disable_paging']:
                        session.default_fetch_size = 0
                    else:
                        session.default_fetch_size = default_fetch_size
                    for insert in a['inserts']:
                        session.execute(insert)
                    for i in range(len(a['queries'])):
                        try:
                            if a['queries'][i].startswith("#SORTED"):
                                res = session.execute(a['queries'][i].replace('#SORTED', ''))
                                self.assertEqual(sorted([list(row) for row in res]), a['results'][i])
                            elif a['queries'][i].startswith("#REMOTER_RUN"):
                                for node in self.db_cluster.nodes:
                                    node.remoter.run(a['queries'][i].replace('#REMOTER_RUN', ''))
                            elif a['queries'][i].startswith("#LENGTH"):
                                res = session.execute(a['queries'][i].replace('#LENGTH', ''))
                                self.assertEqual(len([list(row) for row in res]), a['results'][i])
                            else:
                                res = session.execute(a['queries'][i])
                                self.assertEqual([list(row) for row in res], a['results'][i])
                        except Exception as e:
                            print a['queries'][i], e
                            raise e
                    if 'invalid_queries' in a:
                        for i in range(len(a['invalid_queries'])):
                            try:
                                session.execute(a['invalid_queries'][i])
                                self.fail("query '%s' is not valid" % a['invalid_queries'])
                            except InvalidRequest as e:
                                print "Found error '%s' as expected" % e

        self.verify_stress_thread(stress_queue)

    # def test_20_minutes(self):
    #     """
    #     Run cassandra-stress on a cluster for 20 minutes, together with node upgrades.
    #     If upgrade_node_packages defined we specify duration 10 * len(nodes) minutes.
    #     """
    #     self.db_cluster.add_nemesis(nemesis=UpgradeNemesis,
    #                                 loaders=self.loaders,
    #                                 monitoring_set=self.monitors)
    #     self.db_cluster.start_nemesis(interval=10)
    #     duration = 20
    #     if self.params.get('upgrade_node_packages'):
    #         duration = 30 * len(self.db_cluster.nodes)
    #     self.run_stress(stress_cmd=self.params.get('stress_cmd'), duration=duration)
    #
    # def test_20_minutes_rollback(self):
    #     """
    #     Run cassandra-stress on a cluster for 20 minutes, together with node upgrades.
    #     """
    #     self.db_cluster.add_nemesis(nemesis=UpgradeNemesis,
    #                                 loaders=self.loaders,
    #                                 monitoring_set=self.monitors)
    #     self.db_cluster.start_nemesis(interval=10)
    #     self.db_cluster.stop_nemesis(timeout=None)
    #
    #     self.db_cluster.clean_nemesis()
    #
    #     self.db_cluster.add_nemesis(nemesis=RollbackNemesis,
    #                                 loaders=self.loaders,
    #                                 monitoring_set=self.monitors)
    #     self.db_cluster.start_nemesis(interval=10)
    #     self.run_stress(stress_cmd=self.params.get('stress_cmd'),
    #                     duration=self.params.get('cassandra_stress_duration', 20))


if __name__ == '__main__':
    main()
