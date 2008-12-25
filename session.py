from proxy import wrap


class Session(object):

    def __init__(self, db):
        self._db = db
        self._cache = {}
        self._changed = set()

    def __getattr__(self, name):
        return getattr(self._db, name)

    def __delitem__(self, id):
        raise NotImplementedError()

    def __getitem__(self, id):
        doc = self._cache.get(id)
        if doc is not None:
            return doc
        return self._cached(self._db[id])

    def _cached(self, doc):
        def modified():
            self._changed.add(doc.id)
        doc = wrap(doc, modified)
        self._cache[doc.id] = doc
        return doc

    def __setitem__(self, id, content):
        raise NotImplementedError()

    def create(self, data):
        raise NotImplementedError()

    def delete(self, doc):
        raise NotImplementedError()

    def get(self, id, default=None, **options):
        # Try cache first.
        doc = self._cache.get(id)
        if doc is not None:
            return doc
        # Ask CouchDB and cache the response (if found).
        doc = self._db.get(id, default, **options)
        if doc is default:
            return doc
        return self._cached(doc)

    def delete_attachment(self, doc, filename):
        raise NotImplementedError()

    def get_attachment(self, id_or_doc, filename, default=None):
        raise NotImplementedError()

    def put_attachment(self, doc, content, filename=None, content_type=None):
        raise NotImplementedError()

    def query(self, *a, **k):
        return SessionViewResults(self, self._db.query(*a, **k))

    def update(self, documents):
        raise NotImplementedError()

    def view(self, *a, **k):
        return SessionViewResults(self, self._db.view(*a, **k))

    #-----

    def flush(self):
        # Build a list of updates
        updates = (dict(self._cache[doc_id]) for doc_id in self._changed)
        # Perform a bulk update and fix up the cache with the new _rev of each
        # document.
        # XXX I wonder why we have to pass a list instance to update?
        for response in self._db.update(list(updates)):
            self._cache[response['_id']]['_rev'] = response['_rev']
        self._changed.clear()


class SessionViewResults(object):

    def __init__(self, session, view_results):
        self._session = session
        self._view_results = view_results

    def __getattr__(self, name):
        return getattr(self._view_results, name)

    def __len__(self):
        return len(self._view_results)

    def __getitem__(self, key):
        return SessionViewResults(self._session, self._view_results(key))

    def __iter__(self):
        for row in self._view_results:
            yield SessionRow(self._session, row)


class SessionRow(object):

    def __init__(self, session, row):
        self._session = session
        self._row = row

    def __getattr__(self, name):
        return getattr(self._row, name)

    def _get_doc(self):
        doc = self._row.doc
        if doc is not None:
            cached = self._session._cache.get(doc.id)
            if cached is not None:
                return cached
            return self._session._cached(doc)
    doc = property(_get_doc)


if __name__ == '__main__':

    import unittest
    import uuid
    import couchdb

    class BaseTestCase(unittest.TestCase):

        server_url = 'http://localhost:5984/'

        def setUp(self):
            self.db_name = 'test_'+str(uuid.uuid4())
            self.server = couchdb.Server(self.server_url)
            self.db = self.server.create(self.db_name)
            self.session = Session(self.db)
            self.db.update([{'_id': str(i)} for i in range(10)])

        def tearDown(self):
            del self.server[self.db_name]


    class TestView(BaseTestCase):

        def test_view_len(self):
            view = self.session.view('_all_docs')
            assert len(view) == 10

        def test_view_getitem(self):
            assert isinstance(self.session.view('_all_docs'), SessionViewResults)


    class TestCaching(BaseTestCase):

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
            assert row1.doc is self.session[row1.doc.id]

        def test_query(self):
            map_fun = "function(doc) {emit(null, null);}"
            row1 = iter(self.session.query(map_fun)).next()
            assert row1.doc is None
            row1 = iter(self.session.query(map_fun, include_docs=True)).next()
            row2 = iter(self.session.query(map_fun, include_docs=True)).next()
            assert row1.doc is row2.doc is self.session[row1.doc.id]


    class TestModified(BaseTestCase):

        def test_initial(self):
            assert not self.session._changed

        def test_clean_after_read(self):
            doc_id = self.db.create({})
            doc = self.session.get(doc_id)
            assert len(self.session._changed) == 0

        def test_change_existing_setitem(self):
            doc_id = self.db.create({})
            doc = self.session.get(doc_id)
            doc['foo'] = 'bar'
            assert len(self.session._changed) == 1

        def test_change_existing_delitem(self):
            doc_id = self.db.create({'foo': 'bar'})
            doc = self.session.get(doc_id)
            del doc['foo']
            assert len(self.session._changed) == 1

        def test_change_multi_existing(self):
            doc_ids = list(r['_id'] for r in self.db.update([{}, {}]))
            doc1 = self.session.get(doc_ids[0])
            doc2 = self.session.get(doc_ids[1])
            assert not self.session._changed
            doc1['foo'] = ['bar']
            assert len(self.session._changed) == 1
            doc2['foo'] = ['bar']
            assert len(self.session._changed) == 2

        def test_change_dict_in_doc(self):
            doc_id = self.db.create({'dict': {}})
            doc = self.session.get(doc_id)
            doc['dict']['foo'] = 'bar'
            assert len(self.session._changed) == 1

        def test_change_list_in_doc_setitem(self):
            doc_id = self.db.create({'list': [None]})
            doc = self.session.get(doc_id)
            doc['list'][0] = 'foo'
            assert len(self.session._changed) == 1

        def test_change_list_in_doc_setitem_slice(self):
            doc_id = self.db.create({'list': []})
            doc = self.session.get(doc_id)
            doc['list'][:] = ['foo']
            assert len(self.session._changed) == 1

        def test_change_list_in_doc_setitem_slice2(self):
            doc_id = self.db.create({'list': range(3)})
            doc = self.session.get(doc_id)
            doc['list'][::2] = [None, None]
            assert len(self.session._changed) == 1

        def test_change_list_in_doc_delitem(self):
            doc_id = self.db.create({'list': [None]})
            doc = self.session.get(doc_id)
            del doc['list'][0]
            assert len(self.session._changed) == 1

        def test_change_list_in_doc_delitem_slice(self):
            doc_id = self.db.create({'list': []})
            doc = self.session.get(doc_id)
            del doc['list'][:]
            assert len(self.session._changed) == 1

        def test_change_list_in_doc_delitem_slice2(self):
            doc_id = self.db.create({'list': [None, None, None]})
            doc = self.session.get(doc_id)
            del doc['list'][::2]
            assert len(self.session._changed) == 1

        def test_change_list_in_doc_append(self):
            doc_id = self.db.create({'list': []})
            doc = self.session.get(doc_id)
            doc['list'].append('foo')
            assert len(self.session._changed) == 1

        def test_change_list_in_doc_extend(self):
            doc_id = self.db.create({'list': []})
            doc = self.session.get(doc_id)
            doc['list'].extend([])
            assert len(self.session._changed) == 1

        def test_change_list_in_doc_insert(self):
            doc_id = self.db.create({'list': []})
            doc = self.session.get(doc_id)
            doc['list'].insert(0, 'foo')
            assert len(self.session._changed) == 1

        def test_change_list_in_doc_pop(self):
            doc_id = self.db.create({'list': [None]})
            doc = self.session.get(doc_id)
            doc['list'].pop(0)
            assert len(self.session._changed) == 1

        def test_change_list_in_doc_remove(self):
            doc_id = self.db.create({'list': ['foo']})
            doc = self.session.get(doc_id)
            doc['list'].remove('foo')
            assert len(self.session._changed) == 1

        def test_change_collection_from_dict_in_doc(self):
            doc_id = self.db.create({'dict': {'collection': {}}})
            doc = self.session.get(doc_id)
            doc['dict']['collection']['foo'] = 'bar'
            assert len(self.session._changed) == 1

        def test_change_collection_from_list_in_doc_getitem(self):
            doc_id = self.db.create({'list': [{}]})
            doc = self.session.get(doc_id)
            doc['list'][0]['foo'] = 'bar'
            assert len(self.session._changed) == 1

        def test_change_collection_from_list_in_doc_slice(self):
            doc_id = self.db.create({'list': [{}]})
            doc = self.session.get(doc_id)
            doc['list'][:][0]['foo'] = 'bar'
            assert len(self.session._changed) == 1

        def test_change_collection_from_list_in_doc_slice2(self):
            doc_id = self.db.create({'list': [{}]})
            doc = self.session.get(doc_id)
            doc['list'][::2][0]['foo'] = 'bar'
            assert len(self.session._changed) == 1

        def test_get_scalar_from_doc(self):
            doc_id = self.db.create({'foo': 'bar'})
            doc = self.session.get(doc_id)
            assert doc['foo'] == 'bar'
            assert len(self.session._changed) == 0

        def test_get_scalar_from_dict_in_doc(self):
            doc_id = self.db.create({'dict': {'foo': 'bar'}})
            doc = self.session.get(doc_id)
            assert doc['dict']['foo'] == 'bar'
            assert len(self.session._changed) == 0

        def test_get_scalar_from_list_in_doc(self):
            doc_id = self.db.create({'list': ['foo']})
            doc = self.session.get(doc_id)
            assert doc['list'][0] == 'foo'
            assert len(self.session._changed) == 0


    class TestStorage(BaseTestCase):

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


    unittest.main()

