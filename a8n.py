"""
Known limitations:
    * Not thread safe.
"""

import itertools
import UserDict
from peak.rules import abstract, when
from peak.util.proxies import ObjectWrapper


_SENTINEL = object()


@abstract()
def track(obj, recorder):
    pass


@when(track, (dict,))
def track_dict(obj, recorder):
    return Dictionary(obj, recorder)


@when(track, (list,))
def track_list(obj, recorder):
    return List(obj, recorder)


class Tracker(object):

    def __init__(self):
        self._changes = []
        self._recorder_id = itertools.count()
        self._recorder_paths = {}

    def __iter__(self):
        return iter(self._changes)

    def track(self, obj):
        return track(obj, self.make_recorder([]))

    def append(self, change):
        self._changes.append(change)

    def make_recorder(self, path):
        id = self._recorder_id.next()
        self._recorder_paths[id] = path
        return Recorder(self, id)


class Recorder(object):

    def __init__(self, tracker, id):
        self._tracker = tracker
        self._id = id

    @property
    def _path(self):
        return self._tracker._recorder_paths[self._id]

    def make_recorder(self, path):
        return self._tracker.make_recorder(self._path + [path])

    def create(self, path, value):
        self._tracker.append({'action': 'create',
                              'path': self._path + [path],
                              'value': value})

    def edit(self, path, value):
        self._tracker.append({'action': 'edit',
                              'path': self._path + [path],
                              'value': value})

    def remove(self, path):
        self._tracker.append({'action': 'remove',
                              'path': self._path + [path]})

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


class Dictionary(UserDict.DictMixin, ObjectWrapper):

    # TODO:
    #   __contains__(), __iter__(), and iteritems() to improve performance

    __recorder = None

    def __init__(self, subject, recorder):
        super(Dictionary, self).__init__(subject)
        self.__recorder = recorder

    def __getitem__(self, name):
        value = self.__subject__.__getitem__(name)
        return track(value, self.__recorder.make_recorder(name))

    def __setitem__(self, name, value):
        if self.__subject__.get(name, _SENTINEL) is _SENTINEL:
            self.__recorder.create(name, value)
        else:
            self.__recorder.edit(name, value)
        return self.__subject__.__setitem__(name, value)

    def __delitem__(self, name):
        self.__subject__.__delitem__(name)
        self.__recorder.remove(name)

    def keys(self):
        return self.__subject__.keys()


class List(ObjectWrapper):

    __recorder = None

    def __init__(self, subject, recorder):
        super(List, self).__init__(subject)
        self.__recorder = recorder

    def __getitem__(self, pos):
        value = self.__subject__.__getitem__(pos)
        return track(value, self.__recorder.make_recorder(pos))
        
    def __getslice__(self, *a, **k):
        raise NotImplementedError()
        
    def __setitem__(self, pos, item):
        self.__subject__.__setitem__(pos, item)
        self.__recorder.edit(pos, item)

    def __delitem__(self, pos):
        self.__subject__.__delitem__(pos)
        self.__recorder.remove(pos)
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
        self.__recorder.remove(pos)
        self.__recorder.adjust_child_paths(_make_list_adjuster(-1, pos+1))
        return item

    def remove(self, item):
        pos = self.index(item)
        self.__recorder.remove(pos)
        self.__recorder.adjust_child_paths(_make_list_adjuster(-1, pos+1))
        return self.__subject__.remove(item)

    def reverse(self, *a, **k):
        raise NotImplementedError()

    def sort(self, *a, **k):
        raise NotImplementedError()

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

