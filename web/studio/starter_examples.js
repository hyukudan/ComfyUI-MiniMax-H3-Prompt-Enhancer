export const STARTER_EXAMPLES = Object.freeze([
    {
        id: "camera_move",
        title: "Visual camera move",
        description: "One shot with a three-position subject-relative camera path and playback-ready timing.",
        shotPlan: {
            schemaVersion: 2, timingMode: "auto", shots: [{
                id: "s1", generationId: "g1",
                action: "The subject pauses, notices something beyond frame, then turns toward it.",
                cameraStart: { framing: "medium_wide", angle: "eye_level", viewpoint: "three_quarter" },
                cameraEnd: { framing: "medium_close_up", viewpoint: "profile" },
                cameraPath: {
                    motionType: "arc", amplitude: "medium", speed: "slow", easing: "ease_in_out", timing: "during_action",
                    coordinateSpace: "subject", pathShape: "arc_right", waypoints: [
                        { id: "wp1", at: 0, x: -.8, y: 0, z: .7, framing: "medium_wide", angle: "eye_level" },
                        { id: "wp2", at: .55, x: 0, y: .15, z: .9 },
                        { id: "wp3", at: 1, x: .75, y: 0, z: .45, framing: "medium_close_up", angle: "eye_level" },
                    ],
                },
            }],
        },
    },
    {
        id: "dialogue_beats",
        title: "Dialogue with timed delivery",
        description: "A compact two-shot exchange using visible action beats, delivery and mood.",
        shotPlan: {
            schemaVersion: 2, timingMode: "auto", shots: [{
                id: "s1", generationId: "g1", action: "The first speaker leans closer, keeping their voice restrained.",
                actionBeats: [{ id: "beat1", at: .5, dialogue: { text: "We should leave before dawn.", delivery: "whispers", mood: "urgent but controlled" } }],
                cameraStart: { framing: "medium_close_up", angle: "eye_level" },
            }, {
                id: "s2", generationId: "g1", action: "The second speaker studies them, then gives a small nod.",
                transitionIn: "cut", actionBeats: [{ id: "beat1", at: .65, dialogue: { text: "Then we leave now?", delivery: "asks", mood: "quietly decisive" } }],
                cameraStart: { framing: "close_up", angle: "eye_level" },
            }],
        },
    },
    {
        id: "picture_reference",
        title: "Picture reference contract",
        description: "Shows how a logical reference maps to Picture 1 while the real file remains on the generator node.",
        shotPlan: {
            schemaVersion: 2, timingMode: "auto", shots: [{
                id: "s1", generationId: "g1", action: "The subject enters the scene while preserving the referenced visual identity.",
                referenceUses: [{ assetId: "reference.picture", role: "identity_reinforcement" }],
            }],
        },
        mediaProject: {
            schemaVersion: 2, mode: "i2va",
            assets: [{ id: "reference.picture", type: "picture", name: "Identity reference", available: true, description: "Replace this description with what Picture 1 should preserve." }],
            subjects: [], environments: [], generations: [{
                id: "g1", order: 1, activation: { mode: "auto" },
                bindings: [{ assetId: "reference.picture", slotIndex: 1 }], subjectStates: [], environmentStates: [],
            }],
        },
    },
]);

export function applyStarterExample(controller, example) {
    if (!controller || !example?.shotPlan) return false;
    const shotApplied = controller.replaceShotRaw?.(JSON.stringify(example.shotPlan)) !== false;
    const projectApplied = !example.mediaProject || controller.replaceProjectRaw?.(JSON.stringify(example.mediaProject)) !== false;
    return shotApplied && projectApplied;
}
