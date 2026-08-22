import { ensureStudioTokens } from "./tokens.js";

const STYLE_ID = "minimax-h3-studio-styles";

export function ensureStudioStyles() {
    ensureStudioTokens();
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
        .minimax-h3-studio-managed-section { display: none !important; }

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
        @container h3-studio-panel (min-width: 600px) {
            .minimax-h3-media-steps { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        @container h3-studio-panel (max-width: 620px) {
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
            align-content: center;
            gap: 2px;
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
    `;
    document.head.appendChild(style);
}
