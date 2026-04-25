from tt import TranspositionTable, EXACT, LOWER, UPPER

def test_store_and_probe_exact():
    tt = TranspositionTable()
    tt.store(12345, depth=3, flag=EXACT, score=100, best_move=None)
    result = tt.probe(12345)
    assert result == (3, EXACT, 100, None)

def test_probe_miss_returns_none():
    tt = TranspositionTable()
    assert tt.probe(99999) is None

def test_overwrite_on_collision():
    tt = TranspositionTable()
    tt.store(1, depth=2, flag=LOWER, score=50, best_move=None)
    tt.store(1, depth=4, flag=EXACT, score=75, best_move=None)
    result = tt.probe(1)
    assert result == (4, EXACT, 75, None)

def test_clear_removes_all_entries():
    tt = TranspositionTable()
    tt.store(1, depth=3, flag=EXACT, score=100, best_move=None)
    tt.store(2, depth=2, flag=LOWER, score=50, best_move=None)
    tt.clear()
    assert tt.probe(1) is None
    assert tt.probe(2) is None

def test_flag_constants_are_distinct():
    assert len({EXACT, LOWER, UPPER}) == 3
