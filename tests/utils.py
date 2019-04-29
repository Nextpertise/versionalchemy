import unittest
from copy import deepcopy

import sqlalchemy as sa
from sqlalchemy import func, String
from sqlalchemy.orm import sessionmaker

from tests.models import (
    ArchiveTable,
    Base,
    MultiColumnArchiveTable,
    MultiColumnUserTable,
    UserTable,
)
import tests
import versionalchemy as va
from versionalchemy import utils


class VaTestHelpers(object):
    def _add_and_test_version(self, row, version):
        self.session.add(row)
        self.session.commit()
        self.assertEqual(row.version(self.session), version)

    def _result_to_dict(self, res):
        return utils.result_to_dict(res)

    def _verify_archive(
        self,
        expected,
        version,
        log_id=None,
        deleted=False,
        session=None,
        user=None
    ):
        UserTable_ = getattr(self, 'UserTable', UserTable)
        ArchiveTable_ = UserTable_.ArchiveTable
        if session is None:
            session = self.session

        and_clause = sa.and_(ArchiveTable_.va_version == version, *(
            getattr(ArchiveTable_, col_name) == expected[col_name]
            for col_name in UserTable_.va_version_columns
        ))
        res = session.execute(
            sa.select([ArchiveTable_]).
            where(and_clause)
        )
        all_ = self._result_to_dict(res)
        self.assertEquals(len(all_), 1)
        row = all_[0]
        data = row['va_data']
        self.assertEquals(row['va_deleted'], deleted)
        if user is not None:
            self.assertEquals(row['user_id'], user)
        for k in expected:
            self.assertIn(k, data)
            self.assertEquals(data[k], expected[k])
        if log_id is not None:
            self.assertEquals(log_id, row['va_id'])

    def _verify_row(self, expected_dict, version, session=None):
        UserTable_ = getattr(self, 'UserTable', UserTable)
        if session is None:
            session = self.session

        # Query user table and assert there is exactly 1 row
        and_clause = sa.and_(*(
            getattr(UserTable_, col_name) == expected_dict[col_name]
            for col_name in UserTable_.va_version_columns
        ))
        res = session.execute(
            sa.select([UserTable_]).
            where(and_clause)
        )
        all_ = self._result_to_dict(res)
        self.assertEquals(len(all_), 1)
        row_dict = all_[0]

        # Assert the columns match
        for k in expected_dict:
            self.assertEqual(row_dict[k], expected_dict[k])

    def _verify_deleted(self, key, session=None):
        if session is None:
            session = self.session

        UserTable_ = getattr(self, 'UserTable', UserTable)
        ArchiveTable_ = UserTable_.ArchiveTable
        version_col_names = UserTable_.va_version_columns
        self.assertEquals(len(key), len(version_col_names))

        and_clause = sa.and_(*[
            getattr(ArchiveTable_, col_name) == key[col_name]
            for col_name in version_col_names
        ])
        res = session.execute(
            sa.select([func.count(ArchiveTable_.va_id)])
            .where(and_clause)
        )
        self.assertEquals(res.scalar(), 0)

        and_clause = sa.and_(*[
            getattr(UserTable_, col_name) == key[col_name]
            for col_name in version_col_names
        ])
        res = session.execute(
            sa.select([func.count(UserTable_.id)])
            .where(and_clause)
        )
        self.assertEquals(res.scalar(), 0)


class SQLiteTestBase(unittest.TestCase, VaTestHelpers):
    def __init__(self, methodName='runTest'):
        # isolation_level is set so sqlite supports savepoints
        self.engine = sa.create_engine('sqlite://', connect_args={'isolation_level': None})
        self.Session = sessionmaker(bind=self.engine)
        va.init()
        super(SQLiteTestBase, self).__init__(methodName=methodName)

    def setUp(self):
        print('setup')

        if hasattr(UserTable, 'test_column1'):
            try:
                delattr(UserTable, 'test_column1')
            except:
                pass
            sa.inspect(UserTable).mapper._expire_memoizations()
            del sa.inspect(UserTable).mapper.columns['test_column1']
            del sa.inspect(UserTable).mapper._props['test_column1']

        if hasattr(UserTable, 'test_column3'):
            try:
                delattr(UserTable, 'test_column3')
            except:
                pass
            sa.inspect(UserTable).mapper._expire_memoizations()
            del sa.inspect(UserTable).mapper.columns['test_column3']
            del sa.inspect(UserTable).mapper._props['test_column3']

        try:
            delete_cmd = 'drop table {}'
            self.engine.execute(delete_cmd.format(UserTable.__tablename__))
        except Exception as e:
            pass

        Base.metadata.create_all(self.engine)
        UserTable.register(ArchiveTable, self.engine)
        MultiColumnUserTable.register(MultiColumnArchiveTable, self.engine)
        self.p1 = dict(product_id=10, col1='foobar', col2=10, col3=1)
        self.p2 = dict(product_id=11, col1='baz', col2=11, col3=1)
        self.p3 = dict(product_id=2546, col1='test', col2=12, col3=0)

        self.session = self.Session()

    def tearDown(self):
        self.dropAll()
        self.session.close()

    def dropAll(self):
        delete_cmd = 'drop table {}'
        self.engine.execute(delete_cmd.format(UserTable.__tablename__))
        self.engine.execute(delete_cmd.format(ArchiveTable.__tablename__))
        self.engine.execute(delete_cmd.format(MultiColumnUserTable.__tablename__))
        self.engine.execute(delete_cmd.format(MultiColumnArchiveTable.__tablename__))

    def addTestNullableColumn(self):
        setattr(UserTable, 'test_column1', sa.Column(String(50), nullable=True))
        try:
            self.engine.execute('alter table {} add column test_column1 VARCHAR(50) NULL;'.format(
                UserTable.__tablename__))
        except:
            pass

    def deleteTestNullableColumn(self):
        UserTable.__mapper__._dispose_called = True
        delattr(UserTable, 'test_column1')
        sa.inspect(UserTable).mapper._expire_memoizations()
        del sa.inspect(UserTable).mapper.columns['test_column1']
        del sa.inspect(UserTable).mapper._props['test_column1']
        UserTable.__mapper__._dispose_called = False

    def addTestNoDefaultNoNullColumn(self):
        setattr(UserTable, 'test_column3', sa.Column(String(50), nullable=False))
        self.engine.execute('alter table {} add column test_column3 VARCHAR(50) NOT NULL DEFAULT "";'.format(
            UserTable.__tablename__))
