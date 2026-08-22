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
