const TOKEN_STYLE_ID = "minimax-h3-studio-tokens";

// v3 separates Camera from Look. readStudioPrefs maps the former combined
// `camera` destination from v2 to `look` without touching workflow data.
export const STUDIO_UI_STORAGE_KEY = "minimax_h3_studio_ui_v3";
export const STUDIO_UI_LEGACY_STORAGE_KEY = "minimax_h3_studio_ui_v2";
export const STUDIO_MIN_WIDTH = 420;
export const STUDIO_MAX_WIDTH = 1100;

export const STUDIO_TOKEN_CSS = `
    .minimax-h3-studio, .minimax-h3-dashboard {
        --h3-space-1: 4px;
        --h3-space-2: 8px;
        --h3-space-3: 12px;
        --h3-space-4: 16px;
        --h3-space-6: 24px;
        --h3-rail-width: 88px;
        --h3-rail-compact-width: 44px;
        --h3-list-width: clamp(240px, 38%, 300px);
        --h3-row-height: 44px;
        --h3-control-height: 30px;
        --h3-control-compact-height: 26px;
        --h3-chip-height: 22px;
        --h3-radius-sm: 5px;
        --h3-radius-md: 8px;
        --h3-radius-lg: 12px;
        --h3-bg: var(--comfy-menu-bg, #171b21);
        --h3-surface: var(--comfy-input-bg, #20262e);
        --h3-surface-raised: color-mix(in srgb, var(--h3-surface) 88%, white 12%);
        --h3-input-bg: var(--comfy-input-bg, #11151a);
        --h3-border: var(--border-color, #3a4350);
        --h3-border-strong: color-mix(in srgb, var(--h3-border) 74%, white 26%);
        --h3-text: var(--input-text, #f2f5f8);
        --h3-text-muted: var(--descrip-text, #c7d0dc);
        --h3-button-text: #f7f9fc;
        --h3-on-primary: #0b1220;
        --h3-accent: var(--p-primary-color, #7ca6ff);
        --h3-error: #e5484d;
        --h3-warning: #f0a020;
        --h3-tip: #4d9fff;
        --h3-success: #2fbf71;
        --h3-readonly: #8f9aab;
        --h3-focus: 0 0 0 2px var(--h3-bg), 0 0 0 4px var(--h3-accent);
        --h3-font: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        --h3-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
`;

export function ensureStudioTokens() {
    if (document.getElementById(TOKEN_STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = TOKEN_STYLE_ID;
    style.textContent = STUDIO_TOKEN_CSS;
    document.head.appendChild(style);
}
