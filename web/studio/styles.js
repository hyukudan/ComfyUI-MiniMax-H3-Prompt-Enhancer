import { ensureStudioTokens } from "./tokens.js";

const STYLE_ID = "minimax-h3-studio-styles";

export function ensureStudioStyles() {
    ensureStudioTokens();
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
        .minimax-h3-studio-managed-section { display: none !important; }

        .minimax-h3-reference-node-panel {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            align-items: center;
            gap: var(--h3-space-3);
            min-height: 78px;
            padding: var(--h3-space-3);
            border: 1px solid var(--h3-border);
            border-radius: var(--h3-radius-lg);
            background: linear-gradient(135deg, color-mix(in srgb, var(--h3-accent) 12%, var(--h3-surface)), var(--h3-surface));
            color: var(--h3-text);
            font: 12px/1.35 var(--h3-font);
            box-sizing: border-box;
        }
        .minimax-h3-reference-node-copy { display: grid; min-width: 0; gap: 3px; }
        .minimax-h3-reference-node-copy strong { overflow-wrap: anywhere; font-size: 13px; }
        .minimax-h3-reference-node-copy span { display: -webkit-box; overflow: hidden; color: var(--h3-text-muted); overflow-wrap: anywhere; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
        .minimax-h3-reference-node-panel > button { min-width: 96px; min-height: 34px; white-space: normal; }
        @media (max-width: 520px) {
            .minimax-h3-reference-node-panel { grid-template-columns: 1fr; }
            .minimax-h3-reference-node-panel > button { width: 100%; }
        }

        .minimax-h3-dashboard {
            display: grid;
            grid-template-columns: minmax(118px, 1fr) auto;
            gap: var(--h3-space-2);
            margin-top: var(--h3-space-1);
            border-top: 1px solid color-mix(in srgb, var(--h3-border) 72%, transparent);
            padding: var(--h3-space-3) 0 var(--h3-space-2);
            color: var(--h3-text);
            font: 12px/1.35 var(--h3-font);
        }
        .minimax-h3-dashboard button {
            color: inherit;
            font: inherit;
        }
        .minimax-h3-dashboard-open {
            display: flex;
            min-height: 36px;
            align-items: center;
            justify-content: center;
            gap: var(--h3-space-2);
            border: 1px solid color-mix(in srgb, var(--h3-accent) 60%, var(--h3-border));
            border-radius: var(--h3-radius-md);
            padding: 5px 12px;
            background: color-mix(in srgb, var(--h3-accent) 15%, var(--h3-surface));
            cursor: pointer;
            font-weight: 650;
        }
        .minimax-h3-dashboard-links {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: flex-end;
            gap: var(--h3-space-1);
        }
        .minimax-h3-chip {
            display: inline-flex;
            min-width: 34px;
            min-height: 28px;
            align-items: center;
            justify-content: center;
            gap: 3px;
            border: 1px solid var(--h3-border);
            border-radius: 999px;
            padding: 3px 7px;
            background: var(--h3-surface);
            cursor: pointer;
        }
        .minimax-h3-chip-count:empty { display: none; }
        .minimax-h3-dashboard button:hover { border-color: var(--h3-accent); }
        .minimax-h3-dashboard button:focus-visible { outline: none; box-shadow: var(--h3-focus); }

        .minimax-h3-studio {
            position: fixed;
            z-index: 100000;
            inset: 0 0 0 auto;
            max-width: 100vw;
            display: flex;
            container: h3-studio / inline-size;
            flex-direction: column;
            overflow: visible;
            border-left: 1px solid var(--h3-border-strong);
            background: var(--h3-bg);
            box-shadow: -12px 0 32px rgba(0, 0, 0, .45);
            color: var(--h3-text);
            font: 13px/1.45 var(--h3-font);
            animation: minimax-h3-drawer-in 180ms ease-out;
        }
        .minimax-h3-studio[hidden] { display: none; }
        .minimax-h3-studio[data-resizing="true"] { user-select: none; }
        @keyframes minimax-h3-drawer-in {
            from { transform: translateX(24px); opacity: .65; }
            to { transform: translateX(0); opacity: 1; }
        }
        .minimax-h3-studio-resizer {
            position: absolute;
            z-index: 4;
            inset: 0 auto 0 -4px;
            width: 8px;
            touch-action: none;
            cursor: ew-resize;
        }
        .minimax-h3-production-context {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 1px;
            border-top: 1px solid var(--h3-border);
            border-bottom: 1px solid var(--h3-border);
            background: var(--h3-border);
        }
        .minimax-h3-production-context-item {
            display: grid;
            min-width: 0;
            gap: 1px;
            padding: 6px 10px;
            background: color-mix(in srgb, var(--h3-surface) 82%, var(--h3-bg));
        }
        .minimax-h3-production-context-item small {
            overflow: hidden;
            color: var(--h3-text-muted);
            font-size: 10px;
            font-weight: 750;
            letter-spacing: .065em;
            line-height: 1.2;
            text-overflow: ellipsis;
            text-transform: uppercase;
            white-space: nowrap;
        }
        .minimax-h3-production-context-item strong {
            overflow: hidden;
            color: var(--h3-text);
            font: 650 11.5px/1.25 var(--h3-mono);
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .minimax-h3-studio-resizer::after {
            position: absolute;
            inset: 0 auto 0 3px;
            width: 2px;
            background: transparent;
            content: "";
            transition: background 140ms ease-out;
        }
        .minimax-h3-studio-resizer:hover::after,
        .minimax-h3-studio-resizer:focus-visible::after,
        .minimax-h3-studio[data-resizing="true"] .minimax-h3-studio-resizer::after { background: var(--h3-accent); }
        .minimax-h3-studio-resizer:focus-visible { outline: none; }

        .minimax-h3-studio-header {
            position: relative;
            flex: none;
            border-bottom: 1px solid var(--h3-border);
            background: color-mix(in srgb, var(--h3-bg) 92%, white 8%);
        }
        .minimax-h3-header-main {
            display: flex;
            min-height: 52px;
            align-items: center;
            gap: var(--h3-space-3);
            padding: var(--h3-space-2) var(--h3-space-3) var(--h3-space-1) var(--h3-space-4);
        }
        .minimax-h3-header-identity { min-width: 128px; flex: 1; }
        .minimax-h3-studio-header h2 {
            margin: 0;
            font-size: 16px;
            font-weight: 650;
            letter-spacing: -.01em;
        }
        .minimax-h3-header-context {
            margin: 1px 0 0;
            color: var(--h3-text-muted);
            font-size: 11.5px;
            text-transform: capitalize;
        }
        .minimax-h3-header-state {
            display: flex;
            align-items: center;
            gap: var(--h3-space-2);
        }
.minimax-h3-detail-mode {
            display: inline-flex;
            gap: 2px;
            border: 1px solid var(--h3-border);
            border-radius: 999px;
            padding: 2px;
            background: var(--h3-input-bg);
        }
        .minimax-h3-detail-mode button {
            min-height: 24px;
            border: 0;
            border-radius: 999px;
            padding: 2px 8px;
            background: transparent;
            color: var(--h3-text-muted);
            font-size: 11px;
            cursor: pointer;
        }
        .minimax-h3-detail-mode button[aria-pressed="true"] {
            background: color-mix(in srgb, var(--h3-accent) 18%, var(--h3-surface));
            color: var(--h3-text);
        }
        .minimax-h3-saved-state { color: var(--h3-text-muted); font-size: 11.5px; white-space: nowrap; }
        .minimax-h3-review-button {
            display: inline-flex;
            min-height: var(--h3-control-height);
            align-items: center;
            gap: 6px;
            border: 1px solid var(--h3-border);
            border-radius: 999px;
            padding: 3px 9px;
            background: var(--h3-surface);
            color: var(--h3-button-text);
            cursor: pointer;
            white-space: nowrap;
        }
        .minimax-h3-review-button:hover:not(:disabled) {
            border-color: color-mix(in srgb, var(--h3-accent) 62%, var(--h3-border));
            background: color-mix(in srgb, var(--h3-surface-raised) 82%, var(--h3-accent) 18%);
        }
        .minimax-h3-review-button[data-state="error"] { border-color: var(--h3-error); }
        .minimax-h3-review-button[data-state="warning"] { border-color: var(--h3-warning); }
        .minimax-h3-review-button[data-state="stale"] { border-color: var(--h3-readonly); }
        .minimax-h3-icon-button,
        .minimax-h3-rail-collapse {
            display: inline-grid;
            width: var(--h3-control-height);
            min-width: var(--h3-control-height);
            height: var(--h3-control-height);
            place-items: center;
            border: 1px solid transparent;
            border-radius: var(--h3-radius-sm);
            padding: 0;
            background: transparent;
            color: var(--h3-text-muted);
            cursor: pointer;
        }
        .minimax-h3-icon-button:hover,
        .minimax-h3-rail-collapse:hover { border-color: var(--h3-border); background: var(--h3-surface); color: var(--h3-text); }
        .minimax-h3-source-pill {
            display: inline-flex;
            min-height: var(--h3-chip-height);
            align-items: center;
            gap: 5px;
            border: 1px solid var(--h3-border);
            border-radius: 999px;
            padding: 1px 7px;
            background: var(--h3-surface);
            color: var(--h3-text-muted);
            font-size: 11px;
            white-space: nowrap;
        }
        .minimax-h3-source-pill[data-kind="malformed"] { border-color: var(--h3-error); color: color-mix(in srgb, var(--h3-error) 70%, white); }
        .minimax-h3-source-pill[data-kind="future"] { border-color: var(--h3-readonly); }
        .minimax-h3-source-pill[data-kind="v1"] { border-color: var(--h3-border-strong); }
        .minimax-h3-source-name { color: var(--h3-text); font-weight: 600; }
        .minimax-h3-shortcuts {
            position: absolute;
            z-index: 5;
            top: 46px;
            right: 42px;
            width: min(330px, calc(100% - 32px));
            border: 1px solid var(--h3-border-strong);
            border-radius: var(--h3-radius-md);
            padding: var(--h3-space-3);
            background: var(--h3-surface-raised);
            box-shadow: 0 8px 24px rgba(0, 0, 0, .5);
        }
        .minimax-h3-shortcuts[hidden] { display: none; }
        .minimax-h3-shortcuts h3 { margin: 0 0 var(--h3-space-2); font-size: 14px; }
        .minimax-h3-shortcuts dl { display: grid; grid-template-columns: 92px 1fr; gap: 5px 10px; margin: 0; }
        .minimax-h3-shortcuts dt { color: var(--h3-text); font-family: var(--h3-mono); }
        .minimax-h3-shortcuts dd { margin: 0; color: var(--h3-text-muted); }

        .minimax-h3-studio-body {
            display: grid;
            min-height: 0;
            flex: 1;
            grid-template-columns: var(--h3-rail-width) minmax(0, 1fr);
        }
        .minimax-h3-studio-rail {
            display: flex;
            min-height: 0;
            flex-direction: column;
            border-right: 1px solid var(--h3-border);
            background: color-mix(in srgb, var(--h3-bg) 94%, black 6%);
        }
        .minimax-h3-studio-tabs {
            display: grid;
            align-content: start;
            gap: 2px;
            overflow-y: auto;
            padding: var(--h3-space-2) 5px;
        }
        .minimax-h3-studio-tab {
            position: relative;
            display: grid;
            min-height: 54px;
            place-items: center;
            gap: 2px;
            border: 0;
            border-radius: var(--h3-radius-md);
            padding: 6px 3px;
            background: transparent;
            color: var(--h3-text-muted);
            cursor: pointer;
        }
        .minimax-h3-studio-tab::before {
            position: absolute;
            inset: 8px auto 8px -5px;
            width: 3px;
            border-radius: 0 3px 3px 0;
            background: transparent;
            content: "";
        }
        .minimax-h3-studio-tab:hover { background: var(--h3-surface); color: var(--h3-text); }
        .minimax-h3-studio-tab[aria-selected="true"] {
            background: color-mix(in srgb, var(--h3-accent) 14%, transparent);
            color: var(--h3-text);
        }
        .minimax-h3-studio-tab[aria-selected="true"]::before { background: var(--h3-accent); }
        .minimax-h3-tab-label { max-width: 78px; overflow: hidden; font-size: 10px; font-weight: 600; text-align: center; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-rail-collapse { margin: auto auto var(--h3-space-2); }
        .minimax-h3-studio[data-rail-collapsed="true"] .minimax-h3-studio-body { grid-template-columns: var(--h3-rail-compact-width) minmax(0, 1fr); }
        .minimax-h3-studio[data-rail-collapsed="true"] .minimax-h3-tab-label { display: none; }
        .minimax-h3-studio[data-rail-collapsed="true"] .minimax-h3-studio-tab { min-height: 42px; }
        .minimax-h3-studio[data-rail-collapsed="true"] .minimax-h3-rail-collapse svg { transform: rotate(180deg); }

        .minimax-h3-studio-panel {
            min-width: 0;
            min-height: 0;
            overflow: auto;
            padding: var(--h3-space-4);
            scrollbar-color: var(--h3-border-strong) transparent;
            container-name: h3-studio-panel;
            container-type: inline-size;
        }
        .minimax-h3-studio-panel > * { min-width: 0; max-width: 100%; box-sizing: border-box; }
        .minimax-h3-section-media {
            display: grid;
            align-content: start;
            gap: var(--h3-space-4);
        }
        .minimax-h3-section-media > .minimax-h3-studio-toolbar,
        .minimax-h3-master-pane > .minimax-h3-studio-toolbar { margin-bottom: 0; }
        /* This nested master/detail grid is itself an item of the Media grid.
           The shared master/detail rule uses min-height: 0 for scrollable
           editors; here that let the parent row collapse to the toolbar's
           min-content height while the inspector painted over the following
           generation block. Restore the intrinsic height in this context. */
        .minimax-h3-section-media > .minimax-h3-master-detail {
            min-height: auto;
            align-self: start;
        }
        .minimax-h3-section-media > h3 { margin: var(--h3-space-1) 0 0; }
        .minimax-h3-media-onboarding {
            display: grid;
            min-width: 0;
            gap: var(--h3-space-3);
            border: 1px solid color-mix(in srgb, var(--h3-accent) 32%, var(--h3-border));
            border-radius: var(--h3-radius-md);
            padding: var(--h3-space-3);
            background: color-mix(in srgb, var(--h3-accent) 7%, var(--h3-surface));
        }
        .minimax-h3-media-onboarding-intro,
        .minimax-h3-media-onboarding-intro > span,
        .minimax-h3-media-step-number + div { min-width: 0; }
        .minimax-h3-media-onboarding-intro { display: grid; gap: 3px; }
        .minimax-h3-media-onboarding-intro > span,
        .minimax-h3-media-steps li span,
        .minimax-h3-media-generation-heading p { color: var(--h3-text-muted); font-size: 11.5px; line-height: 1.45; overflow-wrap: anywhere; }
        .minimax-h3-media-steps {
            display: grid;
            grid-template-columns: minmax(0, 1fr);
            gap: var(--h3-space-2);
            margin: 0;
            padding: 0;
            list-style: none;
        }
        .minimax-h3-media-steps li { display: flex; min-width: 0; gap: var(--h3-space-2); align-items: flex-start; }
        .minimax-h3-media-step-number {
            display: inline-grid;
            width: 22px;
            height: 22px;
            flex: 0 0 22px;
            place-items: center;
            border-radius: 999px;
            background: var(--h3-accent);
            color: #10151d !important;
            font-size: 11px !important;
            font-weight: 750;
        }
        .minimax-h3-media-step-number + div { display: grid; gap: 2px; }
        .minimax-h3-media-generation-heading { display: grid; min-width: 0; gap: 3px; padding-top: var(--h3-space-1); }
        .minimax-h3-media-generation-heading h3,
        .minimax-h3-media-generation-heading p { margin: 0; }
        .minimax-h3-media-empty-note {
            margin: 0;
            border: 1px dashed var(--h3-border-strong);
            border-radius: var(--h3-radius-sm);
            padding: var(--h3-space-2);
            background: color-mix(in srgb, var(--h3-surface-raised) 76%, transparent);
            color: var(--h3-text-muted);
            overflow-wrap: anywhere;
        }
        .minimax-h3-media-assistant {
            display: grid;
            min-width: 0;
            gap: var(--h3-space-3);
            border: 1px solid color-mix(in srgb, var(--h3-tip) 42%, var(--h3-border));
            border-radius: var(--h3-radius-md);
            padding: var(--h3-space-3);
            background: color-mix(in srgb, var(--h3-tip) 7%, var(--h3-surface));
        }
        .minimax-h3-media-assistant-heading { display: flex; min-width: 0; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--h3-space-2); }
        .minimax-h3-media-assistant-heading strong { min-width: 0; font-size: 13px; overflow-wrap: anywhere; }
        .minimax-h3-media-assistant-heading span { border-radius: 999px; padding: 3px 7px; background: color-mix(in srgb, var(--h3-tip) 15%, var(--h3-input-bg)); color: var(--h3-tip); font-size: 10.5px; font-weight: 700; }
        .minimax-h3-media-assistant > p { margin: 0; color: var(--h3-text-muted); line-height: 1.45; }
        .minimax-h3-media-assistant > button { justify-self: start; max-width: 100%; white-space: normal; text-align: left; }
        .minimax-h3-media-assistant-assignments { display: flex; min-width: 0; flex-wrap: wrap; gap: 6px; }
        .minimax-h3-media-assistant-assignments span { border: 1px solid var(--h3-border); border-radius: 999px; padding: 4px 7px; background: var(--h3-input-bg); color: var(--h3-text-muted); font-size: 11px; }
        .minimax-h3-media-workflows {
            display: grid;
            min-width: 0;
            align-content: start;
            gap: var(--h3-space-4);
        }
        .minimax-h3-media-recipes {
            min-width: 0;
            margin: 0;
            column-gap: var(--h3-space-2);
            row-gap: var(--h3-space-3);
        }
        .minimax-h3-media-recipes + .minimax-h3-planning-context { margin-top: var(--h3-space-1); }
        .minimax-h3-reference-director {
            display: grid;
            min-width: 0;
            gap: var(--h3-space-3);
            overflow: visible;
            border: 1px solid color-mix(in srgb, var(--h3-accent) 46%, var(--h3-border));
            border-radius: var(--h3-radius-lg);
            padding: var(--h3-space-3);
            background:
                radial-gradient(circle at 18% 0, color-mix(in srgb, var(--h3-accent) 13%, transparent), transparent 34%),
                var(--h3-surface);
        }
        .minimax-h3-reference-director-header {
            display: flex;
            min-width: 0;
            flex-wrap: wrap;
            align-items: flex-start;
            justify-content: space-between;
            gap: var(--h3-space-3);
        }
        .minimax-h3-reference-director-header > div { min-width: 220px; flex: 1; }
        .minimax-h3-reference-director-header h3,
        .minimax-h3-reference-director-header p,
        .minimax-h3-reference-director h4,
        .minimax-h3-reference-director section > p { margin: 0; }
        .minimax-h3-reference-director-header h3 { font-size: 16px; }
        .minimax-h3-reference-director-header p,
        .minimax-h3-reference-director section > p { margin-top: 2px; color: var(--h3-text-muted); font-size: 10.5px; line-height: 1.4; }
        .minimax-h3-reference-director-status {
            border: 1px solid color-mix(in srgb, var(--h3-accent) 50%, var(--h3-border));
            border-radius: 999px;
            padding: 4px 8px;
            background: color-mix(in srgb, var(--h3-accent) 10%, var(--h3-input-bg));
            color: var(--h3-accent);
            font-size: 10px;
            font-weight: 700;
        }
        .minimax-h3-reference-director-board {
            display: grid;
            min-width: 0;
            grid-template-columns: minmax(150px, .8fr) minmax(250px, 1.35fr) minmax(160px, .85fr);
            gap: var(--h3-space-2);
        }
        .minimax-h3-reference-director-board > section {
            display: grid;
            min-width: 0;
            align-content: start;
            gap: var(--h3-space-2);
            border: 1px solid var(--h3-border);
            border-radius: var(--h3-radius-md);
            padding: var(--h3-space-2);
            background: color-mix(in srgb, var(--h3-input-bg) 78%, var(--h3-surface));
        }
        .minimax-h3-reference-director-board h4 { font-size: 11px; letter-spacing: .04em; text-transform: uppercase; }
        .minimax-h3-reference-card-grid,
        .minimax-h3-reference-output-list,
        .minimax-h3-reference-relationship-rail { display: grid; min-width: 0; align-content: start; gap: 6px; }
        .minimax-h3-reference-output-card {
            display: grid; min-width: 0; gap: 3px; border: 1px solid var(--h3-border);
            border-radius: 7px; padding: 7px 8px; background: var(--h3-surface);
        }
        .minimax-h3-reference-output-card strong { color: var(--h3-accent); font: 700 10px/1.3 var(--h3-mono); }
        .minimax-h3-reference-output-card > span { display: grid; min-width: 0; gap: 2px; color: var(--h3-text-muted); font-size: 10px; overflow-wrap: anywhere; }
        .minimax-h3-reference-output-card code { color: var(--h3-text); font: 600 9px/1.35 var(--h3-mono); }
        .minimax-h3-reference-card {
            display: grid;
            min-width: 0;
            grid-template-columns: 40px minmax(0, 1fr);
            align-items: center;
            gap: 7px;
            border-color: var(--h3-border) !important;
            padding: 6px !important;
            background: var(--h3-surface) !important;
            text-align: left;
        }
        .minimax-h3-reference-card:hover,
        .minimax-h3-reference-card[aria-pressed="true"] { border-color: var(--h3-accent) !important; box-shadow: inset 3px 0 var(--h3-accent); }
        .minimax-h3-reference-card > span:nth-child(2) { display: grid; min-width: 0; gap: 1px; }
        .minimax-h3-reference-card strong,
        .minimax-h3-reference-card small { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-reference-card small { color: var(--h3-text-muted); font-size: 9.5px; font-family: var(--h3-mono); }
        .minimax-h3-reference-card-links { grid-column: 1 / -1; color: var(--h3-text-muted); font-size: 9.5px; }
        .minimax-h3-reference-import-row { display: flex; min-width: 0; flex-wrap: wrap; align-items: center; gap: 6px; }
        .minimax-h3-reference-import-row .minimax-h3-reference-director-feedback { flex: 1 1 120px; }
        .minimax-h3-reference-import { border-color: color-mix(in srgb, var(--h3-accent) 60%, var(--h3-border)) !important; color: var(--h3-accent) !important; }
        .minimax-h3-reference-target-group { display: grid; min-width: 0; gap: 5px; }
        .minimax-h3-reference-target-group > strong { color: var(--h3-text-muted); font-size: 9.5px; letter-spacing: .04em; text-transform: uppercase; }
        .minimax-h3-reference-entity {
            display: grid;
            min-width: 0;
            gap: 6px;
            border: 1px solid var(--h3-border);
            border-radius: var(--h3-radius-sm);
            padding: 7px;
            background: var(--h3-surface);
        }
        .minimax-h3-reference-entity > span { overflow-wrap: anywhere; font-size: 11px; font-weight: 650; }
        .minimax-h3-reference-dropzones { display: flex; min-width: 0; flex-wrap: wrap; gap: 4px; }
        .minimax-h3-reference-dropzone {
            min-height: 28px !important;
            border-style: dashed !important;
            border-radius: 999px !important;
            padding: 3px 8px !important;
            background: var(--h3-input-bg) !important;
            font-size: 9.5px;
        }
        .minimax-h3-reference-dropzone[data-tone="identity"] { color: color-mix(in srgb, var(--h3-accent) 78%, white); }
        .minimax-h3-reference-dropzone[data-tone="voice"] { color: color-mix(in srgb, var(--h3-success) 78%, white); }
        .minimax-h3-reference-dropzone[data-tone="environment"] { color: color-mix(in srgb, var(--h3-tip) 78%, white); }
        .minimax-h3-reference-dropzone[data-tone="motion"] { color: color-mix(in srgb, var(--h3-warning) 78%, white); }
        .minimax-h3-reference-dropzone[data-drag="ready"] { border-style: solid !important; border-color: var(--h3-accent) !important; background: color-mix(in srgb, var(--h3-accent) 16%, var(--h3-input-bg)) !important; }
        .minimax-h3-reference-dropzone:disabled { cursor: not-allowed; opacity: .35; }
        .minimax-h3-reference-output-row {
            display: grid;
            min-width: 0;
            grid-template-columns: auto minmax(0, 1fr);
            gap: 2px 7px;
            border-left: 2px solid var(--h3-accent);
            padding: 5px 7px;
            background: var(--h3-surface);
        }
        .minimax-h3-reference-output-row strong { color: var(--h3-accent); font: 700 10px/1.3 var(--h3-mono); }
        .minimax-h3-reference-output-row span { min-width: 0; overflow: hidden; font-size: 10.5px; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-reference-output-row small { grid-column: 1 / -1; color: var(--h3-text-muted); font-size: 9px; overflow-wrap: anywhere; }
        .minimax-h3-reference-target-empty,
        .minimax-h3-reference-director-feedback { margin: 0; color: var(--h3-text-muted); font-size: 10px; line-height: 1.4; }
        .minimax-h3-reference-director-feedback[data-valid="false"] { color: var(--h3-error); }
        @container h3-studio-panel (min-width: 600px) {
            .minimax-h3-media-steps { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        @container h3-studio-panel (max-width: 760px) {
            .minimax-h3-reference-director-board { grid-template-columns: minmax(150px, .8fr) minmax(250px, 1.2fr); }
            .minimax-h3-reference-output-rail { grid-column: 1 / -1; }
            .minimax-h3-reference-output-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        @container h3-studio-panel (max-width: 620px) {
            .minimax-h3-reference-director-board { grid-template-columns: minmax(0, 1fr); }
            .minimax-h3-reference-output-rail { grid-column: auto; }
            .minimax-h3-reference-card-grid,
            .minimax-h3-reference-output-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .minimax-h3-look-block .minimax-h3-studio-columns { grid-template-columns: minmax(0, 1fr); }
            .minimax-h3-look-intro-toolbar { grid-template-columns: minmax(0, 1fr); }
            .minimax-h3-look-intro-toolbar button { justify-self: start; }
        }
        .minimax-h3-section-camera,
        .minimax-h3-section-look {
            display: grid;
            align-content: start;
            grid-auto-rows: max-content;
            gap: var(--h3-space-3);
        }
        .minimax-h3-section-camera > .minimax-h3-studio-status,
        .minimax-h3-section-look > .minimax-h3-studio-status { margin: 0; }
        .minimax-h3-section-shots > .minimax-h3-studio-toolbar + .minimax-h3-studio-status { display: none; }
        .minimax-h3-studio button,
        .minimax-h3-studio input,
        .minimax-h3-studio select,
        .minimax-h3-studio textarea { color: inherit; font: inherit; }
        .minimax-h3-studio button { min-height: var(--h3-control-height); }
        .minimax-h3-studio-panel button {
            border: 1px solid var(--h3-border-strong);
            border-radius: var(--h3-radius-sm);
            padding: 4px 9px;
            background: var(--h3-surface);
            color: var(--h3-button-text);
            cursor: pointer;
        }
        .minimax-h3-studio-panel input:not([type="checkbox"]):not([type="radio"]),
        .minimax-h3-studio-panel select,
        .minimax-h3-studio-panel textarea {
            min-height: var(--h3-control-height);
            box-sizing: border-box;
            border: 1px solid var(--h3-border-strong);
            border-radius: var(--h3-radius-sm);
            padding: 5px 7px;
            background: var(--h3-input-bg);
        }
        .minimax-h3-studio button:focus-visible,
        .minimax-h3-studio input:focus-visible,
        .minimax-h3-studio select:focus-visible,
        .minimax-h3-studio textarea:focus-visible,
        .minimax-h3-studio [tabindex]:focus-visible { outline: none; box-shadow: var(--h3-focus); }
        .minimax-h3-button {
            display: inline-flex;
            min-height: var(--h3-control-height);
            align-items: center;
            justify-content: center;
            gap: 6px;
            border: 1px solid var(--h3-border-strong);
            border-radius: var(--h3-radius-sm);
            padding: 4px 10px;
            cursor: pointer;
        }
        .minimax-h3-button-primary {
            border-color: color-mix(in srgb, var(--h3-accent) 84%, white 16%) !important;
            background: var(--h3-accent) !important;
            color: var(--h3-on-primary) !important;
            font-weight: 700;
        }
        .minimax-h3-button-secondary {
            border-color: var(--h3-border-strong) !important;
            background: color-mix(in srgb, var(--h3-surface) 88%, white 12%) !important;
            color: var(--h3-button-text) !important;
            font-weight: 600;
        }
        .minimax-h3-button-primary:hover:not(:disabled) { background: color-mix(in srgb, var(--h3-accent) 88%, white 12%) !important; }
        .minimax-h3-button-secondary:hover:not(:disabled) {
            border-color: color-mix(in srgb, var(--h3-accent) 62%, var(--h3-border)) !important;
            background: color-mix(in srgb, var(--h3-surface-raised) 82%, var(--h3-accent) 18%) !important;
        }
        .minimax-h3-button:active:not(:disabled) { transform: translateY(1px); }
        .minimax-h3-button:disabled,
        .minimax-h3-studio button:disabled { opacity: .55; cursor: not-allowed; filter: saturate(.35); }
        .minimax-h3-muted { color: var(--h3-text-muted); }

        .minimax-h3-studio-grid {
            display: grid;
            min-height: 0;
            grid-template-columns: minmax(0, 1fr);
            gap: var(--h3-space-3);
        }
        @container h3-studio-panel (min-width: 600px) {
            .minimax-h3-studio-grid {
                grid-template-columns: var(--h3-list-width) minmax(0, 1fr);
            }
        }
        .minimax-h3-virtual-list {
            position: relative;
            height: min(68vh, 640px);
            overflow: auto;
            border: 1px solid var(--h3-border);
            border-radius: var(--h3-radius-md);
            background: var(--h3-surface);
        }
        .minimax-h3-shot-timeline {
            display: grid;
            min-width: 0;
            gap: 6px;
            border: 1px solid var(--h3-border);
            border-radius: var(--h3-radius-md);
            padding: 8px;
            background: color-mix(in srgb, var(--h3-input-bg) 76%, var(--h3-surface));
        }
        .minimax-h3-shot-timeline-heading {
            display: flex;
            min-width: 0;
            align-items: baseline;
            justify-content: space-between;
            gap: var(--h3-space-2);
        }
        .minimax-h3-shot-timeline-heading strong { font-size: 11.5px; }
        .minimax-h3-shot-timeline-heading span {
            overflow: hidden;
            color: var(--h3-text-muted);
            font-size: 10px;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .minimax-h3-shot-timeline-track {
            min-width: 0;
            overflow-x: auto;
            scrollbar-gutter: stable;
        }
        .minimax-h3-shot-timeline-strip {
            position: relative;
            display: flex;
            width: 100%;
            min-width: 0;
        }
        .minimax-h3-shot-timeline-clip {
            display: grid;
            min-width: 0;
            min-height: 66px;
            flex: 0 0 auto;
            align-content: start;
            gap: 2px;
            overflow: hidden;
            border: 1px solid var(--h3-border-strong);
            border-radius: 0;
            padding: 7px 8px;
            background: color-mix(in srgb, var(--h3-surface) 84%, var(--h3-accent) 4%);
            color: var(--h3-text);
            text-align: left;
            cursor: pointer;
        }
        .minimax-h3-shot-timeline-clip:hover {
            border-color: color-mix(in srgb, var(--h3-accent) 65%, var(--h3-border));
            background: color-mix(in srgb, var(--h3-accent) 10%, var(--h3-surface));
        }
        .minimax-h3-shot-timeline-clip:first-child { border-radius: 5px 0 0 5px; }
        .minimax-h3-shot-timeline-clip:last-of-type { border-radius: 0 5px 5px 0; }
        .minimax-h3-shot-timeline-clip[aria-pressed="true"] {
            border-color: var(--h3-accent);
            background: color-mix(in srgb, var(--h3-accent) 16%, var(--h3-surface));
            box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--h3-accent) 55%, transparent);
        }
        .minimax-h3-shot-timeline-time {
            color: var(--h3-tip);
            font: 9.5px/1.2 var(--h3-mono);
            white-space: nowrap;
        }
        .minimax-h3-shot-timeline-action {
            display: -webkit-box;
            overflow: hidden;
            color: var(--h3-text-muted);
            font-size: 10px;
            line-height: 1.25;
            -webkit-box-orient: vertical;
            -webkit-line-clamp: 2;
        }
        .minimax-h3-shot-timeline-boundary {
            position: absolute;
            z-index: 2;
            top: 0;
            bottom: 0;
            width: 12px;
            transform: translateX(-50%);
            touch-action: none;
            cursor: col-resize;
        }
        .minimax-h3-shot-timeline-boundary::after {
            position: absolute;
            inset: 5px auto 5px 5px;
            width: 2px;
            border-radius: 2px;
            background: color-mix(in srgb, var(--h3-accent) 72%, var(--h3-border-strong));
            content: "";
            box-shadow: 0 0 0 1px color-mix(in srgb, var(--h3-bg) 70%, transparent);
        }
        .minimax-h3-shot-timeline-boundary:hover::after,
        .minimax-h3-shot-timeline-boundary:focus-visible::after { width: 4px; background: var(--h3-accent); }
        .minimax-h3-shot-timeline-boundary:focus-visible { outline: none; }
        .minimax-h3-shot-anchor-lane {
            position: relative;
            width: 100%;
            height: 52px;
            border-top: 1px solid var(--h3-border);
            background: repeating-linear-gradient(90deg, transparent 0 85px, color-mix(in srgb, var(--h3-border) 38%, transparent) 85px 86px);
        }
        .minimax-h3-shot-anchor {
            position: absolute;
            top: 5px;
            display: grid;
            max-width: 190px;
            grid-template-columns: 34px minmax(0, 1fr);
            align-items: center;
            gap: 6px;
            transform: translateX(0);
            border: 1px solid color-mix(in srgb, var(--h3-accent) 65%, var(--h3-border));
            border-radius: 5px;
            padding: 3px 6px 3px 3px;
            background: color-mix(in srgb, var(--h3-surface-raised) 90%, var(--h3-accent) 10%);
            color: var(--h3-text);
            text-align: left;
            cursor: pointer;
        }
        .minimax-h3-shot-anchor[data-edge="end"] { transform: translateX(-100%); }
        .minimax-h3-shot-anchor:hover,
        .minimax-h3-shot-anchor:focus-visible { border-color: var(--h3-accent); background: color-mix(in srgb, var(--h3-accent) 17%, var(--h3-surface)); }
        .minimax-h3-shot-anchor-thumb { display: grid; width: 32px; height: 32px; place-items: center; border-radius: 3px; background: linear-gradient(135deg, color-mix(in srgb, var(--h3-accent) 28%, var(--h3-input-bg)), var(--h3-input-bg)); font: 700 10px/1 var(--h3-mono); }
        .minimax-h3-shot-anchor-copy { display: grid; min-width: 0; }
        .minimax-h3-shot-anchor-copy strong,
        .minimax-h3-shot-anchor-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-shot-anchor-copy strong { font-size: 9.5px; }
        .minimax-h3-shot-anchor-copy small { color: var(--h3-text-muted); font-size: 8.5px; }
        .minimax-h3-virtual-spacer { position: relative; }
        .minimax-h3-virtual-row {
            position: absolute;
            left: 0;
            right: 0;
            display: grid;
            height: 60px;
            align-content: center;
            gap: 3px;
            border: 0;
            border-bottom: 1px solid var(--h3-border);
            padding: 0 9px;
            background: var(--h3-surface);
            color: var(--h3-text);
            text-align: left;
        }
        .minimax-h3-shot-row-primary {
            display: flex;
            min-width: 0;
            align-items: center;
            gap: 5px;
        }
        .minimax-h3-shot-row-title {
            min-width: 0;
            margin-right: auto;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .minimax-h3-shot-row-chip {
            flex: 0 0 auto;
            max-width: 72px;
            overflow: hidden;
            border: 1px solid var(--h3-border);
            border-radius: 999px;
            padding: 1px 6px;
            color: var(--h3-text-muted);
            font-size: 10px;
            font-weight: 650;
            line-height: 1.35;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .minimax-h3-shot-row-generation { max-width: 64px; }
        .minimax-h3-shot-row-action {
            display: block;
            min-width: 0;
            overflow: hidden;
            color: var(--h3-text-muted);
            font-size: 11px;
            line-height: 1.25;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .minimax-h3-virtual-row:hover { background: var(--h3-surface-raised); }
        .minimax-h3-virtual-row[aria-selected="true"] {
            background: color-mix(in srgb, var(--h3-accent) 14%, var(--h3-surface));
            box-shadow: inset 3px 0 var(--h3-accent);
        }
        .minimax-h3-studio-editor { display: grid; gap: var(--h3-space-3); align-content: start; }
        .minimax-h3-studio-field { display: grid; min-width: 0; gap: var(--h3-space-1); }
        .minimax-h3-studio-field > span {
            min-width: 0;
            color: var(--h3-text-muted);
            font-size: 11.5px;
            font-weight: 600;
            letter-spacing: .01em;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }
        .minimax-h3-studio-field input:not([type="checkbox"]):not([type="radio"]),
        .minimax-h3-studio-field select,
        .minimax-h3-studio-field textarea {
            width: 100%;
            min-height: var(--h3-control-height);
            box-sizing: border-box;
            border: 1px solid var(--h3-border-strong);
            border-radius: var(--h3-radius-sm);
            padding: 5px 7px;
            background: var(--h3-input-bg);
            color: var(--h3-text);
        }
        .minimax-h3-studio-field input[type="checkbox"],
        .minimax-h3-studio-field input[type="radio"] {
            width: auto;
            min-height: 0;
            justify-self: start;
            margin: 0;
        }
        .minimax-h3-studio-field textarea { min-height: 76px; resize: vertical; }
        .minimax-h3-studio-columns { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--h3-space-2); }
        .minimax-h3-progressive-disclosure {
            display: grid;
            min-width: 0;
            gap: var(--h3-space-2);
            margin-top: var(--h3-space-1);
            border-top: 1px solid var(--h3-border);
            padding: var(--h3-space-3) 0 var(--h3-space-1);
        }
        .minimax-h3-progressive-disclosure > summary {
            display: flex;
            width: 100%;
            min-height: 30px;
            box-sizing: border-box;
            align-items: center;
            cursor: pointer;
            color: var(--h3-text-muted);
            font-size: 11.5px;
            font-weight: 650;
        }
        .minimax-h3-progressive-disclosure > .minimax-h3-field-hint { margin-bottom: var(--h3-space-2); }
        .minimax-h3-select-search { position: relative; width: 100%; }
        .minimax-h3-searchable-select { display: flex; width: 100%; min-width: 0; flex-direction: column; gap: 4px; }
        .minimax-h3-searchable-select-trigger {
            width: 100%;
            min-width: 0;
            min-height: var(--h3-control-height);
            overflow: hidden;
            border: 1px solid var(--h3-border-strong);
            border-radius: var(--h3-radius-sm);
            padding: 5px 7px;
            background: var(--h3-input-bg);
            color: var(--h3-text);
            text-align: left;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .minimax-h3-searchable-select-popover {
            position: fixed;
            z-index: 100020;
            display: flex;
            min-width: 0;
            box-sizing: border-box;
            flex-direction: column;
            gap: var(--h3-space-1);
            overflow: hidden;
            border: 1px solid var(--h3-border-strong, #59626d);
            border-radius: var(--h3-radius-md, 8px);
            padding: var(--h3-space-2, 8px);
            background: var(--h3-input-bg, #171b20);
            box-shadow: 0 12px 32px rgba(0, 0, 0, .58);
            color: var(--h3-text, #f7f9fc);
            font: 13px/1.45 var(--h3-font, Inter, system-ui, sans-serif);
        }
        .minimax-h3-searchable-select-popover button,
        .minimax-h3-searchable-select-popover input { color: inherit; font: inherit; }
        .minimax-h3-searchable-select-popover button:not(:disabled) { cursor: pointer; }
        .minimax-h3-searchable-select-popover button:disabled { cursor: not-allowed; }
        .minimax-h3-searchable-select-popover[hidden] { display: none; }
        .minimax-h3-visual-navigation {
            display: flex;
            min-width: 0;
            align-items: center;
            gap: var(--h3-space-2);
            border-bottom: 1px solid var(--h3-border);
            padding-bottom: var(--h3-space-1);
        }
        .minimax-h3-visual-back {
            min-height: 24px !important;
            flex: none;
            border: 0 !important;
            padding: 2px 5px !important;
            background: transparent !important;
            color: var(--h3-button-text) !important;
            cursor: pointer;
        }
        .minimax-h3-visual-back[hidden] { display: none; }
        .minimax-h3-visual-breadcrumb {
            min-width: 0;
            overflow: hidden;
            color: var(--h3-text-muted);
            font-size: 10.5px;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .minimax-h3-searchable-select-options {
            display: grid;
            min-height: 0;
            flex: 1 1 auto;
            overflow-y: auto;
            overscroll-behavior: contain;
            scrollbar-gutter: stable;
        }
        .minimax-h3-visual-nav-choice {
            display: flex;
            min-width: 0;
            min-height: 44px;
            align-items: center;
            justify-content: space-between;
            gap: var(--h3-space-2);
            border: 0 !important;
            border-bottom: 1px solid var(--h3-border) !important;
            border-radius: 0 !important;
            padding: 7px 8px !important;
            background: transparent !important;
            color: var(--h3-button-text) !important;
            text-align: left;
        }
        .minimax-h3-visual-nav-choice:hover,
        .minimax-h3-visual-nav-choice:focus-visible { background: color-mix(in srgb, var(--h3-accent) 12%, transparent) !important; }
        .minimax-h3-visual-nav-choice strong { min-width: 0; overflow-wrap: anywhere; }
        .minimax-h3-visual-nav-choice span { flex: none; color: var(--h3-text-muted); font-size: 10.5px; }
        .minimax-h3-visual-nav-neutral { border-bottom-style: dashed !important; }
        .minimax-h3-searchable-select-family {
            position: sticky;
            z-index: 1;
            top: 0;
            border-bottom: 1px solid var(--h3-border);
            padding: 9px 7px 5px;
            background: var(--h3-input-bg);
            color: var(--h3-text);
            font-size: 11.5px;
            font-weight: 750;
        }
        .minimax-h3-searchable-select-branch { display: grid; gap: 3px; }
        .minimax-h3-searchable-select-group {
            padding: 6px 7px 2px;
            color: var(--h3-text-muted);
            font-size: 10px;
            font-weight: 700;
            letter-spacing: .04em;
            text-transform: uppercase;
        }
        .minimax-h3-searchable-select-option {
            display: grid;
            min-width: 0;
            min-height: 48px;
            grid-template-columns: 56px minmax(0, 1fr);
            align-items: center;
            gap: var(--h3-space-2);
            border: 1px solid transparent !important;
            padding: 5px 7px !important;
            background: transparent !important;
            text-align: left;
        }
        .minimax-h3-searchable-select-option[data-preview="placeholder"] { grid-template-columns: minmax(0, 1fr); min-height: 36px; }
        .minimax-h3-searchable-select-option:hover,
        .minimax-h3-searchable-select-option:focus-visible,
        .minimax-h3-searchable-select-option[aria-selected="true"] {
            border-color: color-mix(in srgb, var(--h3-accent) 48%, var(--h3-border)) !important;
            background: color-mix(in srgb, var(--h3-accent) 12%, transparent) !important;
        }
        .minimax-h3-visual-preview {
            display: grid;
            width: 56px;
            height: 34px;
            box-sizing: border-box;
            place-items: center;
            overflow: hidden;
            border: 1px dashed var(--h3-border-strong);
            border-radius: 4px;
            background: repeating-linear-gradient(135deg, var(--h3-surface) 0 6px, var(--h3-surface-raised) 6px 12px);
            color: var(--h3-text-muted);
            font-size: 8.5px;
            line-height: 1.1;
            text-align: center;
        }
        img.minimax-h3-visual-preview { border-style: solid; object-fit: cover; }
        .minimax-h3-visual-option-copy { display: grid; min-width: 0; gap: 1px; }
        .minimax-h3-visual-option-copy strong { overflow-wrap: anywhere; font-size: 11.5px; font-weight: 600; }
        .minimax-h3-visual-option-copy small { color: var(--h3-text-muted); font-size: 9.5px; }
        .minimax-h3-visual-preview-notice {
            margin: var(--h3-space-1) 2px 0;
            color: var(--h3-text-muted);
            font-size: 9.5px;
            line-height: 1.35;
        }
        .minimax-h3-mood-options { gap: var(--h3-space-1); }
        .minimax-h3-mood-group { display: grid; min-width: 0; gap: 2px; }
        .minimax-h3-mood-group-heading {
            position: sticky;
            z-index: 1;
            top: 0;
            border-bottom: 1px solid var(--h3-border);
            padding: 8px 7px 4px;
            background: var(--h3-input-bg);
            color: var(--h3-text-muted);
            font-size: 10px;
            font-weight: 750;
            letter-spacing: .04em;
            text-transform: uppercase;
        }
        .minimax-h3-mood-option {
            display: grid;
            min-width: 0;
            min-height: 48px;
            align-content: center;
            gap: 2px;
            border: 1px solid transparent !important;
            padding: 6px 8px !important;
            background: transparent !important;
            color: var(--h3-button-text) !important;
            text-align: left;
        }
        .minimax-h3-mood-option strong { min-width: 0; overflow-wrap: anywhere; font-size: 11.5px; }
        .minimax-h3-mood-option small { color: var(--h3-text-muted); font-size: 10px; line-height: 1.35; overflow-wrap: anywhere; }
        .minimax-h3-mood-option:hover,
        .minimax-h3-mood-option:focus-visible,
        .minimax-h3-mood-option[aria-selected="true"] {
            border-color: color-mix(in srgb, var(--h3-accent) 48%, var(--h3-border)) !important;
            background: color-mix(in srgb, var(--h3-accent) 12%, transparent) !important;
        }
        .minimax-h3-mood-guardrail {
            margin: var(--h3-space-1) 0 0;
            border-top: 1px solid var(--h3-border);
            padding-top: var(--h3-space-2);
            color: var(--h3-text-muted);
            font-size: 10px;
            line-height: 1.4;
        }
        .minimax-h3-select-search-icon {
            position: absolute;
            z-index: 1;
            top: 50%;
            left: 8px;
            transform: translateY(-50%);
            color: var(--h3-text-muted);
            pointer-events: none;
        }
        .minimax-h3-select-search input[type="search"] { width: 100%; padding-right: 30px; padding-left: 27px; }
        .minimax-h3-select-search input[type="search"]::-webkit-search-cancel-button { display: none; }
        .minimax-h3-select-search-clear {
            position: absolute;
            top: 50%;
            right: 3px;
            width: 24px;
            min-height: 24px !important;
            transform: translateY(-50%);
            border: 0 !important;
            padding: 0 !important;
            background: transparent !important;
        }
        .minimax-h3-select-search-clear:disabled { visibility: hidden; }
        .minimax-h3-select-search-status { display: none; margin: 0; color: var(--h3-text-muted); font-size: 11px; }
        .minimax-h3-select-search-status[data-visible="true"] { display: block; }
        .minimax-h3-studio-toolbar { display: flex; min-width: 0; max-width: 100%; flex-wrap: wrap; align-items: center; gap: 7px; margin-bottom: var(--h3-space-3); }
        .minimax-h3-studio-toolbar > * { min-width: 0; max-width: 100%; }
        .minimax-h3-studio-toolbar > div:first-child { display: grid; min-width: 0; margin-right: auto; }
        .minimax-h3-studio-toolbar > div:first-child > span { color: var(--h3-text-muted); font-size: 11.5px; }
        .minimax-h3-studio-status,
        .minimax-h3-source-card {
            border: 1px solid var(--h3-border);
            border-radius: var(--h3-radius-md);
            padding: var(--h3-space-3);
            background: var(--h3-surface);
        }
        .minimax-h3-studio-status[data-kind="malformed"],
        .minimax-h3-source-card[data-kind="malformed"] { border-color: var(--h3-error); background: color-mix(in srgb, var(--h3-error) 12%, var(--h3-surface)); }
        .minimax-h3-studio-status[data-kind="future"],
        .minimax-h3-source-card[data-kind="future"] { border-color: var(--h3-readonly); background: color-mix(in srgb, var(--h3-readonly) 12%, var(--h3-surface)); }
        .minimax-h3-studio-status[data-kind="error"] { border-color: var(--h3-error); background: color-mix(in srgb, var(--h3-error) 12%, var(--h3-surface)); }
        .minimax-h3-studio-status[data-kind="warning"] { border-color: var(--h3-warning); background: color-mix(in srgb, var(--h3-warning) 12%, var(--h3-surface)); }
        .minimax-h3-studio-status[data-kind="stale"] { border-color: var(--h3-readonly); color: var(--h3-text-muted); }
        .minimax-h3-studio-status[data-kind="v1"],
        .minimax-h3-source-card[data-kind="v1"] { border-color: var(--h3-border-strong); }
        .minimax-h3-entity-list { display: grid; gap: 6px; }
        .minimax-h3-entity-card {
            border: 1px solid var(--h3-border);
            border-radius: var(--h3-radius-md);
            padding: var(--h3-space-3);
            background: var(--h3-surface);
        }
        .minimax-h3-entity-card summary { cursor: pointer; font-weight: 600; }

        .minimax-h3-master-detail {
            display: grid;
            min-height: 0;
            grid-template-columns: minmax(0, 1fr);
            gap: var(--h3-space-3);
        }
        .minimax-h3-master-pane,
        .minimax-h3-inspector-pane,
        .minimax-h3-generation-pane {
            display: grid;
            min-width: 0;
            align-content: start;
            gap: var(--h3-space-3);
        }
        .minimax-h3-generation-pane > *,
        .minimax-h3-media-assets > *,
        .minimax-h3-section-media details,
        .minimax-h3-section-media .minimax-h3-studio-editor {
            min-width: 0;
            max-width: 100%;
            box-sizing: border-box;
        }
        @container h3-studio-panel (min-width: 600px) {
            .minimax-h3-master-detail {
                grid-template-columns: var(--h3-list-width) minmax(0, 1fr);
            }
        }
        .minimax-h3-master-list {
            display: grid;
            align-content: start;
            overflow: hidden;
            border: 1px solid var(--h3-border);
            border-radius: var(--h3-radius-md);
            background: var(--h3-surface);
        }
        .minimax-h3-master-row {
            position: relative;
            display: grid;
            min-height: var(--h3-row-height);
            grid-template-columns: minmax(0, 1fr);
            align-items: center;
            gap: 8px;
            border: 0;
            border-bottom: 1px solid var(--h3-border);
            border-radius: 0;
            padding: 7px 10px;
            background: transparent;
            color: var(--h3-text);
            text-align: left;
            cursor: pointer;
        }
        .minimax-h3-master-row:last-child { border-bottom: 0; }
        .minimax-h3-master-row:hover { background: var(--h3-surface-raised); }
        .minimax-h3-master-row[aria-selected="true"],
        .minimax-h3-master-row.is-selected {
            background: color-mix(in srgb, var(--h3-accent) 14%, var(--h3-surface));
            box-shadow: inset 3px 0 var(--h3-accent);
        }
        .minimax-h3-master-row strong,
        .minimax-h3-master-row small { min-width: 0; overflow-wrap: anywhere; }
        .minimax-h3-master-row small { color: var(--h3-text-muted); }
        .minimax-h3-entity-media-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
        .minimax-h3-visual-asset-picker { display: grid; grid-template-columns: repeat(auto-fill, minmax(112px, 1fr)); gap: 8px; }
        .minimax-h3-visual-asset-tile { position: relative; display: grid; min-width: 0; grid-template-rows: 88px auto; overflow: hidden; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-md); background: var(--h3-surface); cursor: pointer; }
        .minimax-h3-visual-asset-tile:hover { border-color: var(--h3-border-strong); }
        .minimax-h3-visual-asset-tile[data-selected="true"] { border-color: var(--h3-accent); box-shadow: 0 0 0 1px var(--h3-accent); }
        .minimax-h3-visual-asset-tile > input { position: absolute; z-index: 1; top: 7px; right: 7px; margin: 0; accent-color: var(--h3-accent); }
        .minimax-h3-visual-asset-preview { display: grid; min-width: 0; place-items: center; overflow: hidden; background: var(--h3-surface-raised); color: var(--h3-text-muted); font-size: 28px; }
        .minimax-h3-visual-asset-preview img { width: 100%; height: 100%; object-fit: cover; }
        .minimax-h3-visual-asset-copy { display: grid; min-width: 0; gap: 1px; padding: 7px 8px; }
        .minimax-h3-visual-asset-copy strong, .minimax-h3-visual-asset-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-visual-asset-copy small { color: var(--h3-text-muted); font-size: 10px; }
        .minimax-h3-shot-mention-row { display: flex; min-width: 0; flex-wrap: wrap; align-items: center; gap: 5px; padding-top: 7px; }
        .minimax-h3-shot-mention-row > span { color: var(--h3-text-muted); font-size: 10px; letter-spacing: .05em; text-transform: uppercase; }
        .minimax-h3-shot-mention-row > button { border-radius: 999px; padding: 3px 8px; }
        .minimax-h3-shot-mention-row > .minimax-h3-shot-subject-chip { display: inline-grid; min-height: 34px; grid-template-columns: 24px minmax(0, auto) 14px; align-items: center; gap: 6px; border: 1px solid var(--h3-border) !important; padding: 3px 7px 3px 4px !important; background: var(--h3-surface) !important; color: var(--h3-text) !important; text-align: left; }
        .minimax-h3-shot-subject-avatar { display: grid; width: 24px; height: 24px; place-items: center; overflow: hidden; border-radius: 50%; background: color-mix(in srgb, var(--h3-accent) 18%, var(--h3-surface)); color: var(--h3-accent); font-size: 10px; font-weight: 750; }
        .minimax-h3-shot-subject-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .minimax-h3-shot-subject-copy { display: grid; min-width: 0; gap: 0; }
        .minimax-h3-shot-subject-copy strong, .minimax-h3-shot-subject-copy small { max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-shot-subject-copy strong { font-size: 10px; }
        .minimax-h3-shot-subject-copy small { color: var(--h3-text-muted); font-size: 8.5px; font-weight: 500; text-transform: none; }
        .minimax-h3-shot-subject-status { color: var(--h3-success) !important; font-size: 11px !important; font-weight: 800; letter-spacing: 0 !important; }
        .minimax-h3-media-row-copy { display: grid; min-width: 0; gap: 2px; }
        .minimax-h3-media-visual {
            position: relative;
            display: grid;
            min-height: 112px;
            place-content: center;
            gap: 5px;
            overflow: hidden;
            border: 1px solid var(--h3-border-strong);
            border-radius: var(--h3-radius-md);
            background:
                linear-gradient(135deg, color-mix(in srgb, var(--h3-accent) 18%, transparent), transparent 55%),
                repeating-linear-gradient(0deg, transparent 0 15px, color-mix(in srgb, var(--h3-border) 35%, transparent) 15px 16px),
                var(--h3-input-bg);
            color: var(--h3-text-muted);
            text-align: center;
        }
        .minimax-h3-media-visual[data-type="video"] { background-color: color-mix(in srgb, var(--h3-tip) 9%, var(--h3-input-bg)); }
        .minimax-h3-media-visual[data-type="audio"] { background-color: color-mix(in srgb, var(--h3-success) 9%, var(--h3-input-bg)); }
        .minimax-h3-media-visual > strong { color: var(--h3-text); font: 700 24px/1 var(--h3-mono); }
        .minimax-h3-media-visual > small { padding-inline: 6px; color: var(--h3-text-muted); font-size: 9.5px; }
        .minimax-h3-media-visual > img,
        .minimax-h3-media-visual > video {
            display: block;
            width: 100%;
            height: 112px;
            object-fit: cover;
            background: #090b0f;
        }
        .minimax-h3-media-visual > audio { width: min(100%, 360px); margin: 10px; }
        .minimax-h3-media-visual[data-physical="ready"] { border-color: color-mix(in srgb, var(--h3-success) 46%, var(--h3-border-strong)); }
        .minimax-h3-media-visual.is-compact { width: 40px; min-height: 40px; border-radius: 5px; }
        .minimax-h3-media-visual.is-compact > img,
        .minimax-h3-media-visual.is-compact > video { width: 40px; height: 40px; }
        .minimax-h3-media-visual.is-compact > strong { font-size: 15px; }
        .minimax-h3-media-visual.is-compact > small { overflow: hidden; font-size: 7.5px; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-media-preview-card {
            display: grid;
            grid-template-columns: minmax(112px, .42fr) minmax(0, 1fr);
            align-items: center;
            gap: var(--h3-space-3);
            border: 1px solid var(--h3-border);
            border-radius: var(--h3-radius-md);
            padding: 8px;
            background: color-mix(in srgb, var(--h3-input-bg) 78%, var(--h3-surface));
        }
        .minimax-h3-media-preview-card > div { display: grid; gap: 4px; }
        .minimax-h3-media-preview-card > div > span { color: var(--h3-text-muted); font-size: 11px; }
        .minimax-h3-inspector,
        .minimax-h3-inspector-body { display: grid; align-content: start; gap: var(--h3-space-3); }
        /* Shot sections need a larger inter-card rhythm than their 12px internal
           rhythm. 16px keeps Story, beats, timing, presence, place, references,
           camera and transitions visually distinct without inflating card bodies. */
        .minimax-h3-section-shots .minimax-h3-shot-inspector {
            row-gap: var(--h3-space-4);
        }
        .minimax-h3-section-shots .minimax-h3-shot-inspector > .minimax-h3-inspector-section,
        .minimax-h3-section-shots .minimax-h3-shot-inspector > .minimax-h3-shot-camera-summary {
            margin-block: 0;
        }
        .minimax-h3-inspector-section,
        .minimax-h3-inspector-block {
            overflow: hidden;
            border: 1px solid var(--h3-border);
            border-radius: var(--h3-radius-md);
            background: var(--h3-surface);
        }
        .minimax-h3-inspector-heading {
            display: flex;
            min-height: 40px;
            align-items: center;
            justify-content: space-between;
            gap: var(--h3-space-2);
            margin: 0;
            padding: 8px 12px;
            background: color-mix(in srgb, var(--h3-surface) 92%, white 8%);
            font-size: 13px;
            font-weight: 650;
        }
        .minimax-h3-inspector-block > summary {
            display: flex;
            min-height: 40px;
            align-items: center;
            padding: 8px 12px;
            cursor: pointer;
            background: color-mix(in srgb, var(--h3-surface) 92%, white 8%);
            font-weight: 650;
        }
        .minimax-h3-inspector-section > .minimax-h3-inspector-body,
        .minimax-h3-inspector-block > .minimax-h3-inspector-body,
        .minimax-h3-inspector-block > .minimax-h3-studio-editor { padding: var(--h3-space-3); }
        .minimax-h3-studio-panel > .minimax-h3-studio-status + .minimax-h3-inspector-block,
        .minimax-h3-studio-panel > .minimax-h3-inspector-block + .minimax-h3-inspector-block {
            margin-top: var(--h3-space-3);
        }
        .minimax-h3-source-state-message { margin: 0; line-height: 1.45; }
        .minimax-h3-inline-repair { margin-top: var(--h3-space-2); }
        .minimax-h3-inline-repair > summary {
            width: fit-content;
            cursor: pointer;
            color: var(--h3-text-muted);
            font-size: 11.5px;
            font-weight: 600;
        }
        .minimax-h3-inline-repair-source {
            width: 100%;
            min-height: 88px !important;
            margin-top: var(--h3-space-2);
            resize: vertical;
            font-family: var(--h3-mono) !important;
            font-size: 11.5px !important;
        }
        .minimax-h3-inline-repair-actions { display: flex; justify-content: flex-start; margin-top: var(--h3-space-2); }
        .minimax-h3-inspector-actions { display: flex; flex-wrap: wrap; gap: var(--h3-space-2); padding-top: var(--h3-space-2); }
        .minimax-h3-field-hint,
        .minimax-h3-usage-note,
        .minimax-h3-panel-help {
            margin: 2px 0 0;
            color: var(--h3-text-muted);
            font-size: 11.5px;
        }
        .minimax-h3-usage-note { padding: 6px 8px; border-left: 2px solid var(--h3-tip); background: color-mix(in srgb, var(--h3-tip) 9%, transparent); }
        .minimax-h3-picker-list,
        .minimax-h3-inline-list,
        .minimax-h3-token-editor,
        .minimax-h3-activation-list { display: grid; gap: 6px; }
        .minimax-h3-picker-option,
        .minimax-h3-token-row,
        .minimax-h3-presence-row,
        .minimax-h3-target-editor,
        .minimax-h3-reference-use,
        .minimax-h3-transition-row,
        .minimax-h3-inline-editor,
        .minimax-h3-activation-row,
        .minimax-h3-binding-row,
        .minimax-h3-state-row,
        .minimax-h3-check-row {
            display: flex;
            min-width: 0;
            flex-wrap: wrap;
            align-items: center;
            gap: 6px;
            border: 1px solid var(--h3-border);
            border-radius: var(--h3-radius-sm);
            padding: 7px;
            background: var(--h3-input-bg);
        }
        .minimax-h3-scale-relationship { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); min-width: 0; gap: var(--h3-space-3); border: 1px solid var(--h3-border); border-radius: var(--h3-radius-md); padding: var(--h3-space-3); background: var(--h3-input-bg); }
        .minimax-h3-scale-relationship > .minimax-h3-button { justify-self: start; }
        .minimax-h3-inline-editor > .minimax-h3-studio-field,
        .minimax-h3-binding-row > .minimax-h3-studio-field,
        .minimax-h3-state-row > .minimax-h3-studio-field {
            flex: 1 1 160px;
            max-width: 100%;
        }
        .minimax-h3-activation-row,
        .minimax-h3-capacity,
        .minimax-h3-inspector-actions > span,
        .minimax-h3-check-row > span { overflow-wrap: anywhere; }
        .minimax-h3-picker-option { width: 100%; justify-content: flex-start; text-align: left; cursor: pointer; }
        .minimax-h3-picker-option:hover { border-color: var(--h3-accent); }
        .minimax-h3-presence-row > label,
        .minimax-h3-check-row,
        .minimax-h3-check-row > label { display: inline-flex; align-items: center; gap: 6px; }
        .minimax-h3-state-chip,
        .minimax-h3-source-chip {
            display: inline-flex;
            min-height: var(--h3-chip-height);
            align-items: center;
            gap: 4px;
            border: 1px solid var(--h3-border-strong);
            border-radius: 999px;
            padding: 1px 7px;
            background: var(--h3-surface);
            color: var(--h3-text-muted);
            font-size: 11px;
        }
        .minimax-h3-chip-picker {
            display: flex;
            min-width: 0;
            max-width: 100%;
            flex-wrap: wrap;
            align-items: center;
            gap: 6px;
        }
        .minimax-h3-provenance,
        .minimax-h3-provenance-row { color: var(--h3-text-muted); font-size: 11.5px; }
        .minimax-h3-provenance.is-conflict,
        .minimax-h3-provenance-row.is-conflict { color: var(--h3-error); }
        .minimax-h3-segmented { display: flex; min-width: 0; max-width: 100%; flex-wrap: wrap; gap: 2px; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-md); padding: 2px; background: var(--h3-input-bg); }
        .minimax-h3-segmented button { border: 0; border-radius: 5px; padding: 3px 9px; background: transparent; }
        .minimax-h3-segmented button[aria-selected="true"],
        .minimax-h3-segmented button[aria-pressed="true"] { background: color-mix(in srgb, var(--h3-accent) 18%, var(--h3-surface)); color: var(--h3-text); }
        .minimax-h3-capacity { margin: 6px 0; color: var(--h3-text-muted); font-variant-numeric: tabular-nums; }
        .minimax-h3-capacity[data-state="error"] { color: var(--h3-error); }
        .minimax-h3-danger { border-color: var(--h3-error) !important; color: color-mix(in srgb, var(--h3-error) 72%, white) !important; }
        .minimax-h3-camera-group { display: grid; gap: var(--h3-space-2); }
        .minimax-h3-camera-group h4 { margin: 0; color: var(--h3-text-muted); font-size: 11.5px; font-weight: 650; letter-spacing: .04em; text-transform: uppercase; }
        .minimax-h3-look-block { min-width: 0; }
        .minimax-h3-look-block > .minimax-h3-studio-editor { min-width: 0; gap: var(--h3-space-4); padding: var(--h3-space-4); }
        .minimax-h3-look-intro-toolbar { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: start; gap: var(--h3-space-3); }
        .minimax-h3-look-intro-toolbar > span { min-width: 0; line-height: 1.45; overflow-wrap: anywhere; }
        .minimax-h3-look-camera .minimax-h3-camera-group { min-width: 0; gap: var(--h3-space-3); border-bottom: 1px solid var(--h3-border); padding-bottom: var(--h3-space-4); }
        .minimax-h3-look-camera .minimax-h3-camera-group:last-child { border-bottom: 0; padding-bottom: 0; }
        .minimax-h3-look-camera .minimax-h3-camera-group h4 { padding: 2px 0; }
        .minimax-h3-look-block .minimax-h3-studio-columns > * { min-width: 0; }
        .minimax-h3-shot-camera-summary {
            display: grid;
            min-width: 0;
            grid-template-columns: minmax(0, 1fr) auto;
            align-items: center;
            gap: var(--h3-space-3);
            border: 1px solid color-mix(in srgb, var(--h3-accent) 34%, var(--h3-border));
            border-radius: var(--h3-radius-md);
            padding: var(--h3-space-3);
            background: color-mix(in srgb, var(--h3-accent) 7%, var(--h3-surface));
        }
        .minimax-h3-shot-camera-summary > div { display: grid; min-width: 0; gap: 3px; }
        .minimax-h3-shot-camera-summary p { margin: 0; color: var(--h3-text-muted); font-size: 11.5px; line-height: 1.4; overflow-wrap: anywhere; }
        .minimax-h3-action-beat { display: grid; min-width: 0; gap: 8px; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-md); padding: 10px; background: color-mix(in srgb, var(--h3-input-bg) 82%, transparent); }
        .minimax-h3-action-beat + .minimax-h3-action-beat { margin-top: 8px; }
        .minimax-h3-action-beat-header { display: flex; min-width: 0; align-items: center; gap: 8px; }
        .minimax-h3-action-beat-header > span { margin-right: auto; color: var(--h3-text-muted); font-size: 10.5px; }
        .minimax-h3-action-beat > input[type="range"] { width: 100%; accent-color: var(--h3-accent); }
        .minimax-h3-action-beat-dialogue { display: grid; min-width: 0; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; border-top: 1px solid var(--h3-border); padding-top: 8px; }
        .minimax-h3-camera-workspace-header {
            display: flex;
            min-width: 0;
            flex-wrap: wrap;
            align-items: flex-start;
            justify-content: space-between;
            gap: var(--h3-space-3);
        }
        .minimax-h3-camera-workspace-header > div { min-width: 220px; flex: 1; }
        .minimax-h3-camera-workspace-header h2,
        .minimax-h3-camera-workspace-header p { margin: 0; }
        .minimax-h3-camera-workspace-header h2 { font-size: 18px; }
        .minimax-h3-camera-workspace-header p { max-width: 70ch; margin-top: 2px; color: var(--h3-text-muted); }
        .minimax-h3-camera-shot-selector {
            display: grid;
            min-width: 0;
            grid-template-columns: minmax(0, 1fr) auto;
            align-items: end;
            gap: var(--h3-space-3);
            border: 1px solid var(--h3-border);
            border-radius: var(--h3-radius-md);
            padding: var(--h3-space-3);
            background: var(--h3-surface);
        }
        .minimax-h3-camera-shot-selector select { width: 100%; min-width: 0; }
        .minimax-h3-camera-workspace { display: grid; min-width: 0; gap: var(--h3-space-3); }
        .minimax-h3-look-row { display: grid; min-width: 0; align-items: end; gap: var(--h3-space-2); }
        .minimax-h3-look-row-library { grid-template-columns: minmax(0, 1fr) auto auto; }
        .minimax-h3-look-row-save { grid-template-columns: minmax(0, 1fr) auto; }
        .minimax-h3-look-row-transfer { display: flex; flex-wrap: wrap; align-items: center; }
        .minimax-h3-look-row > input { width: 100%; min-width: 0; }
        .minimax-h3-provenance-table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
        .minimax-h3-provenance-table th,
        .minimax-h3-provenance-table td { border-bottom: 1px solid var(--h3-border); padding: 7px 8px; text-align: left; }
        .minimax-h3-provenance-table th { color: var(--h3-text-muted); font-size: 11.5px; font-weight: 600; }
        .minimax-h3-provenance-row {
            display: grid;
            grid-template-columns: minmax(110px, .7fr) minmax(120px, 1fr) minmax(150px, 1.2fr);
            align-items: center;
            gap: var(--h3-space-2);
            border-bottom: 1px solid var(--h3-border);
            padding: 7px 8px;
        }
        .minimax-h3-provenance-row:last-child { border-bottom: 0; }

        .minimax-h3-source-card { display: grid; gap: var(--h3-space-2); max-width: 760px; }
        .minimax-h3-source-card h3,
        .minimax-h3-source-card p { margin: 0; }
        .minimax-h3-source-editor {
            width: 100%;
            min-height: 220px;
            box-sizing: border-box;
            border: 1px solid var(--h3-border-strong);
            border-radius: var(--h3-radius-sm);
            padding: var(--h3-space-2);
            background: var(--h3-input-bg);
            font: 12px/1.5 var(--h3-mono) !important;
            resize: vertical;
        }
        .minimax-h3-source-feedback { color: var(--h3-error); font-size: 12px; }
        .minimax-h3-source-feedback[data-valid="true"] { color: var(--h3-success); }
        .minimax-h3-source-actions { display: flex; flex-wrap: wrap; gap: var(--h3-space-2); }
        .minimax-h3-source-raw summary { cursor: pointer; color: var(--h3-text-muted); }
        .minimax-h3-source-raw pre { max-height: 280px; overflow: auto; padding: var(--h3-space-2); background: var(--h3-input-bg); font: 12px/1.5 var(--h3-mono); white-space: pre-wrap; }
        .minimax-h3-source-copy-status { align-self: center; color: var(--h3-text-muted); font-size: 12px; }
        .minimax-h3-source-tools {
            margin-top: var(--h3-space-1);
            border-top: 1px solid var(--h3-border);
            color: var(--h3-text-muted);
        }
        .minimax-h3-source-tools > summary {
            display: flex;
            min-height: 34px;
            align-items: center;
            justify-content: space-between;
            gap: var(--h3-space-2);
            padding: 7px 2px;
            cursor: pointer;
            font-size: 11.5px;
            font-weight: 600;
            list-style-position: inside;
        }
        .minimax-h3-source-tools > summary:hover { color: var(--h3-text); }
        .minimax-h3-source-tools-attention {
            border-radius: 999px;
            padding: 1px 7px;
            background: color-mix(in srgb, var(--h3-warning) 13%, transparent);
            color: var(--h3-warning);
            font-size: 10.5px;
            font-weight: 600;
        }
        .minimax-h3-source-tools-body {
            display: grid;
            gap: var(--h3-space-2);
            padding: var(--h3-space-1) 0 var(--h3-space-3);
        }
        .minimax-h3-source-tools .minimax-h3-source-card[data-kind="v1"] {
            border-color: transparent;
            padding: var(--h3-space-2);
            background: transparent;
            color: var(--h3-text-muted);
        }
        .minimax-h3-source-tools-gate { margin-top: auto; }
        .minimax-h3-source-tools-gate > .minimax-h3-source-card { margin: var(--h3-space-1) 0 var(--h3-space-3); }
        .minimax-h3-source-unavailable { margin: auto 0; }
        .minimax-h3-source-gated { display: flex; min-height: 100%; flex-direction: column; }

        .minimax-h3-overview { display: grid; align-content: start; gap: var(--h3-space-4); }
        .minimax-h3-overview-intro h2 { margin: 0 0 var(--h3-space-1); font-size: 21px; line-height: 1.25; }
        .minimax-h3-overview-intro p { max-width: 66ch; margin: 0; color: var(--h3-text-muted); }
        .minimax-h3-overview-actions { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--h3-space-3); }
        .minimax-h3-overview-action,
        .minimax-h3-overview-section,
        .minimax-h3-overview-health,
        .minimax-h3-preflight,
        .minimax-h3-empty-state {
            border: 1px solid var(--h3-border);
            border-radius: var(--h3-radius-md);
            background: var(--h3-surface);
        }
        .minimax-h3-overview-action { display: flex; min-height: 150px; flex-direction: column; align-items: flex-start; padding: var(--h3-space-4); }
        .minimax-h3-overview-action h3,
        .minimax-h3-overview-section > h3,
        .minimax-h3-overview-health h3,
        .minimax-h3-empty-state h3 { margin: 0; font-size: 15px; font-weight: 650; }
        .minimax-h3-overview-action p { margin: var(--h3-space-2) 0 var(--h3-space-3); color: var(--h3-text-muted); }
        .minimax-h3-overview-action button { margin-top: auto; }
        .minimax-h3-starters { display: grid; gap: var(--h3-space-3); }
        .minimax-h3-starters h3 { margin: 0; font-size: 15px; }
        .minimax-h3-starters p { margin: var(--h3-space-1) 0 0; color: var(--h3-text-muted); }
        .minimax-h3-starter-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--h3-space-2); }
        .minimax-h3-starter-card { display: grid; min-width: 0; align-content: start; gap: 5px; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-md); padding: var(--h3-space-3); background: var(--h3-surface); color: var(--h3-text); text-align: left; }
        .minimax-h3-starter-card span { color: var(--h3-text-muted); font-size: 11.5px; line-height: 1.4; overflow-wrap: anywhere; }
        .minimax-h3-starter-card em { margin-top: var(--h3-space-2); color: var(--h3-tip); font-size: 11px; font-style: normal; font-weight: 700; }
        .minimax-h3-starter-card:hover { border-color: color-mix(in srgb, var(--h3-tip) 58%, var(--h3-border)); background: color-mix(in srgb, var(--h3-tip) 7%, var(--h3-surface)); }
        .minimax-h3-overview-section { padding: var(--h3-space-4); }
        .minimax-h3-pipeline { display: flex; gap: var(--h3-space-2); overflow-x: auto; padding-top: var(--h3-space-3); }
        .minimax-h3-generation-card {
            display: grid;
            min-width: 172px;
            gap: 3px;
            border: 1px solid var(--h3-border-strong);
            border-radius: var(--h3-radius-md);
            padding: var(--h3-space-3);
            background: var(--h3-input-bg);
            color: var(--h3-text);
            text-align: left;
            cursor: pointer;
        }
        .minimax-h3-generation-card span { color: var(--h3-text-muted); font-size: 11.5px; }
        .minimax-h3-library-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--h3-space-2); padding-top: var(--h3-space-3); }
        .minimax-h3-library-card {
            display: grid;
            border: 1px solid var(--h3-border);
            border-radius: var(--h3-radius-sm);
            padding: var(--h3-space-2);
            background: var(--h3-input-bg);
            color: var(--h3-text-muted);
            text-align: left;
            cursor: pointer;
        }
        .minimax-h3-library-card strong { color: var(--h3-text); font-size: 18px; }
        .minimax-h3-overview-health { display: flex; align-items: center; justify-content: space-between; gap: var(--h3-space-3); padding: var(--h3-space-4); }
        .minimax-h3-overview-health p { margin: var(--h3-space-1) 0 0; color: var(--h3-text-muted); }
        .minimax-h3-preflight { display: grid; gap: var(--h3-space-3); padding: var(--h3-space-4); }
        .minimax-h3-preflight[data-status="ready"] { border-color: color-mix(in srgb, var(--h3-success) 45%, var(--h3-border)); }
        .minimax-h3-preflight[data-status="attention"] { border-color: color-mix(in srgb, var(--h3-warning) 45%, var(--h3-border)); }
        .minimax-h3-preflight[data-status="blocked"] { border-color: color-mix(in srgb, var(--h3-error) 48%, var(--h3-border)); }
        .minimax-h3-preflight-header { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: start; gap: var(--h3-space-3); }
        .minimax-h3-preflight-header h3 { margin: 2px 0 var(--h3-space-1); font-size: 15px; }
        .minimax-h3-preflight-header p { margin: 0; color: var(--h3-text-muted); }
        .minimax-h3-preflight-eyebrow { color: var(--h3-text-muted); font-size: 10.5px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; }
        .minimax-h3-preflight-badge { min-width: 42px; border: 1px solid currentColor; border-radius: 999px; padding: 4px 8px; color: var(--h3-success); font-size: 11px; font-weight: 700; text-align: center; }
        .minimax-h3-preflight[data-status="attention"] .minimax-h3-preflight-badge { color: var(--h3-warning); }
        .minimax-h3-preflight[data-status="blocked"] .minimax-h3-preflight-badge { color: var(--h3-error); }
        .minimax-h3-preflight-list { display: grid; gap: 6px; }
        .minimax-h3-preflight-item { display: grid; min-width: 0; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: var(--h3-space-3); border: 1px solid var(--h3-border); border-left: 3px solid var(--h3-warning); border-radius: var(--h3-radius-sm); padding: 7px 9px; background: var(--h3-input-bg); color: var(--h3-text); text-align: left; }
        .minimax-h3-preflight-item[data-severity="error"] { border-left-color: var(--h3-error); }
        .minimax-h3-preflight-item span { min-width: 0; overflow-wrap: anywhere; }
        .minimax-h3-preflight-item strong { color: var(--h3-tip); font-size: 11px; white-space: nowrap; }
        .minimax-h3-source-pills { display: flex; flex-wrap: wrap; gap: 6px; }
        .minimax-h3-source-cards { display: grid; gap: var(--h3-space-2); }
        .minimax-h3-project-transfer { border-top: 1px solid var(--h3-border); padding-top: var(--h3-space-2); }
        .minimax-h3-project-transfer > summary { width: fit-content; cursor: pointer; color: var(--h3-text-muted); font-size: 11.5px; font-weight: 650; }
        .minimax-h3-project-transfer-body { display: grid; gap: var(--h3-space-2); padding-top: var(--h3-space-2); }
        .minimax-h3-project-transfer-body > p { margin: 0; color: var(--h3-text-muted); line-height: 1.45; }
        .minimax-h3-project-transfer textarea { width: 100%; min-height: 112px; box-sizing: border-box; border: 1px solid var(--h3-border-strong); border-radius: var(--h3-radius-sm); padding: 7px; background: var(--h3-input-bg); color: var(--h3-text); font: 11px/1.45 var(--h3-mono); resize: vertical; }
        .minimax-h3-empty-state { padding: var(--h3-space-6); text-align: center; }
        .minimax-h3-empty-state p { margin: var(--h3-space-2) auto var(--h3-space-3); color: var(--h3-text-muted); }
        .minimax-h3-empty-actions { display: flex; justify-content: center; gap: var(--h3-space-2); }

        .minimax-h3-review-toolbar { display: flex; align-items: center; gap: var(--h3-space-3); margin-bottom: var(--h3-space-3); }
        .minimax-h3-review-toolbar h2 { margin: 0; font-size: 18px; }
        .minimax-h3-review-content { display: grid; gap: var(--h3-space-2); }
        .minimax-h3-review-content > .minimax-h3-studio-toolbar { justify-content: space-between; }
        .minimax-h3-review-content > .minimax-h3-studio-toolbar > div { display: grid; }
        .minimax-h3-review-content > .minimax-h3-studio-toolbar span { color: var(--h3-text-muted); font-size: 11.5px; }
        .minimax-h3-review-run-bar { display: grid; grid-template-columns: minmax(220px, 1fr) auto; align-items: center; gap: 10px 14px; margin-bottom: var(--h3-space-3); padding: 12px; border: 1px solid color-mix(in srgb, var(--h3-accent) 34%, var(--h3-border)); border-radius: var(--h3-radius-md); background: color-mix(in srgb, var(--h3-accent) 6%, var(--h3-surface)); }
        .minimax-h3-review-run-bar > div:first-child { display: grid; gap: 3px; }
        .minimax-h3-review-run-bar > div:first-child span { color: var(--h3-text-muted); font-size: 11px; }
        .minimax-h3-review-run-bar > div:nth-child(2) { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 7px; }
        .minimax-h3-review-run-bar > [role="status"] { min-height: 14px; grid-column: 1 / -1; color: var(--h3-success); font-size: 10px; }
        .minimax-h3-review-run-bar > [role="status"][data-valid="false"] { color: var(--h3-danger); }
        .minimax-h3-review-summary { font-variant-numeric: tabular-nums; white-space: nowrap; }
        .minimax-h3-review-dismiss-toggle { margin-left: auto; white-space: nowrap; }
        .minimax-h3-review-group { display: grid; gap: var(--h3-space-2); }
        .minimax-h3-review-group > h3 { margin: var(--h3-space-2) 0 0; font-size: 14px; }
        .minimax-h3-review-card {
            display: grid;
            gap: var(--h3-space-2);
            border: 1px solid var(--h3-border);
            border-left-width: 3px;
            border-radius: var(--h3-radius-md);
            padding: var(--h3-space-3);
            background: var(--h3-surface);
        }
        .minimax-h3-review-card[data-severity="error"] { border-left-color: var(--h3-error); }
        .minimax-h3-review-card[data-severity="warning"] { border-left-color: var(--h3-warning); }
        .minimax-h3-review-card[data-severity="advice"] { border-left-color: var(--h3-tip); }
        .minimax-h3-review-card[data-stale="true"] { opacity: .68; }
        .minimax-h3-review-card[data-resolved="true"] { border-left-color: var(--h3-success); }
        .minimax-h3-review-card[data-dismissed="true"] { opacity: .58; border-left-color: var(--h3-readonly); }
        .minimax-h3-review-card header { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; align-items: center; gap: var(--h3-space-2); }
        .minimax-h3-review-card header span,
        .minimax-h3-review-card footer { color: var(--h3-text-muted); font-size: 11px; }
        .minimax-h3-review-dismiss { min-height: 24px !important; border: 0; padding: 2px 6px; background: transparent; color: var(--h3-text-muted); text-decoration: underline; cursor: pointer; }
        .minimax-h3-review-message { margin: 0; }
        .minimax-h3-review-card blockquote { margin: 0; border-left: 2px solid var(--h3-border-strong); padding-left: var(--h3-space-2); color: var(--h3-text-muted); font-style: italic; }
        .minimax-h3-review-card ul { margin: 0; padding-left: var(--h3-space-6); }
        .minimax-h3-review-actions { display: flex; flex-wrap: wrap; gap: var(--h3-space-2); }
        .minimax-h3-location-chip {
            justify-self: start;
            min-height: var(--h3-chip-height) !important;
            border: 1px solid var(--h3-border-strong);
            border-radius: 999px;
            padding: 1px 8px;
            background: var(--h3-input-bg);
            color: var(--h3-text-muted);
            cursor: pointer;
        }
        .minimax-h3-review-budget { display: grid; gap: var(--h3-space-2); border: 1px solid var(--h3-border); border-radius: var(--h3-radius-md); padding: var(--h3-space-3); background: var(--h3-surface-raised); }
        .minimax-h3-review-budget > header { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: var(--h3-space-2); }
        .minimax-h3-review-budget > header span { color: var(--h3-text-muted); font-size: 11px; }
        .minimax-h3-review-budget > p { margin: 0; font-variant-numeric: tabular-nums; }
        .minimax-h3-review-budget-rows { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1px var(--h3-space-4); }
        .minimax-h3-review-budget-rows > div { display: flex; min-width: 0; justify-content: space-between; gap: var(--h3-space-2); border-top: 1px solid var(--h3-border); padding: 5px 0; }
        .minimax-h3-review-budget-rows span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-transform: capitalize; }
        .minimax-h3-review-budget-rows strong { white-space: nowrap; font-size: 11px; font-variant-numeric: tabular-nums; }
        .minimax-h3-diagnostic-target { outline: 2px solid var(--h3-accent); outline-offset: 3px; border-radius: var(--h3-radius-sm); animation: minimax-h3-diagnostic-pulse .8s ease-out 2; }
        @keyframes minimax-h3-diagnostic-pulse { 50% { outline-color: color-mix(in srgb, var(--h3-accent) 35%, transparent); } }

        @container h3-studio (max-width: 799px) {
            .minimax-h3-overview-actions { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .minimax-h3-starter-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .minimax-h3-saved-state { display: none; }
        }
        @container h3-studio (max-width: 559px) {
            .minimax-h3-scale-relationship { grid-template-columns: minmax(0, 1fr); }
            .minimax-h3-studio-grid,
            .minimax-h3-master-detail { grid-template-columns: 1fr; }
            .minimax-h3-virtual-list { height: min(36vh, 320px); }
            .minimax-h3-overview-actions { grid-template-columns: 1fr; }
            .minimax-h3-starter-grid { grid-template-columns: 1fr; }
            .minimax-h3-overview-action { min-height: 0; }
            .minimax-h3-overview-health { align-items: flex-start; flex-direction: column; }
            .minimax-h3-preflight-header,
            .minimax-h3-preflight-item { grid-template-columns: minmax(0, 1fr); }
            .minimax-h3-preflight-badge { justify-self: start; }
            .minimax-h3-saved-state { display: none; }
            .minimax-h3-production-context { grid-template-columns: repeat(3, minmax(0, 1fr)); }
            .minimax-h3-production-context-item[data-context-key="generations"],
            .minimax-h3-production-context-item[data-context-key="media"] { display: none; }
            .minimax-h3-shot-timeline-heading { align-items: flex-start; flex-direction: column; }
            .minimax-h3-header-main { flex-wrap: wrap; align-items: flex-start; }
            .minimax-h3-header-identity { flex-basis: 100%; }
            .minimax-h3-header-state { width: 100%; justify-content: flex-end; }
            .minimax-h3-header-state { gap: 2px; }
            .minimax-h3-review-label { max-width: 104px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            .minimax-h3-review-content > .minimax-h3-studio-toolbar { align-items: flex-start; }
            .minimax-h3-review-summary { order: 2; }
            .minimax-h3-review-dismiss-toggle { order: 3; flex-basis: 100%; margin-left: 0; }
            .minimax-h3-review-budget-rows { grid-template-columns: 1fr; }
            .minimax-h3-review-card header { grid-template-columns: minmax(0, 1fr) auto; }
            .minimax-h3-review-card header > span { grid-column: 1; }
            .minimax-h3-action-beat-dialogue { grid-template-columns: minmax(0, 1fr); }
        }
        @container h3-studio (max-width: 479px) {
            .minimax-h3-reference-card-grid,
            .minimax-h3-reference-output-list { grid-template-columns: minmax(0, 1fr); }
            .minimax-h3-studio-body { grid-template-columns: var(--h3-rail-compact-width) minmax(0, 1fr); }
            .minimax-h3-tab-label { display: none; }
            .minimax-h3-studio-tab { min-height: 42px; }
            .minimax-h3-rail-collapse { display: none; }
            .minimax-h3-studio-panel { padding: var(--h3-space-3); }
            .minimax-h3-studio-columns,
            .minimax-h3-library-grid,
            .minimax-h3-provenance-row { grid-template-columns: 1fr; }
            .minimax-h3-shot-camera-summary,
            .minimax-h3-camera-shot-selector { grid-template-columns: minmax(0, 1fr); align-items: start; }
        }
        @media (max-width: 699px) {
            .minimax-h3-studio { width: 100vw !important; border-left: 0; }
            .minimax-h3-studio-resizer { display: none; }
        }
        @media (min-width: 2160px) {
            .minimax-h3-studio-panel { padding: var(--h3-space-6); }
        }
        @media (prefers-reduced-motion: reduce) {
            .minimax-h3-studio,
            .minimax-h3-studio *,
            .minimax-h3-dashboard * { scroll-behavior: auto !important; transition: none !important; animation: none !important; }
        }
        .minimax-h3-look-detail-mode {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: var(--h3-space-4);
            padding: var(--h3-space-3) var(--h3-space-4);
            border: 1px solid var(--h3-border);
            border-radius: var(--h3-radius-md);
            background: var(--h3-surface-raised);
        }
        .minimax-h3-look-detail-mode p {
            margin: var(--h3-space-1) 0 0;
            color: var(--h3-text-muted);
        }
        .minimax-h3-look-detail-mode .minimax-h3-detail-mode { flex: 0 0 auto; }
        @container h3-studio (max-width: 479px) {
            .minimax-h3-look-detail-mode { align-items: stretch; flex-direction: column; }
            .minimax-h3-look-detail-mode .minimax-h3-detail-mode { align-self: flex-start; }
        }

        .minimax-h3-director-workspace-header {
            display: flex; align-items: flex-start; justify-content: space-between; gap: var(--h3-space-4);
            margin-bottom: var(--h3-space-4);
        }
        .minimax-h3-section-storyboard { padding: 0; }
        .minimax-h3-section-storyboard > .minimax-h3-director-workspace-header {
            margin: var(--h3-space-4) var(--h3-space-4) 0;
            padding-top: var(--h3-space-1);
        }
        .minimax-h3-section-storyboard > :not(.minimax-h3-director-workspace-header):not(.minimax-h3-director-shot-context) {
            width: calc(100% - (2 * var(--h3-space-4)));
            margin-right: var(--h3-space-4);
            margin-left: var(--h3-space-4);
        }
        .minimax-h3-director-workspace-header h2 { margin: 0; font-size: 20px; }
        .minimax-h3-director-workspace-header p { margin: 4px 0 0; color: var(--h3-text-muted); }
        .minimax-h3-director-shot-context { position: sticky; z-index: 12; top: 0; display: grid; gap: 8px; margin: 0 0 var(--h3-space-4); padding: 9px var(--h3-space-4) 7px; border-bottom: 1px solid var(--h3-border); background: var(--h3-surface); box-shadow: 0 8px 18px color-mix(in srgb, #000 18%, transparent); isolation: isolate; }
        .minimax-h3-director-shot-context-top { display: grid; grid-template-columns: minmax(220px, 1fr) auto auto; align-items: center; gap: 10px; }
        .minimax-h3-director-shot-context-identity { display: grid; min-width: 0; gap: 2px; }
        .minimax-h3-director-shot-context-identity > strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-director-shot-context-meta { display: flex; min-width: 0; flex-wrap: wrap; align-items: center; gap: 5px; color: var(--h3-text-muted); font-size: 10px; }
        .minimax-h3-director-shot-context-meta > span:not(.minimax-h3-scope-chip)::after { margin-left: 5px; color: var(--h3-border-strong); content: "·"; }
        .minimax-h3-scope-chip { display: inline-flex; min-height: 22px; align-items: center; border: 1px solid color-mix(in srgb, var(--h3-accent) 38%, var(--h3-border)); border-radius: 999px; padding: 2px 7px; background: color-mix(in srgb, var(--h3-accent) 10%, var(--h3-surface)); color: var(--h3-accent); font-size: 9px; font-weight: 750; white-space: nowrap; }
        .minimax-h3-director-mode-switch { display: inline-flex; flex-wrap: wrap; gap: 3px; padding: 3px; border: 1px solid var(--h3-border); border-radius: 999px; background: var(--h3-surface); }
        .minimax-h3-director-mode { min-height: 30px; border: 0 !important; border-radius: 999px !important; padding: 4px 11px !important; background: transparent !important; color: var(--h3-text-muted) !important; }
        .minimax-h3-director-mode[aria-selected="true"] { background: color-mix(in srgb, var(--h3-accent) 22%, var(--h3-surface-raised)) !important; color: var(--h3-text) !important; }
        .minimax-h3-director-scene-strip { display: flex; gap: var(--h3-space-2); margin: 0; padding: 0 0 2px; overflow-x: auto; scroll-snap-type: x proximity; }
        .minimax-h3-director-scene-card { display: grid; flex: 0 0 210px; grid-template-columns: 28px minmax(0, 1fr); gap: 2px 8px; min-height: 82px; border: 1px solid var(--h3-border) !important; border-radius: var(--h3-radius-md) !important; padding: 9px !important; background: var(--h3-surface) !important; text-align: left; scroll-snap-align: start; }
        .minimax-h3-director-scene-card[data-selected="true"] { border-color: var(--h3-accent) !important; box-shadow: inset 0 0 0 1px var(--h3-accent); background: color-mix(in srgb, var(--h3-accent) 9%, var(--h3-surface)) !important; }
        .minimax-h3-director-scene-card[data-drag="before"] { border-left: 4px solid var(--h3-accent) !important; transform: translateX(2px); }
        .minimax-h3-director-scene-card strong, .minimax-h3-director-scene-card small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-director-scene-card small { grid-column: 2; color: var(--h3-text-muted); }
        .minimax-h3-director-scene-camera { color: color-mix(in srgb, var(--h3-accent) 72%, var(--h3-text-muted)) !important; font-size: 10px; }
        .minimax-h3-director-scene-number { grid-row: 1 / 3; color: var(--h3-accent); font-weight: 750; }
        .minimax-h3-director-add-scene { flex: 0 0 86px; min-height: 66px; border: 1px dashed var(--h3-border) !important; border-radius: var(--h3-radius-md) !important; background: transparent !important; }
        .minimax-h3-files-toolbar { display: flex; align-items: center; justify-content: space-between; gap: var(--h3-space-3); margin-bottom: var(--h3-space-3); }
        .minimax-h3-files-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: var(--h3-space-3); }
        .minimax-h3-file-card { display: grid; grid-template-columns: 64px minmax(0, 1fr); gap: 8px; align-items: center; overflow: hidden; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-lg); padding: 8px; background: var(--h3-surface-raised); }
        .minimax-h3-file-card[data-ready="false"] { border-style: dashed; }
        .minimax-h3-file-preview { display: grid; width: 64px; height: 64px; place-items: center; overflow: hidden; border-radius: var(--h3-radius-md); background: color-mix(in srgb, var(--h3-accent) 12%, var(--h3-surface)); color: var(--h3-accent); font-size: 22px; }
        .minimax-h3-file-preview img, .minimax-h3-file-preview video { width: 100%; height: 100%; object-fit: cover; }
        .minimax-h3-file-copy { display: grid; min-width: 0; gap: 3px; }
        .minimax-h3-file-copy strong, .minimax-h3-file-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-file-copy small { color: var(--h3-text-muted); text-transform: capitalize; }
        .minimax-h3-file-card > button { grid-column: 1 / -1; justify-self: stretch; }
        .minimax-h3-director-asset-tray { display: grid; gap: 8px; margin-bottom: var(--h3-space-4); padding: 10px; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-lg); background: var(--h3-surface); }
        .minimax-h3-director-tray-header { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
        .minimax-h3-director-tray-header div { font-weight: 750; }
        .minimax-h3-director-tray-header span { color: var(--h3-text-muted); font-size: 11px; }
        .minimax-h3-director-asset-rail { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 2px; }
        .minimax-h3-director-asset-card { display: grid; flex: 0 0 154px; grid-template-columns: 42px minmax(0, 1fr); align-items: center; gap: 8px; min-height: 52px; border: 1px solid var(--h3-border) !important; border-radius: var(--h3-radius-md) !important; padding: 5px !important; background: var(--h3-surface-raised) !important; text-align: left; cursor: grab; }
        .minimax-h3-director-asset-card:active { cursor: grabbing; }
        .minimax-h3-director-asset-card[data-selected="true"] { border-color: var(--h3-accent) !important; box-shadow: inset 0 0 0 1px var(--h3-accent); }
        .minimax-h3-director-asset-visual { display: grid; width: 42px; height: 42px; place-items: center; overflow: hidden; border-radius: var(--h3-radius-sm); background: color-mix(in srgb, var(--h3-accent) 12%, var(--h3-surface)); color: var(--h3-accent); }
        .minimax-h3-director-asset-visual img, .minimax-h3-director-asset-visual video { width: 100%; height: 100%; object-fit: cover; }
        .minimax-h3-director-asset-copy { display: grid; min-width: 0; gap: 2px; }
        .minimax-h3-director-asset-copy strong, .minimax-h3-director-asset-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-director-asset-copy small { color: var(--h3-text-muted); text-transform: capitalize; }
        .minimax-h3-director-tray-empty { flex: 1 1 auto; min-height: 48px; border: 1px dashed var(--h3-border) !important; border-radius: var(--h3-radius-md) !important; background: transparent !important; color: var(--h3-text-muted) !important; }
        .minimax-h3-director-compose-grid { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(280px, .75fr); gap: var(--h3-space-3); }
        .minimax-h3-director-stage { position: relative; display: grid; min-height: 370px; grid-template-rows: auto auto auto auto; overflow: hidden; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-lg); background: radial-gradient(circle at 50% 20%, color-mix(in srgb, var(--h3-accent) 14%, transparent), transparent 43%), linear-gradient(180deg, var(--h3-surface-raised), var(--h3-surface)); }
        .minimax-h3-director-backdrop { display: flex; align-items: center; justify-content: space-between; gap: var(--h3-space-3); padding: 12px 14px; border-bottom: 1px solid var(--h3-border); background: color-mix(in srgb, var(--h3-surface-raised) 80%, transparent); }
        .minimax-h3-director-backdrop > div { display: grid; gap: 3px; }
        .minimax-h3-director-backdrop-media { display: flex !important; min-width: 0; margin-left: auto; }
        .minimax-h3-director-kicker { color: var(--h3-text-muted); font-size: 10px; font-weight: 750; letter-spacing: .08em; }
        .minimax-h3-director-cast { display: flex; align-items: flex-start; justify-content: center; flex-wrap: wrap; gap: var(--h3-space-3); min-height: 84px; padding: var(--h3-space-4); border: 1px solid transparent; border-radius: var(--h3-radius-lg); transition: border-color .15s ease, background .15s ease; }
        .minimax-h3-director-cast[data-subject-drag-over="true"] { border-color: var(--h3-accent); background: color-mix(in srgb, var(--h3-accent) 12%, transparent); }
        .minimax-h3-director-empty-subject-target { min-height: 82px; max-width: 280px; border: 1px dashed color-mix(in srgb, var(--h3-accent) 58%, var(--h3-border)) !important; border-radius: var(--h3-radius-lg) !important; padding: 14px 18px !important; background: color-mix(in srgb, var(--h3-accent) 6%, transparent) !important; color: var(--h3-text-muted) !important; }
        .minimax-h3-director-empty-subject-target[data-drag="ready"] { border-style: solid !important; background: color-mix(in srgb, var(--h3-accent) 22%, var(--h3-surface)) !important; color: var(--h3-text) !important; }
        .minimax-h3-director-subject-card { min-width: 220px; max-width: 320px; border: 1px solid color-mix(in srgb, var(--h3-accent) 40%, var(--h3-border)); border-radius: var(--h3-radius-lg); background: color-mix(in srgb, var(--h3-surface-raised) 88%, transparent); overflow: clip; }
        .minimax-h3-director-subject-summary { display: grid; grid-template-columns: 44px minmax(0, 1fr) auto; align-items: center; gap: 9px; min-height: 62px; padding: 8px 10px; cursor: pointer; list-style: none; }
        .minimax-h3-director-subject-summary::-webkit-details-marker { display: none; }
        .minimax-h3-director-subject-summary::after { content: "⌄"; grid-column: 3; grid-row: 1; align-self: start; color: var(--h3-text-muted); transition: transform .15s ease; }
        .minimax-h3-director-subject-card[open] > .minimax-h3-director-subject-summary::after { transform: rotate(180deg); }
        .minimax-h3-director-subject-summary .minimax-h3-director-avatar { width: 42px; height: 42px; border-width: 1px; font-size: 16px; }
        .minimax-h3-director-subject-summary-copy { display: grid; min-width: 0; gap: 2px; }
        .minimax-h3-director-subject-summary-copy > strong, .minimax-h3-director-subject-summary-copy > small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-director-subject-status { display: flex; grid-column: 2 / 4; gap: 5px; margin-top: -3px; color: var(--h3-text-muted); }
        .minimax-h3-director-subject-status small { padding: 1px 5px; border-radius: 999px; background: var(--h3-surface-2); font-size: 9px; }
        .minimax-h3-director-subject-expanded { display: grid; gap: 9px; padding: 0 10px 10px; border-top: 1px solid var(--h3-border); }
        .minimax-h3-director-llm-subject { margin-top: -5px; color: var(--h3-text-muted); font-size: 10px; }
        .minimax-h3-director-avatar { display: grid; width: 64px; height: 64px; place-items: center; overflow: hidden; border: 2px solid color-mix(in srgb, var(--h3-accent) 44%, var(--h3-border)); border-radius: 50%; background: color-mix(in srgb, var(--h3-accent) 24%, var(--h3-surface)); color: var(--h3-accent); font-size: 22px; font-weight: 800; }
        .minimax-h3-director-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .minimax-h3-director-bound-strip { display: flex; width: 100%; flex-wrap: wrap; justify-content: center; gap: 5px; }
        .minimax-h3-director-bound-media { display: grid; min-width: 0; max-width: 84px; gap: 3px; justify-items: center; padding: 4px; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-sm); background: color-mix(in srgb, var(--h3-surface) 78%, transparent); }
        .minimax-h3-director-bound-media small { display: block; width: 100%; overflow: hidden; color: var(--h3-text-muted); font-size: 9px; text-align: center; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-director-bound-media .minimax-h3-director-asset-visual { width: 46px; height: 38px; border-radius: 5px; }
        .minimax-h3-director-narrative { display: grid; gap: 10px; padding-bottom: 12px; border-top: 1px solid var(--h3-border); background: color-mix(in srgb, var(--h3-surface) 90%, transparent); }
        .minimax-h3-director-action, .minimax-h3-director-camera-line { padding: 11px 14px; border-top: 1px solid var(--h3-border); }
        .minimax-h3-director-action { display: grid; gap: 5px; }
        .minimax-h3-director-narrative .minimax-h3-director-action { border-top: 0; }
        .minimax-h3-director-narrative .minimax-h3-director-dialogue-sound { margin: 0 12px; }
        .minimax-h3-director-action textarea { min-height: 62px; resize: vertical; border-color: transparent; background: color-mix(in srgb, var(--h3-surface-raised) 72%, transparent); }
        .minimax-h3-director-action textarea:hover, .minimax-h3-director-action textarea:focus { border-color: var(--h3-border); background: var(--h3-surface-raised); }
        .minimax-h3-director-camera-line { display: grid; width: 100%; gap: 9px; border-right: 0 !important; border-bottom: 0 !important; border-left: 0 !important; border-radius: 0 !important; background: color-mix(in srgb, var(--h3-accent) 5%, var(--h3-surface)) !important; color: var(--h3-text) !important; text-align: left; cursor: pointer; }
        .minimax-h3-director-camera-line:hover { background: color-mix(in srgb, var(--h3-accent) 11%, var(--h3-surface)) !important; }
        .minimax-h3-director-camera-heading { display: flex; align-items: center; gap: 8px; }
        .minimax-h3-director-camera-heading strong { color: var(--h3-accent); font-size: 11px; }
        .minimax-h3-director-camera-edit { margin-left: auto; color: var(--h3-text-muted); font-size: 10px; }
        .minimax-h3-director-camera-phases { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
        .minimax-h3-director-camera-phase { display: grid; min-width: 0; grid-template-columns: 22px minmax(0, 1fr); gap: 0 6px; padding: 7px 8px; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-sm); background: var(--h3-surface-raised); }
        .minimax-h3-director-camera-phase b { display: grid; grid-row: 1 / 3; width: 22px; height: 22px; place-items: center; align-self: center; border-radius: 50%; background: color-mix(in srgb, var(--h3-accent) 18%, var(--h3-surface)); color: var(--h3-accent); font-size: 11px; }
        .minimax-h3-director-camera-phase small { color: var(--h3-text-muted); font-size: 9px; text-transform: uppercase; }
        .minimax-h3-director-camera-phase > span { overflow: hidden; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-director-lanes { display: grid; gap: 6px; grid-column: 1; padding: 12px; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-lg); background: var(--h3-surface); }
        .minimax-h3-director-lanes h3 { margin: 0 0 4px; }
        .minimax-h3-director-reference-actions { display: flex; align-items: center; gap: 7px; }
        .minimax-h3-director-subject-targets { display: flex; flex-wrap: wrap; justify-content: center; gap: 4px; }
        .minimax-h3-director-drop-wrapper { display: inline-flex; align-items: center; gap: 4px; flex-wrap: wrap; }
        .minimax-h3-reference-scope { padding: 2px 6px; border-radius: 999px; background: var(--h3-surface-strong); color: var(--h3-text-muted); font-size: 9px; font-weight: 700; white-space: nowrap; }
        .minimax-h3-director-drop-wrapper .minimax-h3-director-drop-target { border-radius: 999px 0 0 999px !important; }
        .minimax-h3-director-drop-import { min-width: 24px; min-height: 26px; border: 1px dashed color-mix(in srgb, var(--h3-accent) 52%, var(--h3-border)) !important; border-left: 0 !important; border-radius: 0 999px 999px 0 !important; padding: 2px 6px !important; background: color-mix(in srgb, var(--h3-accent) 7%, transparent) !important; color: var(--h3-accent) !important; font-size: 13px !important; }
        .minimax-h3-director-drop-import:hover { border-style: solid !important; background: color-mix(in srgb, var(--h3-accent) 22%, var(--h3-surface)) !important; }
        .minimax-h3-director-drop-wrapper[data-connected="true"] .minimax-h3-director-drop-import { border-radius: 0 !important; }
        .minimax-h3-director-drop-disconnect { min-width: 24px; min-height: 26px; border: 1px solid var(--h3-border) !important; border-left: 0 !important; border-radius: 0 999px 999px 0 !important; padding: 2px 6px !important; background: var(--h3-surface-2) !important; color: var(--h3-muted) !important; font-size: 15px !important; cursor: pointer; }
        .minimax-h3-director-drop-disconnect:hover { border-color: var(--h3-danger) !important; color: var(--h3-danger) !important; }
        .minimax-h3-director-drop-target { min-height: 26px; border: 1px dashed color-mix(in srgb, var(--h3-accent) 52%, var(--h3-border)) !important; border-radius: 999px !important; padding: 3px 8px !important; background: color-mix(in srgb, var(--h3-accent) 7%, transparent) !important; color: var(--h3-text-muted) !important; font-size: 10px !important; white-space: nowrap; }
        .minimax-h3-director-drop-target:not(:disabled):hover, .minimax-h3-director-drop-target[data-drag="ready"] { border-style: solid !important; background: color-mix(in srgb, var(--h3-accent) 24%, var(--h3-surface)) !important; color: var(--h3-text) !important; }
        .minimax-h3-director-drop-target[data-connected="true"] { border-style: solid !important; border-color: color-mix(in srgb, var(--h3-success) 62%, var(--h3-border)) !important; color: var(--h3-success) !important; }
        .minimax-h3-director-drop-target[data-drag="invalid"] { border-color: var(--h3-danger) !important; color: var(--h3-danger) !important; }
        .minimax-h3-director-drop-target:disabled { opacity: .34; }
        .minimax-h3-director-lane { display: grid; grid-template-columns: 108px minmax(0, 1fr) auto; align-items: center; gap: 10px; padding: 7px 9px; border-radius: var(--h3-radius-sm); background: var(--h3-surface-raised); }
        .minimax-h3-director-lane span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-director-lane .is-empty, .minimax-h3-director-placeholder { color: var(--h3-text-muted); font-style: italic; }
        .minimax-h3-director-lane-guidance { color: var(--h3-text-muted); white-space: nowrap; }
        .minimax-h3-director-direction { display: grid; gap: 9px; grid-column: 1; padding: 12px; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-lg); background: var(--h3-surface); }
        .minimax-h3-director-direction h3 { margin: 0 0 4px; }
        .minimax-h3-director-direction-cards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
        .minimax-h3-director-direction-card { display: grid; min-width: 0; gap: 7px; padding: 10px !important; border: 1px solid var(--h3-border) !important; border-radius: var(--h3-radius-md) !important; background: var(--h3-surface-raised) !important; color: var(--h3-text) !important; text-align: left; }
        .minimax-h3-director-direction-card:hover { border-color: color-mix(in srgb, var(--h3-accent) 62%, var(--h3-border)) !important; background: color-mix(in srgb, var(--h3-accent) 8%, var(--h3-surface-raised)) !important; }
        .minimax-h3-director-direction-summary { overflow: hidden; color: var(--h3-text-muted); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-director-inspector { display: flex; min-width: 0; max-width: 100%; grid-column: 2; grid-row: 1 / 4; flex-direction: column; align-self: start; gap: var(--h3-space-3); overflow: hidden; box-sizing: border-box; padding: 14px; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-lg); background: var(--h3-surface-raised); }
        .minimax-h3-director-inspector h3 { margin: -5px 0 2px; }
        .minimax-h3-director-scene-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
        .minimax-h3-director-scene-heading > div:first-child { display: grid; gap: 3px; }
        .minimax-h3-director-scene-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 3px; }
        .minimax-h3-director-scene-actions .minimax-h3-director-text-button { min-height: 24px; padding: 2px 6px !important; font-size: 9px !important; }
        .minimax-h3-director-scene-actions .minimax-h3-director-delete { color: var(--h3-warning) !important; }
        .minimax-h3-director-scene-actions .minimax-h3-director-delete-confirm { color: var(--h3-error) !important; }
        .minimax-h3-director-inspector textarea { min-height: 104px; }
        .minimax-h3-director-scene-setup { display: grid; min-width: 0; gap: 9px; padding: 10px 14px; border-bottom: 1px solid var(--h3-border); background: color-mix(in srgb, var(--h3-surface-raised) 82%, transparent); }
        .minimax-h3-director-scene-setup .minimax-h3-studio-field,
        .minimax-h3-director-scene-setup select { min-width: 0; max-width: 100%; }
        .minimax-h3-director-inspector-heading { display: grid; min-width: 0; gap: 6px; }
        .minimax-h3-director-dialogue-sound { display: grid; gap: 8px; padding: 10px; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-md); background: var(--h3-surface); }
        .minimax-h3-director-dialogue-form { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; padding: 8px; border: 1px solid color-mix(in srgb, var(--h3-accent) 38%, var(--h3-border)); border-radius: var(--h3-radius-sm); background: color-mix(in srgb, var(--h3-accent) 5%, transparent); }
        .minimax-h3-director-dialogue-field { display: grid; min-width: 0; gap: 4px; color: var(--h3-text-muted); font-size: 9px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }
        .minimax-h3-director-dialogue-field.is-wide { grid-column: 1 / -1; }
        .minimax-h3-director-dialogue-field select, .minimax-h3-director-dialogue-field textarea { min-width: 0; width: 100%; color: var(--h3-text); font-size: 10px; font-weight: 400; letter-spacing: normal; text-transform: none; }
        .minimax-h3-director-dialogue-field textarea { min-height: 66px; resize: vertical; }
        .minimax-h3-director-dialogue-form .minimax-h3-director-inline-status { grid-column: 1 / -1; }
        .minimax-h3-director-sound-group { display: grid; gap: 5px; padding-top: 7px; border-top: 1px solid var(--h3-border); }
        .minimax-h3-director-sound-group > small:not(.minimax-h3-director-kicker) { color: var(--h3-text-muted); font-size: 9px; }
        .minimax-h3-director-voice-row, .minimax-h3-director-audio-reference-row { display: grid; gap: 5px; padding: 6px; border-radius: var(--h3-radius-sm); background: var(--h3-surface-raised); }
        .minimax-h3-director-voice-row > span { display: grid; gap: 2px; }
        .minimax-h3-director-voice-row b { font-size: 10px; }
        .minimax-h3-director-voice-row small { color: var(--h3-text-muted); font-size: 9px; }
        .minimax-h3-director-dialogue-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 6px; padding: 7px; border-left: 2px solid var(--h3-accent); border-radius: var(--h3-radius-sm); background: var(--h3-surface-raised); }
        .minimax-h3-director-dialogue-row > span { display: grid; min-width: 0; gap: 3px; }
        .minimax-h3-director-dialogue-row b, .minimax-h3-director-dialogue-row q { overflow: hidden; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-director-dialogue-row small { color: var(--h3-text-muted); font-size: 9px; }
        .minimax-h3-director-audio-player { width: 100%; max-width: 230px; height: 28px; }
        .minimax-h3-audio-trim { display: grid; gap: 8px; min-width: 0; padding: 9px; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-sm); background: color-mix(in srgb, var(--h3-surface-raised) 82%, transparent); }
        .minimax-h3-audio-trim-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
        .minimax-h3-audio-trim-heading strong { font-size: 10px; }
        .minimax-h3-audio-trim-heading small, .minimax-h3-audio-trim-status { color: var(--h3-text-muted); font-size: 9px; }
        .minimax-h3-audio-trim-timeline { position: relative; height: 54px; overflow: hidden; border-radius: 5px; background: var(--h3-surface); }
        .minimax-h3-audio-waveform { width: 100%; height: 54px; opacity: .82; }
        .minimax-h3-audio-trim-selection { position: absolute; inset-block: 0; border-inline: 2px solid var(--h3-accent); background: color-mix(in srgb, var(--h3-accent) 20%, transparent); pointer-events: none; }
        .minimax-h3-audio-trim-ranges { position: relative; height: 18px; }
        .minimax-h3-audio-trim-ranges input { position: absolute; inset: 0; width: 100%; margin: 0; background: transparent; pointer-events: none; }
        .minimax-h3-audio-trim-ranges input::-webkit-slider-thumb { pointer-events: auto; }
        .minimax-h3-audio-trim-times { display: grid; grid-template-columns: 74px 74px minmax(0, 1fr); align-items: center; gap: 6px; }
        .minimax-h3-audio-trim-times input { min-width: 0; }
        .minimax-h3-audio-trim-duration { justify-self: end; color: var(--h3-text-muted); font-size: 9px; }
        .minimax-h3-audio-trim-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
        .minimax-h3-audio-trim > audio { display: none; }
        .minimax-h3-audio-trim-status[data-valid="false"] { color: var(--error-text, #ff8b8b); }
        .minimax-h3-director-ambience-note { margin: 0; padding: 7px; border-radius: var(--h3-radius-sm); background: color-mix(in srgb, var(--h3-accent) 6%, transparent); color: var(--h3-text-muted); font-size: 9px; line-height: 1.4; }
        .minimax-h3-director-setup-actions { display: flex; min-width: 0; flex-wrap: wrap; align-items: center; justify-content: flex-start; gap: 4px 7px; }
        .minimax-h3-director-text-button { min-height: 24px; border: 0 !important; padding: 2px 4px !important; background: transparent !important; color: var(--h3-accent) !important; font-size: 11px !important; }
        .minimax-h3-director-inline-creator { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: 6px; padding: 8px; border: 1px solid color-mix(in srgb, var(--h3-accent) 42%, var(--h3-border)); border-radius: var(--h3-radius-md); background: color-mix(in srgb, var(--h3-accent) 7%, var(--h3-surface)); }
        .minimax-h3-director-inline-creator input { min-width: 0; }
        .minimax-h3-director-inline-status { grid-column: 1 / -1; color: var(--h3-danger); font-size: 11px; }
        .minimax-h3-director-cast-picker { display: flex; flex-wrap: wrap; gap: 5px; }
        .minimax-h3-director-cast-chip { min-height: 28px; border: 1px solid var(--h3-border) !important; border-radius: 999px !important; padding: 3px 9px !important; background: var(--h3-surface) !important; color: var(--h3-text-muted) !important; }
        .minimax-h3-director-cast-chip[aria-pressed="true"] { border-color: var(--h3-accent) !important; background: color-mix(in srgb, var(--h3-accent) 18%, var(--h3-surface)) !important; color: var(--h3-text) !important; }
        .minimax-h3-director-cast-chip[data-drag="ready"] { border-color: var(--h3-accent) !important; box-shadow: 0 0 0 2px color-mix(in srgb, var(--h3-accent) 25%, transparent); background: color-mix(in srgb, var(--h3-accent) 24%, var(--h3-surface)) !important; color: var(--h3-text) !important; }
        .minimax-h3-director-scene-summary { display: grid; grid-template-columns: 1fr auto; gap: 7px 12px; margin: 0; padding: 10px 0; border-block: 1px solid var(--h3-border); }
        .minimax-h3-director-scene-summary dt { color: var(--h3-text-muted); }
        .minimax-h3-director-scene-summary dd { margin: 0; font-weight: 650; }
        .minimax-h3-director-llm-handoff { display: grid; gap: 7px; padding: 10px; border: 1px solid color-mix(in srgb, var(--h3-accent) 36%, var(--h3-border)); border-radius: var(--h3-radius-md); background: color-mix(in srgb, var(--h3-accent) 5%, var(--h3-surface)); }
        .minimax-h3-director-llm-disclosure { color: var(--h3-text-muted); font-size: 10px; font-weight: 700; cursor: pointer; }
        .minimax-h3-director-llm-note { margin: 0; color: var(--h3-text-muted); font-size: 10px; }
        .minimax-h3-director-llm-row { display: grid; gap: 5px; padding-top: 7px; border-top: 1px solid var(--h3-border); }
        .minimax-h3-director-llm-identity { display: flex; align-items: baseline; gap: 6px; min-width: 0; }
        .minimax-h3-director-llm-identity b { flex: 0 0 auto; color: var(--h3-accent); font-family: var(--h3-font-mono); font-size: 10px; }
        .minimax-h3-director-llm-identity span { overflow: hidden; font-size: 11px; font-weight: 650; text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-director-llm-links { display: flex; flex-wrap: wrap; gap: 4px; }
        .minimax-h3-director-llm-links > small { color: var(--h3-text-muted); font-size: 9px; }
        .minimax-h3-director-llm-link { border: 1px solid var(--h3-border); border-radius: 999px; padding: 2px 6px; background: var(--h3-surface-raised); color: var(--h3-text-muted); font-family: var(--h3-font-mono); font-size: 8px; }
        .minimax-h3-director-llm-link[data-state="ready"] { border-color: color-mix(in srgb, var(--h3-success) 62%, var(--h3-border)); color: var(--h3-success); }
        .minimax-h3-director-llm-link[data-state="missing"], .minimax-h3-director-llm-link[data-state="unassigned"] { border-color: color-mix(in srgb, var(--h3-warning) 55%, var(--h3-border)); color: var(--h3-warning); }
        .minimax-h3-director-llm-copy-status { min-height: 12px; color: var(--h3-success); font-size: 9px; }
        .minimax-h3-director-empty { min-height: 330px; place-content: center; }
        .minimax-h3-director-embedded-editor, .minimax-h3-director-library-host { min-width: 0; }
        .minimax-h3-director-wiring-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--h3-space-3); margin-bottom: var(--h3-space-4); }
        .minimax-h3-director-wiring-stats > div { display: grid; gap: 2px; padding: 12px; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-md); background: var(--h3-surface); }
        .minimax-h3-director-wiring-stats strong { color: var(--h3-accent); font-size: 22px; }
        .minimax-h3-director-wiring-stats span { color: var(--h3-text-muted); }
        .minimax-h3-director-wiring-groups { display: grid; gap: var(--h3-space-3); margin-bottom: var(--h3-space-4); }
        .minimax-h3-director-wiring-group { display: grid; gap: 7px; padding: 12px; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-lg); background: var(--h3-surface); }
        .minimax-h3-director-wiring-group h3 { margin: 0 0 3px; }
        .minimax-h3-director-wire-card { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 9px 10px; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-md); background: var(--h3-surface-raised); }
        .minimax-h3-director-wire-card > div { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 2px 10px; min-width: 0; }
        .minimax-h3-director-wire-card small { grid-column: 2; color: var(--h3-text-muted); text-transform: capitalize; }
        .minimax-h3-director-wire-status { flex: 0 0 auto; border-radius: 999px; padding: 3px 8px; background: color-mix(in srgb, var(--h3-warning) 18%, transparent); color: var(--h3-warning); font-size: 11px; font-weight: 700; }
        .minimax-h3-director-wire-card[data-status="ready"] .minimax-h3-director-wire-status { background: color-mix(in srgb, var(--h3-success) 18%, transparent); color: var(--h3-success); }
        .minimax-h3-director-look-handoff { display: grid; max-width: 680px; min-height: 280px; place-content: center; gap: var(--h3-space-3); padding: clamp(24px, 7vw, 72px); border: 1px solid var(--h3-border); border-radius: var(--h3-radius-lg); background: radial-gradient(circle at 50% 0, color-mix(in srgb, var(--h3-accent) 16%, transparent), transparent 52%), var(--h3-surface); }
        .minimax-h3-director-look-handoff h3, .minimax-h3-director-look-handoff p { margin: 0; }
        .minimax-h3-director-review-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: var(--h3-space-3); padding: 9px 11px; border: 1px solid var(--h3-border); border-radius: var(--h3-radius-lg); background: var(--h3-surface); }
        .minimax-h3-director-review-footer > span { display: grid; min-width: 0; gap: 2px; }
        .minimax-h3-director-review-footer small { overflow: hidden; color: var(--h3-text-muted); text-overflow: ellipsis; white-space: nowrap; }
        .minimax-h3-director-compose-feedback { margin: var(--h3-space-3) 0 0; padding: 9px 11px; border-radius: var(--h3-radius-md); background: color-mix(in srgb, var(--h3-success) 12%, var(--h3-surface)); color: var(--h3-success); }
        .minimax-h3-director-compose-feedback[data-valid="false"] { background: color-mix(in srgb, var(--h3-danger) 12%, var(--h3-surface)); color: var(--h3-danger); }
        @container h3-studio-panel (max-width: 700px) {
            .minimax-h3-director-workspace-header { flex-direction: column; }
            .minimax-h3-director-shot-context-top { grid-template-columns: 1fr auto; }
            .minimax-h3-director-shot-context-identity { grid-column: 1 / -1; }
            .minimax-h3-director-compose-grid { grid-template-columns: 1fr; }
            .minimax-h3-director-inspector { grid-column: 1; grid-row: auto; }
            .minimax-h3-director-lanes { grid-column: 1; }
            .minimax-h3-director-direction { grid-column: 1; }
            .minimax-h3-director-inspector .minimax-h3-director-scene-heading { display: none; }
            .minimax-h3-director-inspector { padding: 10px; }
            .minimax-h3-director-review-footer { align-items: stretch; flex-direction: column; }
            .minimax-h3-director-review-footer .minimax-h3-button { width: 100%; }
            .minimax-h3-review-run-bar { grid-template-columns: 1fr; }
            .minimax-h3-review-run-bar > div:nth-child(2) { justify-content: flex-start; }
        }
        @container h3-studio-panel (max-width: 460px) {
            .minimax-h3-director-mode-switch { width: 100%; border-radius: var(--h3-radius-md); }
            .minimax-h3-director-mode { flex: 1 1 auto; }
            .minimax-h3-director-wiring-stats { grid-template-columns: 1fr; }
            .minimax-h3-director-wire-card { align-items: flex-start; flex-direction: column; }
            .minimax-h3-director-lane { grid-template-columns: 1fr auto; }
            .minimax-h3-director-lane > span { grid-column: 1 / -1; }
            .minimax-h3-director-tray-header { align-items: flex-start; flex-direction: column; }
            .minimax-h3-director-camera-phases { grid-template-columns: 1fr; }
            .minimax-h3-director-direction-cards { grid-template-columns: 1fr; }
            .minimax-h3-director-dialogue-form { grid-template-columns: 1fr; }
            .minimax-h3-director-dialogue-field.is-wide { grid-column: 1; }
            .minimax-h3-director-inline-creator { grid-template-columns: 1fr 1fr; }
            .minimax-h3-director-inline-creator input { grid-column: 1 / -1; }
        }
    `;
    document.head.appendChild(style);
}
