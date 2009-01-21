import unittest

import a8n


"""
TODO:
    test slice operations
"""


class TestDictTracking(unittest.TestCase):

    def test_add_item(self):
        tracker = a8n.Tracker()
        obj = tracker.track({})
        obj['foo'] = 'bar'
        assert list(tracker) == [{'action': 'create', 'path': ['foo'], 'value': 'bar'}]

    def test_add_item_set_same_item(self):
        tracker = a8n.Tracker()
        obj = tracker.track({})
        obj['foo'] = 'oof'
        obj['foo'] = 'bar'
        assert list(tracker) == [{'action': 'create', 'path': ['foo'], 'value': 'bar'}]

    def test_add_item_del_same_item(self):
        tracker = a8n.Tracker()
        obj = tracker.track({})
        obj['foo'] = 'oof'
        del obj['foo']
        assert list(tracker) == []

    def test_change_item(self):
        tracker = a8n.Tracker()
        obj = tracker.track({'foo': 'foo'})
        obj['foo'] = 'bar'
        assert list(tracker) == [{'action': 'edit', 'path': ['foo'], 'value': 'bar', 'was': 'foo'}]

    def test_change_same_item(self):
        tracker = a8n.Tracker()
        obj = tracker.track({'foo': 'foo'})
        obj['foo'] = 'a'
        obj['foo'] = 'b'
        assert list(tracker) == [{'action': 'edit', 'path': ['foo'], 'value': 'b', 'was': 'foo'}]

    def test_change_same_del_same_item(self):
        tracker = a8n.Tracker()
        obj = tracker.track({'foo': 'foo'})
        obj['foo'] = 'a'
        del obj['foo']
        assert list(tracker) == [{'action': 'remove', 'path': ['foo'], 'was': 'foo'}]

    def test_del_item(self):
        tracker = a8n.Tracker()
        obj = tracker.track({'foo': 'foo'})
        del obj['foo']
        assert list(tracker) == [{'action': 'remove', 'path': ['foo'], 'was': 'foo'}]

    def test_del_missing_item(self):
        tracker = a8n.Tracker()
        obj = tracker.track({})
        try:
            del obj['foo']
        except KeyError:
            pass
        assert list(tracker) == []

    def test_del_item_add_same(self):
        tracker = a8n.Tracker()
        obj = tracker.track({'foo': 'foo'})
        del obj['foo']
        obj['foo'] = 'bar'
        assert list(tracker) == [{'action': 'remove', 'path': ['foo'], 'was': 'foo'},
                                 {'action': 'create', 'path': ['foo'], 'value': 'bar'}]

    def test_del_item_add_same_del_same(self):
        tracker = a8n.Tracker()
        obj = tracker.track({'foo': 'foo'})
        del obj['foo']
        obj['foo'] = 'bar'
        del obj['foo']
        assert list(tracker) == [{'action': 'remove', 'path': ['foo'], 'was': 'foo'}]

    def test_replace_nested_with_actions(sel):
        tracker = a8n.Tracker()
        obj = tracker.track({'nested': {'a': 0, 'c': 2}})
        obj['nested']['a'] = 1
        obj['nested']['b'] = 2
        del obj['nested']['c']
        assert list(tracker) == [{'action': 'edit', 'path': ['nested', 'a'], 'value': 1, 'was': 0},
                                 {'action': 'create', 'path': ['nested', 'b'], 'value': 2},
                                 {'action': 'remove', 'path': ['nested', 'c'], 'was': 2}]
        obj['nested'] = {}
        assert list(tracker) == [{'action': 'edit', 'path': ['nested'], 'value': {}, 'was': {'a': 0, 'c': 2}}]

    def test_remove_nested_with_actions(sel):
        tracker = a8n.Tracker()
        obj = tracker.track({'nested': {'a': 0, 'c': 2}})
        obj['nested']['a'] = 1
        obj['nested']['b'] = 2
        del obj['nested']['c']
        assert list(tracker) == [{'action': 'edit', 'path': ['nested', 'a'], 'value': 1, 'was': 0},
                                 {'action': 'create', 'path': ['nested', 'b'], 'value': 2},
                                 {'action': 'remove', 'path': ['nested', 'c'], 'was': 2}]
        del obj['nested']
        assert list(tracker) == [{'action': 'remove', 'path': ['nested'], 'was': {'a': 0, 'c': 2}}]


class TestListTracking(unittest.TestCase):

    def test_setitem(self):
        tracker = a8n.Tracker()
        obj = tracker.track(['foo'])
        obj[0] = 'bar'
        assert list(tracker) == [{'action': 'edit', 'path': [0], 'value': 'bar', 'was': 'foo'}]

    def test_setitem_error(self):
        tracker = a8n.Tracker()
        obj = tracker.track(['foo'])
        try:
            obj[1] = 'bar'
        except IndexError:
            pass
        assert list(tracker) == []

    def test_setitem_twice(self):
        tracker = a8n.Tracker()
        obj = tracker.track(['foo'])
        obj[0] = 'bar'
        obj[0] = 'oof'
        assert list(tracker) == [{'action': 'edit', 'path': [0], 'value': 'oof', 'was': 'foo'}]

    def test_delitem(self):
        tracker = a8n.Tracker()
        obj = tracker.track(['foo'])
        del obj[0]
        assert list(tracker) == [{'action': 'remove', 'path': [0], 'was': 'foo'}]

    def test_delitem_error(self):
        tracker = a8n.Tracker()
        obj = tracker.track(['foo'])
        try:
            del obj[1]
        except IndexError:
            pass
        assert list(tracker) == []

    def test_set_then_delete(self):
        tracker = a8n.Tracker()
        obj = tracker.track(['foo'])
        obj[0] = 'bar'
        del obj[0]
        assert list(tracker) == [{'action': 'remove', 'path': [0], 'was': 'foo'}]

    def test_append(self):
        tracker = a8n.Tracker()
        obj = tracker.track([])
        obj.append('foo')
        assert list(tracker) == [{'action': 'create', 'path': [0], 'value': 'foo'}]

    def test_append_then_delete(self):
        tracker = a8n.Tracker()
        obj = tracker.track([])
        obj.append('foo')
        del obj[0]
        assert list(tracker) == []

    def test_extend(self):
        tracker = a8n.Tracker()
        obj = tracker.track([])
        obj.extend(['foo', 'bar'])
        assert list(tracker) == [
            {'action': 'create', 'path': [0], 'value': 'foo'},
            {'action': 'create', 'path': [1], 'value': 'bar'},
        ]

    def test_insert(self):
        tracker = a8n.Tracker()
        obj = tracker.track([1, 3])
        obj.insert(1, 2)
        assert list(tracker) == [{'action': 'create', 'path': [1], 'value': 2}]
        tracker = a8n.Tracker()
        obj = tracker.track([])
        obj.insert(10, 1)
        assert list(tracker) == [{'action': 'create', 'path': [0], 'value': 1}]
        tracker = a8n.Tracker()
        obj = tracker.track([])
        obj.insert(-10, 1)
        assert list(tracker) == [{'action': 'create', 'path': [0], 'value': 1}]

    def test_pop(self):
        tracker = a8n.Tracker()
        obj = tracker.track([1, 2, 3])
        obj.pop(0)
        assert list(tracker) == [{'action': 'remove', 'path': [0], 'was': 1}]
        tracker = a8n.Tracker()
        obj = tracker.track([1, 2, 3])
        obj.pop()
        assert list(tracker) == [{'action': 'remove', 'path': [2], 'was': 3}]
        tracker = a8n.Tracker()
        obj = tracker.track([1, 2, 3])
        try:
            obj.pop(100)
        except IndexError:
            pass
        assert list(tracker) == []

    def test_remove(self):
        tracker = a8n.Tracker()
        obj = tracker.track([1, 2, 3])
        obj.remove(2)
        assert list(tracker) == [{'action': 'remove', 'path': [1], 'was': 2}]
        tracker = a8n.Tracker()
        obj = tracker.track([1, 2, 3])
        try:
            obj.remove(10)
        except ValueError:
            pass
        assert list(tracker) == []

    def test_add_then_remove(self):
        tracker = a8n.Tracker()
        obj = tracker.track([1, 2, 3])
        obj.append(4)
        obj.remove(4)
        assert list(tracker) == []

    def test_replace_nested_with_actions(sel):
        tracker = a8n.Tracker()
        obj = tracker.track([{'a': 0, 'c': 2}])
        obj[0]['a'] = 1
        obj[0]['b'] = 2
        del obj[0]['c']
        assert list(tracker) == [{'action': 'edit', 'path': [0, 'a'], 'value': 1, 'was': 0},
                                 {'action': 'create', 'path': [0, 'b'], 'value': 2},
                                 {'action': 'remove', 'path': [0, 'c'], 'was': 2}]
        obj[0] = {}
        assert list(tracker) == [{'action': 'edit', 'path': [0], 'value': {}, 'was': {'a': 0, 'c': 2}}]

    def test_remove_nested_with_actions(sel):
        tracker = a8n.Tracker()
        obj = tracker.track([{'a': 0, 'c': 2}])
        obj[0]['a'] = 1
        obj[0]['b'] = 2
        del obj[0]['c']
        assert list(tracker) == [{'action': 'edit', 'path': [0, 'a'], 'value': 1, 'was': 0},
                                 {'action': 'create', 'path': [0, 'b'], 'value': 2},
                                 {'action': 'remove', 'path': [0, 'c'], 'was': 2}]
        del obj[0]
        assert list(tracker) == [{'action': 'remove', 'path': [0], 'was': {'a': 0, 'c': 2}}]


class TestNested(unittest.TestCase):

    def test_dict_in_dict(self):
        tracker = a8n.Tracker()
        obj = tracker.track({'dict': {}})
        obj['dict']['foo'] = 'bar'
        assert list(tracker) == [{'action': 'create', 'path': ['dict', 'foo'], 'value': 'bar'}]

    def test_dict_in_list(self):
        tracker = a8n.Tracker()
        obj = tracker.track([{}])
        obj[0]['foo'] = 'bar'
        assert list(tracker) == [{'action': 'create', 'path': [0, 'foo'], 'value': 'bar'}]

    def test_list_in_dict(self):
        tracker = a8n.Tracker()
        obj = tracker.track({'list': []})
        obj['list'].append('foo')
        assert list(tracker) == [{'action': 'create', 'path': ['list', 0], 'value': 'foo'}]

    def test_list_in_list(self):
        tracker = a8n.Tracker()
        obj = tracker.track([[]])
        obj[0].append('foo')
        assert list(tracker) == [{'action': 'create', 'path': [0, 0], 'value': 'foo'}]


class TestChangingPaths(unittest.TestCase):

    def test_delitem(self):
        tracker = a8n.Tracker()
        obj = tracker.track([{}, {}])
        a_dict = obj[1]
        a_dict['a'] = 'a'
        assert list(tracker) == [{'action': 'create', 'path': [1, 'a'], 'value': 'a'}]
        del obj[0]
        assert list(tracker) == [{'action': 'create', 'path': [1, 'a'], 'value': 'a'},
                                 {'action': 'remove', 'path': [0], 'was': {}}]
        a_dict['b'] = 'b'
        assert list(tracker) == [{'action': 'create', 'path': [1, 'a'], 'value': 'a'},
                                 {'action': 'remove', 'path': [0], 'was': {}},
                                 {'action': 'create', 'path': [0, 'b'], 'value': 'b'}]

    def test_insert(self):
        tracker = a8n.Tracker()
        obj = tracker.track([{}, {}])
        a_dict = obj[1]
        obj.insert(0, {})
        a_dict['foo'] = 'bar'
        assert list(tracker) == [{'action': 'create', 'path': [0], 'value': {}},
                                 {'action': 'create', 'path': [2, 'foo'], 'value': 'bar'}]

    def test_pop(self):
        tracker = a8n.Tracker()
        obj = tracker.track([{}, {}])
        a_dict = obj[1]
        obj.pop(0)
        a_dict['foo'] = 'bar'
        assert list(tracker) == [{'action': 'remove', 'path': [0], 'was': {}},
                                 {'action': 'create', 'path': [0, 'foo'], 'value': 'bar'}]

    def test_remove(self):
        tracker = a8n.Tracker()
        obj = tracker.track([{'a': 1}, {'b': 2}])
        a_dict = obj[1]
        obj.remove({'a': 1})
        a_dict['b'] = 'b'
        assert list(tracker) == [{'action': 'remove', 'path': [0], 'was': {'a': 1}},
                                 {'action': 'edit', 'path': [0, 'b'], 'value': 'b', 'was': 2}]


class TestUntracked(unittest.TestCase):

    def test_untracked_in_dict(self):
        tracker = a8n.Tracker()
        obj = tracker.track({})
        obj['untracked'] = {}
        obj['untracked']['foo'] = 'bar'
        assert list(tracker) == [{'action': 'create', 'path': ['untracked'], 'value': {'foo': 'bar'}}]

    def test_untracked_in_list(self):
        tracker = a8n.Tracker()
        obj = tracker.track([])
        obj.append({})
        obj[0]['foo'] = 'bar'
        assert list(tracker) == [{'action': 'create', 'path': [0], 'value': {'foo': 'bar'}}]


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

