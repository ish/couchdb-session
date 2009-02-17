import itertools
import uuid
import couchdb

from couchdbsession import a8n


class Session(object):

    tracker_factory = a8n.Tracker

    def __init__(self, db, pre_flush_hook=None, post_flush_hook=None,
                 encode_doc=None, decode_doc=None):
        self._db = db
        self._pre_flush_hook = pre_flush_hook
        self._post_flush_hook = post_flush_hook
        self._encode_doc = encode_doc
        self._decode_doc = decode_doc
        self.reset()

    #- Additional magic methods.

    def __getattr__(self, name):
        return getattr(self._db, name)

    #- Override couchdb.Database methods.

    def __iter__(self):
        # XXX Not entirely sure why we need this as all we're doing if passing
        # on the call but without it a magic method called __length_hint__ is
        # called, followed soon after by an exception from couchdb.
        return iter(self._db)

    def __len__(self):
        return len(self._db)

    def __delitem__(self, id):
        # XXX Really not sure this is a good way to delete a document, i.e.
        # without specifying the _rev, but I'll reluctantly support it because
        # the underlying database does.
        self.delete(self[id])

    def __getitem__(self, id):
        doc = self.get(id)
        if doc is None:
            raise couchdb.ResourceNotFound()
        return doc

    def __setitem__(self, id, content):
        # Ignore docs with a _rev, we should already be tracking changes to it
        # if it's been changed.
        if '_rev' in content:
            return
        doc = dict(content)
        doc['_id'] = id
        self.create(doc)

    def create(self, doc):
        # XXX Note: Session's create() has slightly different semantics to
        # couchdb-python.
        # In couchdb-python the doc id is returned and the doc dict is left
        # untouched. Here, we need to cache the document so get() and
        # __getitem__() work as expected but the document returned from those
        # should contain and id.
        # The choice was to store a copy of the doc dict, with the id added, in
        # the cache or simple update the doc dict with an id and store the doc
        # dict itself in the cache.
        # deepcopy is not a very nice thing to use so, in the end the decision
        # was to store the doc dict dict in the cache.
        if '_id' not in doc:
            doc['_id'] = uuid.uuid4().hex
        self._created.add(doc['_id'])
        return self._cached(doc)['_id']

    def delete(self, doc):
        if doc['_id'] in self._created:
            self._created.remove(doc['_id'])
        else:
            self._changed.discard(doc['_id'])
            self._deleted[doc['_id']] = doc
        del self._cache[doc['_id']]

    def get(self, id, default=None, **options):
        # Try cache first.
        doc = self._cache.get(id)
        if doc is not None:
            return doc
        if id in self._deleted:
            return None
        # Ask CouchDB and cache the response (if found).
        doc = self._db.get(id, default, **options)
        if doc is default:
            return doc
        doc = self.decode_doc(doc)
        return self._tracked_and_cached(doc)

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

    #- Additional methods.

    def encode_doc(self, doc):
        """
        Encode document hook, called whenever a doc is sent to the CouchDB.
        """
        if self._encode_doc:
            return self._encode_doc(doc)
        return doc

    def decode_doc(self, doc):
        """
        Decode document hook, called whenever a doc is retrieved from the
        CouchDB.
        """
        if self._decode_doc:
            return self._decode_doc(doc)
        return doc

    def reset(self):
        """
        Reset the session, forgetting everything it knows.
        """
        self._trackers = {}
        self._cache = {}
        self._created = set()
        self._changed = set()
        self._deleted = {}

    def flush(self):

        # XXX Due to a bug in CouchDB (see issue COUCHDB-188) we can't do
        # deletions at the same time as additions if the list of updates
        # includes a delete and create for the same id. For now, let's keep
        # deletions out of the general updates list and make two calls to the
        # backend.

        while True:
            # Freeze the session and break out of the loop if there's nothing
            # to do.
            deleted, created, changed = self._pre_flush()
            if not (deleted or created or changed):
                break
            # Build a list of deletions.
            deletions = [{'_id': id, '_rev': doc['_rev'], '_deleted': True}
                         for (id, doc) in deleted.iteritems()]
            # Build a list of other updates. Note that we get the subject out of
            # changed documents; they're the only docs that will be wrapped in a8n
            # tracking proxies.
            # XXX It might be nicer if the cache only ever contains the real
            # document to avoid having to know about the __subject__ stuff.
            additions = (self._cache[doc_id] for doc_id in created)
            changes = (self._cache[doc_id].__subject__ for doc_id in changed)
            updates = itertools.chain(additions, changes)
            updates = (self.encode_doc(doc) for doc in updates)
            updates = list(updates)
            # Send deletions and clean up cache.
            if deletions:
                self._db.update(deletions)
            # Perform updates and fix up the cache with the new _revs.
            if updates:
                for response in self._db.update(updates):
                    self._cache[response['_id']]['_rev'] = response['_rev']
            # Reset internal tracking now everything's been written.
            self._post_flush(deleted, created, changed)

    def pre_flush_hook(self, deletions, additions, changes):
        if self._pre_flush_hook is not None:
            self._pre_flush_hook(self, deletions, additions, changes)

    def post_flush_hook(self, deletions, additions, changes):
        if self._post_flush_hook is not None:
            self._post_flush_hook(self, deletions, additions, changes)

    #- Internal methods.

    def _tracked_and_cached(self, doc):
        def callback():
            self._changed.add(doc['_id'])
        tracker = self.tracker_factory(callback)
        doc = tracker.track(doc)
        self._trackers[doc['_id']] = tracker
        return self._cached(doc)

    def _cached(self, doc):
        self._cache[doc['_id']] = doc
        return doc

    def _freeze(self):
        deleted, self._deleted = self._deleted, {}
        created, self._created = self._created, set()
        changed, self._changed = self._changed, set()
        return deleted, created, changed

    def _pre_flush(self):

        all_deleted = {}
        all_created = set()
        all_changed = set()

        while True:
            deleted, created, changed = self._freeze()
            if not (deleted or created or changed):
                break
            all_deleted.update(deleted)
            all_created.update(created)
            all_changed.update(changed)
            def gen_deletions():
                return deleted.itervalues()
            def gen_additions():
                return (self._cache[doc_id] for doc_id in created)
            def gen_changes():
                changes = (self._cache[doc_id] for doc_id in changed)
                changes = ((doc, iter(self._trackers[doc['_id']])) for doc in changes)
                return changes
            self.pre_flush_hook(gen_deletions(), gen_additions(), gen_changes())

        return all_deleted, all_created, all_changed

    def _post_flush(self, deleted, created, changed):
        actions_by_doc = dict((doc_id, self._trackers[doc_id].freeze())
                              for doc_id in changed)
        def gen_deletions():
            return deleted.itervalues()
        def gen_additions():
            return (self._cache[doc_id] for doc_id in created)
        def gen_changes():
            changes = (self._cache[doc_id] for doc_id in changed)
            changes = ((doc, actions_by_doc[doc['_id']]) for doc in changes)
            return changes
        self.post_flush_hook(gen_deletions(), gen_additions(), gen_changes())


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

    @property
    def rows(self):
        return [SessionRow(self._session, row) for row in self._view_results.rows]


class SessionRow(object):

    def __init__(self, session, row):
        self._session = session
        self._row = row

    def __getattr__(self, name):
        return getattr(self._row, name)

    @property
    def doc(self):
        doc = self._row.doc
        if doc is not None:
            cached = self._session._cache.get(doc['_id'])
            if cached is not None:
                return cached
            doc = self._session.decode_doc(doc)
            return self._session._tracked_and_cached(doc)

