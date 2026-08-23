import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
    cameraAnnotationLayout, cameraInstructionPreview, cameraSceneModel, parseCameraFragment, setVisualCameraMotion,
    VISUAL_CAMERA_MOTIONS,
} from "../camera_planner.js";
import { cameraElevationLabel, cameraVerticalSegment } from "../spatial_camera_editor.js";

test("camera elevation fixture keeps UI bands and segment direction in parity", async () => {
    const fixture = JSON.parse(await readFile(new URL("../../../docs/fixtures/camera_elevation_bands.json", import.meta.url), "utf8"));
    for (const row of fixture.bands) assert.equal(cameraElevationLabel(row.value), row.label);
    for (const row of fixture.segments) {
        const segment = cameraVerticalSegment(row.from, row.to);
        assert.equal(segment.kind, row.kind);
        assert.equal(segment.direction, row.direction);
        assert.equal(segment.crossedEyeLine, row.crossedEyeLine);
    }
});

test("camera height UI exposes semantic accessibility copy instead of only raw numbers", async () => {
    const editor = await readFile(new URL("../spatial_camera_editor.js", import.meta.url), "utf8");
    assert.match(editor, /aria-valuetext/);
    assert.match(editor, /Camera height/);
    assert.match(editor, /moves the camera body; Aim controls where the lens points/);
    assert.match(editor, /Very low\s+·\s+Low\s+·\s+Eye level\s+·\s+Elevated\s+·\s+Very elevated/);
});

test("camera elevation uses understandable bands and is present in the H3 preview", () => {
    assert.equal(cameraElevationLabel(1), "Very elevated");
    assert.equal(cameraElevationLabel(0), "Eye level");
    assert.equal(cameraElevationLabel(-1), "Very low");
    const preview = cameraInstructionPreview({ cameraPath: {
        motionType: "tracking", waypoints: [
            { at: 0, x: 0, y: 1, z: 1 },
            { at: 1, x: 0, y: -1, z: -1 },
        ],
    } });
    assert.match(preview, /very elevated/);
    assert.match(preview, /very low/);
});

test("camera preview states vertical transitions instead of leaving the LLM to infer them", () => {
    const preview = cameraInstructionPreview({ cameraPath: {
        motionType: "tracking", waypoints: [
            { at: 0, x: -.72, y: 1, z: .62 },
            { at: .5, x: -.2, y: .52, z: -.29 },
            { at: 1, x: .79, y: -.85, z: -.45 },
        ],
    } });
    assert.match(preview, /descending clearly from very elevated to elevated/);
    assert.match(preview, /continuing to descend steeply from elevated to very low/);
    assert.doesNotMatch(preview, /rising/);
});

test("camera preview changes direction when a later waypoint rises again", () => {
    const preview = cameraInstructionPreview({ cameraPath: {
        motionType: "tracking", waypoints: [
            { at: 0, x: 0, y: .8, z: 0 },
            { at: .5, x: 0, y: -.4, z: 0 },
            { at: 1, x: 0, y: .2, z: 0 },
        ],
    } });
    assert.match(preview, /descending steeply from very elevated to low/);
    assert.match(preview, /rising clearly from low to elevated/);
    assert.doesNotMatch(preview, /continuing to descend/);
});

test("visual camera catalog covers every shot-plan v2 motion without brand vocabulary", () => {
    const tokens = VISUAL_CAMERA_MOTIONS.flatMap((group) => group.items.map(([token]) => token));
    assert.deepEqual(new Set(tokens), new Set([
        "static", "zoom_in", "zoom_out", "push_in", "pull_out", "pan_left", "pan_right",
        "truck_left", "truck_right", "tilt_up", "tilt_down", "pedestal_up", "pedestal_down",
        "arc", "tracking", "shake", "roll_clockwise", "roll_counterclockwise",
    ]));
    assert.doesNotMatch(JSON.stringify(VISUAL_CAMERA_MOTIONS), /disney|pixar|ghibli|wes anderson/i);
});

test("camera scene model distinguishes spatial, optical and orientation paths", () => {
    const dolly = cameraSceneModel({ cameraPath: { motionType: "push_in" } });
    const zoom = cameraSceneModel({ cameraPath: { motionType: "zoom_in" } });
    const pan = cameraSceneModel({ cameraPath: { motionType: "pan_left" } });
    const orbit = cameraSceneModel({ cameraPath: { motionType: "arc" } });
    assert.equal(dolly.kind, "spatial");
    assert.notDeepEqual(dolly.start, dolly.end);
    assert.equal(zoom.kind, "optical");
    assert.deepEqual(zoom.start, zoom.end);
    assert.equal(pan.kind, "orientation");
    assert.match(orbit.path, /Q/);
});

test("camera annotations keep phase and footer labels in separate geometry at narrow width", () => {
    const push = cameraSceneModel({ cameraStart: { framing: "medium" }, cameraPath: { motionType: "push_in" } });
    assert.deepEqual(cameraAnnotationLayout(push), {
        start: { x: 76, y: 198, textAnchor: "middle" },
        end: { x: 120, y: 98, textAnchor: "middle" },
        axes: {
            left: { x: 24, y: 220, textAnchor: "start" },
            right: { x: 336, y: 220, textAnchor: "end" },
        },
        notePlacement: "below-svg",
    });
    for (const motionType of ["push_in", "pull_out", "truck_left", "truck_right", "pedestal_up", "pedestal_down", "arc", "tracking"]) {
        const layout = cameraAnnotationLayout(cameraSceneModel({ cameraPath: { motionType } }));
        assert.ok(Math.abs(layout.start.y - layout.end.y) >= 32, `${motionType} phase labels need vertical separation`);
        assert.ok(layout.start.x >= 52 && layout.start.x <= 308);
        assert.ok(layout.end.x >= 52 && layout.end.x <= 308);
        assert.equal(layout.notePlacement, "below-svg");
    }
});

test("visual motion edits only the existing cameraPath v2 slice", () => {
    const shot = { id: "s1", generationId: "g1", action: "Runs", cameraPath: { motionType: "push_in", speed: "slow", easing: "ease_out" } };
    setVisualCameraMotion(shot, "truck_left");
    assert.deepEqual(shot.cameraPath, { motionType: "truck_left", speed: "slow", easing: "ease_out" });
    setVisualCameraMotion(shot, "static");
    assert.deepEqual(shot.cameraPath, { motionType: "static" });
    setVisualCameraMotion(shot, "");
    assert.equal(shot.cameraPath, undefined);
    assert.equal(shot.action, "Runs");
});

test("prompt preview makes inheritance and H3 camera phases understandable", () => {
    const preview = cameraInstructionPreview({
        cameraStart: { framing: "wide", angle: "eye_level" },
        cameraPath: { motionType: "push_in", amplitude: "small", speed: "slow", timing: "during_action" },
        cameraEnd: { framing: "close_up" },
    });
    assert.match(preview, /Start: Wide, Eye level/);
    assert.match(preview, /Dolly in, small travel, slow pace, during action/);
    assert.match(preview, /End: Close up, Eye level/);
});

test("advanced text fallback stays scoped to the three existing camera v2 objects", () => {
    const valid = parseCameraFragment(JSON.stringify({ cameraStart: { framing: "wide" }, cameraPath: { motionType: "arc", speed: "slow" }, cameraEnd: { framing: "medium" } }));
    assert.equal(valid.ok, true);
    assert.equal(parseCameraFragment('{"cameraPath":{"motionType":"fly"}}').ok, false);
    assert.equal(parseCameraFragment('{"cameraRig":"crane"}').ok, false);
    assert.equal(parseCameraFragment('{"cameraPath":{"motionType":"static","speed":"slow"}}').ok, false);
    assert.equal(parseCameraFragment('{"cameraStart":{"framing":"cinematic"}}').ok, false);
    assert.equal(parseCameraFragment('{"cameraEnd":{"target":{"kind":"subject","id":"s1"}}}').ok, false);
});

test("planner responsiveness follows its editor column instead of the full Studio panel", async () => {
    const styles = await readFile(new URL("../camera_planner_styles.js", import.meta.url), "utf8");
    assert.match(styles, /container: h3-camera-planner \/ inline-size/);
    assert.match(styles, /@container h3-camera-planner \(min-width: 680px\)/);
    assert.doesNotMatch(styles, /@container h3-studio-panel/);
    assert.doesNotMatch(styles, /\.minimax-h3-camera-stage-note\s*\{[^}]*position:\s*absolute/s);
    assert.doesNotMatch(styles, /minimax-h3-spatial-camera-glyph[^}]*transform-origin/s);
    assert.match(styles, /minimax-h3-spatial-camera-body/);
    assert.match(styles, /minimax-h3-spatial-camera-front/);
});
