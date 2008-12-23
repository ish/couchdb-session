import UserDict
from peak.util.proxies import ObjectWrapper
from couchdb.client import Document as CouchDBDocument


def wrap(obj, modified):
    if isinstance(obj, CouchDBDocument):
        return Document(obj, modified)
    elif isinstance(obj, dict):
        return Dictionary(obj, modified)
    elif isinstance(obj, list):
        return List(obj, modified)
    return obj


class Dictionary(UserDict.DictMixin, ObjectWrapper):

    # TODO:
    #   __contains__(), __iter__(), and iteritems() to improve performance

    __modified = None

    def __init__(self, subject, modified):
        super(Dictionary, self).__init__(subject)
        self.__modified = modified

    def __getitem__(self, *a, **k):
        value = super(Dictionary, self).__getitem__(*a, **k)
        return wrap(value, self.__modified)

    def __setitem__(self, *a, **k):
        self.__modified()
        return super(Dictionary, self).__setitem__(*a, **k)

    def __delitem__(self, *a, **k):
        self.__modified()
        return super(Dictionary, self).__delitem__(*a, **k)

    def keys(self, *a, **k):
        return super(Dictionary, self).keys(*a, **k)


class Document(Dictionary):
    pass


class List(ObjectWrapper):

    __modified = None

    def __init__(self, subject, modified):
        super(List, self).__init__(subject)
        self.__modified = modified

    def __getitem__(self, *a, **k):
        value = self.__subject__.__getitem__(*a, **k)
        return wrap(value, self.__modified)
        
    def __getslice__(self, *a, **k):
        value = self.__subject__.__getslice__(*a, **k)
        return wrap(value, self.__modified)
        
    def __setitem__(self, *a, **k):
        self.__modified()
        return self.__subject__.__setitem__(*a, **k)

    def __delitem__(self, *a, **k):
        self.__modified()
        return self.__subject__.__delitem__(*a, **k)

    def __setslice__(self, *a, **k):
        self.__modified()
        return self.__subject__.__setslice__(*a, **k)

    def __delslice__(self, *a, **k):
        self.__modified()
        return self.__subject__.__delslice__(*a, **k)

    def append(self, *a, **k):
        self.__modified()
        return self.__subject__.append(*a, **k)

    def extend(self, *a, **k):
        self.__modified()
        return self.__subject__.extend(*a, **k)

    def insert(self, *a, **k):
        self.__modified()
        return self.__subject__.insert(*a, **k)

    def pop(self, *a, **k):
        self.__modified()
        return self.__subject__.pop(*a, **k)

    def remove(self, *a, **k):
        self.__modified()
        return self.__subject__.remove(*a, **k)

