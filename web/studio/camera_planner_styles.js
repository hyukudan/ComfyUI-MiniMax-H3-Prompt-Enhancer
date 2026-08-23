const STYLE_ID = "minimax-h3-camera-planner-styles";

export function ensureCameraPlannerStyles() {
    if (document.getElementById?.(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
        .minimax-h3-camera-planner {
            display: grid;
            container: h3-camera-planner / inline-size;
            min-width: 0;
            gap: var(--h3-space-3);
            overflow: hidden;
            border: 1px solid color-mix(in srgb, var(--h3-accent) 38%, var(--h3-border));
            border-radius: var(--h3-radius-md);
            background: linear-gradient(145deg, color-mix(in srgb, var(--h3-surface) 92%, var(--h3-accent) 8%), var(--h3-surface));
        }
        .minimax-h3-camera-planner-header {
            display: flex;
            min-width: 0;
            flex-wrap: wrap;
            align-items: flex-start;
            gap: var(--h3-space-2);
            padding: var(--h3-space-3) var(--h3-space-3) 0;
        }
        .minimax-h3-camera-planner-title { min-width: 180px; flex: 1; }
        .minimax-h3-camera-planner-title h3,
        .minimax-h3-camera-planner-title p { margin: 0; }
        .minimax-h3-camera-planner-title p { margin-top: 2px; color: var(--h3-text-muted); font-size: 11.5px; }
        .minimax-h3-camera-planner-badge {
            display: inline-flex;
            min-height: var(--h3-chip-height);
            align-items: center;
            border: 1px solid var(--h3-border-strong);
            border-radius: 999px;
            padding: 1px 8px;
            color: var(--h3-text-muted);
            font-size: 10.5px;
            white-space: nowrap;
        }
        .minimax-h3-camera-stage {
            position: relative;
            min-width: 0;
            margin: 0 var(--h3-space-3);
            overflow: hidden;
            border: 1px solid color-mix(in srgb, var(--h3-accent) 24%, var(--h3-border));
            border-radius: var(--h3-radius-md);
            background:
                radial-gradient(circle at 50% 42%, color-mix(in srgb, var(--h3-accent) 10%, transparent), transparent 36%),
                color-mix(in srgb, var(--h3-bg) 88%, black 12%);
        }
        .minimax-h3-camera-stage svg { display: block; width: 100%; height: auto; min-height: 210px; }
        .minimax-h3-camera-grid-line { stroke: color-mix(in srgb, var(--h3-border-strong) 62%, transparent); stroke-width: 1; }
        .minimax-h3-camera-axis { stroke: color-mix(in srgb, var(--h3-text-muted) 52%, transparent); stroke-width: 1.2; }
        .minimax-h3-camera-trajectory { fill: none; stroke: var(--h3-accent); stroke-width: 4; stroke-linecap: round; stroke-dasharray: 8 6; }
        .minimax-h3-camera-trajectory[data-kind="orientation"] { stroke: var(--h3-tip); stroke-dasharray: 3 5; }
        .minimax-h3-camera-position circle { fill: var(--h3-surface-raised); stroke: var(--h3-accent); stroke-width: 3; }
        .minimax-h3-camera-position[data-phase="end"] circle { stroke: var(--h3-tip); }
        .minimax-h3-camera-position text,
        .minimax-h3-camera-subject text,
        .minimax-h3-camera-axis-label { fill: var(--h3-text-muted); font: 600 10px/1 var(--h3-font); }
        .minimax-h3-camera-subject circle { fill: color-mix(in srgb, var(--h3-tip) 24%, var(--h3-surface)); stroke: var(--h3-tip); stroke-width: 2; }
        .minimax-h3-camera-subject path { fill: color-mix(in srgb, var(--h3-tip) 38%, transparent); stroke: var(--h3-tip); stroke-width: 2; }
        .minimax-h3-camera-direction { fill: color-mix(in srgb, var(--h3-accent) 24%, transparent); stroke: var(--h3-accent); stroke-width: 1.5; }
        .minimax-h3-spatial-aim-line {
            fill: none;
            stroke: color-mix(in srgb, var(--h3-tip) 52%, transparent);
            stroke-width: 1.2;
            stroke-dasharray: 3 4;
            pointer-events: none;
        }
        .minimax-h3-spatial-aim-line[data-selected="true"] { stroke: var(--h3-tip); stroke-width: 1.8; }
        .minimax-h3-spatial-aim-target { color: var(--h3-tip); pointer-events: none; }
        .minimax-h3-spatial-aim-target circle {
            fill: color-mix(in srgb, var(--h3-surface) 82%, transparent);
            stroke: currentColor;
            stroke-width: 1.4;
        }
        .minimax-h3-spatial-aim-target path { fill: none; stroke: currentColor; stroke-width: 1.4; }
        .minimax-h3-spatial-aim-label { fill: var(--h3-text); font: 650 10px/1 var(--h3-font); paint-order: stroke; stroke: var(--h3-surface); stroke-width: 3px; }
        .minimax-h3-spatial-aim-target[data-selected="true"] { color: var(--h3-accent); pointer-events: auto; cursor: grab; }
        .minimax-h3-spatial-aim-target[data-selected="true"]:active { cursor: grabbing; }
        .minimax-h3-spatial-arrowhead { fill: var(--h3-accent); stroke: none; }
        .minimax-h3-camera-stage-note {
            margin: 0;
            border-top: 1px solid color-mix(in srgb, var(--h3-border) 70%, transparent);
            padding: 5px 8px 6px;
            color: var(--h3-text-muted);
            font-size: 9.5px;
            text-align: right;
        }
        .minimax-h3-camera-phases {
            display: grid;
            min-width: 0;
            gap: var(--h3-space-2);
            padding: 0 var(--h3-space-3);
        }
        .minimax-h3-camera-phase {
            display: grid;
            min-width: 0;
            gap: var(--h3-space-2);
            border: 1px solid var(--h3-border);
            border-radius: var(--h3-radius-sm);
            padding: var(--h3-space-2);
            background: color-mix(in srgb, var(--h3-input-bg) 82%, transparent);
        }
        .minimax-h3-camera-phase-heading { display: flex; align-items: center; gap: 7px; font-weight: 650; }
        .minimax-h3-camera-phase-number {
            display: inline-grid;
            width: 21px;
            height: 21px;
            place-items: center;
            border-radius: 999px;
            background: color-mix(in srgb, var(--h3-accent) 20%, var(--h3-surface));
            color: var(--h3-text);
            font-size: 10px;
        }
        .minimax-h3-camera-phase-controls { display: grid; min-width: 0; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
        .minimax-h3-camera-phase-controls label { display: grid; min-width: 0; gap: 3px; color: var(--h3-text-muted); font-size: 10.5px; }
        .minimax-h3-camera-phase-controls select { width: 100%; min-width: 0; }
        .minimax-h3-camera-motion-groups { display: grid; min-width: 0; gap: var(--h3-space-2); }
        .minimax-h3-camera-motion-group { display: grid; min-width: 0; gap: 5px; }
        .minimax-h3-camera-motion-group > span { color: var(--h3-text-muted); font-size: 10.5px; font-weight: 650; }
        .minimax-h3-camera-motion-buttons { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 5px; }
        .minimax-h3-camera-motion-button {
            display: flex;
            min-width: 0;
            align-items: center;
            justify-content: flex-start;
            gap: 7px;
            text-align: left;
        }
        .minimax-h3-camera-motion-button[aria-pressed="true"] {
            border-color: var(--h3-accent) !important;
            background: color-mix(in srgb, var(--h3-accent) 18%, var(--h3-surface)) !important;
            box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--h3-accent) 32%, transparent);
        }
        .minimax-h3-camera-motion-symbol { width: 22px; flex: 0 0 22px; color: var(--h3-accent); font: 700 13px/1 var(--h3-mono); text-align: center; }
        .minimax-h3-camera-feel { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--h3-space-2); }
        .minimax-h3-camera-preview {
            display: grid;
            gap: 3px;
            margin: 0 var(--h3-space-3) var(--h3-space-3);
            border-left: 3px solid var(--h3-accent);
            padding: 8px 10px;
            background: color-mix(in srgb, var(--h3-accent) 8%, var(--h3-input-bg));
        }
        .minimax-h3-camera-preview strong { color: var(--h3-text); font-size: 10.5px; letter-spacing: .04em; text-transform: uppercase; }
        .minimax-h3-camera-preview span { color: var(--h3-text-muted); line-height: 1.45; }
        .minimax-h3-camera-advanced { overflow: hidden; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-md); background: var(--h3-surface); }
        .minimax-h3-camera-advanced > summary { min-height: 40px; padding: 8px 12px; cursor: pointer; font-weight: 650; }
        .minimax-h3-camera-advanced-body { display: grid; gap: var(--h3-space-3); padding: 0 var(--h3-space-3) var(--h3-space-3); }
        .minimax-h3-camera-data-fallback { border-top: 1px solid var(--h3-border); padding-top: var(--h3-space-2); }
        .minimax-h3-camera-data-fallback > summary { cursor: pointer; color: var(--h3-text-muted); font-size: 11.5px; font-weight: 650; }
        .minimax-h3-camera-data-fallback textarea { width: 100%; min-height: 130px; box-sizing: border-box; margin-top: var(--h3-space-2); font: 11px/1.45 var(--h3-mono) !important; }
        .minimax-h3-camera-data-feedback { min-height: 18px; margin: 5px 0; color: var(--h3-text-muted); font-size: 11px; }
        .minimax-h3-camera-data-feedback[data-kind="error"] { color: var(--h3-error); }
        .minimax-h3-spatial-editor { display: grid; min-width: 0; gap: 10px; margin: 0 var(--h3-space-3); }
        .minimax-h3-spatial-empty {
            display: grid; justify-items: center; gap: 7px; min-height: 230px; align-content: center;
            border: 1px dashed color-mix(in srgb, var(--h3-accent) 48%, var(--h3-border)); border-radius: var(--h3-radius-md);
            padding: 24px; text-align: center; background: radial-gradient(circle at 50% 36%, color-mix(in srgb, var(--h3-accent) 12%, transparent), transparent 42%), var(--h3-bg);
        }
        .minimax-h3-spatial-empty h3, .minimax-h3-spatial-empty p { margin: 0; }
        .minimax-h3-spatial-empty p { max-width: 420px; color: var(--h3-text-muted); line-height: 1.45; }
        .minimax-h3-spatial-empty-art { display: grid; width: 54px; height: 54px; place-items: center; border: 1px solid var(--h3-accent); border-radius: 18px; color: var(--h3-accent); font-size: 30px; background: color-mix(in srgb, var(--h3-accent) 12%, var(--h3-surface)); }
        .minimax-h3-spatial-toolbar { display: grid; min-width: 0; grid-template-columns: repeat(2, minmax(0, 1fr)); align-items: end; gap: 7px; }
        .minimax-h3-spatial-toolbar select { width: 100%; min-width: 0; }
        .minimax-h3-spatial-anchor-warning { flex: 1 0 100%; color: var(--h3-warning, #f3c969); font-size: 10px; line-height: 1.35; }
        .minimax-h3-spatial-segments { display: inline-flex; align-self: end; overflow: hidden; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-sm); }
        .minimax-h3-spatial-segments button { min-height: 32px; border: 0 !important; border-radius: 0 !important; padding: 5px 10px; }
        .minimax-h3-spatial-segments button[aria-pressed="true"] { color: var(--h3-text); background: color-mix(in srgb, var(--h3-accent) 22%, var(--h3-surface)) !important; }
        .minimax-h3-spatial-workspace { display: grid; min-width: 0; grid-template-columns: minmax(0, 1fr); gap: 10px; }
        .minimax-h3-spatial-canvas { min-width: 0; overflow: hidden; border: 1px solid color-mix(in srgb, var(--h3-accent) 34%, var(--h3-border)); border-radius: var(--h3-radius-md); background: radial-gradient(circle at 50% 45%, color-mix(in srgb, var(--h3-accent) 12%, transparent), transparent 42%), color-mix(in srgb, var(--h3-bg) 90%, black 10%); }
        .minimax-h3-spatial-canvas svg { display: block; width: 100%; min-height: 270px; touch-action: none; }
        .minimax-h3-spatial-grid { fill: none; stroke: color-mix(in srgb, var(--h3-border-strong) 46%, transparent); stroke-width: 1; }
        .minimax-h3-spatial-axis-label { fill: color-mix(in srgb, var(--h3-text-muted) 86%, transparent); font: 650 8px/1 var(--h3-mono); letter-spacing: .05em; pointer-events: none; }
        .minimax-h3-spatial-elevation { fill: none; stroke: var(--h3-tip); stroke-width: 1.5; stroke-dasharray: 4 4; pointer-events: none; }
        .minimax-h3-spatial-elevation-foot { fill: var(--h3-bg); stroke: var(--h3-tip); stroke-width: 1.5; pointer-events: none; }
        .minimax-h3-spatial-path-shadow { fill: none; stroke: color-mix(in srgb, black 50%, transparent); stroke-width: 10; opacity: .35; }
        .minimax-h3-spatial-path { fill: none; stroke: var(--h3-accent); stroke-width: 4; stroke-linecap: round; filter: drop-shadow(0 0 5px color-mix(in srgb, var(--h3-accent) 60%, transparent)); }
        .minimax-h3-spatial-target circle:first-child { fill: color-mix(in srgb, var(--h3-tip) 14%, var(--h3-bg)); stroke: var(--h3-tip); stroke-width: 2; }
        .minimax-h3-spatial-target circle:nth-child(2) { fill: var(--h3-tip); }
        .minimax-h3-spatial-point text { fill: var(--h3-text); pointer-events: none; font: 700 10px/1 var(--h3-font); }
        .minimax-h3-spatial-point .minimax-h3-spatial-point-meta { fill: var(--h3-text-muted); font: 600 8px/1 var(--h3-font); text-transform: uppercase; }
        .minimax-h3-spatial-origin-label { fill: var(--h3-text-muted); font: 650 9px/1 var(--h3-font); letter-spacing: .06em; }
        .minimax-h3-spatial-point { cursor: grab; outline: none; }
        .minimax-h3-spatial-point:active { cursor: grabbing; }
        .minimax-h3-spatial-point circle { fill: var(--h3-surface-raised); stroke: var(--h3-border-strong); stroke-width: 2; }
        .minimax-h3-spatial-point path { fill: color-mix(in srgb, var(--h3-accent) 25%, var(--h3-surface)); stroke: var(--h3-accent); stroke-width: 2; }
        .minimax-h3-spatial-point[data-selected="true"] circle { fill: color-mix(in srgb, var(--h3-accent) 22%, var(--h3-surface)); stroke: var(--h3-accent); stroke-width: 3; }
        .minimax-h3-spatial-point:focus-visible circle { stroke: var(--h3-tip); stroke-width: 4; }
        .minimax-h3-spatial-playhead { pointer-events: none; filter: drop-shadow(0 0 5px var(--h3-tip)); }
        .minimax-h3-spatial-playhead circle { fill: var(--h3-tip); stroke: var(--h3-bg); stroke-width: 2; }
        .minimax-h3-spatial-playhead path { fill: color-mix(in srgb, var(--h3-tip) 70%, white); stroke: var(--h3-bg); stroke-width: 1.5; }
        .minimax-h3-spatial-playback { display: grid; min-width: 0; grid-template-columns: auto minmax(80px, 1fr) 38px; align-items: center; gap: 8px; border-top: 1px solid var(--h3-border); padding: 8px; }
        .minimax-h3-spatial-playback button { min-height: 30px; }
        .minimax-h3-spatial-playback input { width: 100%; min-width: 0; accent-color: var(--h3-tip); }
        .minimax-h3-spatial-playback output { color: var(--h3-text-muted); font: 10.5px/1 var(--h3-mono); text-align: right; }
        .minimax-h3-spatial-timeline { display: flex; min-width: 0; flex-wrap: wrap; gap: 5px; border-top: 1px solid var(--h3-border); padding: 8px; }
        .minimax-h3-spatial-timeline button { min-height: 30px; padding: 4px 8px; font-size: 10.5px; }
        .minimax-h3-spatial-timeline button[aria-pressed="true"] { border-color: var(--h3-accent) !important; background: color-mix(in srgb, var(--h3-accent) 18%, var(--h3-surface)) !important; }
        .minimax-h3-spatial-inspector { display: grid; align-content: start; min-width: 0; gap: 10px; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-md); padding: 11px; background: var(--h3-surface); }
        .minimax-h3-spatial-inspector-heading { display: flex; justify-content: space-between; gap: 8px; }
        .minimax-h3-spatial-inspector-heading span { color: var(--h3-text-muted); font-size: 10.5px; }
        .minimax-h3-spatial-slider { display: grid; min-width: 0; gap: 4px; }
        .minimax-h3-spatial-slider > span { display: flex; justify-content: space-between; gap: 8px; color: var(--h3-text-muted); font-size: 10.5px; }
        .minimax-h3-spatial-slider output { color: var(--h3-text); font-family: var(--h3-mono); }
        .minimax-h3-spatial-slider input { width: 100%; min-width: 0; accent-color: var(--h3-accent); }
        .minimax-h3-spatial-aim { display: grid; min-width: 0; gap: 4px; }
        .minimax-h3-spatial-aim > span,
        .minimax-h3-spatial-select > span { color: var(--h3-text-muted); font-size: 10.5px; }
        .minimax-h3-spatial-aim select,
        .minimax-h3-spatial-select select { width: 100%; min-width: 0; }
        .minimax-h3-spatial-select { display: grid; min-width: 0; gap: 4px; }
        .minimax-h3-spatial-camera-glyph { transform-box: fill-box; transform-origin: center; }
        .minimax-h3-spatial-inspector-actions { display: flex; flex-wrap: wrap; gap: 6px; padding-top: 4px; }
        .minimax-h3-spatial-note { margin: 0; color: var(--h3-text-muted); font-size: 9.5px; text-align: right; }
        .minimax-h3-camera-preset-disclosure { margin: 0 var(--h3-space-3); overflow: hidden; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-md); background: color-mix(in srgb, var(--h3-surface) 88%, transparent); }
        .minimax-h3-camera-preset-disclosure > summary { min-height: 38px; padding: 8px 11px; cursor: pointer; color: var(--h3-text); font-weight: 650; }
        .minimax-h3-camera-preset-disclosure .minimax-h3-camera-phases { padding: 0 10px 10px; }
        .minimax-h3-staging-header { display: grid; gap: 5px; }
        .minimax-h3-staging-header h2, .minimax-h3-staging-header p { margin: 0; }
        .minimax-h3-staging-header p { max-width: 68ch; color: var(--h3-text-muted); line-height: 1.45; }
        .minimax-h3-staging-toolbar { display: grid; min-width: 0; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--h3-space-3); align-items: end; }
        .minimax-h3-staging-stage { min-width: 0; overflow: hidden; border: 1px solid color-mix(in srgb, var(--h3-accent) 34%, var(--h3-border)); border-radius: var(--h3-radius-md); background: radial-gradient(circle at 50% 48%, color-mix(in srgb, var(--h3-accent) 11%, transparent), transparent 50%), var(--h3-bg); }
        .minimax-h3-staging-stage svg { display: block; width: 100%; min-height: 300px; touch-action: none; }
        .minimax-h3-stage-floor { fill: color-mix(in srgb, var(--h3-surface) 82%, transparent); stroke: var(--h3-border-strong); stroke-width: 1.5; }
        .minimax-h3-stage-grid { stroke: color-mix(in srgb, var(--h3-border-strong) 54%, transparent); stroke-dasharray: 4 6; }
        .minimax-h3-stage-axis { fill: var(--h3-text-muted); font: 650 9px/1 var(--h3-mono); letter-spacing: .06em; }
        .minimax-h3-stage-movement { stroke: var(--h3-tip); stroke-width: 3; stroke-dasharray: 6 5; opacity: .8; }
        .minimax-h3-stage-subject { cursor: grab; outline: none; }
        .minimax-h3-stage-subject:active { cursor: grabbing; }
        .minimax-h3-stage-subject circle { fill: color-mix(in srgb, var(--h3-accent) 18%, var(--h3-surface-raised)); stroke: var(--h3-accent); stroke-width: 2; }
        .minimax-h3-stage-subject text { fill: var(--h3-text); font: 700 10px/1 var(--h3-font); pointer-events: none; }
        .minimax-h3-stage-subject.is-selected circle, .minimax-h3-stage-subject:focus-visible circle { fill: color-mix(in srgb, var(--h3-tip) 22%, var(--h3-surface)); stroke: var(--h3-tip); stroke-width: 4; }
        .minimax-h3-staging-inspector { display: grid; min-width: 0; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--h3-space-3); align-items: end; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-md); padding: var(--h3-space-3); background: var(--h3-surface); }
        .minimax-h3-staging-inspector h3 { grid-column: 1 / -1; margin: 0; }
        .minimax-h3-staging-inspector .minimax-h3-button-danger { justify-self: start; }
        .minimax-h3-staging-preview { display: grid; gap: 4px; border-left: 3px solid var(--h3-tip); border-radius: 0 var(--h3-radius-sm) var(--h3-radius-sm) 0; padding: 10px 12px; background: color-mix(in srgb, var(--h3-tip) 8%, var(--h3-surface)); }
        .minimax-h3-staging-preview span { color: var(--h3-text-muted); line-height: 1.45; }
        @container h3-studio (max-width: 520px) {
            .minimax-h3-staging-toolbar, .minimax-h3-staging-inspector { grid-template-columns: minmax(0, 1fr); }
        }
        @container h3-camera-planner (min-width: 720px) {
            .minimax-h3-spatial-workspace { grid-template-columns: minmax(0, 1.55fr) minmax(190px, .72fr); }
            .minimax-h3-spatial-toolbar { grid-template-columns: auto repeat(4, minmax(118px, 1fr)); }
        }
        @container h3-camera-planner (min-width: 680px) {
            .minimax-h3-camera-phases { grid-template-columns: minmax(0, .8fr) minmax(0, 1.25fr) minmax(0, .8fr); }
        }
        @container h3-camera-planner (min-width: 900px) {
            .minimax-h3-camera-motion-buttons { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        }
        @container h3-camera-planner (max-width: 420px) {
            .minimax-h3-camera-phase-controls,
            .minimax-h3-camera-feel { grid-template-columns: minmax(0, 1fr); }
        }
        @container h3-camera-planner (max-width: 350px) {
            .minimax-h3-camera-motion-buttons { grid-template-columns: minmax(0, 1fr); }
        }
    `;
    document.head?.appendChild(style);
}
