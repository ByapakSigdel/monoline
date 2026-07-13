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
from monoline.model3d import Model3DState


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


def test_set_video_clears_bitmap():
    doc = Document(80, 40)
    doc.set_bitmap(BM1)
    doc.set_video("/tmp/clip.mp4")
    assert doc.bitmap is None
    assert doc.video_path == "/tmp/clip.mp4"
    assert doc.playback_bitmap is None


def test_set_bitmap_clears_video():
    doc = Document(80, 40)
    doc.set_video("/tmp/clip.mp4")
    doc.set_bitmap(BM1)
    assert doc.video_path is None
    assert doc.bitmap is BM1


def test_set_video_undo_redo():
    doc = Document(80, 40)
    doc.set_video("/tmp/a.mp4")
    doc.set_video("/tmp/b.mp4")
    doc.undo()
    assert doc.video_path == "/tmp/a.mp4"
    doc.undo()
    assert doc.video_path is None
    doc.redo()
    assert doc.video_path == "/tmp/a.mp4"


def test_display_bitmap_prefers_playback():
    doc = Document(80, 40)
    doc.set_bitmap(BM1)
    live = Bitmap(80, 40, {(2, 2): (255, "#0000ff")})
    doc.set_playback_bitmap(live)
    assert doc.display_bitmap is live


def test_clear_removes_video():
    doc = Document(80, 40)
    doc.set_video("/tmp/a.mp4")
    doc.clear()
    assert doc.video_path is None
    doc.undo()
    assert doc.video_path == "/tmp/a.mp4"


def test_set_model3d_clears_bitmap():
    doc = Document(80, 40)
    doc.set_bitmap(BM1)
    doc.set_model3d(Model3DState(path="/tmp/m.obj"))
    assert doc.bitmap is None
    assert doc.model3d is not None


def test_set_model3d_undo_redo():
    from monoline.model3d import Model3DState
    doc = Document(80, 40)
    doc.set_model3d(Model3DState(path="/tmp/a.obj"))
    doc.undo()
    assert doc.model3d is None
    doc.redo()
    assert doc.model3d.path == "/tmp/a.obj"


def test_display_bitmap_prefers_model():
    doc = Document(80, 40)
    doc.set_bitmap(BM1)
    live = Bitmap(80, 40, {(2, 2): (255, "#0000ff")})
    doc.set_model_bitmap(live)
    assert doc.display_bitmap is live
