import datetime
import unittest

from couchdbsession import a8n


"""
TODO:
    test slice operations
"""

def XXX_WITHOUT_WAS(l):
    return [dict((k,v) for (k,v) in i.iteritems() if k != 'was') for i in l]


class TestTracker(unittest.TestCase):

    def test_dirty_callback(self):
        state = []
        def callback():
            state.append(None)
        tracker = a8n.Tracker(callback)
        tracker.track({})['foo'] ='bar'
        assert state


class TestImmutableTracking(unittest.TestCase):

    def test_types(self):
        tracker = a8n.Tracker()
        for obj in [None, True, False, 'string', u'unicode', 1, 1L, 1.0,
                    datetime.datetime.utcnow(), datetime.date.today(),
                    datetime.datetime.utcnow().time(), ('a', 'tuple')]:
            assert obj is tracker.track(obj)


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

    def test_change_to_same(self):
        tracker = a8n.Tracker()
        obj = tracker.track({'foo': 'bar'})
        obj['foo'] = 'bar'
        assert list(tracker) == []

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
        assert XXX_WITHOUT_WAS(tracker) == XXX_WITHOUT_WAS([{'action': 'remove', 'path': ['foo'], 'was': 'foo'}])

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
        assert XXX_WITHOUT_WAS(tracker) == XXX_WITHOUT_WAS([{'action': 'edit', 'path': ['nested'], 'value': {}, 'was': {'a': 0, 'c': 2}}])

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
        assert XXX_WITHOUT_WAS(tracker) == XXX_WITHOUT_WAS([{'action': 'remove', 'path': ['nested'], 'was': {'a': 0, 'c': 2}}])

    def test_update(self):
        tracker = a8n.Tracker()
        obj = tracker.track({})
        obj.update({'foo': 'bar'})
        assert list(tracker) == [{'action': 'create', 'path': ['foo'], 'value': 'bar'}]

    def test_edits_not_wrapped(self):
        tracker = a8n.Tracker()
        obj = tracker.track({'foo': {}})
        assert hasattr(obj['foo'], '__subject__')
        obj['foo'] = {'different': 'dict'}
        assert not hasattr(obj['foo'], '__subject__')


class TestListTracking(unittest.TestCase):

    def test_setitem(self):
        tracker = a8n.Tracker()
        obj = tracker.track(['foo'])
        obj[0] = 'bar'
        assert list(tracker) == [{'action': 'edit', 'path': [0], 'value': 'bar', 'was': 'foo'}]

    def test_change_to_same(self):
        tracker = a8n.Tracker()
        obj = tracker.track(['foo'])
        obj[0] = 'foo'
        assert list(tracker) == []

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
        assert XXX_WITHOUT_WAS(tracker) == XXX_WITHOUT_WAS([{'action': 'remove', 'path': [0], 'was': 'foo'}])

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
        assert XXX_WITHOUT_WAS(tracker) == XXX_WITHOUT_WAS([{'action': 'edit', 'path': [0], 'value': {}, 'was': {'a': 0, 'c': 2}}])

    def test_remove_nested_with_actions(self):
        tracker = a8n.Tracker()
        obj = tracker.track([{'a': 0, 'c': 2}])
        obj[0]['a'] = 1
        obj[0]['b'] = 2
        del obj[0]['c']
        assert list(tracker) == [{'action': 'edit', 'path': [0, 'a'], 'value': 1, 'was': 0},
                                 {'action': 'create', 'path': [0, 'b'], 'value': 2},
                                 {'action': 'remove', 'path': [0, 'c'], 'was': 2}]
        del obj[0]
        assert XXX_WITHOUT_WAS(tracker) == XXX_WITHOUT_WAS([{'action': 'remove', 'path': [0], 'was': {'a': 0, 'c': 2}}])

    def test_iter(self):
        tracker = a8n.Tracker()
        obj = tracker.track([{}, {}])
        for d in obj:
            d['foo'] = 'bar'
        assert list(tracker) == [{'action': 'create', 'path': [0, 'foo'], 'value': 'bar'},
                                 {'action': 'create', 'path': [1, 'foo'], 'value': 'bar'}]

    def test_sort_forward(self):
        tests = [
            ([3, 1, 2], [{'action': 'edit', 'path': [0], 'value': 1, 'was': 3},
                         {'action': 'edit', 'path': [1], 'value': 2, 'was': 1},
                         {'action': 'edit', 'path': [2], 'value': 3, 'was': 2}]),
            ([1, 3, 2], [{'action': 'edit', 'path': [1], 'value': 2, 'was': 3},
                         {'action': 'edit', 'path': [2], 'value': 3, 'was': 2}]),
            ([1], []),
        ]
        for l, actions in tests:
            input = list(l)
            output = sorted(l)
            tracker = a8n.Tracker()
            obj = tracker.track(l)
            obj.sort()
            assert obj == output
            assert list(tracker) == actions

    def test_sort_reverse(self):
        tests = [
            ([3, 1, 2], [{'action': 'edit', 'path': [1], 'value': 2, 'was': 1},
                         {'action': 'edit', 'path': [2], 'value': 1, 'was': 2}]),
            ([1, 3, 2], [{'action': 'edit', 'path': [0], 'value': 3, 'was': 1},
                         {'action': 'edit', 'path': [1], 'value': 2, 'was': 3},
                         {'action': 'edit', 'path': [2], 'value': 1, 'was': 2}]),
            ([1], []),
        ]
        for l, actions in tests:
            input = list(l)
            output = sorted(l, reverse=True)
            tracker = a8n.Tracker()
            obj = tracker.track(l)
            obj.sort(reverse=True)
            assert obj == output
            assert list(tracker) == actions

    def test_edits_not_wrapped(self):
        tracker = a8n.Tracker()
        obj = tracker.track([[]])
        obj[0] = ['different', 'list']
        # getitem
        assert not hasattr(obj[0], '__subject__')
        # iter
        assert not hasattr(iter(obj).next(), '__subject__')


class TestNested(unittest.TestCase):

    def test_dict_in_dict(self):
        tracker = a8n.Tracker()
        obj = tracker.track({'dict': {}})
        obj['dict']['foo'] = 'bar'
        assert list(tracker) == [{'action': 'create', 'path': ['dict', 'foo'], 'value': 'bar'}]

    def test_dict_in_dict_update(self):
        tracker = a8n.Tracker()
        obj = tracker.track({'dict': {}})
        obj['dict'].update({'foo': 'bar'})
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


if __name__ == '__main__':
    unittest.main()

