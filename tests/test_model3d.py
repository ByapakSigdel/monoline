import pytest

from monoline.model3d import (
    ModelPose,
    is_model_path,
    load_mesh,
    render_model,
)


@pytest.fixture
def triangle_obj(tmp_path):
    p = tmp_path / "tri.obj"
    p.write_text(
        "v 0 0 0\n"
        "v 1 0 0\n"
        "v 0 1 0\n"
        "f 1 2 3\n",
        encoding="utf-8",
    )
    return str(p)


def test_is_model_path():
    assert is_model_path("mesh.obj") is True
    assert is_model_path("mesh.png") is False


def test_load_mesh_obj(triangle_obj):
    vertices, faces = load_mesh(triangle_obj)
    assert len(vertices) == 3
    assert faces == [(0, 1, 2)]


def test_render_model_produces_cells(triangle_obj):
    vertices, faces = load_mesh(triangle_obj)
    bm = render_model(vertices, faces, ModelPose(), 40, 40,
                      "#292e42", "#7aa2f7")
    assert bm.width == 40
    assert bm.height == 40
    assert bm.cells


def test_render_model_respects_pose(triangle_obj):
    vertices, faces = load_mesh(triangle_obj)
    base = render_model(vertices, faces, ModelPose(), 40, 40,
                        "#292e42", "#7aa2f7")
    moved = render_model(vertices, faces, ModelPose(yaw=0.8, pan_x=10), 40, 40,
                         "#292e42", "#7aa2f7")
    assert base.cells != moved.cells
