import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

const NODE_NAME = "MiniMaxH3PromptEnhancer";
const CREATIVE_NODE_NAMES = new Set([
    NODE_NAME,
    "MiniMaxH3GGUFPromptEnhancer",
    "MiniMaxH3PromptGuideBuilder",
    "MiniMaxH3PromptValidator",
]);
const AUDIO_NODE_NAMES = new Set([
    NODE_NAME,
    "MiniMaxH3GGUFPromptEnhancer",
    "MiniMaxH3PromptGuideBuilder",
    "MiniMaxH3PromptValidator",
]);
const API_MODEL_REFRESH = "Refresh API model list";
const API_MODEL_PICKER = "Available API models";
const AUTOMATIC_MODEL = "(automatic selection)";
const REMOTE_WIDGETS = [
    "endpoint",
    "model",
    "api_key",
    "allow_remote_endpoint",
    API_MODEL_REFRESH,
    API_MODEL_PICKER,
];
const LOCAL_WIDGETS = [
    "local_model",
    "llama_server_path",
    "gpu_layers",
    "context_size",
    "threads",
    "startup_timeout",
    "keep_server_loaded",
];
const INSTRUMENTAL_WIDGET = "instrumental_description";
const MIN_NODE_WIDTH = 560;
const MIN_NODE_HEIGHT = 320;
const MIN_MULTILINE_HEIGHT = 72;
const MAX_MULTILINE_HEIGHT = 720;
const MULTILINE_HEIGHTS_PROPERTY = "minimaxH3MultilineHeights";
const ACCORDION_STATE_PROPERTY = "minimaxH3AccordionState";
const DISPLAY_LABELS = {
    basic_prompt: "Describe your video",
    duration_seconds: "Duration (seconds)",
    reference_context: "Reference notes (optional)",
    endpoint: "API endpoint",
    model: "API model ID (blank = auto)",
    local_model: "Local GGUF model",
    llama_server_path: "llama.cpp server executable",
    gpu_layers: "GPU layers (auto recommended)",
    context_size: "LLM context size",
    threads: "CPU threads (0 = auto)",
    startup_timeout: "Local model startup timeout",
    enhance_description: "Enhance description",
    ambience_foley_policy: "Scene sounds (ambience & foley)",
    background_score_policy: "Background score",
    instrumental_description: "Instrumental description",
    voice_performance: "Voice performance",
    aspect_ratio: "Aspect ratio",
    media_manifest: "Media metadata JSON (optional)",
    multishot_shot_count: "Multishot count",
    frame_count: "Exact frames (0 = use duration)",
    multishot_identity_lock: "Multishot identity lock",
    multishot_voice_lock: "Multishot voice lock",
    multishot_setting_lock: "Multishot setting lock",
    use_remote_model: "Use LM Studio / API model",
    allow_remote_endpoint: "Allow non-local endpoint",
    keep_server_loaded: "Keep local model loaded",
    show_advanced_controls: "Advanced settings",
};
const DISPLAY_PLACEHOLDERS = {
    basic_prompt: "Describe the video you want: subject, action, setting, camera, dialogue and sound…",
    reference_context: "Example: Picture 1 supplies the character identity; Audio 1 supplies the Spanish voice…",
    instrumental_description: "Example: low strings, 90 BPM, sparse percussion, gradual crescendo…",
    media_manifest: '{"items":[{"type":"picture","role":"identity"}]}',
    multishot_identity_lock: "Identity, wardrobe and appearance that every chained prompt must preserve…",
    multishot_voice_lock: "Voice, language and delivery that every chained prompt must preserve…",
    multishot_setting_lock: "Location, lighting and continuity that every chained prompt must preserve…",
};
const MULTILINE_TITLES = {
    basic_prompt: "Video description",
    prompt: "H3 prompt to validate",
    source_prompt: "Original request",
    reference_context: "Reference notes (optional)",
    instrumental_description: "Instrumental direction (optional)",
    media_manifest: "Media metadata JSON (optional)",
    multishot_identity_lock: "Identity continuity (optional)",
    multishot_voice_lock: "Voice continuity (optional)",
    multishot_setting_lock: "Setting continuity (optional)",
};
const DEFAULT_MULTILINE_HEIGHTS = {
    basic_prompt: 190,
    prompt: 190,
    source_prompt: 190,
    reference_context: 130,
    instrumental_description: 110,
    media_manifest: 150,
    multishot_identity_lock: 110,
    multishot_voice_lock: 110,
    multishot_setting_lock: 110,
};
const FIELD_STYLE_ID = "minimax-h3-field-styles";
const CREATIVE_TREATMENT_WIDGET = "creative_treatment_json";
const SHOT_PLAN_WIDGET = "shot_plan_json";
const CINEMATOGRAPHY_WIDGET = "cinematography_json";
const CREATIVE_PANEL_WIDGET = "MiniMax H3 creative direction";
const CREATIVE_SCHEMA_VERSION = 1;
const SHOT_PLAN_SCHEMA_VERSION = 1;
const CINEMATOGRAPHY_SCHEMA_VERSION = 1;
const MAX_SHOTS = 64;
const DEFAULT_EXACT_SHOT_DURATION = 1;
const CREATIVE_CHOICES = {
    genre: [
        ["none", "No preference"],
        ["action", "Action"],
        ["horror", "Horror"],
        ["thriller", "Thriller"],
        ["romance", "Romance"],
        ["comedy", "Comedy"],
        ["drama", "Drama"],
        ["adventure", "Adventure / epic"],
        ["mystery", "Mystery"],
    ],
    visualLanguage: [
        ["none", "No preference"],
        ["anime_general", "General anime"],
        ["anime_shonen", "Kinetic action anime"],
        ["anime_shojo", "Lyrical character anime"],
        ["animation_2d", "2D animation"],
        ["documentary_observational", "Observational documentary"],
        ["live_action_naturalistic", "Naturalistic live action"],
        ["stylized_3d_animation", "Stylized 3D animation"],
        ["stop_motion_handcrafted", "Handcrafted stop motion"],
        ["painterly_2d", "Painterly 2D"],
        ["graphic_novel", "Graphic novel"],
        ["clean_commercial", "Clean commercial"],
    ],
    worldAesthetic: [
        ["none", "No preference"],
        ["cyberpunk", "Cyberpunk"],
        ["film_noir", "Film noir"],
        ["science_fiction", "Science fiction"],
        ["high_fantasy", "High fantasy"],
        ["retrofuturism", "Retrofuturism"],
        ["near_future_functional", "Functional near future"],
        ["gothic", "Gothic"],
        ["solarpunk", "Solarpunk"],
        ["steampunk", "Steampunk"],
        ["post_apocalyptic", "Post-apocalyptic"],
        ["historical_period", "Historical period"],
        ["retrofuturism_atomic_age", "Atomic-age retrofuturism"],
        ["retrofuturism_cassette", "Cassette futurism"],
        ["retrofuturism_y2k", "Y2K futurism"],
    ],
    tone: [
        ["none", "No preference"],
        ["epic", "Epic"],
        ["intimate", "Intimate"],
        ["dark", "Dark"],
        ["tense", "Tense"],
        ["hopeful", "Hopeful"],
        ["melancholic", "Melancholic"],
        ["playful", "Playful"],
        ["restrained", "Restrained"],
        ["serene", "Serene"],
        ["eerie", "Eerie"],
        ["whimsical", "Whimsical"],
        ["surreal", "Surreal"],
        ["clinical", "Clinical"],
        ["raw", "Raw"],
    ],
};
const CINEMATOGRAPHY_CHOICES = {
    colorPalette: [["none", "No preference"], ["natural", "Natural"], ["warm", "Warm"], ["cool", "Cool"], ["restrained", "Restrained chroma"], ["vibrant", "Vibrant"], ["monochrome", "Monochrome"]],
    exposureContrast: [["none", "No preference"], ["high_key", "High-key"], ["balanced", "Balanced"], ["low_key", "Low-key"], ["high_contrast", "High contrast"], ["soft_contrast", "Soft contrast"]],
    cameraMotion: [["none", "No preference"], ["static", "Static shot"], ["zoom_in", "Zoom in"], ["zoom_out", "Zoom out"], ["push_in", "Push in"], ["pull_out", "Pull out"], ["pan_left", "Pan left"], ["pan_right", "Pan right"], ["truck_left", "Truck left"], ["truck_right", "Truck right"], ["tilt_up", "Tilt up"], ["tilt_down", "Tilt down"], ["pedestal_up", "Pedestal up"], ["pedestal_down", "Pedestal down"], ["arc", "Arc shot"], ["tracking", "Tracking shot"], ["pov", "POV"], ["shake_slightly", "Shake slightly"], ["shake_strongly", "Shake strongly"], ["roll_clockwise", "Roll clockwise"], ["roll_counterclockwise", "Roll counterclockwise"]],
    cameraAmplitude: [["auto", "Automatic"], ["small", "Small"], ["medium", "Medium"], ["large", "Large"]],
    cameraSpeed: [["auto", "Automatic"], ["slow", "Slow"], ["normal", "Normal"], ["fast", "Fast"]],
    optics: [["none", "No preference"], ["wide_perspective", "Wide perspective"], ["natural_perspective", "Natural perspective"], ["compressed_telephoto", "Compressed telephoto"]],
    depthOfField: [["none", "No preference"], ["deep", "Deep focus"], ["balanced", "Balanced depth"], ["shallow", "Shallow focus"]],
    imageTexture: [["none", "No preference"], ["clean_digital", "Clean digital"], ["subtle_stable_grain", "Subtle stable grain"], ["film_16mm", "16mm-inspired"], ["film_35mm", "35mm-inspired"]],
    lensEffects: [["none", "No preference"], ["clean", "Clean optics"], ["subtle_diffusion", "Subtle diffusion"], ["restrained_halation", "Restrained halation"]],
    motionRendering: [["none", "No preference"], ["crisp", "Crisp motion"], ["natural_blur", "Natural motion blur"], ["energetic_blur", "Energetic motion blur"]],
};
const CINEMATOGRAPHY_FIELDS = [
    ["colorPalette", "Color palette"], ["exposureContrast", "Exposure / contrast"],
    ["cameraMotion", "H3 camera motion"], ["cameraAmplitude", "Motion amplitude"],
    ["cameraSpeed", "Motion speed"], ["optics", "Optics"],
    ["depthOfField", "Depth of field"], ["imageTexture", "Image texture"],
    ["lensEffects", "Lens effects"], ["motionRendering", "Motion rendering"],
];
const CREATIVE_FIELD_DEFINITIONS = [
    {
        key: "genre",
        label: "Narrative genre",
        title: "Guides pacing, editing, camera, performance, and sound. It does not invent genre-specific events or create cuts.",
    },
    {
        key: "visualLanguage",
        label: "Visual language",
        title: "Guides rendering, staging, poses, and visual grammar. It does not add powers, characters, or actions.",
    },
    {
        key: "worldAesthetic",
        label: "World / aesthetic",
        title: "Guides compatible materials, color, lighting, and production design. It does not invent technology, magic, or locations.",
    },
    {
        key: "tone",
        label: "Tone",
        title: "Guides intensity, composition, performance, and mix. It does not change facts, dialogue, or content.",
    },
];

function ensureFieldTitleStyles() {
    if (document.getElementById(FIELD_STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = FIELD_STYLE_ID;
    style.textContent = `
        .minimax-h3-field {
            display: flex;
            flex-direction: column;
            gap: 4px;
            width: 100%;
            height: 100%;
            min-height: 0;
            overflow: hidden;
            box-sizing: border-box;
        }
        .minimax-h3-field-title {
            flex: 0 0 auto;
            padding: 0 2px;
            overflow: hidden;
            color: var(--descrip-text, #aaa);
            font-size: 11px;
            font-weight: 600;
            line-height: 16px;
            text-overflow: ellipsis;
            white-space: nowrap;
            user-select: none;
        }
        .minimax-h3-field > textarea {
            flex: 1 1 auto;
            width: 100%;
            height: auto;
            min-height: 0;
            resize: none;
            box-sizing: border-box;
        }
        .minimax-h3-field-resizer {
            position: relative;
            flex: 0 0 10px;
            height: 10px;
            cursor: ns-resize;
            touch-action: none;
        }
        .minimax-h3-field-resizer::after {
            position: absolute;
            top: 4px;
            left: 38%;
            width: 24%;
            height: 2px;
            border-radius: 2px;
            background: color-mix(in srgb, var(--descrip-text, #aaa) 55%, transparent);
            content: "";
        }
        .minimax-h3-field-resizer:hover::after,
        .minimax-h3-field-resizer:focus-visible::after {
            background: var(--p-button-text-primary-color, #ddd);
        }
        .widget-item .minimax-h3-field-title {
            display: none;
        }
        .minimax-h3-creative-panel {
            display: flex;
            flex-direction: column;
            gap: 8px;
            width: 100%;
            height: 100%;
            min-height: 0;
            padding: 2px 1px;
            overflow: hidden;
            box-sizing: border-box;
            color: var(--input-text, #ddd);
            font-size: 12px;
            line-height: 1.35;
        }
        .minimax-h3-creative-panel,
        .minimax-h3-creative-panel * {
            box-sizing: border-box;
        }
        .minimax-h3-creative-panel details {
            flex: 0 0 auto;
            margin: 0;
            padding: 0;
            border: 1px solid color-mix(in srgb, var(--border-color, #666) 62%, transparent);
            border-radius: 6px;
            background: color-mix(in srgb, var(--comfy-input-bg, #222) 78%, transparent);
            overflow: hidden;
        }
        .minimax-h3-creative-panel details[open] {
            overflow: visible;
        }
        .minimax-h3-creative-panel summary {
            min-height: 30px;
            padding: 6px 9px;
            cursor: pointer;
            color: var(--descrip-text, #bbb);
            font-weight: 650;
            user-select: none;
        }
        .minimax-h3-panel-body {
            display: flex;
            flex-direction: column;
            gap: 7px;
            padding: 0 8px 8px;
        }
        .minimax-h3-settings-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 7px 9px;
        }
        .minimax-h3-settings-grid .minimax-h3-wide {
            grid-column: 1 / -1;
        }
        .minimax-h3-setting-field {
            display: flex;
            min-width: 0;
            flex-direction: column;
            gap: 3px;
        }
        .minimax-h3-setting-field > span {
            overflow: hidden;
            color: var(--descrip-text, #aaa);
            font-size: 10.5px;
            font-weight: 600;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .minimax-h3-setting-field input[type="text"],
        .minimax-h3-setting-field input[type="password"],
        .minimax-h3-setting-field input[type="number"],
        .minimax-h3-setting-field select,
        .minimax-h3-setting-field textarea {
            width: 100%;
            min-height: 27px;
            padding: 3px 5px;
            border: 1px solid var(--border-color, #666);
            border-radius: 4px;
            outline: none;
            background: var(--comfy-input-bg, #222);
            color: var(--input-text, #ddd);
            font: inherit;
        }
        .minimax-h3-setting-field textarea {
            min-height: 72px;
            resize: vertical;
        }
        .minimax-h3-setting-toggle {
            display: flex;
            min-height: 27px;
            align-items: center;
            gap: 7px;
            padding: 3px 1px;
            color: var(--input-text, #ddd);
        }
        .minimax-h3-setting-toggle input {
            margin: 0;
        }
        .minimax-h3-setting-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }
        .minimax-h3-setting-actions button {
            min-height: 27px;
            padding: 4px 9px;
            border: 1px solid var(--border-color, #666);
            border-radius: 4px;
            background: var(--comfy-input-bg, #292929);
            color: var(--input-text, #ddd);
            cursor: pointer;
            font: inherit;
        }
        .minimax-h3-section-hidden {
            display: none !important;
        }
        .minimax-h3-panel-help,
        .minimax-h3-panel-status,
        .minimax-h3-shot-summary {
            margin: 0;
            color: var(--descrip-text, #aaa);
            font-size: 10.5px;
            line-height: 1.35;
        }
        .minimax-h3-panel-status {
            display: none;
            padding: 5px 7px;
            border-radius: 4px;
            background: color-mix(in srgb, var(--warning-color, #b68a33) 18%, transparent);
        }
        .minimax-h3-treatment-disabled .minimax-h3-treatment-controls {
            opacity: 0.48;
            filter: saturate(0.55);
        }
        .minimax-h3-treatment-disabled .minimax-h3-panel-status {
            display: block;
        }
        .minimax-h3-treatment-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 7px 9px;
        }
        .minimax-h3-treatment-field {
            display: flex;
            min-width: 0;
            flex-direction: column;
            gap: 3px;
        }
        .minimax-h3-treatment-field > span,
        .minimax-h3-timing-label {
            overflow: hidden;
            color: var(--descrip-text, #aaa);
            font-size: 10.5px;
            font-weight: 600;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .minimax-h3-creative-panel select,
        .minimax-h3-creative-panel textarea,
        .minimax-h3-creative-panel input[type="number"] {
            width: 100%;
            border: 1px solid var(--border-color, #666);
            border-radius: 4px;
            outline: none;
            background: var(--comfy-input-bg, #222);
            color: var(--input-text, #ddd);
            font: inherit;
        }
        .minimax-h3-creative-panel select:focus-visible,
        .minimax-h3-creative-panel textarea:focus-visible,
        .minimax-h3-creative-panel input[type="number"]:focus-visible,
        .minimax-h3-creative-panel button:focus-visible {
            border-color: var(--p-primary-color, #7ca6ff);
            box-shadow: 0 0 0 1px var(--p-primary-color, #7ca6ff);
        }
        .minimax-h3-creative-panel select {
            height: 27px;
            padding: 2px 5px;
        }
        .minimax-h3-shot-toolbar {
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(190px, auto);
            align-items: end;
            gap: 8px;
        }
        .minimax-h3-timing-field {
            display: flex;
            min-width: 0;
            flex-direction: column;
            gap: 3px;
        }
        .minimax-h3-add-shot,
        .minimax-h3-shot-button {
            min-height: 27px;
            border: 1px solid var(--border-color, #666);
            border-radius: 4px;
            background: var(--comfy-input-bg, #292929);
            color: var(--input-text, #ddd);
            cursor: pointer;
            font: inherit;
        }
        .minimax-h3-add-shot {
            padding: 4px 9px;
            font-weight: 600;
        }
        .minimax-h3-add-shot:hover:not(:disabled),
        .minimax-h3-shot-button:hover:not(:disabled) {
            background: color-mix(in srgb, var(--comfy-input-bg, #292929) 68%, #fff 12%);
        }
        .minimax-h3-add-shot:disabled,
        .minimax-h3-shot-button:disabled {
            cursor: default;
            opacity: 0.38;
        }
        .minimax-h3-shot-list {
            display: flex;
            max-height: 342px;
            min-height: 38px;
            flex-direction: column;
            gap: 7px;
            padding-right: 2px;
            overflow-x: hidden;
            overflow-y: auto;
            scrollbar-gutter: stable;
        }
        .minimax-h3-shot-empty {
            padding: 10px 8px;
            border: 1px dashed color-mix(in srgb, var(--border-color, #666) 72%, transparent);
            border-radius: 5px;
            color: var(--descrip-text, #999);
            text-align: center;
        }
        .minimax-h3-shot-row {
            display: grid;
            grid-template-columns: 29px minmax(0, 1fr) 57px;
            align-items: stretch;
            gap: 6px;
            padding: 6px;
            border: 1px solid color-mix(in srgb, var(--border-color, #666) 72%, transparent);
            border-radius: 5px;
            background: color-mix(in srgb, var(--comfy-input-bg, #222) 88%, transparent);
        }
        .minimax-h3-shot-index {
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
            background: color-mix(in srgb, var(--border-color, #666) 27%, transparent);
            color: var(--descrip-text, #bbb);
            font-weight: 700;
        }
        .minimax-h3-shot-fields {
            display: grid;
            min-width: 0;
            grid-template-columns: minmax(0, 1fr);
            gap: 5px;
        }
        .minimax-h3-shot-fields.minimax-h3-shot-fields-exact {
            grid-template-columns: minmax(0, 1fr) 82px;
        }
        .minimax-h3-shot-description {
            min-height: 50px;
            padding: 5px 6px;
            resize: vertical;
            line-height: 1.35;
        }
        .minimax-h3-shot-duration-field {
            display: flex;
            min-width: 0;
            flex-direction: column;
            gap: 3px;
        }
        .minimax-h3-shot-duration-field > span {
            color: var(--descrip-text, #aaa);
            font-size: 10px;
            white-space: nowrap;
        }
        .minimax-h3-shot-duration {
            height: 27px;
            padding: 2px 4px;
        }
        .minimax-h3-shot-duration[aria-invalid="true"] {
            border-color: var(--error-text, #e66);
        }
        .minimax-h3-shot-description[aria-invalid="true"] {
            border-color: var(--error-text, #e66);
        }
        .minimax-h3-shot-summary[data-invalid="true"] {
            color: var(--error-text, #e99);
            font-weight: 600;
        }
        .minimax-h3-shot-actions {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            align-content: start;
            gap: 4px;
        }
        .minimax-h3-shot-button {
            min-width: 0;
            min-height: 23px;
            padding: 1px 3px;
            line-height: 1;
        }
        .minimax-h3-shot-delete {
            grid-column: 1 / -1;
            color: var(--error-text, #e99);
        }
        @media (max-width: 520px) {
            .minimax-h3-treatment-grid,
            .minimax-h3-shot-toolbar,
            .minimax-h3-settings-grid {
                grid-template-columns: minmax(0, 1fr);
            }
            .minimax-h3-settings-grid .minimax-h3-wide {
                grid-column: auto;
            }
        }
    `;
    document.head.appendChild(style);
}

function widgetTextElement(widget) {
    if (widget?.__minimaxTextInput instanceof HTMLTextAreaElement) return widget.__minimaxTextInput;
    if (widget?.element instanceof HTMLTextAreaElement) return widget.element;
    if (widget?.inputEl instanceof HTMLTextAreaElement) return widget.inputEl;
    return null;
}

function clampMultilineHeight(value) {
    return Math.min(MAX_MULTILINE_HEIGHT, Math.max(MIN_MULTILINE_HEIGHT, Math.round(value)));
}

function setMultilineHeight(node, widget, height, persist = true) {
    const preferredHeight = clampMultilineHeight(height);
    widget.__minimaxPreferredHeight = preferredHeight;
    if (persist) {
        if (!node.properties) node.properties = {};
        const heights = node.properties[MULTILINE_HEIGHTS_PROPERTY] ?? {};
        node.properties[MULTILINE_HEIGHTS_PROPERTY] = { ...heights, [widget.name]: preferredHeight };
    }
    node.graph?.setDirtyCanvas?.(true, true);
    node.setDirtyCanvas?.(true, true);
}

function addMultilineTitle(node, widget, title) {
    const textarea = widgetTextElement(widget);
    if (!textarea) return;
    ensureFieldTitleStyles();
    if (widget.__minimaxFieldWrapper) {
        widget.__minimaxFieldTitle.textContent = title;
        const restoredHeight = Number(node.properties?.[MULTILINE_HEIGHTS_PROPERTY]?.[widget.name]);
        if (Number.isFinite(restoredHeight)) setMultilineHeight(node, widget, restoredHeight, false);
        return;
    }
    const wrapper = document.createElement("div");
    wrapper.className = "minimax-h3-field";
    const heading = document.createElement("div");
    heading.className = "minimax-h3-field-title";
    heading.textContent = title;
    const headingId = `minimax-h3-field-${widget.name}-${Math.random().toString(36).slice(2)}`;
    heading.id = headingId;
    textarea.setAttribute("aria-labelledby", headingId);
    const resizer = document.createElement("div");
    resizer.className = "minimax-h3-field-resizer";
    resizer.tabIndex = 0;
    resizer.setAttribute("role", "separator");
    resizer.setAttribute("aria-orientation", "horizontal");
    resizer.title = "Drag to resize. Double-click to restore the default height.";
    const parent = textarea.parentNode;
    if (parent) parent.replaceChild(wrapper, textarea);
    wrapper.append(heading, textarea, resizer);
    widget.__minimaxTextInput = textarea;
    widget.__minimaxFieldTitle = heading;
    widget.__minimaxFieldWrapper = wrapper;
    widget.__minimaxFieldResizer = resizer;
    const originalComputeSize = widget.computeSize?.bind(widget);
    widget.__minimaxOriginalComputeSize = originalComputeSize;
    const savedHeight = Number(node.properties?.[MULTILINE_HEIGHTS_PROPERTY]?.[widget.name]);
    const defaultHeight = DEFAULT_MULTILINE_HEIGHTS[widget.name] ?? 110;
    setMultilineHeight(node, widget, Number.isFinite(savedHeight) ? savedHeight : defaultHeight, false);
    widget.computeSize = (width) => {
        const original = originalComputeSize?.(width);
        const originalWidth = Array.isArray(original) && Number.isFinite(original[0]) ? original[0] : width;
        return [originalWidth, widget.__minimaxPreferredHeight];
    };
    resizer.addEventListener("pointerdown", (event) => {
        if (event.button !== 0) return;
        event.preventDefault();
        event.stopPropagation();
        const startY = event.clientY;
        const startHeight = widget.__minimaxPreferredHeight;
        const startNodeHeight = Number(node.size?.[1]) || MIN_NODE_HEIGHT;
        resizer.setPointerCapture?.(event.pointerId);
        const onMove = (moveEvent) => {
            const nextHeight = clampMultilineHeight(startHeight + moveEvent.clientY - startY);
            const delta = nextHeight - startHeight;
            setMultilineHeight(node, widget, nextHeight);
            node.setSize?.([Math.max(MIN_NODE_WIDTH, node.size?.[0] ?? MIN_NODE_WIDTH), Math.max(MIN_NODE_HEIGHT, startNodeHeight + delta)]);
        };
        const onEnd = () => {
            window.removeEventListener("pointermove", onMove, true);
            window.removeEventListener("pointerup", onEnd, true);
            window.removeEventListener("pointercancel", onEnd, true);
            fitNodeToVisibleWidgets(node);
        };
        window.addEventListener("pointermove", onMove, true);
        window.addEventListener("pointerup", onEnd, true);
        window.addEventListener("pointercancel", onEnd, true);
    });
    resizer.addEventListener("dblclick", (event) => {
        event.preventDefault();
        event.stopPropagation();
        setMultilineHeight(node, widget, defaultHeight);
        fitNodeToVisibleWidgets(node);
    });
    resizer.addEventListener("keydown", (event) => {
        if (!["ArrowUp", "ArrowDown"].includes(event.key)) return;
        event.preventDefault();
        event.stopPropagation();
        const direction = event.key === "ArrowDown" ? 1 : -1;
        const step = event.shiftKey ? 60 : 20;
        setMultilineHeight(node, widget, widget.__minimaxPreferredHeight + direction * step);
        fitNodeToVisibleWidgets(node);
    });
    // ComfyUI positions/mounts widget.element. The value callbacks still close
    // over the original textarea, so wrapping changes presentation only.
    widget.element = wrapper;
}

function applyMultilineTitles(node) {
    for (const [name, title] of Object.entries(MULTILINE_TITLES)) {
        const widget = node.widgets?.find((candidate) => candidate.name === name);
        if (widget) addMultilineTitle(node, widget, title);
    }
}

function setWidgetVisible(widget, visible) {
    if (!widget) return;
    if (!widget.__minimaxOriginal) {
        widget.__minimaxOriginal = {
            type: widget.type,
            computeSize: widget.computeSize,
            hidden: Boolean(widget.hidden),
            optionsHidden: Boolean(widget.options?.hidden),
            inputDisplay: widget.inputEl?.style?.display ?? "",
            elementDisplay: widget.element?.style?.display ?? "",
        };
    }
    if (!widget.options) widget.options = {};
    if (visible) {
        widget.hidden = false;
        widget.options.hidden = false;
        widget.type = widget.__minimaxOriginal.type;
        widget.computeSize = widget.__minimaxOriginal.computeSize;
        if (widget.inputEl?.style) widget.inputEl.style.display = widget.__minimaxOriginal.inputDisplay;
        if (widget.element?.style) widget.element.style.display = widget.__minimaxOriginal.elementDisplay;
    } else {
        // Canvas nodes read widget.hidden; Vue nodes read widget.options.hidden.
        // Set both so remote/local controls are genuinely mutually exclusive.
        widget.hidden = true;
        widget.options.hidden = true;
        if (!window.LiteGraph?.vueNodesMode) {
            widget.type = "converted-widget";
            widget.computeSize = () => [0, -4];
        }
        if (widget.inputEl?.style) widget.inputEl.style.display = "none";
        if (widget.element?.style) widget.element.style.display = "none";
    }
}

function normalizeDynamicCombo(node, name) {
    const widget = node.widgets?.find((candidate) => candidate.name === name);
    const values = widget?.options?.values;
    if (!widget || !Array.isArray(values) || values.length === 0) return;
    if (!values.includes(widget.value)) widget.value = values[0];
}

function assignMigratedValue(widget, value) {
    if (!widget || Object.is(widget.value, value)) return false;
    widget.value = value;
    const input = widgetTextElement(widget);
    if (input && typeof value === "string") input.value = value;
    widget.callback?.(value);
    return true;
}

function sanitizeIntegerWidget(node, name, fallback, min, max) {
    const widget = node.widgets?.find((candidate) => candidate.name === name);
    if (!widget) return false;
    const parsed = typeof widget.value === "number" ? widget.value : Number(widget.value);
    const value = Number.isInteger(parsed) && parsed >= min && parsed <= max ? parsed : fallback;
    return assignMigratedValue(widget, value);
}

function sanitizeNumberWidget(node, name, fallback, min, max) {
    const widget = node.widgets?.find((candidate) => candidate.name === name);
    if (!widget) return false;
    const parsed = typeof widget.value === "number" ? widget.value : Number(widget.value);
    const value = Number.isFinite(parsed) && parsed >= min && parsed <= max ? parsed : fallback;
    return assignMigratedValue(widget, value);
}

function sanitizeStringWidget(node, name, fallback = "") {
    const widget = node.widgets?.find((candidate) => candidate.name === name);
    if (!widget) return false;
    return assignMigratedValue(widget, typeof widget.value === "string" ? widget.value : fallback);
}

function sanitizeEnumWidget(node, name, allowed, fallback) {
    const widget = node.widgets?.find((candidate) => candidate.name === name);
    if (!widget) return false;
    return assignMigratedValue(widget, allowed.includes(widget.value) ? widget.value : fallback);
}

function sanitizeBooleanWidget(node, name, fallback) {
    const widget = node.widgets?.find((candidate) => candidate.name === name);
    if (!widget) return false;
    return assignMigratedValue(widget, typeof widget.value === "boolean" ? widget.value : fallback);
}

function defaultCreativeTreatment() {
    return {
        schemaVersion: CREATIVE_SCHEMA_VERSION,
        genre: "none",
        visualLanguage: "none",
        worldAesthetic: "none",
        tone: "none",
    };
}

function defaultShotPlan() {
    return {
        schemaVersion: SHOT_PLAN_SCHEMA_VERSION,
        timingMode: "auto",
        shots: [],
    };
}

function defaultCinematography() {
    return {
        schemaVersion: CINEMATOGRAPHY_SCHEMA_VERSION,
        colorPalette: "none",
        exposureContrast: "none",
        cameraMotion: "none",
        cameraAmplitude: "auto",
        cameraSpeed: "auto",
        optics: "none",
        depthOfField: "none",
        imageTexture: "none",
        lensEffects: "none",
        motionRendering: "none",
    };
}

function parseJsonObject(value) {
    if (value && typeof value === "object" && !Array.isArray(value)) return value;
    if (typeof value !== "string" || !value.trim()) return null;
    try {
        const parsed = JSON.parse(value);
        return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : null;
    } catch {
        return null;
    }
}

function allowedCreativeValue(key, value) {
    const values = CREATIVE_CHOICES[key]?.map(([token]) => token) ?? [];
    return typeof value === "string" && values.includes(value) ? value : "none";
}

function sanitizeCreativeTreatment(value) {
    const parsed = parseJsonObject(value);
    if (!parsed || parsed.schemaVersion !== CREATIVE_SCHEMA_VERSION) return defaultCreativeTreatment();
    return {
        schemaVersion: CREATIVE_SCHEMA_VERSION,
        genre: allowedCreativeValue("genre", parsed.genre),
        visualLanguage: allowedCreativeValue("visualLanguage", parsed.visualLanguage),
        worldAesthetic: allowedCreativeValue("worldAesthetic", parsed.worldAesthetic),
        tone: allowedCreativeValue("tone", parsed.tone),
    };
}

function allowedCinematographyValue(key, value) {
    const values = CINEMATOGRAPHY_CHOICES[key]?.map(([token]) => token) ?? [];
    const fallback = ["cameraAmplitude", "cameraSpeed"].includes(key) ? "auto" : "none";
    return typeof value === "string" && values.includes(value) ? value : fallback;
}

function sanitizeCinematography(value) {
    const parsed = parseJsonObject(value);
    if (!parsed || parsed.schemaVersion !== CINEMATOGRAPHY_SCHEMA_VERSION) return defaultCinematography();
    const state = { schemaVersion: CINEMATOGRAPHY_SCHEMA_VERSION };
    for (const [key] of CINEMATOGRAPHY_FIELDS) {
        state[key] = allowedCinematographyValue(key, parsed[key]);
    }
    if (["none", "static", "pov"].includes(state.cameraMotion)) {
        state.cameraAmplitude = "auto";
        state.cameraSpeed = "auto";
    }
    return state;
}

function validDuration(value) {
    const number = typeof value === "number" ? value : Number(value);
    return Number.isFinite(number) && number > 0 && number <= 3600 ? number : null;
}

function validShotId(value) {
    return typeof value === "string" && /^[A-Za-z0-9_-]{1,64}$/.test(value);
}

function nextShotId(shots, reserved = new Set()) {
    const used = new Set([
        ...shots.map((shot) => String(shot?.id ?? "")),
        ...reserved,
    ]);
    let highest = 0;
    for (const id of used) {
        const match = /^s(\d+)$/.exec(id);
        if (match) highest = Math.max(highest, Number(match[1]));
    }
    let candidate;
    do candidate = `s${++highest}`;
    while (used.has(candidate));
    return candidate;
}

function sanitizeShotPlan(value) {
    const parsed = parseJsonObject(value);
    if (!parsed || parsed.schemaVersion !== SHOT_PLAN_SCHEMA_VERSION || !Array.isArray(parsed.shots)) {
        return defaultShotPlan();
    }

    const requestedTiming = parsed.timingMode === "exact" ? "exact" : "auto";
    const shots = [];
    const usedIds = new Set();
    let exactIsComplete = requestedTiming === "exact";
    for (const rawShot of parsed.shots.slice(0, MAX_SHOTS)) {
        const source = rawShot && typeof rawShot === "object" && !Array.isArray(rawShot) ? rawShot : {};
        let id = typeof source.id === "string" ? source.id.trim() : "";
        if (!validShotId(id) || usedIds.has(id)) id = nextShotId(shots, usedIds);
        usedIds.add(id);
        const shot = {
            id,
            description: typeof source.description === "string"
                ? source.description.replaceAll("\0", "").slice(0, 8000)
                : "",
        };
        if (requestedTiming === "exact") {
            const duration = validDuration(source.durationSeconds);
            if (duration === null) {
                exactIsComplete = false;
            } else {
                shot.durationSeconds = duration;
            }
        }
        shots.push(shot);
    }

    // An incomplete exact plan must not reach the backend with a mixture of
    // timed and untimed rows. Downgrade it to auto instead of inventing times.
    const timingMode = exactIsComplete ? "exact" : "auto";
    if (timingMode === "auto") {
        for (const shot of shots) delete shot.durationSeconds;
    }
    return {
        schemaVersion: SHOT_PLAN_SCHEMA_VERSION,
        timingMode,
        shots,
    };
}

function serializeCreativeTreatment(state) {
    return JSON.stringify({
        schemaVersion: CREATIVE_SCHEMA_VERSION,
        genre: allowedCreativeValue("genre", state?.genre),
        visualLanguage: allowedCreativeValue("visualLanguage", state?.visualLanguage),
        worldAesthetic: allowedCreativeValue("worldAesthetic", state?.worldAesthetic),
        tone: allowedCreativeValue("tone", state?.tone),
    });
}

function serializeCinematography(state) {
    const result = { schemaVersion: CINEMATOGRAPHY_SCHEMA_VERSION };
    for (const [key] of CINEMATOGRAPHY_FIELDS) {
        result[key] = allowedCinematographyValue(key, state?.[key]);
    }
    if (["none", "static", "pov"].includes(result.cameraMotion)) {
        result.cameraAmplitude = "auto";
        result.cameraSpeed = "auto";
    }
    return JSON.stringify(result);
}

function serializeShotPlan(state) {
    const sanitized = sanitizeShotPlan(JSON.stringify({
        schemaVersion: SHOT_PLAN_SCHEMA_VERSION,
        timingMode: state?.timingMode,
        shots: Array.isArray(state?.shots) ? state.shots : [],
    }));
    return JSON.stringify(sanitized);
}

function hideJsonStorageWidget(widget) {
    if (!widget) return;
    if (!widget.__minimaxJsonStorageHidden) {
        widget.__minimaxJsonStorageHidden = true;
        widget.__minimaxJsonStorageComputeSize = widget.computeSize;
    }
    if (!widget.options) widget.options = {};
    widget.hidden = true;
    widget.options.hidden = true;
    // Keep the original widget type and serialization contract intact. Only
    // collapse its presentation; changing it to converted-widget can make API
    // prompt serialization treat the value as a linked input.
    widget.computeSize = () => [0, -4];
    if (widget.inputEl?.style) widget.inputEl.style.display = "none";
    if (widget.element?.style) widget.element.style.display = "none";
}

function writeJsonStorage(node, widget, serializedValue) {
    if (!widget || Object.is(widget.value, serializedValue)) return false;
    node.__minimaxWritingCreativeStorage = true;
    try {
        widget.value = serializedValue;
        const input = widgetTextElement(widget);
        if (input) input.value = serializedValue;
        widget.callback?.(serializedValue);
    } finally {
        node.__minimaxWritingCreativeStorage = false;
    }
    node.graph?.setDirtyCanvas?.(true, true);
    node.setDirtyCanvas?.(true, true);
    return true;
}

function markPanelWidgetNonPersistent(widget) {
    if (!widget) return;
    widget.serialize = false;
    if (!widget.options) widget.options = {};
    widget.options.serialize = false;
    widget.serializeValue = () => undefined;
}

function createPanelElement(tagName, className, textContent = "") {
    const element = document.createElement(tagName);
    if (className) element.className = className;
    if (textContent) element.textContent = textContent;
    return element;
}

function accordionState(node, key, fallback = false) {
    return Boolean(node.properties?.[ACCORDION_STATE_PROPERTY]?.[key] ?? fallback);
}

function persistAccordionState(node, key, open) {
    if (!node.properties) node.properties = {};
    node.properties[ACCORDION_STATE_PROPERTY] = {
        ...(node.properties[ACCORDION_STATE_PROPERTY] ?? {}),
        [key]: Boolean(open),
    };
}

function creativeChoiceLabel(key, value) {
    return CREATIVE_CHOICES[key]?.find(([candidate]) => candidate === value)?.[1] ?? value;
}

function cinematographyChoiceLabel(key, value) {
    return CINEMATOGRAPHY_CHOICES[key]?.find(([candidate]) => candidate === value)?.[1] ?? value;
}

function setCanonicalValue(node, widget, value) {
    if (!widget || Object.is(widget.value, value)) return;
    widget.value = value;
    const input = widgetTextElement(widget);
    if (input && typeof value === "string") input.value = value;
    widget.callback?.(value);
    node.graph?.setDirtyCanvas?.(true, true);
    node.setDirtyCanvas?.(true, true);
}

function createWidgetProxy(node, name, label, { wide = false, multiline = false, password = false } = {}) {
    const widget = node.widgets?.find((candidate) => candidate.name === name);
    if (!widget) return null;
    const field = createPanelElement("label", `minimax-h3-setting-field${wide ? " minimax-h3-wide" : ""}`);
    field.appendChild(createPanelElement("span", "", label));
    let control;
    const values = widget.options?.values;
    const isBoolean = widget.type === "toggle" || typeof widget.value === "boolean";
    if (isBoolean) {
        field.classList.add("minimax-h3-setting-toggle");
        field.replaceChildren();
        control = createPanelElement("input", "");
        control.type = "checkbox";
        control.checked = Boolean(widget.value);
        field.append(control, createPanelElement("span", "", label));
        control.addEventListener("change", () => setCanonicalValue(node, widget, control.checked));
    } else if (Array.isArray(values)) {
        control = createPanelElement("select", "");
        for (const value of values) {
            const option = document.createElement("option");
            option.value = String(value);
            option.textContent = String(value);
            control.appendChild(option);
        }
        control.value = String(widget.value ?? values[0] ?? "");
        control.addEventListener("change", () => setCanonicalValue(node, widget, control.value));
    } else if (multiline) {
        control = createPanelElement("textarea", "");
        control.value = String(widget.value ?? "");
        control.addEventListener("input", () => setCanonicalValue(node, widget, control.value));
    } else {
        control = createPanelElement("input", "");
        const numeric = widget.type === "number" || typeof widget.value === "number";
        control.type = numeric ? "number" : password ? "password" : "text";
        control.value = String(widget.value ?? "");
        if (numeric) {
            if (Number.isFinite(widget.options?.min)) control.min = String(widget.options.min);
            if (Number.isFinite(widget.options?.max)) control.max = String(widget.options.max);
            if (Number.isFinite(widget.options?.step)) control.step = String(widget.options.step);
        }
        const eventName = numeric ? "change" : "input";
        control.addEventListener(eventName, () => {
            const value = numeric ? Number(control.value) : control.value;
            if (!numeric || Number.isFinite(value)) setCanonicalValue(node, widget, value);
        });
    }
    control.setAttribute("aria-label", label);
    control.title = widget.options?.tooltip ?? label;
    if (!control.parentNode) field.appendChild(control);
    return { field, control, widget };
}

function appendProxy(grid, proxy) {
    if (proxy?.field) grid.appendChild(proxy.field);
    return proxy;
}

function syncWidgetProxy(proxy) {
    if (!proxy?.control || !proxy?.widget) return;
    if (proxy.control.type === "checkbox") proxy.control.checked = Boolean(proxy.widget.value);
    else proxy.control.value = String(proxy.widget.value ?? "");
}

function syncSettingsPanelProxies(node) {
    const panel = node.__minimaxCreativePanel;
    if (!panel) return;
    for (const section of [panel.modelSetup, panel.chainedSettings, panel.advancedSettings]) {
        for (const proxy of Object.values(section?.proxies ?? {})) syncWidgetProxy(proxy);
    }
    if (panel.modelSetup?.backendControl) {
        panel.modelSetup.backendControl.value = node.widgets?.find((widget) => widget.name === "use_remote_model")?.value
            ? "remote" : "local";
        panel.modelSetup.updateBackend?.();
    }
    panel.advancedSettings?.refreshSummary?.();
}

function addSelectOptions(select, choices) {
    for (const [value, label] of choices) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        select.appendChild(option);
    }
}

function roundedDuration(value) {
    return Math.max(0.01, Math.round(value * 1000) / 1000);
}

function effectiveDuration(node) {
    const frameValue = Number(node.widgets?.find((widget) => widget.name === "frame_count")?.value);
    if (Number.isInteger(frameValue) && frameValue > 0) return frameValue / 24;
    return validDuration(node.widgets?.find((widget) => widget.name === "duration_seconds")?.value)
        ?? DEFAULT_EXACT_SHOT_DURATION;
}

function rebalanceExactDurations(node, state = node.__minimaxShotPlanState) {
    if (!state || state.timingMode !== "exact" || !state.shots.length) return;
    const total = effectiveDuration(node);
    const chained = node.widgets?.find((widget) => widget.name === "mode")?.value === "chained_multishot";
    if (chained) {
        const perSegment = Math.round(total * 1_000_000) / 1_000_000;
        for (const shot of state.shots) shot.durationSeconds = perSegment;
        return;
    }
    // Millisecond allocation makes timestamps readable; the final row absorbs
    // any remainder so the JSON sum still equals effectiveDuration exactly.
    const regular = Math.max(0.001, Math.floor((total / state.shots.length) * 1000) / 1000);
    state.shots.forEach((shot, index) => {
        const duration = index === state.shots.length - 1
            ? total - regular * (state.shots.length - 1)
            : regular;
        shot.durationSeconds = Math.round(duration * 1_000_000) / 1_000_000;
    });
}

function updateCreativePanelHeight(node) {
    const panel = node.__minimaxCreativePanel;
    if (!panel) return;
    let preferredHeight = 12;
    for (const details of panel.root.querySelectorAll(":scope > details")) {
        if (details.classList.contains("minimax-h3-section-hidden")) continue;
        const body = details.querySelector(":scope > .minimax-h3-panel-body");
        preferredHeight += details.open ? 31 + Math.max(0, body?.scrollHeight ?? 0) : 31;
        preferredHeight += 8;
    }
    preferredHeight = Math.max(72, preferredHeight);
    panel.widget.__minimaxPreferredHeight = preferredHeight;
    panel.root.style.height = `${preferredHeight}px`;
    panel.widget.computeSize = (width) => [Math.max(MIN_NODE_WIDTH, Number(width) || 0), preferredHeight];
    fitNodeToVisibleWidgets(node);
}

function updateCreativePanelMode(node) {
    const panel = node.__minimaxCreativePanel;
    if (!panel) return;
    const chained = node.widgets?.find((widget) => widget.name === "mode")?.value === "chained_multishot";
    panel.addShotButton.textContent = chained ? "+ Add independent segment" : "+ Add shot";
    panel.addShotButton.title = panel.addShotButton.disabled
        ? `Limit reached: ${MAX_SHOTS} rows.`
        : chained
            ? "Adds one autonomous generation to the chained_multishot package. The order is authoritative."
            : "Adds one explicit cut. The LLM will not create additional cuts.";
    panel.timingSelect.disabled = chained;
    panel.timingSelect.title = chained
        ? "Every chained segment uses the global Duration setting."
        : "Auto distributes the duration. Exact requires a positive duration for every shot.";
    if (panel.chainedSettings) {
        panel.chainedSettings.details.classList.toggle("minimax-h3-section-hidden", !chained);
        const count = Number(node.widgets?.find((widget) => widget.name === "multishot_shot_count")?.value ?? 0);
        panel.chainedSettings.summary.textContent = `Chained multishot · ${count > 0 ? `${count} segments` : "Automatic count"}`;
    }
    for (const textarea of panel.shotList.querySelectorAll("textarea.minimax-h3-shot-description")) {
        textarea.placeholder = chained
            ? "Describe only this independent segment…"
            : "Describe what happens in this shot…";
    }
}

function handleCreativePanelModeChange(node) {
    const currentMode = String(node.widgets?.find((widget) => widget.name === "mode")?.value ?? "auto");
    const previousMode = node.__minimaxCreativePanelMode;
    node.__minimaxCreativePanelMode = currentMode;
    if (previousMode !== undefined && previousMode !== currentMode
        && node.__minimaxShotPlanState?.timingMode === "exact") {
        rebalanceExactDurations(node);
        commitShotPlan(node);
        renderShotRows(node);
        return;
    }
    updateCreativePanelMode(node);
    updateShotSummary(node);
}

function handleEffectiveDurationChange(node) {
    if (node.__minimaxShotPlanState?.timingMode !== "exact") return;
    rebalanceExactDurations(node);
    commitShotPlan(node);
    renderShotRows(node);
}

function updateCreativePanelEnhancementState(node) {
    const panel = node.__minimaxCreativePanel;
    if (!panel) return;
    const widgetValue = node.widgets?.find((widget) => widget.name === "enhance_description")?.value;
    const enabled = widgetValue === undefined || widgetValue === true || widgetValue === 1
        || String(widgetValue).toLowerCase() === "true";
    panel.treatmentBody.classList.toggle("minimax-h3-treatment-disabled", !enabled);
    panel.treatmentStatus.textContent = enabled
        ? ""
        : "Treatment is saved but will not be applied while Enhance description is disabled.";
    updateCreativePanelHeight(node);
}

function commitCreativeTreatment(node) {
    const widget = node.widgets?.find((candidate) => candidate.name === CREATIVE_TREATMENT_WIDGET);
    writeJsonStorage(node, widget, serializeCreativeTreatment(node.__minimaxCreativeTreatmentState));
    updateCreativeTreatmentSummary(node);
}

function commitCinematography(node) {
    const widget = node.widgets?.find((candidate) => candidate.name === CINEMATOGRAPHY_WIDGET);
    writeJsonStorage(node, widget, serializeCinematography(node.__minimaxCinematographyState));
    updateCinematographySummary(node);
}

function updateCinematographySummary(node) {
    const panel = node.__minimaxCreativePanel;
    const state = node.__minimaxCinematographyState;
    if (!panel?.cinematographySummary || !state) return;
    const active = CINEMATOGRAPHY_FIELDS
        .map(([key]) => [key, state[key]])
        .filter(([key, value]) => !(["cameraAmplitude", "cameraSpeed"].includes(key) ? value === "auto" : value === "none"))
        .map(([key, value]) => cinematographyChoiceLabel(key, value));
    panel.cinematographySummary.textContent = `Cinematography · ${active.length ? active.join(" · ") : "No preferences"}`;
    const moving = !["none", "static", "pov"].includes(state.cameraMotion);
    for (const key of ["cameraAmplitude", "cameraSpeed"]) {
        const select = panel.cinematographySelects?.[key];
        if (select) {
            select.disabled = !moving;
            select.title = moving
                ? "H3 documents camera movement as motion type + amplitude + speed."
                : "Choose a moving H3 camera motion first.";
        }
    }
}

function updateCreativeTreatmentSummary(node) {
    const panel = node.__minimaxCreativePanel;
    const state = node.__minimaxCreativeTreatmentState;
    if (!panel || !state) return;
    const active = CREATIVE_FIELD_DEFINITIONS
        .map(({ key }) => [key, state[key]])
        .filter(([, value]) => value && value !== "none")
        .map(([key, value]) => creativeChoiceLabel(key, value));
    const prefix = node.__minimaxCreativeNodeName === "MiniMaxH3PromptValidator"
        ? "Creative direction to validate"
        : "Creative direction";
    panel.treatmentSummary.textContent = `${prefix} · ${active.length ? active.join(" · ") : "No preferences"}`;
}

function commitShotPlan(node) {
    const widget = node.widgets?.find((candidate) => candidate.name === SHOT_PLAN_WIDGET);
    const serialized = serializeShotPlan(node.__minimaxShotPlanState);
    writeJsonStorage(node, widget, serialized);
}

function updateShotSummary(node) {
    const panel = node.__minimaxCreativePanel;
    const state = node.__minimaxShotPlanState;
    if (!panel || !state) return;
    const count = state.shots.length;
    if (!count) {
        panel.shotSummaryLabel.textContent = node.widgets?.find((widget) => widget.name === "mode")?.value === "chained_multishot"
            ? "Segment plan · No segments"
            : "Shot plan · No shots";
        panel.shotSummary.dataset.invalid = "false";
        panel.shotSummary.textContent = node.__minimaxCreativeNodeName === "MiniMaxH3PromptValidator"
            ? "No rows: validate the prompt without requiring an explicit plan."
            : "No rows: the enhancer may decide the staging and cuts.";
        return;
    }
    const missingDescriptions = state.shots.filter((shot) => !String(shot.description ?? "").trim()).length;
    const chainedMode = node.widgets?.find((widget) => widget.name === "mode")?.value === "chained_multishot";
    panel.shotSummaryLabel.textContent = `${chainedMode ? "Segment plan" : "Shot plan"} · ${count} ${chainedMode
        ? (count === 1 ? "segment" : "segments")
        : (count === 1 ? "shot" : "shots")} · ${state.timingMode === "exact" && !chainedMode ? "Exact timing" : "Auto timing"}`;
    const problems = [];
    if (missingDescriptions) {
        problems.push(`${missingDescriptions} ${missingDescriptions === 1 ? "row needs" : "rows need"} a description`);
    }
    if (state.timingMode === "exact") {
        const total = state.shots.reduce((sum, shot) => sum + (validDuration(shot.durationSeconds) ?? 0), 0);
        const expected = effectiveDuration(node);
        const chained = chainedMode;
        if (chained) {
            const invalidSegment = state.shots.some((shot) => {
                const duration = validDuration(shot.durationSeconds);
                return duration === null || Math.abs(duration - expected) > 0.05;
            });
            if (invalidSegment) problems.push(`each segment must last ${roundedDuration(expected)} s`);
        } else if (Math.abs(total - expected) > 0.05) {
            problems.push(`the total must be ${roundedDuration(expected)} s`);
        }
        panel.shotSummary.textContent = problems.length
            ? `⚠ ${problems.join("; ")}. Fix the plan before running.`
            : chained
                ? `${count} ${count === 1 ? "segment" : "segments"} · ${roundedDuration(expected)} s each · authoritative order and timing.`
                : `${count} ${count === 1 ? "row" : "rows"} · total duration: ${roundedDuration(total)} s · authoritative order and timing.`;
    } else {
        panel.shotSummary.textContent = problems.length
            ? `⚠ ${problems.join("; ")}. Fix the plan before running.`
            : `${count} ${count === 1 ? "row" : "rows"} · automatic timing · authoritative order.`;
    }
    panel.shotSummary.dataset.invalid = problems.length ? "true" : "false";
}

function renderShotRows(node) {
    const panel = node.__minimaxCreativePanel;
    const state = node.__minimaxShotPlanState;
    if (!panel || !state) return;
    panel.shotList.replaceChildren();
    panel.timingSelect.value = state.timingMode;

    if (!state.shots.length) {
        const empty = createPanelElement(
            "div",
            "minimax-h3-shot-empty",
            "No explicit shots. The main description remains clean.",
        );
        panel.shotList.appendChild(empty);
    }

    state.shots.forEach((shot, index) => {
        const row = createPanelElement("div", "minimax-h3-shot-row");
        row.dataset.shotId = shot.id;
        const indexLabel = createPanelElement("div", "minimax-h3-shot-index", String(index + 1));
        indexLabel.title = `Stable ID: ${shot.id}`;

        const fields = createPanelElement("div", "minimax-h3-shot-fields");
        if (state.timingMode === "exact") fields.classList.add("minimax-h3-shot-fields-exact");
        const description = createPanelElement("textarea", "minimax-h3-shot-description");
        description.rows = 2;
        description.maxLength = 8000;
        description.value = shot.description;
        description.placeholder = node.widgets?.find((widget) => widget.name === "mode")?.value === "chained_multishot"
            ? "Describe only this independent segment…"
            : "Describe what happens in this shot…";
        description.setAttribute("aria-label", `Description for row ${index + 1}`);
        description.setAttribute("aria-invalid", shot.description.trim() ? "false" : "true");
        description.title = "This description is authoritative. Creative treatment does not change its facts.";
        description.addEventListener("input", () => {
            shot.description = description.value.replaceAll("\0", "").slice(0, 8000);
            if (description.value !== shot.description) description.value = shot.description;
            description.setAttribute("aria-invalid", shot.description.trim() ? "false" : "true");
            commitShotPlan(node);
            updateShotSummary(node);
        });
        fields.appendChild(description);

        if (state.timingMode === "exact") {
            const durationField = createPanelElement("label", "minimax-h3-shot-duration-field");
            durationField.appendChild(createPanelElement("span", "", "Duration (s)"));
            const duration = createPanelElement("input", "minimax-h3-shot-duration");
            duration.type = "number";
            duration.min = "0.01";
            duration.max = "3600";
            duration.step = "0.1";
            duration.value = String(shot.durationSeconds);
            duration.setAttribute("aria-label", `Exact duration for row ${index + 1}`);
            duration.title = "Required for every row when exact timing is enabled.";
            duration.addEventListener("input", () => {
                const next = validDuration(duration.value);
                duration.setAttribute("aria-invalid", next === null ? "true" : "false");
                if (next === null) return;
                shot.durationSeconds = next;
                commitShotPlan(node);
                updateShotSummary(node);
            });
            duration.addEventListener("blur", () => {
                const next = validDuration(duration.value);
                if (next === null) duration.value = String(shot.durationSeconds);
                duration.setAttribute("aria-invalid", "false");
            });
            durationField.appendChild(duration);
            fields.appendChild(durationField);
        }

        const actions = createPanelElement("div", "minimax-h3-shot-actions");
        const up = createPanelElement("button", "minimax-h3-shot-button", "↑");
        up.type = "button";
        up.disabled = index === 0;
        up.title = "Move up one position";
        up.setAttribute("aria-label", `Move row ${index + 1} up`);
        up.addEventListener("click", () => {
            if (index <= 0) return;
            [state.shots[index - 1], state.shots[index]] = [state.shots[index], state.shots[index - 1]];
            commitShotPlan(node);
            renderShotRows(node);
        });
        const down = createPanelElement("button", "minimax-h3-shot-button", "↓");
        down.type = "button";
        down.disabled = index >= state.shots.length - 1;
        down.title = "Move down one position";
        down.setAttribute("aria-label", `Move row ${index + 1} down`);
        down.addEventListener("click", () => {
            if (index >= state.shots.length - 1) return;
            [state.shots[index], state.shots[index + 1]] = [state.shots[index + 1], state.shots[index]];
            commitShotPlan(node);
            renderShotRows(node);
        });
        const remove = createPanelElement("button", "minimax-h3-shot-button minimax-h3-shot-delete", "Delete");
        remove.type = "button";
        remove.title = "Deletes this row without changing the main description.";
        remove.setAttribute("aria-label", `Delete row ${index + 1}`);
        remove.addEventListener("click", () => {
            state.shots.splice(index, 1);
            rebalanceExactDurations(node, state);
            commitShotPlan(node);
            renderShotRows(node);
        });
        actions.append(up, down, remove);
        row.append(indexLabel, fields, actions);
        panel.shotList.appendChild(row);
    });

    panel.addShotButton.disabled = state.shots.length >= MAX_SHOTS;
    updateCreativePanelMode(node);
    updateShotSummary(node);
    updateCreativePanelHeight(node);
}

function hydrateCreativeDirectionPanel(node) {
    const panel = node.__minimaxCreativePanel;
    if (!panel) return;
    const creativeWidget = node.widgets?.find((widget) => widget.name === CREATIVE_TREATMENT_WIDGET);
    const shotWidget = node.widgets?.find((widget) => widget.name === SHOT_PLAN_WIDGET);
    const cinematographyWidget = node.widgets?.find((widget) => widget.name === CINEMATOGRAPHY_WIDGET);
    if (!creativeWidget || !shotWidget || !cinematographyWidget) return;

    hideJsonStorageWidget(creativeWidget);
    hideJsonStorageWidget(shotWidget);
    hideJsonStorageWidget(cinematographyWidget);
    const creative = sanitizeCreativeTreatment(creativeWidget.value);
    const shots = sanitizeShotPlan(shotWidget.value);
    const cinematography = sanitizeCinematography(cinematographyWidget.value);
    node.__minimaxCreativeTreatmentState = creative;
    node.__minimaxShotPlanState = shots;
    node.__minimaxCinematographyState = cinematography;
    writeJsonStorage(node, creativeWidget, serializeCreativeTreatment(creative));
    writeJsonStorage(node, shotWidget, JSON.stringify(shots));
    writeJsonStorage(node, cinematographyWidget, serializeCinematography(cinematography));
    for (const definition of CREATIVE_FIELD_DEFINITIONS) {
        panel.creativeSelects[definition.key].value = creative[definition.key];
    }
    updateCreativeTreatmentSummary(node);
    for (const [key] of CINEMATOGRAPHY_FIELDS) {
        panel.cinematographySelects[key].value = cinematography[key];
    }
    updateCinematographySummary(node);
    syncSettingsPanelProxies(node);
    renderShotRows(node);
    updateCreativePanelEnhancementState(node);
    node.__minimaxCreativePanelMode = String(
        node.widgets?.find((widget) => widget.name === "mode")?.value ?? "auto",
    );
    updateCreativePanelMode(node);
}

function wrapJsonStorageCallback(node, widget) {
    if (!widget || widget.__minimaxCreativeStorageWrapped) return;
    widget.__minimaxCreativeStorageWrapped = true;
    const originalCallback = widget.callback;
    widget.callback = function (...args) {
        const result = originalCallback?.apply(this, args);
        if (!node.__minimaxWritingCreativeStorage) hydrateCreativeDirectionPanel(node);
        return result;
    };
}

function createModelSetupDetails(node) {
    const nodeName = node.__minimaxCreativeNodeName;
    if (![NODE_NAME, "MiniMaxH3GGUFPromptEnhancer"].includes(nodeName)) return null;
    const details = createPanelElement("details", "minimax-h3-model-details");
    details.open = accordionState(node, "modelSetup");
    const summary = createPanelElement("summary", "", "Model setup");
    const body = createPanelElement("div", "minimax-h3-panel-body");
    const grid = createPanelElement("div", "minimax-h3-settings-grid");
    body.appendChild(grid);
    details.append(summary, body);

    const canonicalNames = [];
    const proxies = {};
    let backendControl = null;
    let updateBackend = null;
    const add = (name, label, options = {}) => {
        const proxy = appendProxy(grid, createWidgetProxy(node, name, label, options));
        if (proxy) {
            proxies[name] = proxy;
            canonicalNames.push(name);
        }
        return proxy;
    };

    if (nodeName === NODE_NAME) {
        canonicalNames.push(API_MODEL_REFRESH, API_MODEL_PICKER);
        const backendWidget = node.widgets?.find((widget) => widget.name === "use_remote_model");
        if (backendWidget) {
            canonicalNames.push("use_remote_model");
            const field = createPanelElement("label", "minimax-h3-setting-field minimax-h3-wide");
            field.appendChild(createPanelElement("span", "", "Prompt model backend"));
            const backend = createPanelElement("select", "");
            backendControl = backend;
            addSelectOptions(backend, [["remote", "OpenAI-compatible API"], ["local", "Local GGUF via llama.cpp"]]);
            backend.value = Boolean(backendWidget.value) ? "remote" : "local";
            field.appendChild(backend);
            grid.appendChild(field);

            const remoteGrid = createPanelElement("div", "minimax-h3-settings-grid minimax-h3-wide");
            const localGrid = createPanelElement("div", "minimax-h3-settings-grid minimax-h3-wide");
            grid.append(remoteGrid, localGrid);
            const addTo = (target, name, label, options = {}) => {
                const proxy = createWidgetProxy(node, name, label, options);
                if (proxy) {
                    proxies[name] = proxy;
                    canonicalNames.push(name);
                    target.appendChild(proxy.field);
                }
                return proxy;
            };
            addTo(remoteGrid, "endpoint", "API endpoint", { wide: true });
            addTo(remoteGrid, "model", "API model ID (blank = auto)");
            addTo(remoteGrid, "api_key", "API key", { password: true });
            addTo(remoteGrid, "allow_remote_endpoint", "Allow non-local endpoint", { wide: true });
            const discovery = createPanelElement("div", "minimax-h3-setting-actions minimax-h3-wide");
            const discovered = createPanelElement("select", "");
            addSelectOptions(discovered, [[AUTOMATIC_MODEL, AUTOMATIC_MODEL]]);
            const refresh = createPanelElement("button", "", "Refresh API models");
            refresh.type = "button";
            refresh.addEventListener("click", async () => {
                refresh.disabled = true;
                refresh.textContent = "Loading…";
                try {
                    const response = await api.fetchApi("/minimax_h3_prompt_enhancer/models", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            endpoint: node.widgets?.find((widget) => widget.name === "endpoint")?.value ?? "",
                            api_key: node.widgets?.find((widget) => widget.name === "api_key")?.value ?? "",
                            allow_remote_endpoint: node.widgets?.find((widget) => widget.name === "allow_remote_endpoint")?.value === true,
                        }),
                    });
                    const payload = await response.json();
                    if (!response.ok) throw new Error(payload?.error ?? `HTTP ${response.status}`);
                    discovered.replaceChildren();
                    addSelectOptions(discovered, [[AUTOMATIC_MODEL, AUTOMATIC_MODEL], ...(payload.models ?? []).map((value) => [value, value])]);
                    const current = String(node.widgets?.find((widget) => widget.name === "model")?.value ?? "");
                    discovered.value = current && [...discovered.options].some((option) => option.value === current)
                        ? current : AUTOMATIC_MODEL;
                } catch (error) {
                    notifyModelDiscoveryError(error?.message ?? String(error));
                } finally {
                    refresh.disabled = false;
                    refresh.textContent = "Refresh API models";
                }
            });
            discovered.addEventListener("change", () => {
                const modelWidget = node.widgets?.find((widget) => widget.name === "model");
                setCanonicalValue(node, modelWidget, discovered.value === AUTOMATIC_MODEL ? "" : discovered.value);
                if (proxies.model?.control) proxies.model.control.value = String(modelWidget?.value ?? "");
            });
            discovery.append(discovered, refresh);
            remoteGrid.appendChild(discovery);

            addTo(localGrid, "local_model", "Local GGUF model", { wide: true });
            addTo(localGrid, "llama_server_path", "llama.cpp server executable", { wide: true });
            addTo(localGrid, "gpu_layers", "GPU layers");
            addTo(localGrid, "context_size", "LLM context size");
            addTo(localGrid, "threads", "CPU threads");
            addTo(localGrid, "startup_timeout", "Startup timeout");
            addTo(localGrid, "keep_server_loaded", "Keep local model loaded", { wide: true });

            updateBackend = () => {
                const remote = backend.value === "remote";
                remoteGrid.classList.toggle("minimax-h3-section-hidden", !remote);
                localGrid.classList.toggle("minimax-h3-section-hidden", remote);
                setCanonicalValue(node, backendWidget, remote);
                summary.textContent = remote
                    ? `Model setup · API · ${String(node.widgets?.find((widget) => widget.name === "model")?.value || "Automatic model")}`
                    : `Model setup · Local GGUF · ${String(node.widgets?.find((widget) => widget.name === "local_model")?.value || "No model")}`;
                updateCreativePanelHeight(node);
            };
            backend.addEventListener("change", updateBackend);
            grid.addEventListener("input", () => updateBackend?.());
            grid.addEventListener("change", () => updateBackend?.());
            updateBackend();
        }
    } else {
        add("gguf_model_path", "GGUF model path", { wide: true });
        add("llama_server_path", "llama.cpp server executable", { wide: true });
        add("registered_model_dirs", "Additional registered model roots", { wide: true });
        add("gpu_layers", "GPU layers");
        add("context_size", "LLM context size");
        add("threads", "CPU threads");
        add("startup_timeout", "Startup timeout");
        add("keep_server_loaded", "Keep local model loaded", { wide: true });
        summary.textContent = "Model setup · Direct GGUF";
    }
    return { details, summary, body, canonicalNames, proxies, backendControl, updateBackend };
}

function createChainedSettingsDetails(node) {
    if (!node.widgets?.some((widget) => widget.name === "multishot_shot_count")) return null;
    const details = createPanelElement("details", "minimax-h3-chained-details");
    details.open = accordionState(node, "chainedMultishot");
    const summary = createPanelElement("summary", "", "Chained multishot");
    const body = createPanelElement("div", "minimax-h3-panel-body");
    const grid = createPanelElement("div", "minimax-h3-settings-grid");
    const canonicalNames = [];
    const proxies = {};
    const add = (name, label, options = {}) => {
        const proxy = appendProxy(grid, createWidgetProxy(node, name, label, options));
        if (proxy) {
            canonicalNames.push(name);
            proxies[name] = proxy;
        }
    };
    add("multishot_shot_count", "Segment count");
    add("multishot_identity_lock", "Identity continuity", { wide: true, multiline: true });
    add("multishot_voice_lock", "Voice continuity", { wide: true, multiline: true });
    add("multishot_setting_lock", "Setting continuity", { wide: true, multiline: true });
    grid.addEventListener("input", () => updateCreativePanelMode(node));
    grid.addEventListener("change", () => updateCreativePanelMode(node));
    body.appendChild(grid);
    details.append(summary, body);
    return { details, summary, body, canonicalNames, proxies };
}

function createAdvancedSettingsDetails(node) {
    const fields = [
        ["temperature", "Temperature"],
        ["max_tokens", "Maximum output tokens"],
        ["timeout_seconds", "Request timeout"],
        ["request_timeout", "Request timeout"],
        ["repair_attempts", "Repair attempts"],
        ["disable_thinking", "Disable model thinking", { wide: true }],
        ["frame_count", "Exact frames (0 = use duration)"],
        ["media_manifest", "Media metadata JSON", { wide: true, multiline: true }],
    ];
    const available = fields.filter(([name]) => node.widgets?.some((widget) => widget.name === name));
    if (!available.length) return null;
    const details = createPanelElement("details", "minimax-h3-advanced-details");
    details.open = accordionState(node, "advancedSettings")
        || node.widgets?.find((widget) => widget.name === "show_advanced_controls")?.value === true;
    const summary = createPanelElement("summary", "", "Advanced settings · Defaults");
    const body = createPanelElement("div", "minimax-h3-panel-body");
    const help = createPanelElement("p", "minimax-h3-panel-help", "Exact timing, structured media metadata, and language-model tuning. Most workflows can keep these defaults.");
    const grid = createPanelElement("div", "minimax-h3-settings-grid");
    const canonicalNames = ["show_advanced_controls"];
    const proxies = {};
    for (const [name, label, options] of available) {
        const proxy = appendProxy(grid, createWidgetProxy(node, name, label, options));
        if (proxy) {
            canonicalNames.push(name);
            proxies[name] = proxy;
        }
    }
    const refreshSummary = () => {
        const frames = Number(node.widgets?.find((widget) => widget.name === "frame_count")?.value ?? 0);
        const manifest = String(node.widgets?.find((widget) => widget.name === "media_manifest")?.value ?? "").trim();
        const active = [];
        if (frames > 0) active.push(`Exact frames: ${frames}`);
        if (manifest) active.push("Media metadata active");
        summary.textContent = `Advanced settings · ${active.length ? active.join(" · ") : "Defaults"}`;
    };
    grid.addEventListener("input", refreshSummary);
    grid.addEventListener("change", refreshSummary);
    refreshSummary();
    body.append(help, grid);
    details.append(summary, body);
    return { details, summary, body, canonicalNames, proxies, refreshSummary };
}

function addCreativeDirectionPanel(node) {
    const creativeWidget = node.widgets?.find((widget) => widget.name === CREATIVE_TREATMENT_WIDGET);
    const shotWidget = node.widgets?.find((widget) => widget.name === SHOT_PLAN_WIDGET);
    const cinematographyWidget = node.widgets?.find((widget) => widget.name === CINEMATOGRAPHY_WIDGET);
    if (!creativeWidget || !shotWidget || !cinematographyWidget || typeof node.addDOMWidget !== "function") return;
    hideJsonStorageWidget(creativeWidget);
    hideJsonStorageWidget(shotWidget);
    hideJsonStorageWidget(cinematographyWidget);
    wrapJsonStorageCallback(node, creativeWidget);
    wrapJsonStorageCallback(node, shotWidget);
    wrapJsonStorageCallback(node, cinematographyWidget);
    if (node.__minimaxCreativePanel) {
        hydrateCreativeDirectionPanel(node);
        return;
    }

    ensureFieldTitleStyles();
    const root = createPanelElement("div", "minimax-h3-creative-panel");
    root.addEventListener("pointerdown", (event) => event.stopPropagation());

    const isValidator = node.__minimaxCreativeNodeName === "MiniMaxH3PromptValidator";
    const modelSetup = createModelSetupDetails(node);
    const chainedSettings = createChainedSettingsDetails(node);
    const treatmentDetails = createPanelElement("details", "minimax-h3-treatment-details");
    treatmentDetails.open = accordionState(node, "creativeDirection");
    const treatmentSummary = createPanelElement(
        "summary",
        "",
        isValidator ? "Creative direction to validate" : "Creative direction · No preferences",
    );
    treatmentSummary.title = isValidator
        ? "Expected context used to verify that the prompt follows the treatment without changing its story."
        : "Adds creative direction without rewriting the story or creating cuts.";
    const treatmentBody = createPanelElement("div", "minimax-h3-panel-body");
    const treatmentControls = createPanelElement("div", "minimax-h3-treatment-controls");
    const treatmentHelp = createPanelElement(
        "p",
        "minimax-h3-panel-help",
        isValidator
            ? "Define the expected treatment for consistency validation. It does not rewrite the prompt or invent content."
            : "Adds directing emphasis for the LLM. It never invents story, dialogue, characters, actions, or cuts.",
    );
    const treatmentGrid = createPanelElement("div", "minimax-h3-treatment-grid");
    const creativeSelects = {};
    for (const definition of CREATIVE_FIELD_DEFINITIONS) {
        const field = createPanelElement("label", "minimax-h3-treatment-field");
        field.title = definition.title;
        field.appendChild(createPanelElement("span", "", definition.label));
        const select = createPanelElement("select", "");
        select.setAttribute("aria-label", definition.label);
        select.title = definition.title;
        addSelectOptions(select, CREATIVE_CHOICES[definition.key]);
        select.addEventListener("change", () => {
            node.__minimaxCreativeTreatmentState[definition.key] = allowedCreativeValue(definition.key, select.value);
            commitCreativeTreatment(node);
        });
        creativeSelects[definition.key] = select;
        field.appendChild(select);
        treatmentGrid.appendChild(field);
    }
    const treatmentStatus = createPanelElement("p", "minimax-h3-panel-status");
    treatmentControls.append(treatmentHelp, treatmentGrid);
    treatmentBody.append(treatmentControls, treatmentStatus);
    treatmentDetails.append(treatmentSummary, treatmentBody);

    const cinematographyDetails = createPanelElement("details", "minimax-h3-cinematography-details");
    cinematographyDetails.open = accordionState(node, "cinematography");
    const cinematographySummary = createPanelElement("summary", "", "Cinematography · No preferences");
    cinematographySummary.title = "Explicit H3-oriented camera, color, optics, focus, texture, and motion-rendering controls.";
    const cinematographyBody = createPanelElement("div", "minimax-h3-panel-body");
    const cinematographyHelp = createPanelElement(
        "p",
        "minimax-h3-panel-help",
        "Optional explicit presentation controls. H3 camera movement follows motion type + amplitude + speed. Source facts, references, shot rows, and explicit colors remain authoritative.",
    );
    const cinematographyGrid = createPanelElement("div", "minimax-h3-treatment-grid");
    const cinematographySelects = {};
    for (const [key, label] of CINEMATOGRAPHY_FIELDS) {
        const field = createPanelElement("label", "minimax-h3-treatment-field");
        field.appendChild(createPanelElement("span", "", label));
        const select = createPanelElement("select", "");
        select.setAttribute("aria-label", label);
        addSelectOptions(select, CINEMATOGRAPHY_CHOICES[key]);
        select.addEventListener("change", () => {
            const state = node.__minimaxCinematographyState;
            if (!state) return;
            state[key] = allowedCinematographyValue(key, select.value);
            if (key === "cameraMotion" && ["none", "static", "pov"].includes(state.cameraMotion)) {
                state.cameraAmplitude = "auto";
                state.cameraSpeed = "auto";
                cinematographySelects.cameraAmplitude.value = "auto";
                cinematographySelects.cameraSpeed.value = "auto";
            }
            commitCinematography(node);
        });
        cinematographySelects[key] = select;
        field.appendChild(select);
        cinematographyGrid.appendChild(field);
    }
    cinematographyBody.append(cinematographyHelp, cinematographyGrid);
    cinematographyDetails.append(cinematographySummary, cinematographyBody);

    const shotDetails = createPanelElement("details", "minimax-h3-shot-details");
    shotDetails.open = accordionState(node, "shotPlan");
    const shotSummaryLabel = createPanelElement("summary", "", "Shot plan · No shots");
    shotSummaryLabel.title = "When rows are present, their count and order are authoritative and the LLM cannot create extra cuts.";
    const shotBody = createPanelElement("div", "minimax-h3-panel-body");
    const shotHelp = createPanelElement(
        "p",
        "minimax-h3-panel-help",
        isValidator
            ? "Optional. Each row defines the expected plan that the prompt must follow. Empty means no explicit plan is required."
            : "Optional. Each row fixes one shot and its order. Empty lets the enhancer decide; rows do not clutter the main description.",
    );
    const toolbar = createPanelElement("div", "minimax-h3-shot-toolbar");
    const timingField = createPanelElement("label", "minimax-h3-timing-field");
    timingField.appendChild(createPanelElement("span", "minimax-h3-timing-label", "Timing"));
    const timingSelect = createPanelElement("select", "");
    timingSelect.setAttribute("aria-label", "Shot timing mode");
    timingSelect.title = "Auto distributes the duration. Exact requires a positive duration for every row.";
    addSelectOptions(timingSelect, [["auto", "Auto-distribute"], ["exact", "Set duration per shot"]]);
    timingField.appendChild(timingSelect);
    const addShotButton = createPanelElement("button", "minimax-h3-add-shot", "+ Add shot");
    addShotButton.type = "button";
    toolbar.append(timingField, addShotButton);
    const shotList = createPanelElement("div", "minimax-h3-shot-list");
    shotList.setAttribute("aria-live", "polite");
    const shotSummary = createPanelElement("p", "minimax-h3-shot-summary");
    shotBody.append(shotHelp, toolbar, shotList, shotSummary);
    shotDetails.append(shotSummaryLabel, shotBody);
    const advancedSettings = createAdvancedSettingsDetails(node);
    if (modelSetup) root.appendChild(modelSetup.details);
    if (chainedSettings) root.appendChild(chainedSettings.details);
    root.append(treatmentDetails, cinematographyDetails, shotDetails);
    if (advancedSettings) root.appendChild(advancedSettings.details);

    const panelWidget = node.addDOMWidget(
        CREATIVE_PANEL_WIDGET,
        "minimaxH3CreativeDirection",
        root,
        { serialize: false, hideOnZoom: false },
    );
    markPanelWidgetNonPersistent(panelWidget);
    node.__minimaxCreativePanel = {
        root,
        widget: panelWidget,
        treatmentDetails,
        treatmentSummary,
        treatmentBody,
        treatmentStatus,
        creativeSelects,
        cinematographyDetails,
        cinematographySummary,
        cinematographySelects,
        shotDetails,
        shotSummaryLabel,
        timingSelect,
        addShotButton,
        shotList,
        shotSummary,
        modelSetup,
        chainedSettings,
        advancedSettings,
    };
    const managedNames = new Set([
        ...(modelSetup?.canonicalNames ?? []),
        ...(chainedSettings?.canonicalNames ?? []),
        ...(advancedSettings?.canonicalNames ?? []),
    ]);
    node.__minimaxProxyManagedWidgets = managedNames;
    for (const name of managedNames) {
        setWidgetVisible(node.widgets?.find((widget) => widget.name === name), false);
    }

    const bindAccordion = (details, key) => {
        if (!details) return;
        details.addEventListener("toggle", () => {
            persistAccordionState(node, key, details.open);
            if (key === "advancedSettings") {
                setCanonicalValue(
                    node,
                    node.widgets?.find((widget) => widget.name === "show_advanced_controls"),
                    details.open,
                );
            }
            updateCreativePanelHeight(node);
        });
    };
    bindAccordion(modelSetup?.details, "modelSetup");
    bindAccordion(chainedSettings?.details, "chainedMultishot");
    bindAccordion(treatmentDetails, "creativeDirection");
    bindAccordion(cinematographyDetails, "cinematography");
    bindAccordion(shotDetails, "shotPlan");
    bindAccordion(advancedSettings?.details, "advancedSettings");
    timingSelect.addEventListener("change", () => {
        const state = node.__minimaxShotPlanState;
        if (!state) return;
        if (timingSelect.value === "exact") {
            state.timingMode = "exact";
            rebalanceExactDurations(node, state);
        } else {
            state.timingMode = "auto";
            for (const shot of state.shots) delete shot.durationSeconds;
        }
        commitShotPlan(node);
        renderShotRows(node);
    });
    addShotButton.addEventListener("click", () => {
        const state = node.__minimaxShotPlanState;
        if (!state || state.shots.length >= MAX_SHOTS) return;
        const shot = {
            id: nextShotId(state.shots),
            description: "",
        };
        if (state.timingMode === "exact") shot.durationSeconds = DEFAULT_EXACT_SHOT_DURATION;
        state.shots.push(shot);
        rebalanceExactDurations(node, state);
        commitShotPlan(node);
        renderShotRows(node);
        requestAnimationFrame(() => {
            root.querySelector(`[data-shot-id="${shot.id}"] textarea`)?.focus?.();
            shotList.scrollTop = shotList.scrollHeight;
        });
    });

    hydrateCreativeDirectionPanel(node);
}

function configureCreativeDirectionNode(node, nodeName = node.comfyClass ?? node.type ?? "") {
    node.__minimaxCreativeNodeName = nodeName;
    addCreativeDirectionPanel(node);
    if (!node.__minimaxCreativePanel) return;
    wrapRefreshCallback(node, "enhance_description", updateCreativePanelEnhancementState);
    wrapRefreshCallback(node, "duration_seconds", handleEffectiveDurationChange);
    wrapRefreshCallback(node, "frame_count", handleEffectiveDurationChange);
    hydrateCreativeDirectionPanel(node);
}

function notifyModelDiscoveryError(message) {
    const toast = app.extensionManager?.toast;
    if (toast?.add) {
        toast.add({ severity: "error", summary: "Model discovery failed", detail: message, life: 6000 });
    } else {
        window.alert(`Model discovery failed: ${message}`);
    }
}

function addRemoteModelDiscovery(node) {
    if (node.__minimaxModelDiscoveryAdded) return;
    node.__minimaxModelDiscoveryAdded = true;
    const modelWidget = node.widgets?.find((widget) => widget.name === "model");
    if (!modelWidget || !node.addWidget) return;

    const picker = node.addWidget("combo", API_MODEL_PICKER, AUTOMATIC_MODEL, (value) => {
        modelWidget.value = value === AUTOMATIC_MODEL ? "" : value;
        modelWidget.callback?.(modelWidget.value);
        node.graph?.setDirtyCanvas?.(true, true);
    }, { values: [AUTOMATIC_MODEL], serialize: false });
    picker.serialize = false;
    picker.serializeValue = () => undefined;
    picker.label = "Choose discovered model";

    const refresh = node.addWidget("button", API_MODEL_REFRESH, null, async () => {
        const endpoint = node.widgets?.find((widget) => widget.name === "endpoint")?.value ?? "";
        const apiKey = node.widgets?.find((widget) => widget.name === "api_key")?.value ?? "";
        const allowRemote = node.widgets?.find((widget) => widget.name === "allow_remote_endpoint")?.value === true;
        const previousLabel = refresh.label;
        refresh.label = "Loading models…";
        node.graph?.setDirtyCanvas?.(true, true);
        try {
            const response = await api.fetchApi("/minimax_h3_prompt_enhancer/models", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    endpoint,
                    api_key: apiKey,
                    allow_remote_endpoint: allowRemote,
                }),
            });
            const rawResponse = await response.text();
            let payload;
            try {
                payload = JSON.parse(rawResponse);
            } catch {
                if ([404, 405].includes(response.status)) {
                    throw new Error("The model-list backend is not loaded. Restart ComfyUI, then refresh the page.");
                }
                throw new Error(`The server returned a non-JSON response (HTTP ${response.status}).`);
            }
            if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
            const discovered = Array.isArray(payload.models) ? payload.models.filter(Boolean) : [];
            const current = String(modelWidget.value ?? "").trim();
            const values = [AUTOMATIC_MODEL, ...discovered];
            if (current && !values.includes(current)) values.push(current);
            picker.options.values = values;
            picker.value = current || AUTOMATIC_MODEL;
            if (!discovered.length) notifyModelDiscoveryError("The endpoint returned no chat-capable models.");
        } catch (error) {
            notifyModelDiscoveryError(error?.message || String(error));
        } finally {
            refresh.label = previousLabel;
            // Model discovery changes choices, not layout. Resizing here made
            // multiline DOM widgets feed their stretched height back into the
            // node on every refresh, causing unbounded vertical growth.
            node.graph?.setDirtyCanvas?.(true, true);
            node.setDirtyCanvas?.(true, true);
        }
    }, { serialize: false });
    refresh.serialize = false;
    refresh.serializeValue = () => undefined;
    refresh.label = API_MODEL_REFRESH;
}

function repairLegacyModelDiscoveryShift(node, info) {
    const values = info?.widgets_values;
    if (!Array.isArray(values)) return false;
    const persistentWidgets = (node.widgets ?? []).filter((widget) => widget.serialize !== false);
    const modelIndex = persistentWidgets.findIndex((widget) => widget.name === "model");
    if (modelIndex < 0) return false;
    const legacyButtonValue = values[modelIndex + 1];
    const legacyPickerValue = values[modelIndex + 2];
    if (legacyButtonValue != null || typeof legacyPickerValue !== "string") return false;
    const repairedValues = [
        ...values.slice(0, modelIndex + 1),
        ...values.slice(modelIndex + 3),
    ];
    persistentWidgets.forEach((widget, index) => {
        if (index < repairedValues.length) widget.value = repairedValues[index];
    });
    info.widgets_values = repairedValues;
    return true;
}

function visibleWidgetHeight(node) {
    const width = Math.max(MIN_NODE_WIDTH, Number(node.size?.[0]) || 0);
    let height = 88 + Math.max(0, (node.outputs?.length ?? 0) - 1) * 20;
    for (const widget of node.widgets ?? []) {
        if (widget.hidden || widget.options?.hidden || widget.type === "converted-widget") continue;
        const computed = widget.computeSize?.(width);
        const computedHeight = Array.isArray(computed) && Number.isFinite(computed[1])
            ? computed[1]
            : 0;
        // Never use DOM client/scroll height here: multiline controls stretch
        // with the node and would create a positive resize feedback loop.
        const widgetHeight = Math.max(24, computedHeight);
        height += widgetHeight + 4;
    }
    return height;
}

function fitNodeToVisibleWidgets(node) {
    requestAnimationFrame(() => requestAnimationFrame(() => {
        const computed = node.computeSize?.() ?? [MIN_NODE_WIDTH, MIN_NODE_HEIGHT];
        const width = Math.max(MIN_NODE_WIDTH, Number(node.size?.[0]) || 0, Number(computed[0]) || 0);
        const requiredHeight = Math.max(
            MIN_NODE_HEIGHT,
            Number(computed[1]) || 0,
            visibleWidgetHeight(node),
        );
        node.setSize([width, requiredHeight]);
        node.graph?.setDirtyCanvas?.(true, true);
        node.setDirtyCanvas?.(true, true);
    }));
}

function normalizeMigratedRuntimeWidgets(node, repairDisplacedDescription = false) {
    const context = node.widgets?.find((widget) => widget.name === "context_size");
    const instrumental = node.widgets?.find((widget) => widget.name === INSTRUMENTAL_WIDGET);
    const displacedContext = String(instrumental?.value ?? "").trim();
    if (repairDisplacedDescription && /^\d{4,6}$/.test(displacedContext) && Number(displacedContext) >= 4096) {
        if (context) context.value = Number(displacedContext);
        instrumental.value = "";
    }
    if (["auto", "follow_prompt", "audible", "(no local models found)", "(no GGUF models found)"].includes(displacedContext)
        || /(?:llama-server|\.gguf$)/i.test(displacedContext)) {
        assignMigratedValue(instrumental, "");
    }
    sanitizeEnumWidget(node, "mode", ["auto", "t2va", "i2va", "fl2va", "l2va", "ref2va", "chained_multishot"], "auto");
    sanitizeNumberWidget(node, "duration_seconds", 5, 4, 15);
    sanitizeNumberWidget(node, "temperature", 0.2, 0, 2);
    sanitizeIntegerWidget(node, "max_tokens", 4096, 512, 32768);
    sanitizeIntegerWidget(node, "timeout_seconds", 300, 10, 1800);
    sanitizeIntegerWidget(node, "request_timeout", 300, 10, 1800);
    sanitizeIntegerWidget(node, "repair_attempts", 2, 0, 4);
    sanitizeIntegerWidget(node, "context_size", 16384, 4096, 131072);
    sanitizeIntegerWidget(node, "threads", 0, 0, 256);
    sanitizeIntegerWidget(node, "startup_timeout", 180, 10, 1800);
    sanitizeIntegerWidget(node, "multishot_shot_count", 0, 0, 64);
    sanitizeIntegerWidget(node, "frame_count", 0, 0, 4096);
    sanitizeEnumWidget(node, "ambience_foley_policy", ["auto", "ensure_audible", "off"], "auto");
    sanitizeEnumWidget(node, "background_score_policy", ["follow_prompt", "add_instrumental", "off"], "follow_prompt");
    sanitizeEnumWidget(node, "voice_performance", ["audible", "silent_mouth_acting_experimental", "none"], "audible");
    sanitizeEnumWidget(node, "aspect_ratio", ["auto", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"], "auto");
    sanitizeBooleanWidget(node, "use_remote_model", true);
    sanitizeBooleanWidget(node, "enhance_description", true);
    sanitizeBooleanWidget(node, "disable_thinking", true);
    sanitizeBooleanWidget(node, "allow_remote_endpoint", false);
    sanitizeBooleanWidget(node, "keep_server_loaded", false);
    sanitizeBooleanWidget(node, "show_advanced_controls", false);
    for (const name of [
        "basic_prompt", "prompt", "source_prompt", "reference_context", "endpoint", "model", "api_key",
        "instrumental_description", "media_manifest", "multishot_identity_lock", "multishot_voice_lock",
        "multishot_setting_lock", "llama_server_path", "gguf_model_path", "registered_model_dirs",
    ]) sanitizeStringWidget(node, name);
    const gpuLayers = node.widgets?.find((widget) => widget.name === "gpu_layers");
    const gpuValue = String(gpuLayers?.value ?? "").trim().toLowerCase();
    if (typeof gpuLayers?.value !== "string" || !/^(auto|all|-1|\d+)$/.test(gpuValue)) {
        assignMigratedValue(gpuLayers, "auto");
    }
    widgetTextElement(instrumental)?.setAttribute("aria-label", "Instrumental score description");
    const reference = node.widgets?.find((widget) => widget.name === "reference_context");
    widgetTextElement(reference)?.setAttribute("aria-label", "Optional reference notes");
    const manifest = node.widgets?.find((widget) => widget.name === "media_manifest");
    widgetTextElement(manifest)?.setAttribute("aria-label", "Advanced media metadata JSON");
}

function enforceConditionalVisibility(node) {
    const managed = node.__minimaxProxyManagedWidgets ?? new Set();
    const backendValue = node.widgets?.find((widget) => widget.name === "use_remote_model")?.value;
    const useRemote = backendValue === undefined || backendValue === true || backendValue === 1
        || String(backendValue).toLowerCase() === "true";
    for (const name of REMOTE_WIDGETS) setWidgetVisible(node.widgets?.find((widget) => widget.name === name), !managed.has(name) && useRemote);
    for (const name of LOCAL_WIDGETS) setWidgetVisible(node.widgets?.find((widget) => widget.name === name), !managed.has(name) && !useRemote);
    const score = node.widgets?.find((widget) => widget.name === "background_score_policy");
    setWidgetVisible(node.widgets?.find((widget) => widget.name === INSTRUMENTAL_WIDGET), score?.value === "add_instrumental");
    const modeWidget = node.widgets?.find((widget) => widget.name === "mode");
    if (modeWidget) {
        const multishot = modeWidget.value === "chained_multishot";
        for (const name of ["multishot_shot_count", "multishot_identity_lock", "multishot_voice_lock", "multishot_setting_lock"]) {
            setWidgetVisible(node.widgets?.find((widget) => widget.name === name), !managed.has(name) && multishot);
        }
        const advanced = node.widgets?.find((widget) => widget.name === "show_advanced_controls")?.value === true;
        const reference = node.widgets?.find((widget) => widget.name === "reference_context");
        const manifest = node.widgets?.find((widget) => widget.name === "media_manifest");
        const frames = node.widgets?.find((widget) => widget.name === "frame_count");
        const hasReferenceNotes = String(reference?.value ?? "").trim().length > 0;
        const hasManifest = String(manifest?.value ?? "").trim().length > 0;
        setWidgetVisible(reference, modeWidget.value === "ref2va" || advanced || hasReferenceNotes);
        setWidgetVisible(manifest, !managed.has("media_manifest") && (advanced || hasManifest));
        setWidgetVisible(frames, !managed.has("frame_count") && (advanced || Number(frames?.value ?? 0) > 0));
    }
    for (const name of managed) setWidgetVisible(node.widgets?.find((widget) => widget.name === name), false);
}

function applyLabels(node) {
    for (const [name, label] of Object.entries(DISPLAY_LABELS)) {
        const widget = node.widgets?.find((candidate) => candidate.name === name);
        if (widget) widget.label = label;
    }
    for (const [name, placeholder] of Object.entries(DISPLAY_PLACEHOLDERS)) {
        const widget = node.widgets?.find((candidate) => candidate.name === name);
        if (!widget) continue;
        if (!widget.options) widget.options = {};
        widget.options.placeholder = placeholder;
        const input = widgetTextElement(widget);
        if (input) input.placeholder = placeholder;
    }
}

function refreshInstrumentalWidget(node) {
    const score = node.widgets?.find((widget) => widget.name === "background_score_policy");
    const description = node.widgets?.find((widget) => widget.name === INSTRUMENTAL_WIDGET);
    setWidgetVisible(description, score?.value === "add_instrumental");
    fitNodeToVisibleWidgets(node);
}

function refreshBackendWidgets(node) {
    normalizeMigratedRuntimeWidgets(node);
    const toggle = node.widgets?.find((widget) => widget.name === "use_remote_model");
    const useRemote = toggle?.value === undefined || toggle?.value === true || toggle?.value === 1
        || String(toggle?.value).toLowerCase() === "true";
    const managed = node.__minimaxProxyManagedWidgets ?? new Set();
    for (const name of REMOTE_WIDGETS) {
        setWidgetVisible(node.widgets?.find((widget) => widget.name === name), !managed.has(name) && useRemote);
    }
    for (const name of LOCAL_WIDGETS) {
        setWidgetVisible(node.widgets?.find((widget) => widget.name === name), !managed.has(name) && !useRemote);
    }
    normalizeDynamicCombo(node, "local_model");
    normalizeDynamicCombo(node, "llama_server_path");
    applyLabels(node);
    enforceConditionalVisibility(node);
    refreshInstrumentalWidget(node);
}

function wrapRefreshCallback(node, widgetName, refresh) {
    const widget = node.widgets?.find((candidate) => candidate.name === widgetName);
    if (!widget || widget.__minimaxRefreshWrapped) return;
    widget.__minimaxRefreshWrapped = true;
    const originalCallback = widget.callback;
    widget.callback = function (...args) {
        const callbackResult = originalCallback?.apply(this, args);
        refresh(node);
        return callbackResult;
    };
}

function configureAudioNode(node) {
    applyMultilineTitles(node);
    applyLabels(node);
    normalizeMigratedRuntimeWidgets(node);
    wrapRefreshCallback(node, "background_score_policy", refreshInstrumentalWidget);
    wrapRefreshCallback(node, "mode", (target) => {
        enforceConditionalVisibility(target);
        handleCreativePanelModeChange(target);
        fitNodeToVisibleWidgets(target);
    });
    wrapRefreshCallback(node, "show_advanced_controls", (target) => {
        enforceConditionalVisibility(target);
        fitNodeToVisibleWidgets(target);
    });
    refreshInstrumentalWidget(node);
    enforceConditionalVisibility(node);
}

app.registerExtension({
    name: "MiniMaxH3PromptEnhancer.BackendToggle",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_NAME) return;
        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalCreated?.apply(this, arguments);
            this.__minimaxWidgetMigrationComplete = false;
            addRemoteModelDiscovery(this);
            wrapRefreshCallback(this, "use_remote_model", refreshBackendWidgets);
            configureAudioNode(this);
            configureCreativeDirectionNode(this, NODE_NAME);
            refreshBackendWidgets(this);
            return result;
        };
        const originalConfigured = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = originalConfigured?.apply(this, arguments);
            this.__minimaxWidgetMigrationComplete = false;
            addRemoteModelDiscovery(this);
            repairLegacyModelDiscoveryShift(this, arguments[0]);
            wrapRefreshCallback(this, "use_remote_model", refreshBackendWidgets);
            configureAudioNode(this);
            configureCreativeDirectionNode(this, NODE_NAME);
            refreshBackendWidgets(this);
            return result;
        };
        const originalDrawForeground = nodeType.prototype.onDrawForeground;
        nodeType.prototype.onDrawForeground = function () {
            if (!this.__minimaxWidgetMigrationComplete) {
                normalizeMigratedRuntimeWidgets(this, true);
                this.__minimaxWidgetMigrationComplete = true;
            }
            enforceConditionalVisibility(this);
            const result = originalDrawForeground?.apply(this, arguments);
            const requiredHeight = Math.max(MIN_NODE_HEIGHT, visibleWidgetHeight(this));
            if (Array.isArray(this.size) && this.size[1] + 2 < requiredHeight) {
                this.setSize([Math.max(MIN_NODE_WIDTH, this.size[0]), requiredHeight]);
            }
            return result;
        };
    },
});

app.registerExtension({
    name: "MiniMaxH3PromptEnhancer.AudioPolicyLabels",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (!AUDIO_NODE_NAMES.has(nodeData.name) || nodeData.name === NODE_NAME) return;
        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalCreated?.apply(this, arguments);
            configureAudioNode(this);
            if (CREATIVE_NODE_NAMES.has(nodeData.name)) configureCreativeDirectionNode(this, nodeData.name);
            return result;
        };
        const originalConfigured = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = originalConfigured?.apply(this, arguments);
            configureAudioNode(this);
            if (CREATIVE_NODE_NAMES.has(nodeData.name)) configureCreativeDirectionNode(this, nodeData.name);
            return result;
        };
    },
});
