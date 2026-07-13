"""3D model loading and braille rendering. Pure — no TUI imports."""
from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from monoline.bitmap import Bitmap

DOT_BITS: Dict[Tuple[int, int], int] = {
    (0, 0): 0x01, (0, 1): 0x02, (0, 2): 0x04, (1, 0): 0x08,
    (1, 1): 0x10, (1, 2): 0x20, (0, 3): 0x40, (1, 3): 0x80,
}


def _line_dots(a: Tuple[float, float], b: Tuple[float, float]):
    x0, y0 = int(round(a[0])), int(round(a[1]))
    x1, y1 = int(round(b[0])), int(round(b[1]))
    dx, sx = abs(x1 - x0), 1 if x0 < x1 else -1
    dy, sy = -abs(y1 - y0), 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        yield x0, y0
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy

MODEL_SUFFIXES = {".obj", ".stl", ".glb", ".gltf", ".ply", ".off"}

Vec3 = Tuple[float, float, float]
Face = Tuple[int, int, int]


@dataclass
class ModelPose:
    """Orientation and position inside the model viewport."""

    yaw: float = 0.0
    pitch: float = 0.0
    pan_x: float = 0.0
    pan_y: float = 0.0
    zoom: float = 1.0


@dataclass
class Model3DState:
    path: str
    pose: ModelPose = field(default_factory=ModelPose)
    color: str = "#7aa2f7"


def is_model_path(path: str) -> bool:
    return Path(path).suffix.lower() in MODEL_SUFFIXES


def load_mesh(path: str) -> Tuple[List[Vec3], List[Face]]:
    """Load mesh vertices and triangular faces from a 3D file."""
    try:
        import trimesh
    except ImportError as exc:
        raise ValueError("3D import requires trimesh (reinstall monoline)") from exc
    try:
        loaded = trimesh.load(path, force="mesh")
        if isinstance(loaded, trimesh.Scene):
            meshes = [g for g in loaded.geometry.values()
                      if isinstance(g, trimesh.Trimesh)]
            if not meshes:
                raise ValueError(f"no mesh geometry in {path}")
            loaded = trimesh.util.concatenate(meshes)
        if not isinstance(loaded, trimesh.Trimesh) or loaded.vertices is None:
            raise ValueError(f"unsupported 3D file: {path}")
        vertices = loaded.vertices.tolist()
        faces_raw = loaded.faces.tolist()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(str(exc)) from exc
    faces: List[Face] = []
    for face in faces_raw:
        if len(face) == 3:
            faces.append((int(face[0]), int(face[1]), int(face[2])))
        elif len(face) > 3:
            for i in range(1, len(face) - 1):
                faces.append((int(face[0]), int(face[i]), int(face[i + 1])))
    if not vertices or not faces:
        raise ValueError(f"empty mesh: {path}")
    return vertices, faces


def _normalize_vertices(vertices: Sequence[Vec3]) -> List[Vec3]:
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    cz = (min(zs) + max(zs)) / 2
    span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 1e-6)
    scale = 2.0 / span
    return [((v[0] - cx) * scale, (v[1] - cy) * scale, (v[2] - cz) * scale)
            for v in vertices]


def _rotate(v: Vec3, yaw: float, pitch: float) -> Vec3:
    x, y, z = v
    cy, sy = math.cos(yaw), math.sin(yaw)
    x, z = cy * x + sy * z, -sy * x + cy * z
    cx, sx = math.cos(pitch), math.sin(pitch)
    y, z = cx * y - sx * z, sx * y + cx * z
    return (x, y, z)


def _project(v: Vec3, cx: float, cy: float, scale: float) -> Tuple[float, float, float]:
    x, y, z = v
    depth = z + 4.0
    if depth < 0.2:
        depth = 0.2
    factor = scale / depth
    return (cx + x * factor, cy - y * factor, depth)


def _shade(base: str, amount: float) -> str:
    r = int(base[1:3], 16)
    g = int(base[3:5], 16)
    b = int(base[5:7], 16)
    amount = max(0.15, min(1.0, amount))
    return f"#{int(r * amount):02x}{int(g * amount):02x}{int(b * amount):02x}"


def _space_grid_segments() -> List[Tuple[Vec3, Vec3]]:
    """Reference grid and axes for the model viewport."""
    lines: List[Tuple[Vec3, Vec3]] = []
    extent = 1.35
    step = 0.25
    y = -1.05
    pos = -extent
    while pos <= extent + 1e-9:
        lines.append(((-extent, y, pos), (extent, y, pos)))
        lines.append(((pos, y, -extent), (pos, y, extent)))
        pos += step
    lines.append(((0.0, -1.05, 0.0), (0.0, 1.05, 0.0)))   # Y axis
    lines.append(((0.0, y, 0.0), (extent, y, 0.0)))       # X axis
    lines.append(((0.0, y, 0.0), (0.0, y, extent)))       # Z axis
    return lines


def _draw_segment(dots: Dict[Tuple[int, int], Tuple[float, str]],
                  a: Tuple[float, float, float],
                  b: Tuple[float, float, float],
                  color: str) -> None:
    pa = (a[0], a[1])
    pb = (b[0], b[1])
    depth = (a[2] + b[2]) / 2
    for x, y in _line_dots(pa, pb):
        key = (x, y)
        if key not in dots or depth < dots[key][0]:
            dots[key] = (depth, color)


def render_model(vertices: Sequence[Vec3], faces: Sequence[Face], pose: ModelPose,
                 dot_w: int, dot_h: int, grid_color: str, model_color: str) -> Bitmap:
    """Render a mesh into braille cells with a ground grid and depth shading."""
    centered = _normalize_vertices(vertices)
    cx = dot_w / 2 + pose.pan_x
    cy = dot_h / 2 + pose.pan_y
    scale = min(dot_w, dot_h) * 0.22 * pose.zoom
    dots: Dict[Tuple[int, int], Tuple[float, str]] = {}

    def transform(v: Vec3) -> Tuple[float, float, float]:
        return _project(_rotate(v, pose.yaw, pose.pitch), cx, cy, scale)

    for a, b in _space_grid_segments():
        pa, pb = transform(a), transform(b)
        _draw_segment(dots, pa, pb, grid_color)

    projected = [transform(v) for v in centered]
    for i0, i1, i2 in faces:
        p0, p1, p2 = projected[i0], projected[i1], projected[i2]
        v0, v1, v2 = centered[i0], centered[i1], centered[i2]
        e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
        e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
        nx = e1[1] * e2[2] - e1[2] * e2[1]
        ny = e1[2] * e2[0] - e1[0] * e2[2]
        nz = e1[0] * e2[1] - e1[1] * e2[0]
        length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        rn = _rotate((nx / length, ny / length, nz / length), pose.yaw, pose.pitch)
        shade = _shade(model_color, 0.35 + 0.65 * max(0.0, rn[2]))
        _draw_segment(dots, p0, p1, shade)
        _draw_segment(dots, p1, p2, shade)
        _draw_segment(dots, p2, p0, shade)

    bits: Dict[Tuple[int, int], int] = {}
    colors: Dict[Tuple[int, int], str] = {}
    for (x, y), (_, color) in dots.items():
        if not (0 <= x < dot_w and 0 <= y < dot_h):
            continue
        key = (x // 2, y // 4)
        bits[key] = bits.get(key, 0) | DOT_BITS[(x % 2, y % 4)]
        colors[key] = color

    cells = {key: (pattern, colors[key]) for key, pattern in bits.items()}
    return Bitmap(dot_w, dot_h, cells)


def copy_pose(pose: ModelPose) -> ModelPose:
    return deepcopy(pose)
