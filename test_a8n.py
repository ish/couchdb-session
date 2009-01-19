import unittest

import a8n


class TestDictTracking(unittest.TestCase):

    def test_add_item(self):
        changes = []
        obj = a8n.track({}, [], changes)
        obj['foo'] = 'bar'
        assert changes == [{'action': 'create', 'path': ['foo'], 'value': 'bar'}]

    def test_change_item(self):
        changes = []
        obj = a8n.track({'foo': 'foo'}, [], changes)
        obj['foo'] = 'bar'
        assert changes == [{'action': 'edit', 'path': ['foo'], 'value': 'bar'}]

    def test_del_item(self):
        changes = []
        obj = a8n.track({'foo': 'foo'}, [], changes)
        del obj['foo']
        assert changes == [{'action': 'remove', 'path': ['foo']}]

    def test_del_missing_item(self):
        changes = []
        obj = a8n.track({}, [], changes)
        try:
            del obj['foo']
        except KeyError:
            pass
        assert changes == []


class TestListTracking(unittest.TestCase):

    def test_setitem(self):
        changes = []
        obj = a8n.track(['foo'], [], changes)
        obj[0] = 'bar'
        assert changes == [{'action': 'edit', 'path': [0], 'value': 'bar'}]

    def test_setitem_error(self):
        changes = []
        obj = a8n.track(['foo'], [], changes)
        try:
            obj[1] = 'bar'
        except IndexError:
            pass
        assert changes == []

    def test_delitem(self):
        changes = []
        obj = a8n.track(['foo'], [], changes)
        del obj[0]
        assert changes == [{'action': 'remove', 'path': [0]}]

    def test_delitem_error(self):
        changes = []
        obj = a8n.track(['foo'], [], changes)
        try:
            del obj[1]
        except IndexError:
            pass
        assert changes == []

    def test_append(self):
        changes = []
        obj = a8n.track([], [], changes)
        obj.append('foo')
        assert changes == [{'action': 'create', 'path': [0], 'value': 'foo'}]

    def test_extend(self):
        changes = []
        obj = a8n.track([], [], changes)
        obj.extend(['foo', 'bar'])
        assert changes == [
            {'action': 'create', 'path': [0], 'value': 'foo'},
            {'action': 'create', 'path': [1], 'value': 'bar'},
        ]

    def test_insert(self):
        changes = []
        obj = a8n.track([1, 3], [], changes)
        obj.insert(1, 2)
        assert changes == [{'action': 'create', 'path': [1], 'value': 2}]
        changes = []
        obj = a8n.track([], [], changes)
        obj.insert(10, 1)
        assert changes == [{'action': 'create', 'path': [0], 'value': 1}]
        changes = []
        obj = a8n.track([], [], changes)
        obj.insert(-10, 1)
        assert changes == [{'action': 'create', 'path': [0], 'value': 1}]

    def test_pop(self):
        changes = []
        obj = a8n.track([1, 2, 3], [], changes)
        obj.pop(0)
        assert changes == [{'action': 'remove', 'path': [0]}]
        changes = []
        obj = a8n.track([1, 2, 3], [], changes)
        obj.pop()
        assert changes == [{'action': 'remove', 'path': [2]}]
        changes = []
        obj = a8n.track([1, 2, 3], [], changes)
        try:
            obj.pop(100)
        except IndexError:
            pass
        assert changes == []

    def test_remove(self):
        changes = []
        obj = a8n.track([1, 2, 3], [], changes)
        obj.remove(2)
        assert changes == [{'action': 'remove', 'path': [1]}]
        changes = []
        obj = a8n.track([1, 2, 3], [], changes)
        try:
            obj.remove(10)
        except ValueError:
            pass
        assert changes == []


class TestNested(unittest.TestCase):

    def test_dict_in_dict(self):
        changes = []
        obj = a8n.track({'dict': {}}, [], changes)
        obj['dict']['foo'] = 'bar'
        assert changes == [{'action': 'create', 'path': ['dict', 'foo'], 'value': 'bar'}]

    def test_dict_in_list(self):
        changes = []
        obj = a8n.track([{}], [], changes)
        obj[0]['foo'] = 'bar'
        assert changes == [{'action': 'create', 'path': [0, 'foo'], 'value': 'bar'}]

    def test_list_in_dict(self):
        changes = []
        obj = a8n.track({'list': []}, [], changes)
        obj['list'].append('foo')
        assert changes == [{'action': 'create', 'path': ['list', 0], 'value': 'foo'}]

    def test_list_in_list(self):
        changes = []
        obj = a8n.track([[]], [], changes)
        obj[0].append('foo')
        assert changes == [{'action': 'create', 'path': [0, 0], 'value': 'foo'}]


"""
class _TestChangeTracking(unittest.TestCase):

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
"""


if __name__ == '__main__':
    unittest.main()

