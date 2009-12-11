import itertools
import unittest
import uuid
import couchdb

from couchdbsession import a8n, session


SERVER_URL = 'http://localhost:5984/'


class TempDatabaseMixin(object):
    def setUp(self):
        self.db_name = 'test-couchdbsession-'+str(uuid.uuid4())
        self.server = couchdb.Server(SERVER_URL)
        self.db = self.server.create(self.db_name)
    def tearDown(self):
        del self.server[self.db_name]


class SimpleSessionMixin(object):
    def setUp(self):
        super(SimpleSessionMixin, self).setUp()
        self.session = session.Session(self.db)


class BaseTestCase(SimpleSessionMixin, TempDatabaseMixin, unittest.TestCase):
    pass


class PopulatedDatabaseBaseTestCase(SimpleSessionMixin, TempDatabaseMixin, unittest.TestCase):
    def setUp(self):
        super(PopulatedDatabaseBaseTestCase, self).setUp()
        self.db.update([{'_id': str(i)} for i in range(10)])


class TestEmptyDatabase(BaseTestCase):
    def test_iter(self):
        assert list(self.session._db) == list(self.session)


class TestComposition(PopulatedDatabaseBaseTestCase):

    def test_iter(self):
        """
        Check iteration (doc id generator) works.
        """
        assert list(self.session._db) == list(self.session)

    def test_contains(self):
        doc_id = self.session._db.create({})
        assert '1' in self.session

    def test_len(self):
        assert len(self.session) == 10

    def test_nonzero(self):
        assert bool(self.session)

    def test_get_name(self):
        assert self.session.name == self.db.name

    def test_info(self):
        assert self.session.info() == self.db.info()


class TestView(PopulatedDatabaseBaseTestCase):

    def test_view_len(self):
        view = self.session.view('_all_docs')
        assert len(view) == 10

    def test_view_results(self):
        assert isinstance(self.session.view('_all_docs'), session.SessionViewResults)


class TestViewResults(PopulatedDatabaseBaseTestCase):

    def test_iter(self):
        assert isinstance(iter(self.session.view('_all_docs')).next(), session.SessionRow)

    def test_rows(self):
        assert isinstance(self.session.view('_all_docs').rows[0], session.SessionRow)


class TestCaching(PopulatedDatabaseBaseTestCase):

    def test_get(self):
        doc1 = self.session.get('0')
        doc2 = self.session.get('0')
        assert doc1 is doc2

    def test_getitem(self):
        doc1 = self.session['0']
        doc2 = self.session['0']
        assert doc1 is doc2

    def test_view_iter(self):
        row1 = iter(self.session.view('_all_docs')).next()
        row2 = iter(self.session.view('_all_docs')).next()
        assert row1.doc is row2.doc is None
        row1 = iter(self.session.view('_all_docs', include_docs=True)).next()
        row2 = iter(self.session.view('_all_docs', include_docs=True)).next()
        assert row1.doc is row2.doc is not None
        assert row1.doc is self.session[row1.doc['_id']]

    def test_view_rows(self):
        rows1 = self.session.view('_all_docs', include_docs=True).rows
        rows2 = self.session.view('_all_docs', include_docs=True).rows
        assert rows1[0].doc is rows2[0].doc

    def test_query(self):
        map_fun = "function(doc) {emit(null, null);}"
        row1 = iter(self.session.query(map_fun)).next()
        assert row1.doc is None
        row1 = iter(self.session.query(map_fun, include_docs=True)).next()
        row2 = iter(self.session.query(map_fun, include_docs=True)).next()
        assert row1.doc is row2.doc is self.session[row1.doc['_id']]

    def test_create(self):
        doc_id = self.session.create({})
        assert len(self.session._cache) == 1
        assert doc_id in self.session._cache
        assert self.session.get(doc_id) is self.session.get(doc_id)

    def test_delete(self):
        doc_id = self.db.create({})
        doc = self.session.get(doc_id)
        assert len(self.session._cache) == 1
        assert doc_id in self.session._cache
        self.session.delete(doc)
        assert len(self.session._cache) == 0
        assert doc_id not in self.session._cache


class TestSessionChangeRecorder(BaseTestCase):

    def test_initial(self):
        assert not self.session._changed

    def test_clean_after_read(self):
        doc_id = self.db.create({})
        doc = self.session.get(doc_id)
        assert len(self.session._changed) == 0

    def test_change_multi_existing(self):
        doc_ids = list(r[1] for r in self.db.update([{}, {}]))
        doc1 = self.session.get(doc_ids[0])
        doc2 = self.session.get(doc_ids[1])
        assert not self.session._changed
        doc1['foo'] = ['bar']
        assert len(self.session._changed) == 1
        doc2['foo'] = ['bar']
        assert len(self.session._changed) == 2


class TestUpdates(PopulatedDatabaseBaseTestCase):

    def test_change_one(self):
        doc_id = self.db.create({})
        doc = self.session.get(doc_id)
        doc['foo'] = 'bar'
        self.session.flush()
        assert not self.session._changed
        doc = self.db.get(doc_id)
        assert doc['foo'] == 'bar'

    def test_change_multi(self):
        doc1_id = self.db.create({})
        doc2_id = self.db.create({})
        doc1 = self.session.get(doc1_id)
        doc2 = self.session.get(doc2_id)
        doc1['foo'] = 'bar'
        doc2['bar'] = 'foo'
        self.session.flush()
        assert not self.session._changed
        assert self.db.get(doc1_id)['foo'] == 'bar'
        assert self.db.get(doc2_id)['bar'] == 'foo'

    def test_change_again(self):
        doc_id = self.db.create({})
        doc = self.session.get(doc_id)
        doc['foo'] = 1
        self.session.flush()
        doc['foo'] = 2
        self.session.flush()
        assert self.db.get(doc_id)['foo'] == 2

    def test_setitem(self):
        self.session['1'] = self.session['1']
        assert len(self.session._cache) == 1
        assert len(self.session._changed) == 0


class TestCreation(BaseTestCase):

    def test_create_one(self):
        doc_id = self.session.create({})
        assert doc_id
        # Should have been added to the _created list.
        assert len(self.session._created) == 1
        self.session.flush()
        # Should be added to the database.
        assert self.session._db.get(doc_id)
        doc = self.session.get(doc_id)
        assert doc['_rev']

    def test_create_with_id(self):
        doc_id = self.session.create({'_id': 'foo'})
        assert doc_id == 'foo'
        assert len(self.session._cache) == 1
        assert len(self.session._created) == 1
        assert 'foo' in self.session._created
        assert 'foo' in self.session._cache

    def test_setitem(self):
        self.session['foo'] = {}
        assert len(self.session._cache) == 1
        assert len(self.session._created) == 1
        assert 'foo' in self.session._cache
        assert 'foo' in self.session._created


class TestDelete(BaseTestCase):

    def test_delete_existing(self):
        doc_id = self.session._db.create({})
        doc = self.session.get(doc_id)
        self.session.delete(doc)
        assert len(self.session._deleted) == 1
        assert doc['_id'] in self.session._deleted
        assert self.session.get(doc_id) is None
        self.assertRaises(couchdb.ResourceNotFound, self.session.__getitem__, doc_id)
        self.session.flush()
        assert self.session._db.get(doc_id) is None

    def test_delete_created(self):
        doc_id = self.session.create({})
        doc = self.session.get(doc_id)
        self.session.delete(doc)
        assert not self.session._created
        assert not self.session._deleted
        assert doc_id not in self.session._cache

    def test_delete_changed(self):
        doc_id = self.db.create({})
        doc = self.session.get(doc_id)
        doc['foo'] = 'bar'
        assert len(self.session._changed) == 1
        assert doc_id in self.session._changed
        self.session.delete(doc)
        assert not self.session._changed
        assert len(self.session._deleted) == 1
        assert doc_id in self.session._deleted

    def test_delitem(self):
        doc_id = self.db.create({})
        del self.session[doc_id]
        assert len(self.session._deleted) == 1
        assert doc_id in self.session._deleted
        self.session.flush()
        assert doc_id not in self.db


class TestNested(BaseTestCase):

    def test_nested_dict(self):
        doc_id = self.db.create({'dict': {'foo': 'foo'}})
        doc = self.session.get(doc_id)
        doc['dict']['foo'] = 'oof'
        self.session.flush()
        doc = self.db.get(doc_id)
        assert doc['dict']['foo'] == 'oof'

    def test_nested_list(self):
        doc_id = self.db.create({'list': ['foo']})
        doc = self.session.get(doc_id)
        doc['list'].append('oof')
        self.session.flush()
        doc = self.db.get(doc_id)
        assert doc['list'] == ['foo', 'oof']


class TestCombinations(PopulatedDatabaseBaseTestCase):

    def test_create_using_deleted_doc_id(self):
        doc_id = self.db.create({'foo': 'bar'})
        doc = self.session.get(doc_id)
        self.session.delete(doc)
        self.session.create({'_id': doc_id, 'foo': 'wibble'})
        assert self.session.get(doc_id)['foo'] == 'wibble'
        self.session.flush()
        assert len(self.db) == 11
        assert self.db.get(doc_id)['foo'] == 'wibble'


class TestFlush(TempDatabaseMixin, unittest.TestCase):

    def setUp(self):
        super(TestFlush, self).setUp()
        self.session = session.Session(self.db,
                                       pre_flush_hook=self._flush_hook,
                                       post_flush_hook=self._flush_hook)

    def test_delete(self):
        doc_id = self.db.create({})
        doc = self.session.get(doc_id)
        self.session.delete(doc)
        self.session.flush()
        assert self.db.get(doc_id) is None

    def test_flush_again(self):
        """
        Check multiple flushes during the same session.
        """
        doc_id = self.db.create({})
        doc = self.session.get(doc_id)
        doc['num'] = 1
        self.session.flush()
        assert self.db.get(doc_id)['num'] == 1
        doc['num'] = 2
        self.session.flush()
        assert self.db.get(doc_id)['num'] == 2

    def test_create_change(self):
        """
        Check that a new document can later be changed in the same session.
        """
        doc_id = self.session.create({'num': 1})
        self.session.flush()
        doc = self.session.get(doc_id)
        doc['num'] = 2
        self.session.flush()
        assert self.db.get(doc_id)['num'] == 2

    def _flush_hook(self, session, deletions, additions, changes):
        # Just to consume all the generators to ensure they're correct.
        for i in itertools.chain(deletions, additions, changes):
            pass


class TestFlushHook(TempDatabaseMixin, unittest.TestCase):

    server_url = 'http://localhost:5984/'

    def setUp(self):
        super(TestFlushHook, self).setUp()
        self.db.update([
            {'type': 'tag', 'name': 'foo'},
            {'type': 'tag', 'name': 'bar'},
            {'type': 'post', 'title': 'Post #1', 'tag': 'foo'},
            {'type': 'post', 'title': 'Post #2', 'tag': 'bar'},
            {'_id': '_design/test', 'views': {
                'tag_by_name': {
                    'map': """function(doc) {if(doc.type=='tag') {emit(doc.name, null);}}""",
                    },
                'post_by_tag': {
                    'map': """function(doc) {if(doc.type=='post') {emit(doc.tag, null);}}""",
                    }
                }},
            ])

    def test_pre_flush_type(self):
        def pre_flush_hook(session, deletions, additions, changes):
            for o in additions:
                self.assertTrue(not isinstance(o, a8n.Dictionary))
            for (o, _) in changes:
                self.assertTrue(not isinstance(o, a8n.Dictionary))
        S = session.Session(self.db)
        doc1id = S.create({'model_type': 'test'})
        S.flush()
        S = session.Session(self.db, pre_flush_hook=pre_flush_hook)
        doc1 = S.get(doc1id)
        doc1['foo'] = 'bar'
        doc2id = S.create({})
        S.flush()

    def test_pre_flush_hook_arg(self):
        S = session.Session(self.db, pre_flush_hook=self._flush_hook)
        self._run_test_with_session(S)

    def test_pre_flush_hook_subclass(self):
        flush_hook = self._flush_hook
        class Session(session.Session):
            def pre_flush_hook(self, *a, **k):
                return flush_hook(self, *a, **k)
        S = Session(self.db)
        self._run_test_with_session(S)

    def test_post_flush_hook_arg(self):
        S = session.Session(self.db, post_flush_hook=self._flush_hook)
        self._run_test_with_session(S)

    def test_post_flush_hook_subclass(self):
        flush_hook = self._flush_hook
        class Session(session.Session):
            def post_flush_hook(self, *a, **k):
                return flush_hook(self, *a, **k)
        S = Session(self.db)
        self._run_test_with_session(S)

    def _run_test_with_session(self, session):
        tag = get_one(session, 'test/tag_by_name', 'foo')
        tag['name'] = 'oof'
        session.flush()
        assert len(get_many(session, 'test/post_by_tag', 'foo')) == 0
        assert len(get_many(session, 'test/post_by_tag', 'oof')) == 1
        assert len(get_many(session, 'test/post_by_tag', 'bar')) == 1

    def _flush_hook(self, session, deletions, additions, changes):
        for doc, actions in changes:
            if doc['type'] != 'tag':
                continue
            for action in actions:
                if action['action'] == 'edit' and action['path'] == ['name']:
                    for post in get_many(session, 'test/post_by_tag', action['was']):
                        post['tag'] = action['value']


class TestEncodeDecodeHooks(TempDatabaseMixin, unittest.TestCase):

    def test_encode(self):
        def encode_doc(doc):
            doc = dict(doc)
            doc['foo'] = 'bar'
            return doc
        S = session.Session(self.db, encode_doc=encode_doc)
        S.create({'_id': 'doc'})
        S.flush()
        assert 'foo' not in S.get('doc')
        assert self.db.get('doc')['foo'] == 'bar'

    def test_decode(self):
        def decode_doc(doc):
            doc = dict(doc)
            del doc['foo']
            return doc
        def make_session():
            return session.Session(self.db, decode_doc=decode_doc)
        doc_id = self.db.create({'foo': 'bar'})
        assert 'foo' not in make_session()[doc_id]
        assert 'foo' not in make_session().get(doc_id)
        assert 'foo' not in iter(make_session().view('_all_docs', include_docs=True)).next().doc
        assert 'foo' not in make_session().view('_all_docs', include_docs=True).rows[0].doc


class TestTrackerOverride(TempDatabaseMixin, unittest.TestCase):

    def test_override(self):
        state = {}
        class Tracker(a8n.Tracker):
            def _track(self, obj, path):
                state['_track'] = True
                return super(Tracker, self)._track(obj, path)
        class Session(session.Session):
            tracker_factory = Tracker
        doc_id = self.db.create({})
        doc = Session(self.db).get(doc_id)
        assert state['_track']


def get_one(session, view, key):
    rows = session.view(view, startkey=key, endkey=key, include_docs=True, limit=2).rows
    if len(rows) != 1:
        raise Exception('get_one')
    return rows[0].doc


def get_many(session, view, key):
    rows = session.view(view, startkey=key, endkey=key, include_docs=True).rows
    return [row.doc for row in rows]


if __name__ == '__main__':
    unittest.main()

