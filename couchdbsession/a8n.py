"""
Known limitations:
    * Not thread safe.
"""

import datetime
import itertools
import types
import UserDict
from simplegeneric import generic
from peak.util.proxies import ObjectWrapper
import couchdb
from decimal import Decimal


_SENTINEL = object()


class Tracker(object):

    def __init__(self, dirty_callback=None):
        self._dirty_callback = dirty_callback
        self._changes = []
        self._recorder_id = itertools.count()
        self._recorder_paths = {}
        self._recorder_creates = {}
        self._recorder_edits = {}

    def track(self, obj):
        """
        Start tracking an object.
        """
        return self._track(obj, [])

    def clear(self):
        """
        Forget all changes tracked so far.
        """
        self._changes = []
        self._recorder_creates = {}
        self._recorder_edits = {}

    def freeze(self):
        """
        Clear tracked changes, but return an iterator over everything changed
        so far.
        """
        it = iter(self)
        self.clear()
        return it

    def __iter__(self):
        """
        Iterate the changes.
        """
        return iter(self._changes)

    def append(self, change):
        if not self._changes and self._dirty_callback:
            self._dirty_callback()
        self._changes.append(change)

    def _make_recorder(self, path):
        id = self._recorder_id.next()
        self._recorder_paths[id] = path
        return Recorder(self, id)

    def _track(self, obj, path):
        return _track(obj, self, path)


@generic
def _track(obj, path, tracker):
    pass

@_track.when_type(types.NoneType)
@_track.when_type(bool)
@_track.when_type(float)
@_track.when_type(int)
@_track.when_type(long)
@_track.when_type(str)
@_track.when_type(unicode)
@_track.when_type(datetime.datetime)
@_track.when_type(datetime.date)
@_track.when_type(datetime.time)
@_track.when_type(Decimal)
@_track.when_type(tuple)
def _track_immutable(obj, tracker, path):
    return obj

@_track.when_type(couchdb.Document)
def _track_doc(obj, tracker, path):
    return Document(obj, tracker._make_recorder(path))

@_track.when_type(dict)
def _track_dict(obj, tracker, path):
    return Dictionary(obj, tracker._make_recorder(path))

@_track.when_type(list)
def _track_list(obj, tracker, path):
    return List(obj, tracker._make_recorder(path))


class Recorder(object):

    def __init__(self, tracker, id):
        self._tracker = tracker
        self._id = id

    @property
    def _creates(self):
        return self._tracker._recorder_creates.setdefault(self._id, {})

    @property
    def _edits(self):
        return self._tracker._recorder_edits.setdefault(self._id, {})

    @property
    def _path(self):
        return self._tracker._recorder_paths[self._id]

    def create(self, path, value):
        action = {'action': 'create',
                  'path': self._path + [path],
                  'value': value}
        self._creates[path] = action
        self._tracker.append(action)

    def edit(self, path, value, was):
        self._remove_nested_actions(path)
        # Update a previous 'create' action.
        create_action = self._creates.get(path)
        if create_action is not None:
            create_action['value'] = value
            return
        # Update a previous 'edit' action.
        edit_action = self._edits.get(path)
        if edit_action is not None:
            edit_action['value'] = value
            return
        # Add a new 'edit' action.
        action = {'action': 'edit',
                  'path': self._path + [path],
                  'value': value,
                  'was': was}
        self._edits[path] = action
        self._tracker.append(action)

    def remove(self, path, was):
        self._remove_nested_actions(path)
        # Remove a previous 'create' action.
        create_action = self._creates.pop(path, None)
        if create_action is not None:
            self._tracker._changes.remove(create_action)
            return
        # Remove a previous 'edit' action and continue.
        edit_action = self._edits.pop(path, None)
        if edit_action is not None:
            self._tracker._changes.remove(edit_action)
        # Add a new 'delete' action.
        action = {'action': 'remove',
                  'path': self._path + [path],
                  'was': was}
        self._tracker.append(action)

    def track_child(self, obj, name):
        return self._tracker._track(obj, self._path+[name])

    def adjust_child_paths(self, adjuster):
        # Avoid looking up the path multiple times.
        my_path = self._path
        my_path_len = len(self._path)
        # Loop over all the recorded paths, calling the adjuster for any
        # immediate children, and updating the paths for the future.
        for id, path in self._tracker._recorder_paths.iteritems():
            if not (path[:my_path_len] == my_path and len(path) > my_path_len):
                continue
            child_path = path[my_path_len]
            remaining_path = path[my_path_len+1:]
            new_path = my_path + [adjuster(path[-1])] + remaining_path
            self._tracker._recorder_paths[id] = new_path

    def _remove_nested_actions(self, path):
        full_path = self._path + [path]
        full_path_len = len(full_path)
        to_delete = (i for (i,change) in enumerate(self._tracker._changes)
                     if change['path'][:full_path_len] == full_path and 
                         len(change['path']) > full_path_len)
        for i in sorted(to_delete, reverse=True):
            del self._tracker._changes[i]


class Dictionary(UserDict.DictMixin, ObjectWrapper):

    # TODO:
    #   __contains__(), __iter__(), and iteritems() to improve performance

    __recorder = None
    _private = []

    def __init__(self, subject, recorder):
        super(Dictionary, self).__init__(subject)
        self.__recorder = recorder

    def __getitem__(self, name):
        value = self.__subject__.__getitem__(name)
        if name in self.__recorder._creates or name in self.__recorder._edits:
            return value
        return self.__recorder.track_child(value, name)

    def __setitem__(self, name, value):
        if name not in self._private:
            was = self.__subject__.get(name, _SENTINEL)
            if was is _SENTINEL:
                self.__recorder.create(name, value)
            elif value != was:
                self.__recorder.edit(name, value, was)
        return self.__subject__.__setitem__(name, value)

    def __delitem__(self, name):
        was = self.__subject__[name]
        self.__subject__.__delitem__(name)
        self.__recorder.remove(name, was)

    def keys(self):
        return self.__subject__.keys()


class Document(Dictionary):
    _private = ['_id', '_rev', '_attachments']


class List(ObjectWrapper):

    __recorder = None

    def __init__(self, subject, recorder):
        super(List, self).__init__(subject)
        self.__recorder = recorder

    def __iter__(self):
        for pos, item in enumerate(self.__subject__):
            if pos in self.__recorder._creates or pos in self.__recorder._edits:
                yield item
            else:
                yield self.__recorder.track_child(item, pos)

    def __getitem__(self, pos):
        value = self.__subject__.__getitem__(pos)
        if pos in self.__recorder._creates or pos in self.__recorder._edits:
            return value
        return self.__recorder.track_child(value, pos)
        
    def __getslice__(self, *a, **k):
        raise NotImplementedError()
        
    def __setitem__(self, pos, item):
        was = self.__subject__[pos]
        self.__subject__.__setitem__(pos, item)
        if item != was:
            self.__recorder.edit(pos, item, was)

    def __delitem__(self, pos):
        was = self.__subject__[pos]
        self.__subject__.__delitem__(pos)
        self.__recorder.remove(pos, was)
        self.__recorder.adjust_child_paths(_make_list_adjuster(-1, pos))

    def __setslice__(self, *a, **k):
        raise NotImplementedError()

    def __delslice__(self, *a, **k):
        raise NotImplementedError()

    def append(self, item):
        self.__recorder.create(len(self.__subject__), item)
        return self.__subject__.append(item)

    def extend(self, items):
        pos = len(self.__subject__)
        for i, item in enumerate(items):
            self.__recorder.create(pos+i, item)
        return self.__subject__.extend(items)

    def insert(self, pos, item):
        pos = self.__real_pos(pos)
        self.__recorder.adjust_child_paths(_make_list_adjuster(+1, pos))
        self.__recorder.create(pos, item)
        return self.__subject__.insert(pos, item)

    def pop(self, pos=-1):
        pos = self.__real_pos(pos)
        try:
            item = self.__subject__.pop(pos)
        except IndexError:
            raise
        self.__recorder.remove(pos, item)
        self.__recorder.adjust_child_paths(_make_list_adjuster(-1, pos+1))
        return item

    def remove(self, item):
        pos = self.index(item)
        self.__recorder.remove(pos, item)
        self.__recorder.adjust_child_paths(_make_list_adjuster(-1, pos+1))
        return self.__subject__.remove(item)

    def reverse(self, *a, **k):
        raise NotImplementedError()

    def sort(self, *a, **k):
        before = list(self.__subject__)
        before_pos = dict((id(i), pos) for pos, i in enumerate(self.__subject__))
        self.__subject__.sort(*a, **k)
        for pos, i in enumerate(self.__subject__):
            oldpos = before_pos[id(i)]
            if pos != oldpos:
                self.__recorder.edit(pos, i, before[pos])

    def __real_pos(self, pos):
        if pos < 0:
            pos = len(self.__subject__)+pos
        return max(0, min(pos, len(self.__subject__)))


def _make_list_adjuster(adjustment, start, end=None):
    def adjuster(path):
        if (start is  None or start <= path) and \
           (end is None or path < end):
            return path + adjustment
        return path
    return adjuster

