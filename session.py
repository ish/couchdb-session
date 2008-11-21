class Session(object):

    def __init__(self, db):
        self._db = db
        self._cache = {}

    def __getattr__(self, name):
        return getattr(self._db, name)

    def __delitem__(self, id):
        raise NotImplementedError()

    def __getitem__(self, id):
        doc = self._cache.get(id)
        if doc is not None:
            return doc
        doc = self._cache[id] = self._db[id]
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
        if doc is not default:
            self._cache[doc['_id']] = doc
        return doc

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
            cached = self._session._cache[doc.id] = doc
            return cached
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


    unittest.main()

