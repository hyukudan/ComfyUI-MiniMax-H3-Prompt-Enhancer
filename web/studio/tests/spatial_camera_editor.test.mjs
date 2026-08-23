import test from "node:test";
import assert from "node:assert/strict";

import {
    addSpatialWaypoint,
    aimAnglesForTarget,
    cameraAimTarget,
    cameraDistanceLabel,
    cameraHorizontalDistance,
    cameraIconRotation,
    defaultSpatialWaypoints,
    interpolateSpatialWaypoint,
    normalizeSpatialWaypoints,
    projectCameraPoint,
    redistributeSpatialWaypointTiming,
    stagedAimPoint,
    spatialPathD,
    setCameraHorizontalDistance,
    unprojectCameraPoint,
} from "../spatial_camera_editor.js";

test("camera distance moves only across the floor and never changes height", () => {
    const point = { x: .3, y: .85, z: .4 };
    assert.equal(cameraHorizontalDistance(point), .5);
    assert.equal(cameraDistanceLabel(.5), "Medium distance");
    setCameraHorizontalDistance(point, 1);
    assert.deepEqual(point, { x: .6, y: .85, z: .8 });
    assert.equal(cameraHorizontalDistance(point), 1);
    setCameraHorizontalDistance(point, 0);
    assert.deepEqual(point, { x: 0, y: .85, z: 0 });
});

test("spatial camera defaults are a valid normalized two-point timeline", () => {
    const points = defaultSpatialWaypoints();
    assert.equal(points.length, 2);
    assert.equal(points[0].at, 0);
    assert.equal(points.at(-1).at, 1);
    assert.ok(points.every((point) => point.y === 0), "untouched camera paths must not author vertical motion");
    assert.ok(points.every((point) => [point.x, point.y, point.z].every((value) => value >= -1 && value <= 1)));
});

test("camera icons distinguish anchor, travel and custom aim", () => {
    const points = [
        { id: "a", at: 0, x: -.8, y: 0, z: .5, aimMode: "anchor" },
        { id: "b", at: .5, x: 0, y: 0, z: 0, aimMode: "travel" },
        { id: "c", at: 1, x: .8, y: 0, z: 0, aimMode: "custom", panDegrees: 135 },
    ];
    assert.notEqual(cameraIconRotation(points, 0, "top"), 0);
    assert.equal(cameraIconRotation(points, 1, "top"), 0);
    assert.equal(cameraIconRotation(points, 2, "top"), 33.06);
});

test("dragged aim targets convert back to pan and tilt without confusing camera position", () => {
    const camera = { x: -.4, y: .1, z: .2 };
    const right = aimAnglesForTarget(camera, { x: .6, y: .1, z: .2 });
    const up = aimAnglesForTarget(camera, { x: -.4, y: 1.1, z: .2 });
    assert.deepEqual(right, { panDegrees: 90, tiltDegrees: 0 });
    assert.deepEqual(up, { panDegrees: 180, tiltDegrees: 90 });
    assert.equal(camera.x, -.4);
    assert.equal(camera.y, .1);
    assert.equal(camera.z, .2);
});

test("custom aim target moves to the requested side and elevation", () => {
    const origin = { id: "a", at: 0, x: 0, y: 0, z: 0, aimMode: "custom" };
    const right = cameraAimTarget([{ ...origin, panDegrees: 90, tiltDegrees: 0 }], 0);
    const up = cameraAimTarget([{ ...origin, panDegrees: 0, tiltDegrees: 90 }], 0);
    assert.ok(right.x > .7);
    assert.ok(Math.abs(right.y) < .001);
    assert.ok(up.y > .7);
    assert.ok(Math.abs(up.x) < .001);
    assert.ok(projectCameraPoint(right, "top").x > projectCameraPoint(origin, "top").x);
    assert.ok(projectCameraPoint(up, "front").y < projectCameraPoint(origin, "front").y);
});

test("travel aim at the final point continues forward instead of turning backwards", () => {
    const points = [
        { id: "a", at: 0, x: -.5, y: 0, z: .5, aimMode: "travel" },
        { id: "b", at: 1, x: .5, y: .2, z: -.5, aimMode: "travel" },
    ];
    assert.deepEqual(cameraAimTarget(points, 1), { x: 1.5, y: .4, z: -1.5 });
    assert.equal(cameraIconRotation(points, 0, "top"), cameraIconRotation(points, 1, "top"));
});

test("playback interpolation follows waypoint timing instead of point index", () => {
    const point = interpolateSpatialWaypoint([
        { id: "a", at: 0, x: -1, y: 0, z: 1 },
        { id: "b", at: .25, x: 0, y: 1, z: 0 },
        { id: "c", at: 1, x: 1, y: 0, z: -1 },
    ], .625);
    assert.deepEqual(point, { at: .625, x: .5, y: .5, z: -.5 });
});

test("projection round-trips draggable axes in isometric, top and front views", () => {
    const point = { x: .35, y: -.2, z: .42 };
    for (const view of ["perspective", "top"]) {
        const projected = projectCameraPoint(point, view);
        const result = unprojectCameraPoint(projected, point, view);
        assert.equal(result.x, point.x);
        assert.equal(result.z, point.z);
    }
    const front = unprojectCameraPoint(projectCameraPoint(point, "front"), point, "front");
    assert.equal(front.x, point.x);
    assert.equal(front.y, point.y);
});

test("isometric platform stays a four-corner plane and elevation moves vertically", () => {
    const corners = [
        projectCameraPoint({ x: -1, y: 0, z: -1 }), projectCameraPoint({ x: 1, y: 0, z: -1 }),
        projectCameraPoint({ x: 1, y: 0, z: 1 }), projectCameraPoint({ x: -1, y: 0, z: 1 }),
    ];
    assert.equal(new Set(corners.map((point) => `${point.x},${point.y}`)).size, 4);
    const ground = projectCameraPoint({ x: .2, y: 0, z: -.3 });
    const raised = projectCameraPoint({ x: .2, y: .6, z: -.3 });
    assert.equal(ground.x, raised.x);
    assert.ok(raised.y < ground.y);
});

test("adding a waypoint interpolates position and timing without exceeding six", () => {
    let points = defaultSpatialWaypoints();
    points = addSpatialWaypoint(points, 0);
    assert.equal(points.length, 3);
    assert.equal(points[1].at, .5);
    while (points.length < 6) points = addSpatialWaypoint(points, 0);
    assert.equal(addSpatialWaypoint(points, 0).length, 6);
});

test("adding a waypoint inherits the previous named aim target atomically", () => {
    const points = [
        { id: "a", at: 0, x: -1, y: 0, z: 1, aimMode: "target", aimTarget: { kind: "subject", id: "olivia" } },
        { id: "b", at: 1, x: 1, y: 0, z: -1, aimMode: "travel" },
    ];
    const added = addSpatialWaypoint(points, 0);
    assert.equal(added[1].aimMode, "target");
    assert.deepEqual(added[1].aimTarget, { kind: "subject", id: "olivia" });
    assert.notEqual(added[1].aimTarget, points[0].aimTarget);
});

test("named aim resolves staged subject motion relative to the path anchor", () => {
    const shot = { staging: [
        { subjectId: "juan", start: { x: -.5, y: 0, z: 0 }, end: { x: 0, y: 0, z: .5 }, movement: "walks" },
        { subjectId: "olivia", start: { x: .5, y: 0, z: 0 }, end: { x: .8, y: .2, z: -.2 }, movement: "walks" },
    ] };
    const path = { coordinateSpace: "subject", anchorTarget: { kind: "subject", id: "juan" } };
    const point = stagedAimPoint(shot, path, { at: .5, aimMode: "target", aimTarget: { kind: "subject", id: "olivia" } });
    assert.deepEqual(point, { x: .9, y: .1, z: -.35 });
});

test("adding from the final camera inserts into the preceding span instead of creating a 99-to-100-percent leg", () => {
    const points = [
        { id: "a", at: 0, x: -1, y: 0, z: 1 },
        { id: "b", at: 1, x: 1, y: 0, z: -1 },
    ];
    const added = addSpatialWaypoint(points, 1);
    assert.deepEqual(added.map((point) => point.at), [0, .5, 1]);
    assert.equal(added[1].x, 0);
    assert.equal(added[1].z, 0);
});

test("compressed legacy waypoint timing can be repaired explicitly", () => {
    const repaired = redistributeSpatialWaypointTiming([
        { id: "a", at: 0 }, { id: "b", at: .99 }, { id: "c", at: 1 },
    ]);
    assert.deepEqual(repaired.map((point) => point.at), [0, .5, 1]);
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
