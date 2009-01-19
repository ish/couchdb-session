"""
Known limitations:
    * Not thread safe.
"""

import UserDict
from peak.rules import abstract, when
from peak.util.proxies import ObjectWrapper


_SENTINEL = object()


@abstract()
def track(obj, path, recorder):
    pass


@when(track, (dict,))
def track_dict(obj, path, recorder):
    return Dictionary(obj, path, recorder)


@when(track, (list,))
def track_list(obj, path, recorder):
    return List(obj, path, recorder)


class Dictionary(UserDict.DictMixin, ObjectWrapper):

    # TODO:
    #   __contains__(), __iter__(), and iteritems() to improve performance

    __path = None
    __recorder = None

    def __init__(self, subject, path, recorder):
        super(Dictionary, self).__init__(subject)
        self.__path = path
        self.__recorder = recorder

    def __getitem__(self, name):
        value = self.__subject__.__getitem__(name)
        return track(value, self.__path+[name], self.__recorder)

    def __setitem__(self, name, value):
        if self.__subject__.get(name, _SENTINEL) is _SENTINEL:
            action = 'create'
        else:
            action = 'edit'
        self.__recorder.append({'action': action,
                                'path': self.__path+[name],
                                'value': value})
        return self.__subject__.__setitem__(name, value)

    def __delitem__(self, name):
        self.__subject__.__delitem__(name)
        self.__recorder.append({'action': 'remove',
                                'path': self.__path+[name]})

    def keys(self):
        return self.__subject__.keys()


class List(ObjectWrapper):

    __path = None
    __recorder = None

    def __init__(self, subject, path, recorder):
        super(List, self).__init__(subject)
        self.__path = path
        self.__recorder = recorder

    def __getitem__(self, pos):
        value = self.__subject__.__getitem__(pos)
        return track(value, self.__path+[pos], self.__recorder)
        
    def __getslice__(self, *a, **k):
        value = self.__subject__.__getslice__(*a, **k)
        return wrap(value, self.__recorder)
        
    def __setitem__(self, pos, item):
        self.__subject__.__setitem__(pos, item)
        self.__recorder.append({'action': 'edit',
                                'path': self.__path + [pos],
                                'value': item})

    def __delitem__(self, pos):
        self.__subject__.__delitem__(pos)
        self.__recorder.append({'action': 'remove',
                                'path': self.__path + [pos]})

    def __setslice__(self, *a, **k):
        self.__recorder()
        return self.__subject__.__setslice__(*a, **k)

    def __delslice__(self, *a, **k):
        self.__recorder()
        return self.__subject__.__delslice__(*a, **k)

    def append(self, item):
        self.__recorder.append({'action': 'create',
                                'path': self.__path+[len(self.__subject__)],
                                'value': item})
        return self.__subject__.append(item)

    def extend(self, items):
        pos = len(self.__subject__)
        self.__recorder.extend({'action': 'create',
                                'path': self.__path+[pos+i],
                                'value': item}
                               for i, item in enumerate(items))
        return self.__subject__.extend(items)

    def __real_pos(self, pos):
        if pos < 0:
            pos = len(self.__subject__)+pos
        return max(0, min(pos, len(self.__subject__)))

    def insert(self, pos, item):
        pos = self.__real_pos(pos)
        self.__recorder.append({'action': 'create',
                                'path': self.__path+[pos],
                                'value': item})
        return self.__subject__.insert(pos, item)

    def pop(self, pos=-1):
        pos = self.__real_pos(pos)
        try:
            item = self.__subject__.pop(pos)
        except IndexError:
            raise
        self.__recorder.append({'action': 'remove',
                                'path': self.__path+[pos]})
        return item

    def remove(self, item):
        pos = self.index(item)
        self.__recorder.append({'action': 'remove',
                         'path': self.__path + [pos]})
        return self.__subject__.remove(item)

    def reverse(self, *a, **k):
        raise NotImplementedError()

    def sort(self, *a, **k):
        raise NotImplementedError()

