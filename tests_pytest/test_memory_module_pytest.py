import pytest
from modules.memory_module import add_memory, retrieve_memories, delete_memory

# Monkeypatch database_manager functions
@pytest.fixture(autouse=True)
def db_mocks(monkeypatch):
    class DummyDB:
        def __init__(self):
            self.storage = []
            self.counter = 1
        def add_memory_db(self, content, user):
            self.storage.append({'id': self.counter, 'content': content, 'user': user})
            self.counter += 1
            return self.counter - 1
        def get_memories_db(self, query, limit):
            if query:
                return [m for m in self.storage if query.lower() in m['content'].lower()][:limit]
            return self.storage[:limit]
        def delete_memory_db(self, memory_id):
            pre = len(self.storage)
            self.storage = [m for m in self.storage if m['id'] != memory_id]
            return len(self.storage) < pre
    db = DummyDB()
    monkeypatch.setattr('modules.memory_module.add_memory_db', db.add_memory_db)
    monkeypatch.setattr('modules.memory_module.get_memories_db', db.get_memories_db)
    monkeypatch.setattr('modules.memory_module.delete_memory_db', db.delete_memory_db)
    return db

def test_add_memory_empty():
    out, ok = add_memory("  ", None)
    assert not ok
    assert "Nie mogę zapisać pustej" in out

def test_add_memory_short():
    out, ok = add_memory("abc", None)
    assert not ok
    assert "zbyt krótkiej" in out

def test_add_memory_duplicate(db_mocks):
    db_mocks.storage = [{'id':1, 'content':'Hello', 'user':'assistant'}]
    out, ok = add_memory("Hello", None)
    assert not ok
    assert "już jest zapisana" in out

def test_add_memory_success(db_mocks):
    out, ok = add_memory("Unique content", None)
    assert ok
    assert "Zapamiętałem" in out
    # storage should contain one
    assert len(db_mocks.storage) == 1

def test_retrieve_memories_none(db_mocks):
    # empty storage
    out, ok = retrieve_memories("", None, user=None)
    assert ok
    assert "Brak zapisanych" in out or "Nie znalazłem" in out

def test_retrieve_memories_single(db_mocks):
    db_mocks.storage = [{'id':1, 'content':'Item1', 'user':'assistant'}]
    out, ok = retrieve_memories("", None, user=None)
    assert ok
    assert "Item1" in out

def test_retrieve_memories_filter(db_mocks):
    db_mocks.storage = [
        {'id':1, 'content':'foo', 'user':'assistant'},
        {'id':2, 'content':'bar', 'user':'assistant'}
    ]
    out, ok = retrieve_memories("bar", None, user=None)
    assert ok
    assert "bar" in out

def test_delete_memory_by_id(db_mocks):
    db_mocks.storage = [{'id':1, 'content':'to del', 'user':'assistant'}]
    out, ok = delete_memory("1", None)
    assert ok
    assert "Zapomniałem" in out
    assert len(db_mocks.storage) == 0

def test_delete_memory_by_content(db_mocks):
    db_mocks.storage = [{'id':2, 'content':'findme', 'user':'assistant'}]
    out, ok = delete_memory("findme", None)
    assert ok
    assert "Zapomniałem" in out
    assert len(db_mocks.storage) == 0

def test_delete_memory_empty(db_mocks):
    out, ok = delete_memory("", None)
    assert not ok or "Nie mam już" in out
