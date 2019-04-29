import datetime

from tests.models import (
    ArchiveTable,
    UserTable,
)
from tests.utils import (
    SQLiteTestBase,
)
from datetime import datetime

from versionalchemy.exceptions import LogTableCreationError, RestoreError, LogIdentifyError, HistoryItemNotFound


class TestRestore(SQLiteTestBase):

    def test_restore_row_with_new_nullable_column_by_va_id(self):
        p = UserTable(**self.p1)
        self._add_and_test_version(p, 0)
        p = self.session.query(UserTable).get(p.id)
        first_va_id = p.va_id
        p.col1 = 'test'
        p.col2 = 10
        self.session.commit()
        p = self.session.query(UserTable).get(p.id)
        self.assertEqual(p.col1, 'test')
        self.assertEqual(p.col2, 10)
        self.assertEqual(p.va_id, first_va_id + 1, 'va_id should be increased')
        self.addTestNullableColumn()
        p = self.session.query(UserTable).get(p.id)
        p.va_restore(self.session, va_id=first_va_id)
        p = self.session.query(UserTable).get(p.id)
        self.assertEqual(p.col1, self.p1['col1'])
        self.assertEqual(p.col2, self.p1['col2'])
        self.assertEqual(p.test_column1, None)
        self.assertEqual(p.va_id, first_va_id + 2)

    def test_restore_row_with_new_nullable_column_by_va_version(self):
        p = UserTable(**self.p1)
        self._add_and_test_version(p, 0)
        p = self.session.query(UserTable).get(p.id)
        log = self.session.query(ArchiveTable).get(p.va_id)
        first_va_version = log.va_version
        p.col1 = 'test'
        p.col2 = 10
        self.session.commit()
        p = self.session.query(UserTable).get(p.id)
        self.assertEqual(p.col1, 'test')
        self.assertEqual(p.col2, 10)
        self.addTestNullableColumn()
        p = self.session.query(UserTable).get(p.id)
        p.va_restore(self.session, first_va_version)
        p = self.session.query(UserTable).get(p.id)
        self.assertEqual(p.col1, self.p1['col1'])
        self.assertEqual(p.col2, self.p1['col2'])
        self.assertEqual(p.test_column1, None)

    def test_restore_row_with_non_default_column(self):
        p = UserTable(**self.p1)
        self._add_and_test_version(p, 0)
        p = self.session.query(UserTable).get(p.id)
        first_version = p.va_id
        p.col1 = 'test'
        self.session.commit()
        p = self.session.query(UserTable).get(p.id)
        self.assertEqual(p.col1, 'test')
        self.assertEqual(p.va_id, first_version + 1, 'Version should be increased')
        self.addTestNoDefaultNoNullColumn()
        p = self.session.query(UserTable).get(p.id)

        with self.assertRaises(RestoreError):
            p.va_restore(self.session, first_version)


class TestList(SQLiteTestBase):
    def test_va_list(self):
        p = UserTable(**self.p1)
        self._add_and_test_version(p, 0)
        p = self.session.query(UserTable).get(p.id)
        first_version = p.va_id
        p.col1 = 'test'
        self.session.commit()
        res = p.va_list(self.session)

        expected_response = [
            {'va_id': first_version, 'user_id': None, 'va_version': 0},
            {'va_id': first_version + 1, 'user_id': None, 'va_version': 1},
        ]
        self.assertEqual(res, expected_response)
        res = UserTable.va_list_by_pk(self.session, product_id=p.product_id)
        self.assertEqual(res, expected_response)

    def test_va_list_by_pk_fail(self):
        p = UserTable(**self.p1)
        self._add_and_test_version(p, 0)
        p = self.session.query(UserTable).get(p.id)
        p.col1 = 'test'
        self.session.commit()
        with self.assertRaises(LogIdentifyError):
            UserTable.va_list_by_pk(self.session)


class TestDiff(SQLiteTestBase):
    def test_va_diff_basic_va_id(self):
        p = UserTable(**self.p1)
        p._updated_by = '1'
        self._add_and_test_version(p, 0)
        p = self.session.query(UserTable).get(p.id)
        p.col1 = 'test'
        p._updated_by = '2'
        self.session.commit()

        res = UserTable.va_diff(self.session, va_id=p.va_id)
        self.assertEqual(res, {
            'va_prev_version': 0,
            'va_version': 1,
            'prev_user_id': '1',
            'user_id': '2',
            'change': {
                'col1': {
                    'this': 'test',
                    'prev': 'foobar'
                }
            }
        })

    def test_va_diff_basic_va_version(self):
        p = UserTable(**self.p1)
        p._updated_by = '1'
        self._add_and_test_version(p, 0)
        p = self.session.query(UserTable).get(p.id)

        p.col1 = 'test'
        p._updated_by = '2'
        self.session.commit()
        log = self.session.query(ArchiveTable).get(p.va_id)

        res = UserTable.va_diff(self.session, log.va_version)
        self.assertEqual(res, {
            'va_prev_version': 0,
            'va_version': 1,
            'prev_user_id': '1',
            'user_id': '2',
            'change': {
                'col1': {
                    'this': 'test',
                    'prev': 'foobar'
                }
            }
        })

    def test_va_diff_new_column_and_del_column(self):
        p = UserTable(**self.p1)
        p._updated_by = '1'
        self._add_and_test_version(p, 0)

        print("111", p.__table__.c)
        self.addTestNullableColumn()
        p = self.session.query(UserTable).get(p.id)
        print("222", p.__table__.c)
        p.col1 = 'test'
        p.test_column1 = 'tc1'
        p._updated_by = '2'
        self.session.commit()

        res = UserTable.va_diff(self.session, va_id=p.va_id)
        print("RESULT", res)
        self.assertEqual(res, {
            'va_prev_version': 0,
            'va_version': 1,
            'prev_user_id': '1',
            'user_id': '2',
            'change': {
                'col1': {
                    'this': 'test',
                    'prev': 'foobar'
                },
                'test_column1': {
                    'prev': None,
                    'this': 'tc1',
                }
            }
        })
        print("PASSED")
        self.deleteTestNullableColumn()
        print("DELETED")
        p = self.session.query(UserTable).get(p.id)
        print("P COLS", p.__table__.c)
        p.col1 = 'test2'
        p._updated_by = '1'
        self.session.commit()
        res = UserTable.va_diff(self.session, va_id=p.va_id)
        print("ANOTHER RES", res)
        self.assertEqual(res, {
            'va_prev_version': 1,
            'va_version': 2,
            'prev_user_id': '2',
            'user_id': '1',
            'change': {
                'col1': {
                    'this': 'test2',
                    'prev': 'test'
                },
                'test_column1': {
                    'prev': 'tc1',
                    'this': None,
                }
            }
        })

    def test_va_diff_first_version(self):
        p = UserTable(**self.p1)
        p._updated_by = '1'
        self._add_and_test_version(p, 0)
        p = self.session.query(UserTable).get(p.id)

        res = UserTable.va_diff(self.session, va_id=p.va_id)
        self.assertEqual(res, {
            'va_prev_version': None,
            'va_version': 0,
            'prev_user_id': None,
            'user_id': '1',
            'change': {
                'col1': {
                    'this': 'foobar',
                    'prev': None
                },
                'col2': {'this': 10, 'prev': None},
                'col3': {'prev': None, 'this': 1},
                'product_id': {'prev': None, 'this': 10},
                'id': {'this': 1, 'prev': None}
            }
        })

    def test_va_diff_all(self):
        p = UserTable(**self.p1)
        p._updated_by = '1'
        self._add_and_test_version(p, 0)
        p = self.session.query(UserTable).get(p.id)
        p.col1 = 'test'
        p._updated_by = '2'
        self.session.commit()
        res = UserTable.va_diff_all_by_pk(self.session, product_id=p.product_id)
        expected_result = [{
            'va_prev_version': None,
            'va_version': 0,
            'prev_user_id': None,
            'user_id': '1',
            'change': {
                'col1': {
                    'this': 'foobar',
                    'prev': None
                },
                'col2': {'this': 10, 'prev': None},
                'col3': {'prev': None, 'this': 1},
                'product_id': {'prev': None, 'this': 10},
                'id': {'this': 1, 'prev': None}
            }
        }, {
            'va_prev_version': 0,
            'va_version': 1,
            'prev_user_id': '1',
            'user_id': '2',
            'change': {
                'col1': {
                    'this': 'test',
                    'prev': 'foobar'
                }
            }
        }]
        self.assertEqual(res, expected_result)
        res = p.va_diff_all(self.session)
        self.assertEqual(res, expected_result)

    def test_va_diff_2parallel_history(self):
        p1 = UserTable(**self.p1)
        p2 = UserTable(**self.p2)
        p1._updated_by = '1'
        p2._updated_by = '1'

        self._add_and_test_version(p1, 0)
        self._add_and_test_version(p2, 0)
        p1 = self.session.query(UserTable).get(p1.id)
        p2 = self.session.query(UserTable).get(p2.id)
        p1.col1 = 'test1'
        p2.col1 = 'test2'
        p1._updated_by = '2'
        p2._updated_by = '2'
        self.session.commit()
        res_p1 = UserTable.va_diff(self.session, va_id=p1.va_id)
        self.assertEqual(res_p1, {
            'va_prev_version': 0,
            'va_version': 1,
            'prev_user_id': '1',
            'user_id': '2',
            'change': {
                'col1': {
                    'this': 'test1',
                    'prev': 'foobar'
                }
            }
        })
        res_p2 = UserTable.va_diff(self.session, va_id=p2.va_id)
        self.assertEqual(res_p2, {
            'va_prev_version': 0,
            'va_version': 1,
            'prev_user_id': '1',
            'user_id': '2',
            'change': {
                'col1': {
                    'this': 'test2',
                    'prev': 'baz'
                }
            }
        })


class TestGet(SQLiteTestBase):
    def test_va_get_by_va_id(self):
        p = UserTable(**self.p1)
        self._add_and_test_version(p, 0)
        p = self.session.query(UserTable).get(p.id)
        res = p.va_get(self.session, va_id=p.va_id)
        self.assertEqual(res,
            {
                'other_name': None,
                'id': p.id,
                'product_id': p.product_id,
                'col1': p.col1,
                'col2': p.col2,
                'col3': p.col3,
                'va_id': p.va_id
            }
        )

    def test_va_get_by_version(self):
        p = UserTable(**self.p1)
        self._add_and_test_version(p, 0)
        p = self.session.query(UserTable).get(p.id)
        log = self.session.query(ArchiveTable).get(p.va_id)

        res = p.va_get(self.session, log.va_version)
        self.assertEqual(res,
            {
                'other_name': None,
                'id': p.id,
                'product_id': p.product_id,
                'col1': p.col1,
                'col2': p.col2,
                'col3': p.col3,
                'va_id': p.va_id
            }
        )

    def test_va_get_fails(self):
        p = UserTable(**self.p1)
        self._add_and_test_version(p, 0)
        p = self.session.query(UserTable).get(p.id)
        with self.assertRaises(HistoryItemNotFound):
            p.va_get(self.session, p.va_id + 372)

    def test_va_get_all(self):
        p = UserTable(**self.p1)
        p._updated_by = '1'
        self._add_and_test_version(p, 0)
        p = self.session.query(UserTable).get(p.id)
        p.col1 = 'test'
        p._updated_by = '2'
        self.session.commit()
        expected_result = [
            {
                'record': {
                    'col1': 'foobar',
                    'col2': 10,
                    'col3': 1,
                    'id': 1,
                    'other_name': None,
                    'product_id': 10
                },
                'user_id': '1',
                'va_id': 1,
                'va_version': 0
            },
            {
                'record': {
                    'col1': 'test',
                    'col2': 10,
                    'col3': 1,
                    'id': 1,
                    'other_name': None,
                    'product_id': 10
                },
                'user_id': '2',
                'va_id': 2,
                'va_version': 1
            }
        ]
        res = p.va_get_all(self.session)
        self.assertEqual(res, expected_result)
        res = UserTable.va_get_all_by_pk(self.session, product_id=p.product_id)
        self.assertEqual(res, expected_result)


