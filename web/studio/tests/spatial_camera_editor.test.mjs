import test from "node:test";
import assert from "node:assert/strict";

import {
    addSpatialWaypoint,
    defaultSpatialWaypoints,
    normalizeSpatialWaypoints,
    projectCameraPoint,
    spatialPathD,
    unprojectCameraPoint,
} from "../spatial_camera_editor.js";

test("spatial camera defaults are a valid normalized two-point timeline", () => {
    const points = defaultSpatialWaypoints();
    assert.equal(points.length, 2);
    assert.equal(points[0].at, 0);
    assert.equal(points.at(-1).at, 1);
    assert.ok(points.every((point) => [point.x, point.y, point.z].every((value) => value >= -1 && value <= 1)));
});

test("projection round-trips draggable axes in perspective and top views", () => {
    const point = { x: .35, y: -.2, z: .42 };
    for (const view of ["perspective", "top"]) {
        const projected = projectCameraPoint(point, view);
        const result = unprojectCameraPoint(projected, point, view);
        assert.equal(result.x, point.x);
        assert.equal(result.z, point.z);
    }
});

test("adding a waypoint interpolates position and timing without exceeding six", () => {
    let points = defaultSpatialWaypoints();
    points = addSpatialWaypoint(points, 0);
    assert.equal(points.length, 3);
    assert.equal(points[1].at, .5);
    while (points.length < 6) points = addSpatialWaypoint(points, 0);
    assert.equal(addSpatialWaypoint(points, 0).length, 6);
});

test("normalization clamps coordinates and preserves fixed timeline ends", () => {
    const points = normalizeSpatialWaypoints([
        { id: "a", at: .2, x: -9, y: 4, z: 0 },
        { id: "b", at: .8, x: 9, y: -4, z: 0 },
    ]);
    assert.deepEqual(points.map((point) => point.at), [0, 1]);
    assert.equal(points[0].x, -1);
    assert.equal(points[1].y, -1);
});

test("path rendering distinguishes straight and curved trajectories", () => {
    const points = [
        { x: -.5, y: 0, z: .5 }, { x: 0, y: .2, z: 0 }, { x: .5, y: 0, z: -.5 },
    ];
    assert.match(spatialPathD(points, "perspective", "straight"), / L /);
    assert.match(spatialPathD(points, "perspective", "smooth"), / Q /);
    assert.notEqual(spatialPathD(points, "top", "arc_left"), spatialPathD(points, "top", "arc_right"));
});
