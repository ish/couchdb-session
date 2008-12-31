import unittest
import uuid

import couchdb
import session


class BaseTestCase(unittest.TestCase):

    server_url = 'http://localhost:5984/'

    def setUp(self):
        self.db_name = 'test_'+str(uuid.uuid4())
        self.server = couchdb.Server(self.server_url)
        self.db = self.server.create(self.db_name)
        self.session = session.Session(self.db)
        self.db.update([{'_id': str(i)} for i in range(10)])

    def tearDown(self):
        del self.server[self.db_name]


class TestComposition(BaseTestCase):

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


class TestView(BaseTestCase):

    def test_view_len(self):
        view = self.session.view('_all_docs')
        assert len(view) == 10

    def test_view_getitem(self):
        assert isinstance(self.session.view('_all_docs'), session.SessionViewResults)


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
        assert row1.doc is self.session[row1.doc['_id']]

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


class TestChangeTracking(BaseTestCase):

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


class TestUpdates(BaseTestCase):

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

    def test_setitem(self):
        self.session['foo'] = {}
        assert len(self.session._cache) == 1
        assert len(self.session._created) == 1


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


if __name__ == '__main__':
    unittest.main()

