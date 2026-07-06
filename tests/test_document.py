from monoline.document import Document, Stroke


def stroke(*pts):
    return Stroke(points=list(pts))


def test_add_strokes_appends_and_marks_dirty():
    doc = Document(80, 40)
    assert doc.dirty is False
    doc.add_strokes([stroke((1.0, 1.0), (2.0, 2.0))])
    assert len(doc.strokes) == 1
    assert doc.dirty is True


def test_undo_removes_whole_group():
    doc = Document(80, 40)
    doc.add_strokes([stroke((0, 0)), stroke((1, 1))])  # symmetry pair
    doc.add_strokes([stroke((2, 2))])
    assert doc.undo() is True
    assert len(doc.strokes) == 2
    assert doc.undo() is True
    assert doc.strokes == []
    assert doc.undo() is False


def test_redo_restores_and_new_op_clears_redo():
    doc = Document(80, 40)
    doc.add_strokes([stroke((0, 0))])
    doc.undo()
    assert doc.redo() is True
    assert len(doc.strokes) == 1
    doc.undo()
    doc.add_strokes([stroke((5, 5))])
    assert doc.redo() is False


def test_clear_and_undo_clear():
    doc = Document(80, 40)
    doc.add_strokes([stroke((0, 0)), stroke((1, 1))])
    doc.clear()
    assert doc.strokes == []
    doc.undo()
    assert len(doc.strokes) == 2


def test_clear_empty_is_noop():
    doc = Document(80, 40)
    doc.clear()
    assert doc.undo() is False
