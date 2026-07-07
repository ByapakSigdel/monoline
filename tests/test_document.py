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


from monoline.bitmap import Bitmap


BM1 = Bitmap(80, 40, {(0, 0): (255, "#ffffff")})
BM2 = Bitmap(80, 40, {(1, 1): (1, "#ff0000")})


def test_set_bitmap_undo_redo():
    doc = Document(80, 40)
    doc.set_bitmap(BM1)
    assert doc.bitmap is BM1 and doc.dirty is True
    doc.set_bitmap(BM2)  # replace
    assert doc.bitmap is BM2
    doc.undo()
    assert doc.bitmap is BM1
    doc.undo()
    assert doc.bitmap is None
    doc.redo()
    assert doc.bitmap is BM1
    doc.redo()
    assert doc.bitmap is BM2


def test_set_bitmap_none_when_none_is_noop():
    doc = Document(80, 40)
    doc.set_bitmap(None)
    assert doc.undo() is False


def test_set_bitmap_remove_is_undoable():
    doc = Document(80, 40)
    doc.set_bitmap(BM1)
    doc.set_bitmap(None)
    assert doc.bitmap is None
    doc.undo()
    assert doc.bitmap is BM1


def test_clear_takes_bitmap_and_strokes_one_op():
    doc = Document(80, 40)
    doc.add_strokes([stroke((0, 0), (1, 1))])
    doc.set_bitmap(BM1)
    doc.clear()
    assert doc.strokes == [] and doc.bitmap is None
    doc.undo()
    assert len(doc.strokes) == 1 and doc.bitmap is BM1


def test_clear_bitmap_only_not_noop():
    doc = Document(80, 40)
    doc.set_bitmap(BM1)
    doc.clear()
    assert doc.bitmap is None
    doc.undo()
    assert doc.bitmap is BM1


def test_set_bitmap_clears_redo():
    doc = Document(80, 40)
    doc.add_strokes([stroke((0, 0))])
    doc.undo()
    doc.set_bitmap(BM1)
    assert doc.redo() is False
