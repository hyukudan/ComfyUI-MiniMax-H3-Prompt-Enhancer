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
const API_KEY_WIDGET = "api_key";
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
const INSTRUMENTAL_STYLE_WIDGET = "instrumental_style";
const INSTRUMENTAL_STYLE_PROXY_WIDGET = "minimax_h3_instrumental_style_proxy";
const INSTRUMENTAL_STYLE_CHOICES = [
    ["none", "No genre / preserve description"],
    ["cinematic_orchestral", "Cinematic orchestral"],
    ["hybrid_orchestral_electronic", "Hybrid orchestral / electronic"],
    ["action_cinematic", "Cinematic action"],
    ["mystery_investigation", "Mystery / investigation"],
    ["suspense_build", "Suspense build"],
    ["combat_rhythmic", "Rhythmic combat"],
    ["chinese_martial_arts", "Chinese martial-arts cinema"],
    ["ambient_atmospheric", "Ambient / atmospheric"],
    ["electronic_modern", "Modern electronic"],
    ["synthwave", "Synthwave"],
    ["rock_instrumental", "Instrumental rock"],
    ["jazz", "Jazz"],
    ["classical_chamber", "Classical chamber"],
    ["folk_acoustic", "Acoustic folk"],
    ["hip_hop_instrumental", "Instrumental hip-hop"],
    ["funk_disco", "Funk / disco"],
    ["horror_tension", "Horror tension · restrained"],
    ["horror_intense", "Horror · intense"],
];
const MIN_NODE_WIDTH = 560;
const MIN_NODE_HEIGHT = 320;
const MIN_MULTILINE_HEIGHT = 72;
const MAX_MULTILINE_HEIGHT = 720;
const MAX_GENERATION_SECONDS = 150;
const MAX_GENERATION_FRAMES = 3600;
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
    instrumental_style: "Music genre / style",
    acoustic_space: "Acoustic space (diegetic sound)",
    dialogue_coverage: "Dialogue coverage",
    voice_performance: "Voice performance",
    aspect_ratio: "Aspect ratio",
    media_manifest: "Media metadata JSON (optional)",
    multishot_shot_count: "Multishot count",
    frame_count: "Exact frames (0 = use duration)",
    multishot_identity_lock: "Multishot identity lock",
    multishot_voice_lock: "Multishot voice lock",
    multishot_setting_lock: "Multishot setting lock",
    use_remote_model: "Use OpenAI-compatible API model",
    allow_remote_endpoint: "Allow non-local endpoint",
    keep_server_loaded: "Keep local model loaded",
    show_advanced_controls: "Advanced settings",
    delivery_target: "Prompt delivery target",
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
// Look presets live in the browser profile, not in the workflow: they are a
// personal library that must be reusable across scenes, graphs and node types.
const LOOK_STORAGE_KEY = "minimax_h3_looks_v1";
const LOOK_SCHEMA_VERSION = 1;
// Hard cap with oldest-first eviction (by savedAt). 50 named looks stay well
// under any localStorage quota and keep the picker usable; saving a 51st look
// drops the least recently saved one and says so in the panel status.
const MAX_LOOK_PRESETS = 50;
const MAX_LOOK_NAME_LENGTH = 64;
const MAX_LOOK_PAYLOAD_LENGTH = 20000;
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
        ["crime", "Crime"],
        ["western", "Western"],
        ["sports_competition", "Sports competition"],
    ],
    visualLanguage: [
        ["none", "No preference"],
        ["anime_general", "General anime"],
        ["anime_ultradetailed_cinematic", "Ultra-detailed cinematic anime"],
        ["anime_shonen", "Kinetic action anime (shōnen)"],
        ["anime_shojo", "Lyrical shōjo anime"],
        ["anime_shojo_pastel", "Classic luminous shōjo anime"],
        ["anime_retro_dramatic", "Retro dramatic cel anime"],
        ["anime_retro_gag_family", "Retro family gag anime"],
        ["animation_2d", "General 2D animation"],
        ["heroic_limited_cel_tv", "Heroic limited cel television"],
        ["midcentury_graphic_cel_comedy", "Mid-century graphic cel comedy"],
        ["classic_morning_adventure_cel", "Classic morning adventure cel"],
        ["painterly_2d", "Painterly 2D animation"],
        ["watercolor_2d", "Watercolor 2D animation"],
        ["gouache_2d", "Gouache 2D animation"],
        ["japanese_print_animation", "Japanese print-inspired animation"],
        ["american_comic_pastel", "Pastel American comic"],
        ["graphic_novel", "Graphic novel"],
        ["graphic_noir", "Graphic noir"],
        ["pixel_art_16bit", "16-bit pixel art"],
        ["stylized_3d_animation", "Stylized 3D animation"],
        ["cel_shaded_3d", "Cel-shaded 3D animation"],
        ["low_poly_3d", "Low-poly 3D animation"],
        ["game_3d_cinematic", "Real-time game cinematic"],
        ["game_3d_nextgen", "Next-generation AAA cinematic"],
        ["stop_motion_handcrafted", "Handcrafted stop motion"],
        ["supermarionation", "1960s marionette show (supermarionation)"],
        ["rotoscope_animation", "Rotoscoped animation"],
        ["live_action_naturalistic", "Naturalistic live action"],
        ["live_action_cinematic", "Cinematic narrative live action"],
        ["live_action_classic_black_and_white", "Classic high-contrast black-and-white cinema"],
        ["live_action_gritty", "Gritty immediate live action"],
        ["live_action_expressionist", "Expressionist live action"],
        ["storybook_symmetrical", "Symmetrical storybook tableau"],
        ["live_action_visceral_horror", "Visceral practical-effects horror"],
        ["live_action_1980s_television", "1980s television drama"],
        ["live_action_latin_american_telenovela", "Latin American telenovela"],
        ["live_action_1980s_action", "1980s practical action cinema"],
        ["live_action_classic_chinese_martial_arts", "Classic Chinese-language martial-arts cinema"],
        ["live_action_classic_western", "Classic western cinema"],
        ["live_action_revisionist_western", "Revisionist western cinema"],
        ["live_action_1950s_studio_color", "1950s studio color cinema"],
        ["live_action_midcentury_technicolor_epic", "Mid-century Technicolor epic"],
        ["giallo", "1970s Italian giallo"],
        ["tokusatsu_sentai", "Tokusatsu hero team (sentai)"],
        ["kaiju_suitmation", "Kaiju suitmation & miniatures"],
        ["1970s_new_hollywood", "1970s New Hollywood 35mm"],
        ["silent_era_1920s", "1920s silent era"],
        ["documentary_observational", "Observational documentary"],
        ["mockumentary_talking_head", "Mockumentary with talking heads"],
        ["surveillance_found_footage", "Surveillance / found footage"],
        ["home_camcorder_1990s", "1990s home camcorder"],
        ["clean_commercial", "Clean commercial presentation"],
    ],
    worldAesthetic: [
        ["none", "No preference"],
        ["cyberpunk", "Cyberpunk"],
        ["film_noir", "Film noir"],
        ["nordic_noir", "Nordic noir"],
        ["science_fiction", "Science fiction"],
        ["high_fantasy", "High fantasy"],
        ["retrofuturism", "Retrofuturism"],
        ["near_future_functional", "Functional near future"],
        ["gothic", "Gothic"],
        ["solarpunk", "Solarpunk"],
        ["steampunk", "Steampunk"],
        ["dieselpunk", "Dieselpunk"],
        ["post_apocalyptic", "Post-apocalyptic"],
        ["historical_period", "Historical period"],
        ["analog_1980s", "Analog 1980s"],
        ["urban_industrial", "Urban industrial"],
        ["retrofuturism_atomic_age", "Atomic-age retrofuturism"],
        ["retrofuturism_cassette", "Cassette futurism"],
        ["retrofuturism_y2k", "Y2K futurism"],
        ["liminal_institutional", "Liminal institutional spaces"],
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
        ["kinetic", "Kinetic"],
        ["pulp_heightened", "Pulp heightened"],
        ["stoic", "Stoic"],
    ],
    titleScreenStyle: [
        ["none", "No title-screen treatment"],
        ["minimal_cinematic", "Minimal cinematic title"],
        ["bold_broadcast", "Bold broadcast title"],
        ["classic_cel", "Classic cel title"],
        ["illustrated_pulp", "Illustrated pulp title"],
        ["elegant_editorial", "Elegant editorial title"],
        ["neon_technology", "Neon technology title"],
        ["pixel_art_title", "Pixel-art title"],
        ["silent_intertitle", "Silent-era intertitle"],
    ],
};
const VISUAL_LANGUAGE_GROUPS = [
    ["Anime", ["anime_general", "anime_ultradetailed_cinematic", "anime_shonen", "anime_shojo", "anime_shojo_pastel", "anime_retro_dramatic", "anime_retro_gag_family"]],
    ["Classic television cel", ["heroic_limited_cel_tv", "midcentury_graphic_cel_comedy", "classic_morning_adventure_cel"]],
    ["Drawn & painted 2D", ["animation_2d", "painterly_2d", "watercolor_2d", "gouache_2d", "japanese_print_animation"]],
    ["Graphic & pixel styles", ["american_comic_pastel", "graphic_novel", "graphic_noir", "pixel_art_16bit"]],
    ["3D animation", ["stylized_3d_animation", "cel_shaded_3d", "low_poly_3d"]],
    ["Game cinematics", ["game_3d_cinematic", "game_3d_nextgen"]],
    ["Physical animation", ["stop_motion_handcrafted", "supermarionation", "rotoscope_animation"]],
    ["Live action", ["live_action_naturalistic", "live_action_cinematic", "live_action_classic_black_and_white", "live_action_gritty", "live_action_expressionist", "storybook_symmetrical", "live_action_visceral_horror", "live_action_1980s_television", "live_action_latin_american_telenovela", "live_action_1980s_action", "live_action_classic_chinese_martial_arts", "live_action_classic_western", "live_action_revisionist_western", "live_action_1950s_studio_color", "live_action_midcentury_technicolor_epic", "giallo", "tokusatsu_sentai", "kaiju_suitmation", "silent_era_1920s", "1970s_new_hollywood", "documentary_observational", "mockumentary_talking_head"]],
    // Captured on non-cinema hardware: the look comes from the recording device
    // rather than from a film or animation tradition.
    ["Non-cinema cameras", ["surveillance_found_footage", "home_camcorder_1990s"]],
    ["Commercial & presentation", ["clean_commercial"]],
];
const CINEMATOGRAPHY_CHOICES = {
    colorPalette: [["none", "No preference"], ["natural", "Natural"], ["warm", "Warm"], ["cool", "Cool"], ["restrained", "Restrained chroma"], ["vibrant", "Vibrant"], ["monochrome", "Monochrome"], ["midcentury_dye_transfer", "Mid-century dye-transfer color"], ["two_color_process", "Early two-color process"], ["bleach_bypass", "Bleach bypass"], ["teal_orange", "Teal–orange separation"], ["cross_processed", "Cross-processed color"], ["sepia", "Sepia monochrome"], ["saturated_slide_film", "Saturated slide-film color"], ["classic_western_earth_sky", "Classic western earth & sky"], ["revisionist_western_earth", "Revisionist western muted earth"], ["telenovela_broadcast_color", "Telenovela broadcast color"], ["cold_steel_blue", "Cold steel-blue sci-fi"], ["sterile_white_cyan", "Sterile white–cyan sci-fi"], ["neon_cyan_magenta", "Neon cyan–magenta"], ["soft_pastel", "Soft pastel grade"], ["day_for_night", "Day-for-night moonlight"], ["infrared_aerochrome", "Infrared Aerochrome false color"]],
    exposureContrast: [["none", "No preference"], ["high_key", "High-key"], ["balanced", "Balanced"], ["low_key", "Low-key"], ["high_contrast", "High contrast"], ["soft_contrast", "Soft contrast"]],
    shotScale: [["none", "No preference"], ["extreme_close_up", "Extreme close-up"], ["close_up", "Close-up"], ["medium_close_up", "Medium close-up"], ["medium", "Medium"], ["medium_wide", "Medium wide"], ["wide", "Wide"], ["extreme_wide", "Extreme wide"]],
    cameraAngle: [["none", "No preference"], ["eye_level", "Eye level"], ["low_angle", "Low angle"], ["high_angle", "High angle"], ["overhead", "Overhead"], ["dutch_static", "Dutch (static cant)"], ["worms_eye", "Worm's eye"]],
    cameraViewpoint: [["none", "No preference"], ["pov", "First-person POV"], ["over_the_shoulder", "Over the shoulder"], ["mirror_or_reflection", "Mirror or reflection"]],
    cameraMotion: [["none", "No preference"], ["static", "Static shot"], ["zoom_in", "Zoom in"], ["zoom_out", "Zoom out"], ["push_in", "Push in"], ["pull_out", "Pull out"], ["pan_left", "Pan left"], ["pan_right", "Pan right"], ["truck_left", "Truck left"], ["truck_right", "Truck right"], ["tilt_up", "Tilt up"], ["tilt_down", "Tilt down"], ["pedestal_up", "Pedestal up"], ["pedestal_down", "Pedestal down"], ["arc", "Arc shot"], ["tracking", "Tracking shot"], ["shake", "Handheld shake"], ["roll_clockwise", "Roll clockwise"], ["roll_counterclockwise", "Roll counterclockwise"]],
    cameraAmplitude: [["auto", "Automatic"], ["small", "Small"], ["medium", "Medium"], ["large", "Large"]],
    cameraSpeed: [["auto", "Automatic"], ["slow", "Slow"], ["normal", "Normal"], ["fast", "Fast"]],
    optics: [["none", "No preference"], ["wide_perspective", "Wide perspective"], ["natural_perspective", "Natural perspective"], ["compressed_telephoto", "Compressed telephoto"], ["lens_18mm", "18mm lens"], ["lens_35mm", "35mm lens"], ["lens_50mm", "50mm lens"], ["lens_85mm_compressed", "85mm compressed lens"]],
    depthOfField: [["none", "No preference"], ["deep", "Deep focus"], ["balanced", "Balanced depth"], ["shallow", "Shallow focus"]],
    imageTexture: [["none", "No preference"], ["clean_digital", "Clean digital"], ["subtle_stable_grain", "Subtle stable grain"], ["film_16mm", "16mm-inspired"], ["film_35mm", "35mm-inspired"], ["vhs_analog_video", "VHS analog video"], ["early_digital_dv", "Early MiniDV digital video"]],
    lensEffects: [["none", "No preference"], ["clean", "Clean optics"], ["subtle_diffusion", "Subtle diffusion"], ["restrained_halation", "Restrained halation"]],
    motionRendering: [["none", "No preference"], ["crisp", "Crisp motion"], ["natural_blur", "Natural motion blur"], ["energetic_blur", "Energetic motion blur"]],
};
const CINEMATOGRAPHY_FIELDS = [
    ["colorPalette", "Color palette"], ["exposureContrast", "Exposure / contrast"],
    ["shotScale", "Shot scale"], ["cameraAngle", "Camera angle"],
    ["cameraViewpoint", "Camera viewpoint"],
    ["cameraMotion", "H3 camera motion"], ["cameraAmplitude", "Motion amplitude"],
    ["cameraSpeed", "Motion speed"], ["optics", "Optics"],
    ["depthOfField", "Depth of field"], ["imageTexture", "Image texture"],
    ["lensEffects", "Lens effects"], ["motionRendering", "Motion rendering"],
];
// Values saved by older workflows stay loadable: they resolve exactly as the
// backend parser resolves them.
const LEGACY_CAMERA_MOTIONS = {
    pov: { cameraMotion: "none", cameraViewpoint: "pov" },
    shake_slightly: { cameraMotion: "shake", cameraAmplitude: "small" },
    shake_strongly: { cameraMotion: "shake", cameraAmplitude: "large" },
};
const SHOT_TRANSITION_CHOICES = [
    ["cut", "Cut"], ["match_cut", "Match cut"], ["whip_pan", "Whip pan"], ["hold", "Hold"],
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
    {
        key: "titleScreenStyle",
        label: "Title screen",
        title: "Styles only a title screen/card/intertitle explicitly requested in the Basic prompt. Quote the exact visible title text; this control never invents words or creates a title screen.",
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
        .minimax-h3-panel-suspended {
            visibility: hidden !important;
            pointer-events: none !important;
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
            width: 100%;
            max-width: 100%;
            min-width: 0;
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
            max-width: 100%;
            min-height: 30px;
            padding: 6px 9px;
            overflow: hidden;
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
            min-width: 0;
            max-width: 100%;
            flex-wrap: wrap;
            gap: 6px;
            overflow: hidden;
        }
        .minimax-h3-setting-actions select {
            min-width: 0;
            max-width: 100%;
            flex: 1 1 240px;
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
        .minimax-h3-treatment-field.minimax-h3-wide {
            grid-column: 1 / -1;
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
        .minimax-h3-creative-panel input[type="search"],
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
        .minimax-h3-creative-panel input[type="search"]:focus-visible,
        .minimax-h3-creative-panel input[type="number"]:focus-visible,
        .minimax-h3-creative-panel button:focus-visible {
            border-color: var(--p-primary-color, #7ca6ff);
            box-shadow: 0 0 0 1px var(--p-primary-color, #7ca6ff);
        }
        .minimax-h3-creative-panel select {
            height: 27px;
            padding: 2px 5px;
        }
        .minimax-h3-select-search {
            position: relative;
            width: 100%;
        }
        .minimax-h3-searchable-select {
            display: flex;
            width: 100%;
            flex-direction: column;
            gap: 4px;
        }
        .minimax-h3-searchable-select-trigger {
            width: 100%;
            height: 27px;
            padding: 2px 7px;
            border: 1px solid var(--border-color, #666);
            border-radius: 4px;
            background: var(--comfy-input-bg, #222);
            color: var(--input-text, #ddd);
            overflow: hidden;
            font: inherit;
            text-align: left;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .minimax-h3-searchable-select-popover {
            display: flex;
            flex-direction: column;
            gap: 4px;
            padding: 5px;
            border: 1px solid var(--border-color, #666);
            border-radius: 5px;
            background: var(--comfy-input-bg, #222);
        }
        .minimax-h3-searchable-select-popover[hidden] {
            display: none;
        }
        .minimax-h3-searchable-select-options {
            display: flex;
            max-height: 230px;
            flex-direction: column;
            overflow-y: auto;
        }
        .minimax-h3-searchable-select-group {
            padding: 6px 6px 2px;
            color: var(--descrip-text, #999);
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
        }
        .minimax-h3-searchable-select-option {
            min-height: 27px;
            padding: 4px 7px;
            border: 0;
            border-radius: 3px;
            background: transparent;
            color: var(--input-text, #ddd);
            font: inherit;
            text-align: left;
        }
        .minimax-h3-searchable-select-option:hover,
        .minimax-h3-searchable-select-option:focus-visible,
        .minimax-h3-searchable-select-option[aria-selected="true"] {
            background: color-mix(in srgb, var(--p-primary-color, #7ca6ff) 22%, transparent);
        }
        .minimax-h3-select-search-icon {
            position: absolute;
            top: 50%;
            left: 7px;
            z-index: 1;
            transform: translateY(-50%);
            color: var(--descrip-text, #aaa);
            font-size: 12px;
            line-height: 1;
            pointer-events: none;
        }
        .minimax-h3-select-search input[type="search"] {
            width: 100%;
            height: 27px;
            padding: 2px 27px 2px 25px;
        }
        .minimax-h3-select-search input[type="search"]::-webkit-search-cancel-button {
            display: none;
        }
        .minimax-h3-select-search-clear {
            position: absolute;
            top: 50%;
            right: 3px;
            width: 22px;
            height: 22px;
            padding: 0;
            transform: translateY(-50%);
            border: 0;
            border-radius: 3px;
            background: transparent;
            color: var(--descrip-text, #aaa);
            cursor: pointer;
            font: inherit;
        }
        .minimax-h3-select-search-clear:hover:not(:disabled) {
            background: color-mix(in srgb, var(--comfy-input-bg, #292929) 65%, #fff 12%);
            color: var(--input-text, #ddd);
        }
        .minimax-h3-select-search-clear:disabled {
            visibility: hidden;
        }
        .minimax-h3-select-search-status {
            display: none;
            margin: 0;
            color: var(--descrip-text, #aaa);
            font-size: 10.5px;
        }
        .minimax-h3-select-search-status[data-visible="true"] {
            display: block;
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
        .minimax-h3-shot-camera-field,
        .minimax-h3-shot-transition-field {
            display: flex;
            min-width: 0;
            grid-column: 1 / -1;
            align-items: center;
            gap: 6px;
        }
        .minimax-h3-shot-camera-field > span,
        .minimax-h3-shot-transition-field > span {
            color: var(--descrip-text, #aaa);
            font-size: 10px;
            white-space: nowrap;
        }
        .minimax-h3-shot-camera,
        .minimax-h3-shot-transition {
            min-width: 0;
            height: 25px;
            flex: 1;
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
        .minimax-h3-summary-label {
            display: inline-block;
            max-width: calc(100% - 104px);
            overflow: hidden;
            text-overflow: ellipsis;
            vertical-align: middle;
            white-space: nowrap;
        }
        .minimax-h3-explore-button,
        .minimax-h3-look-button {
            min-height: 23px;
            padding: 2px 8px;
            border: 1px solid var(--border-color, #666);
            border-radius: 4px;
            background: var(--comfy-input-bg, #292929);
            color: var(--input-text, #ddd);
            cursor: pointer;
            font: inherit;
        }
        .minimax-h3-explore-button {
            float: right;
            margin-left: 8px;
            font-weight: 600;
            line-height: 1.1;
        }
        .minimax-h3-explore-button:hover:not(:disabled),
        .minimax-h3-look-button:hover:not(:disabled) {
            background: color-mix(in srgb, var(--comfy-input-bg, #292929) 68%, #fff 12%);
        }
        .minimax-h3-look-button:disabled {
            cursor: default;
            opacity: 0.38;
        }
        .minimax-h3-look-row {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            align-items: end;
            gap: 6px;
        }
        .minimax-h3-look-row .minimax-h3-look-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }
        .minimax-h3-look-field {
            display: flex;
            min-width: 0;
            flex-direction: column;
            gap: 3px;
        }
        .minimax-h3-look-field > span {
            overflow: hidden;
            color: var(--descrip-text, #aaa);
            font-size: 10.5px;
            font-weight: 600;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .minimax-h3-look-field input[type="text"] {
            width: 100%;
            height: 27px;
            padding: 2px 5px;
            border: 1px solid var(--border-color, #666);
            border-radius: 4px;
            outline: none;
            background: var(--comfy-input-bg, #222);
            color: var(--input-text, #ddd);
            font: inherit;
        }
        .minimax-h3-look-field input[type="text"]:focus-visible,
        .minimax-h3-look-transfer:focus-visible,
        .minimax-h3-creative-panel .minimax-h3-explore-button:focus-visible,
        .minimax-h3-creative-panel .minimax-h3-look-button:focus-visible {
            border-color: var(--p-primary-color, #7ca6ff);
            box-shadow: 0 0 0 1px var(--p-primary-color, #7ca6ff);
        }
        .minimax-h3-look-transfer {
            min-height: 64px;
            padding: 4px 6px;
            resize: vertical;
            font-size: 10.5px;
            line-height: 1.35;
        }
        .minimax-h3-look-transfer[hidden] {
            display: none;
        }
        .minimax-h3-look-status {
            display: none;
        }
        .minimax-h3-look-status[data-visible="true"] {
            display: block;
        }
        .minimax-h3-look-status[data-invalid="true"] {
            background: color-mix(in srgb, var(--error-text, #e66) 18%, transparent);
            color: var(--error-text, #e99);
            font-weight: 600;
        }
        @media (max-width: 520px) {
            .minimax-h3-treatment-grid,
            .minimax-h3-shot-toolbar,
            .minimax-h3-settings-grid,
            .minimax-h3-look-row {
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
        titleScreenStyle: "none",
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
        shotScale: "none",
        cameraAngle: "none",
        cameraViewpoint: "none",
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

function preservedCreativeValue(value, fallback = "none") {
    return typeof value === "string" && value.length > 0 ? value : fallback;
}

function sanitizeCreativeTreatment(value) {
    const parsed = parseJsonObject(value);
    if (!parsed || parsed.schemaVersion !== CREATIVE_SCHEMA_VERSION) return defaultCreativeTreatment();
    return {
        schemaVersion: CREATIVE_SCHEMA_VERSION,
        genre: preservedCreativeValue(parsed.genre),
        visualLanguage: preservedCreativeValue(parsed.visualLanguage),
        worldAesthetic: preservedCreativeValue(parsed.worldAesthetic),
        tone: preservedCreativeValue(parsed.tone),
        titleScreenStyle: preservedCreativeValue(parsed.titleScreenStyle),
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
    const legacy = LEGACY_CAMERA_MOTIONS[parsed.cameraMotion] ?? null;
    const state = { schemaVersion: CINEMATOGRAPHY_SCHEMA_VERSION };
    for (const [key] of CINEMATOGRAPHY_FIELDS) {
        state[key] = allowedCinematographyValue(key, legacy?.[key] ?? parsed[key]);
    }
    if (["none", "static"].includes(state.cameraMotion)) {
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

    const timingMode = parsed.timingMode === "exact" ? "exact" : "auto";
    const shots = [];
    const usedIds = new Set();
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
        const motion = LEGACY_CAMERA_MOTIONS[source.cameraMotion]?.cameraMotion ?? source.cameraMotion;
        const cameraMotion = allowedCinematographyValue("cameraMotion", motion);
        if (cameraMotion !== "none") shot.cameraMotion = cameraMotion;
        const transitions = SHOT_TRANSITION_CHOICES.map(([token]) => token);
        if (typeof source.transitionIn === "string" && transitions.includes(source.transitionIn)
            && source.transitionIn !== "cut") {
            shot.transitionIn = source.transitionIn;
        }
        if (timingMode === "exact") {
            // A row without a usable duration keeps no durationSeconds key. The
            // plan stays "exact" on purpose: silently downgrading to auto used
            // to erase every duration the user had already typed. The missing
            // row is surfaced by updateShotSummary (red summary + aria-invalid)
            // and, if it is still missing at run time, rejected by the backend's
            // parse_shot_plan with an explicit error.
            const duration = validDuration(source.durationSeconds);
            if (duration !== null) shot.durationSeconds = duration;
        }
        shots.push(shot);
    }

    // Auto timing never carries per-row durations.
    if (timingMode === "auto") {
        for (const shot of shots) delete shot.durationSeconds;
    }
    // Row 1 has no incoming boundary, so it never carries a transition.
    if (shots.length) delete shots[0].transitionIn;
    return {
        schemaVersion: SHOT_PLAN_SCHEMA_VERSION,
        timingMode,
        shots,
    };
}

function serializeCreativeTreatment(state) {
    return JSON.stringify({
        schemaVersion: CREATIVE_SCHEMA_VERSION,
        genre: preservedCreativeValue(state?.genre),
        visualLanguage: preservedCreativeValue(state?.visualLanguage),
        worldAesthetic: preservedCreativeValue(state?.worldAesthetic),
        tone: preservedCreativeValue(state?.tone),
        titleScreenStyle: preservedCreativeValue(state?.titleScreenStyle),
    });
}

function serializeCinematography(state) {
    const result = { schemaVersion: CINEMATOGRAPHY_SCHEMA_VERSION };
    for (const [key] of CINEMATOGRAPHY_FIELDS) {
        result[key] = allowedCinematographyValue(key, state?.[key]);
    }
    if (["none", "static"].includes(result.cameraMotion)) {
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

// ---------------------------------------------------------------------------
// Look presets. A "look" is the reusable half of the panel: creative treatment
// plus cinematography. The shot plan is deliberately excluded because it is
// scene-specific. Storage is the browser profile (this is a ComfyUI frontend
// extension), never the workflow, so nothing here can shift widgets_values.
// ---------------------------------------------------------------------------
function lookStorageArea() {
    // Hardened profiles throw on the very access to localStorage.
    try {
        return window.localStorage ?? null;
    } catch {
        return null;
    }
}

function normalizeLookName(value) {
    return String(value ?? "").replace(/\s+/g, " ").trim().slice(0, MAX_LOOK_NAME_LENGTH);
}

// Defensive by contract: unknown keys are ignored, missing sections fall back to
// the documented defaults, and malformed input returns null instead of throwing.
function sanitizeLookEnvelope(value, fallbackName = "") {
    const parsed = parseJsonObject(value);
    if (!parsed) return null;
    if (parsed.schemaVersion !== undefined && parsed.schemaVersion !== LOOK_SCHEMA_VERSION) return null;
    const name = normalizeLookName(parsed.name) || normalizeLookName(fallbackName);
    if (!name) return null;
    if (parsed.creativeTreatment === undefined && parsed.cinematography === undefined) return null;
    const savedAt = Number(parsed.savedAt);
    return {
        name,
        schemaVersion: LOOK_SCHEMA_VERSION,
        savedAt: Number.isFinite(savedAt) && savedAt > 0 ? savedAt : Date.now(),
        creativeTreatment: sanitizeCreativeTreatment(parsed.creativeTreatment),
        cinematography: sanitizeCinematography(parsed.cinematography),
    };
}

function readLookPresets() {
    const storage = lookStorageArea();
    if (!storage) return {};
    let raw = null;
    try {
        raw = storage.getItem(LOOK_STORAGE_KEY);
    } catch {
        return {};
    }
    const parsed = parseJsonObject(raw);
    if (!parsed) return {};
    const presets = {};
    for (const [key, value] of Object.entries(parsed)) {
        const envelope = sanitizeLookEnvelope(value, key);
        if (envelope) presets[envelope.name] = envelope;
    }
    return presets;
}

function writeLookPresets(presets) {
    const storage = lookStorageArea();
    if (!storage) return false;
    try {
        storage.setItem(LOOK_STORAGE_KEY, JSON.stringify(presets));
        return true;
    } catch {
        return false;
    }
}

function sortedLookNames(presets) {
    return Object.keys(presets).sort((left, right) => left.localeCompare(right));
}

// Oldest-first eviction keeps the library bounded without ever refusing a save.
function evictOldestLooks(presets) {
    const names = Object.keys(presets);
    if (names.length <= MAX_LOOK_PRESETS) return [];
    const ordered = names.sort((left, right) => (presets[left]?.savedAt ?? 0) - (presets[right]?.savedAt ?? 0));
    const evicted = ordered.slice(0, names.length - MAX_LOOK_PRESETS);
    for (const name of evicted) delete presets[name];
    return evicted;
}

function lookEnvelopeFromNode(node, name) {
    return {
        name: normalizeLookName(name),
        schemaVersion: LOOK_SCHEMA_VERSION,
        savedAt: Date.now(),
        creativeTreatment: sanitizeCreativeTreatment(node.__minimaxCreativeTreatmentState),
        cinematography: sanitizeCinematography(node.__minimaxCinematographyState),
    };
}

function serializeLookEnvelope(envelope) {
    return JSON.stringify({
        name: envelope?.name ?? "",
        schemaVersion: LOOK_SCHEMA_VERSION,
        creativeTreatment: sanitizeCreativeTreatment(envelope?.creativeTreatment),
        cinematography: sanitizeCinematography(envelope?.cinematography),
    });
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

function addVisualLanguageOptions(select, visibleValues = null) {
    const labels = new Map(CREATIVE_CHOICES.visualLanguage);
    addSelectOptions(select, [["none", labels.get("none")]]);
    for (const [groupLabel, values] of VISUAL_LANGUAGE_GROUPS) {
        const visible = visibleValues ? values.filter((value) => visibleValues.has(value)) : values;
        if (!visible.length) continue;
        const group = document.createElement("optgroup");
        group.label = groupLabel;
        addSelectOptions(group, visible.map((value) => [value, labels.get(value)]));
        select.appendChild(group);
    }
}

function normalizedSearchText(value) {
    return String(value ?? "")
        .normalize("NFKD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[_-]+/g, " ")
        .toLocaleLowerCase();
}

function createVisualLanguageSearch(node, select, label) {
    const container = createPanelElement("div", "minimax-h3-searchable-select");
    const trigger = createPanelElement("button", "minimax-h3-searchable-select-trigger");
    trigger.type = "button";
    trigger.setAttribute("role", "combobox");
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    const popover = createPanelElement("div", "minimax-h3-searchable-select-popover");
    popover.hidden = true;
    const search = createPanelElement("div", "minimax-h3-select-search");
    const icon = createPanelElement("span", "minimax-h3-select-search-icon", "🔍");
    icon.setAttribute("aria-hidden", "true");
    const input = createPanelElement("input", "");
    input.type = "search";
    input.autocomplete = "off";
    input.spellcheck = false;
    input.placeholder = "Search visual styles…";
    input.setAttribute("aria-label", `Search ${label}`);
    const list = createPanelElement("div", "minimax-h3-searchable-select-options");
    list.id = `${select.id}-options`;
    list.setAttribute("role", "listbox");
    input.setAttribute("aria-controls", list.id);
    trigger.setAttribute("aria-controls", list.id);
    const clear = createPanelElement("button", "minimax-h3-select-search-clear", "×");
    clear.type = "button";
    clear.disabled = true;
    clear.title = "Clear style search";
    clear.setAttribute("aria-label", "Clear visual style search");
    const status = createPanelElement("p", "minimax-h3-select-search-status");
    status.setAttribute("aria-live", "polite");
    search.append(icon, input, clear);

    const labels = new Map(CREATIVE_CHOICES.visualLanguage);
    const groups = new Map(VISUAL_LANGUAGE_GROUPS.flatMap(([group, values]) => (
        values.map((value) => [value, group])
    )));
    const searchable = CREATIVE_CHOICES.visualLanguage.slice(1).map(([value, choiceLabel]) => ({
        value,
        text: normalizedSearchText(`${choiceLabel} ${value} ${groups.get(value) ?? ""}`),
    }));

    const render = (selectedValue = select.value || "none") => {
        const terms = normalizedSearchText(input.value).trim().split(/\s+/).filter(Boolean);
        const matches = searchable.filter(({ text }) => terms.every((term) => text.includes(term)));
        const visibleValues = new Set(matches.map(({ value }) => value));
        trigger.textContent = `${labels.get(selectedValue) ?? `Unavailable — ${selectedValue}`}  ▾`;
        list.replaceChildren();
        const addChoice = (value) => {
            const option = createPanelElement("button", "minimax-h3-searchable-select-option", labels.get(value));
            option.type = "button";
            option.dataset.value = value;
            option.setAttribute("role", "option");
            option.setAttribute("aria-selected", value === selectedValue ? "true" : "false");
            option.addEventListener("click", () => {
                select.value = value;
                select.dispatchEvent(new Event("change", { bubbles: true }));
                render(value);
                close();
                trigger.focus();
            });
            list.appendChild(option);
        };
        if (!terms.length || normalizedSearchText(labels.get("none")).includes(terms.join(" "))) addChoice("none");
        for (const [groupLabel, values] of VISUAL_LANGUAGE_GROUPS) {
            const visible = values.filter((value) => visibleValues.has(value));
            if (!visible.length) continue;
            list.appendChild(createPanelElement("div", "minimax-h3-searchable-select-group", groupLabel));
            visible.forEach(addChoice);
        }
        clear.disabled = !input.value;
        const noMatches = terms.length > 0 && !list.querySelector("[role='option']");
        status.textContent = noMatches ? "No matching styles. Clear the search to browse all styles." : "";
        status.dataset.visible = noMatches ? "true" : "false";
        scheduleCreativePanelLayout(node);
    };
    const open = () => {
        popover.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
        input.value = "";
        render();
        input.focus();
    };
    const close = () => {
        popover.hidden = true;
        trigger.setAttribute("aria-expanded", "false");
        scheduleCreativePanelLayout(node);
    };
    const clearSearch = () => {
        if (!input.value) return;
        input.value = "";
        render();
        input.focus();
    };
    input.addEventListener("input", () => render());
    input.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            event.preventDefault();
            if (input.value) clearSearch();
            else {
                close();
                trigger.focus();
            }
        } else if (event.key === "ArrowDown" || event.key === "Enter") {
            event.preventDefault();
            list.querySelector("[role='option']")?.focus();
        }
    });
    clear.addEventListener("click", clearSearch);
    trigger.addEventListener("click", () => popover.hidden ? open() : close());
    container.addEventListener("focusout", () => setTimeout(() => {
        if (!container.contains(document.activeElement)) close();
    }, 0));
    popover.append(search, status, list);
    container.append(trigger, popover);
    select.hidden = true;
    select.setAttribute("aria-hidden", "true");
    render();
    return { container, status, trigger, popover, sync: render };
}

function ensureUnavailableOption(select, value) {
    if (typeof value !== "string" || !value) return;
    const exists = [...select.querySelectorAll("option")].some((option) => option.value === value);
    if (exists) return;
    const option = document.createElement("option");
    option.value = value;
    option.textContent = `Unavailable in loaded catalog — ${value}`;
    option.dataset.minimaxUnavailable = "true";
    select.insertBefore(option, select.firstChild?.nextSibling ?? null);
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

function syncCreativePanelSuspension(node) {
    // A collapsed node keeps its DOM widget mounted (hideOnZoom: false keeps it
    // interactive at every zoom), and frontends have shipped versions that do not
    // hide DOM widgets of collapsed nodes. An invisible panel would then keep
    // capturing clicks over whatever sits behind the node's expanded footprint.
    // Suspend interactivity explicitly whenever the node is collapsed.
    const root = node.__minimaxCreativePanel?.root;
    if (root) root.classList.toggle("minimax-h3-panel-suspended", Boolean(node.flags?.collapsed));
}

function installCreativePanelCollapseGuard(node) {
    if (node.__minimaxPanelCollapseGuard) return;
    node.__minimaxPanelCollapseGuard = true;
    const originalCollapse = node.collapse;
    node.collapse = function () {
        const result = originalCollapse?.apply(this, arguments);
        syncCreativePanelSuspension(this);
        return result;
    };
    const originalConfigure = node.onConfigure;
    node.onConfigure = function () {
        const result = originalConfigure?.apply(this, arguments);
        // Workflows saved with the node collapsed restore flags after creation.
        syncCreativePanelSuspension(this);
        return result;
    };
}

function updateCreativePanelHeight(node) {
    const panel = node.__minimaxCreativePanel;
    if (!panel) return;
    syncCreativePanelSuspension(node);
    let preferredHeight = 12;
    for (const details of panel.root.querySelectorAll(":scope > details")) {
        if (details.classList.contains("minimax-h3-section-hidden")) continue;
        const body = details.querySelector(":scope > .minimax-h3-panel-body");
        preferredHeight += details.open ? 31 + Math.max(0, body?.scrollHeight ?? 0) : 31;
        preferredHeight += 8;
    }
    preferredHeight = Math.max(72, preferredHeight);
    const panelWidth = Math.max(240, (Number(node.size?.[0]) || MIN_NODE_WIDTH) - 20);
    const changed = panel.widget.__minimaxPreferredHeight !== preferredHeight
        || panel.widget.__minimaxPreferredWidth !== panelWidth;
    panel.widget.__minimaxPreferredHeight = preferredHeight;
    panel.widget.__minimaxPreferredWidth = panelWidth;
    panel.root.style.width = `${panelWidth}px`;
    panel.root.style.maxWidth = `${panelWidth}px`;
    panel.root.style.height = `${preferredHeight}px`;
    panel.widget.computeSize = () => [panelWidth, preferredHeight];
    if (changed) fitNodeToVisibleWidgets(node);
}

function scheduleCreativePanelLayout(node) {
    if (!node?.__minimaxCreativePanel || node.__minimaxCreativeLayoutPending) return;
    node.__minimaxCreativeLayoutPending = true;
    requestAnimationFrame(() => requestAnimationFrame(() => {
        node.__minimaxCreativeLayoutPending = false;
        updateCreativePanelHeight(node);
    }));
}

function observeCreativePanelLayout(node) {
    const panel = node.__minimaxCreativePanel;
    if (!panel || panel.layoutObserver || typeof ResizeObserver !== "function") return;
    panel.layoutObserver = new ResizeObserver(() => scheduleCreativePanelLayout(node));
    // Also parked on the node so releaseCreativeDirectionPanel can disconnect it
    // without depending on the panel record still being reachable.
    node.__minimaxPanelResizeObserver = panel.layoutObserver;
    for (const body of panel.root.querySelectorAll(".minimax-h3-panel-body")) {
        panel.layoutObserver.observe(body);
    }
}

function releaseCreativeDirectionPanel(node) {
    node.__minimaxPanelResizeObserver?.disconnect?.();
    node.__minimaxPanelResizeObserver = null;
    const panel = node.__minimaxCreativePanel;
    if (panel) {
        panel.layoutObserver = null;
        // addDOMWidget owns the element: ComfyUI detaches it from its DOM
        // container when the node goes away. Only clean up what it left behind,
        // never remove an element the frontend still manages.
        if (panel.root?.isConnected) panel.root.remove();
        // The panel widget is non-persistent (markPanelWidgetNonPersistent), so
        // dropping it cannot shift widgets_values. Removing it keeps a re-added
        // node instance from ending up with two stacked panels.
        const panelIndex = node.widgets?.indexOf(panel.widget) ?? -1;
        if (panelIndex >= 0) node.widgets.splice(panelIndex, 1);
    }
    node.__minimaxCreativePanel = null;
    node.__minimaxPanelCollapseGuard = false;
    node.__minimaxCreativeTreatmentState = null;
    node.__minimaxCinematographyState = null;
    node.__minimaxShotPlanState = null;
    node.__minimaxProxyManagedWidgets = null;
    node.__minimaxInstrumentalStyleProxy = null;
    node.__minimaxCreativeLayoutPending = false;
}

function installCreativePanelCleanup(node) {
    if (node.__minimaxPanelCleanupInstalled) return;
    node.__minimaxPanelCleanupInstalled = true;
    const originalRemoved = node.onRemoved;
    node.onRemoved = function () {
        // Run the previous handler first: addDOMWidget installs its own
        // onRemoved to detach the element, so releasing afterwards never
        // double-removes it.
        const result = originalRemoved?.apply(this, arguments);
        releaseCreativeDirectionPanel(this);
        return result;
    };
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
    const unavailable = CREATIVE_FIELD_DEFINITIONS.flatMap(({ key, label }) => {
        const value = node.__minimaxCreativeTreatmentState?.[key];
        const known = CREATIVE_CHOICES[key].some(([token]) => token === value);
        return known ? [] : [`${label}: ${value}`];
    });
    const messages = [];
    if (!enabled) messages.push("Treatment is saved but will not be applied while Enhance description is disabled.");
    if (unavailable.length) {
        messages.push(`Unavailable in the loaded catalog (${unavailable.join(", ")}). Restart/update ComfyUI or choose a replacement.`);
    }
    panel.treatmentStatus.textContent = messages.join(" ");
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

// Both halves go through the same canonical write path the selects use
// (writeJsonStorage on the JSON storage widgets), then the panel is rehydrated
// from those widgets: selects, summaries, the unavailable-value warning and the
// enhancement notice all rebuild from the stored JSON, never from a side state.
function applyLookEnvelope(node, envelope) {
    if (!envelope) return false;
    const creativeWidget = node.widgets?.find((candidate) => candidate.name === CREATIVE_TREATMENT_WIDGET);
    const cinematographyWidget = node.widgets?.find((candidate) => candidate.name === CINEMATOGRAPHY_WIDGET);
    if (!creativeWidget || !cinematographyWidget) return false;
    // Applied verbatim: serializeCreativeTreatment preserves values that this
    // build's catalog does not know, so hydration can flag them through
    // ensureUnavailableOption instead of silently rewriting the workflow.
    writeJsonStorage(node, creativeWidget, serializeCreativeTreatment(envelope.creativeTreatment));
    writeJsonStorage(node, cinematographyWidget, serializeCinematography(envelope.cinematography));
    hydrateCreativeDirectionPanel(node);
    return true;
}

function setLookStatus(node, message, invalid = false) {
    const status = node.__minimaxCreativePanel?.looks?.status;
    if (!status) return;
    status.textContent = message ?? "";
    status.dataset.visible = message ? "true" : "false";
    status.dataset.invalid = invalid ? "true" : "false";
    scheduleCreativePanelLayout(node);
}

function refreshLookPresets(node) {
    const looks = node.__minimaxCreativePanel?.looks;
    if (!looks) return {};
    const presets = readLookPresets();
    const names = sortedLookNames(presets);
    const previous = looks.select.value;
    looks.select.replaceChildren();
    if (names.length) addSelectOptions(looks.select, names.map((name) => [name, name]));
    else addSelectOptions(looks.select, [["", "No saved looks yet"]]);
    looks.select.value = names.includes(previous) ? previous : (names[0] ?? "");
    looks.select.disabled = !names.length;
    looks.applyButton.disabled = !names.length;
    looks.deleteButton.disabled = !names.length;
    looks.summary.textContent = `Looks · ${names.length ? `${names.length} saved` : "None saved"}`;
    return presets;
}

function randomFrom(values) {
    return values[Math.floor(Math.random() * values.length)];
}

function randomCatalogValue(choices, neutral) {
    const values = (choices ?? []).map(([token]) => token).filter((token) => token !== neutral);
    return values.length ? randomFrom(values) : neutral;
}

// The backend's conflict-resolution pass already reconciles clashing axes at
// generation time, so Explore intentionally carries no compatibility matrix: it
// only has to produce catalog-valid values and let the backend arbitrate.
function exploreLookEnvelope(node, { includeCinematography = false } = {}) {
    const creativeTreatment = sanitizeCreativeTreatment(node.__minimaxCreativeTreatmentState);
    for (const { key } of CREATIVE_FIELD_DEFINITIONS) {
        if (key === "titleScreenStyle") continue;
        creativeTreatment[key] = randomCatalogValue(CREATIVE_CHOICES[key], "none");
    }
    const cinematography = sanitizeCinematography(node.__minimaxCinematographyState);
    // Colour is part of the gamble on every roll; roughly a third of the rolls
    // leave the palette to the model.
    cinematography.colorPalette = Math.random() < 0.3
        ? "none"
        : randomCatalogValue(CINEMATOGRAPHY_CHOICES.colorPalette, "none");
    if (includeCinematography) {
        for (const [key] of CINEMATOGRAPHY_FIELDS) {
            if (key === "colorPalette") continue;
            const neutral = ["cameraAmplitude", "cameraSpeed"].includes(key) ? "auto" : "none";
            cinematography[key] = Math.random() < 0.3
                ? randomCatalogValue(CINEMATOGRAPHY_CHOICES[key], neutral)
                : neutral;
        }
    }
    return {
        name: "Explore",
        schemaVersion: LOOK_SCHEMA_VERSION,
        savedAt: Date.now(),
        creativeTreatment,
        cinematography,
    };
}

function runCreativeExplore(node, fullCinematography) {
    applyLookEnvelope(node, exploreLookEnvelope(node, { includeCinematography: fullCinematography }));
    setLookStatus(
        node,
        fullCinematography
            ? "Explore · new creative direction and full cinematography. The shot plan was left untouched."
            : "Explore · new creative direction and color palette. Shift-click to also roll the cinematography.",
    );
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
    const moving = !["none", "static"].includes(state.cameraMotion);
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
    // Writes the label span, not the <summary>: the Explore button is a sibling
    // inside that summary and must survive every refresh.
    const target = panel.treatmentSummaryLabel ?? panel.treatmentSummary;
    target.textContent = `${prefix} · ${active.length ? active.join(" · ") : "No preferences"}`;
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
        // Rows loaded without a usable duration are kept as-is instead of
        // wiping the whole plan, so they must be reported here.
        const missingDurations = state.shots.filter((shot) => validDuration(shot.durationSeconds) === null).length;
        if (missingDurations) {
            problems.push(`${missingDurations} ${missingDurations === 1 ? "row needs" : "rows need"} a duration`);
        }
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
            // A stored plan may carry a row without a usable duration (hand
            // edited or legacy JSON). Show it as an empty, invalid field instead
            // of printing "undefined" or discarding the sibling durations.
            const storedDuration = validDuration(shot.durationSeconds);
            duration.value = storedDuration === null ? "" : String(storedDuration);
            duration.setAttribute("aria-label", `Exact duration for row ${index + 1}`);
            duration.setAttribute("aria-invalid", storedDuration === null ? "true" : "false");
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
                const current = validDuration(shot.durationSeconds);
                if (next === null) duration.value = current === null ? "" : String(current);
                duration.setAttribute("aria-invalid", validDuration(duration.value) === null ? "true" : "false");
            });
            durationField.appendChild(duration);
            fields.appendChild(durationField);
        }

        const cameraField = createPanelElement("label", "minimax-h3-shot-camera-field");
        cameraField.appendChild(createPanelElement("span", "", "Camera"));
        const cameraSelect = createPanelElement("select", "minimax-h3-shot-camera");
        cameraSelect.setAttribute("aria-label", `Camera motion for row ${index + 1}`);
        cameraSelect.title = "Optional. This motion applies to this shot only and never creates a cut.";
        addSelectOptions(cameraSelect, CINEMATOGRAPHY_CHOICES.cameraMotion);
        cameraSelect.value = shot.cameraMotion ?? "none";
        cameraSelect.addEventListener("change", () => {
            const selected = allowedCinematographyValue("cameraMotion", cameraSelect.value);
            if (selected === "none") delete shot.cameraMotion;
            else shot.cameraMotion = selected;
            commitShotPlan(node);
        });
        cameraField.appendChild(cameraSelect);
        fields.appendChild(cameraField);

        if (index > 0) {
            const transitionField = createPanelElement("label", "minimax-h3-shot-transition-field");
            transitionField.appendChild(createPanelElement("span", "", "Transition in"));
            const transitionSelect = createPanelElement("select", "minimax-h3-shot-transition");
            transitionSelect.setAttribute("aria-label", `Incoming transition for row ${index + 1}`);
            transitionSelect.title = "How this existing cut is executed. It never adds or moves a cut.";
            addSelectOptions(transitionSelect, SHOT_TRANSITION_CHOICES);
            transitionSelect.value = shot.transitionIn ?? "cut";
            transitionSelect.addEventListener("change", () => {
                const tokens = SHOT_TRANSITION_CHOICES.map(([token]) => token);
                const selected = tokens.includes(transitionSelect.value) ? transitionSelect.value : "cut";
                if (selected === "cut") delete shot.transitionIn;
                else shot.transitionIn = selected;
                commitShotPlan(node);
            });
            transitionField.appendChild(transitionSelect);
            fields.appendChild(transitionField);
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
        ensureUnavailableOption(panel.creativeSelects[definition.key], creative[definition.key]);
        const filter = panel.creativeFilters?.[definition.key];
        if (filter) filter.sync(creative[definition.key]);
        else panel.creativeSelects[definition.key].value = creative[definition.key];
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
                    const models = await requestDiscoveredModels(node);
                    discovered.replaceChildren();
                    addSelectOptions(discovered, [[AUTOMATIC_MODEL, AUTOMATIC_MODEL], ...models.map((value) => [value, value])]);
                    const current = String(node.widgets?.find((widget) => widget.name === "model")?.value ?? "");
                    discovered.value = current && [...discovered.options].some((option) => option.value === current)
                        ? current : AUTOMATIC_MODEL;
                    if (!models.length) notifyModelDiscoveryError("The endpoint returned no chat-capable models.");
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
        ["delivery_target", "Prompt delivery target"],
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

// Looks section: save / apply / delete / share the reusable half of the panel.
// Everything it owns lives inside the existing DOM widget, so no node widget is
// created and widgets_values cannot move.
function createLooksDetails(node) {
    const details = createPanelElement("details", "minimax-h3-looks-details");
    details.open = accordionState(node, "looks");
    const summary = createPanelElement("summary", "", "Looks · None saved");
    summary.title = "Reusable presets: creative direction + cinematography. The shot plan stays scene-specific and is never stored in a look.";
    const body = createPanelElement("div", "minimax-h3-panel-body");
    const help = createPanelElement(
        "p",
        "minimax-h3-panel-help",
        `Saved in this browser (up to ${MAX_LOOK_PRESETS} looks; saving beyond that drops the oldest one). A look stores creative direction and cinematography, never the shot plan.`,
    );

    const saveRow = createPanelElement("div", "minimax-h3-look-row");
    const nameField = createPanelElement("label", "minimax-h3-look-field");
    nameField.appendChild(createPanelElement("span", "", "Look name"));
    const nameInput = createPanelElement("input", "");
    nameInput.type = "text";
    nameInput.maxLength = MAX_LOOK_NAME_LENGTH;
    nameInput.placeholder = "Name this look…";
    nameInput.setAttribute("aria-label", "Look name");
    nameInput.title = "Name the current creative direction + cinematography, then press Enter or Save.";
    nameField.appendChild(nameInput);
    const saveActions = createPanelElement("div", "minimax-h3-look-actions");
    const saveButton = createPanelElement("button", "minimax-h3-look-button", "Save current look…");
    saveButton.type = "button";
    saveButton.setAttribute("aria-label", "Save the current look");
    saveButton.title = "Stores the current creative direction and cinematography under the name on the left.";
    saveActions.appendChild(saveButton);
    saveRow.append(nameField, saveActions);

    const presetRow = createPanelElement("div", "minimax-h3-look-row");
    const presetField = createPanelElement("label", "minimax-h3-look-field");
    presetField.appendChild(createPanelElement("span", "", "Saved looks"));
    const select = createPanelElement("select", "");
    select.setAttribute("aria-label", "Saved looks");
    select.title = "Pick a saved look, then Apply. Enter applies the selected look.";
    presetField.appendChild(select);
    const presetActions = createPanelElement("div", "minimax-h3-look-actions");
    const applyButton = createPanelElement("button", "minimax-h3-look-button", "Apply");
    applyButton.type = "button";
    applyButton.setAttribute("aria-label", "Apply the selected look");
    applyButton.title = "Overwrites creative direction and cinematography with the selected look.";
    const deleteButton = createPanelElement("button", "minimax-h3-look-button", "Delete");
    deleteButton.type = "button";
    deleteButton.setAttribute("aria-label", "Delete the selected look");
    deleteButton.title = "Removes the selected look from this browser.";
    presetActions.append(applyButton, deleteButton);
    presetRow.append(presetField, presetActions);

    const transferActions = createPanelElement("div", "minimax-h3-setting-actions");
    const copyButton = createPanelElement("button", "minimax-h3-look-button", "Copy look");
    copyButton.type = "button";
    copyButton.setAttribute("aria-label", "Copy the look as JSON");
    copyButton.title = "Copies the selected look (or the current panel state) to the clipboard as JSON.";
    const pasteButton = createPanelElement("button", "minimax-h3-look-button", "Paste look");
    pasteButton.type = "button";
    pasteButton.setAttribute("aria-label", "Paste a look from JSON");
    pasteButton.title = "Reads a look from the clipboard, or opens a box to paste the JSON into.";
    transferActions.append(copyButton, pasteButton);

    const transfer = createPanelElement("textarea", "minimax-h3-look-transfer");
    transfer.hidden = true;
    transfer.spellcheck = false;
    transfer.setAttribute("aria-label", "Look JSON");
    const status = createPanelElement("p", "minimax-h3-panel-status minimax-h3-look-status");
    status.setAttribute("role", "status");
    status.dataset.visible = "false";
    status.dataset.invalid = "false";

    body.append(help, saveRow, presetRow, transferActions, transfer, status);
    details.append(summary, body);

    const hideTransfer = () => {
        transfer.hidden = true;
        transfer.value = "";
        delete transfer.dataset.mode;
        scheduleCreativePanelLayout(node);
    };
    const showTransfer = (mode, value) => {
        transfer.hidden = false;
        transfer.dataset.mode = mode;
        transfer.readOnly = mode === "copy";
        transfer.value = value;
        transfer.setAttribute("aria-label", mode === "copy" ? "Look JSON to copy" : "Look JSON to import");
        scheduleCreativePanelLayout(node);
        if (mode === "copy") {
            transfer.focus();
            transfer.select();
        } else {
            transfer.focus();
        }
    };

    const saveLook = () => {
        const name = normalizeLookName(nameInput.value) || normalizeLookName(select.value);
        if (!name) {
            setLookStatus(node, "Name the look before saving it.", true);
            nameInput.focus();
            return;
        }
        const presets = readLookPresets();
        const existed = Object.prototype.hasOwnProperty.call(presets, name);
        presets[name] = lookEnvelopeFromNode(node, name);
        const evicted = evictOldestLooks(presets);
        if (!writeLookPresets(presets)) {
            setLookStatus(node, "This browser refused to store the look (private mode or full storage).", true);
            return;
        }
        refreshLookPresets(node);
        select.value = name;
        nameInput.value = "";
        const evictionNote = evicted.length ? ` Oldest look removed: “${evicted.join("”, “")}”.` : "";
        setLookStatus(node, `${existed ? "Updated" : "Saved"} “${name}” (creative direction + cinematography).${evictionNote}`);
    };

    const applyLook = () => {
        const name = select.value;
        const presets = refreshLookPresets(node);
        const envelope = presets[name];
        if (!envelope) {
            setLookStatus(node, "That look is no longer stored in this browser.", true);
            return;
        }
        select.value = name;
        if (!applyLookEnvelope(node, envelope)) {
            setLookStatus(node, "This node has no creative-direction storage to write to.", true);
            return;
        }
        setLookStatus(node, `Applied “${name}”. The shot plan was left untouched.`);
    };

    const deleteLook = () => {
        const name = select.value;
        const presets = readLookPresets();
        if (!Object.prototype.hasOwnProperty.call(presets, name)) {
            refreshLookPresets(node);
            setLookStatus(node, "That look is no longer stored in this browser.", true);
            return;
        }
        delete presets[name];
        if (!writeLookPresets(presets)) {
            setLookStatus(node, "This browser refused to update the stored looks.", true);
            return;
        }
        refreshLookPresets(node);
        setLookStatus(node, `Deleted “${name}”. The applied direction is unchanged.`);
    };

    const importLookText = (text) => {
        const raw = String(text ?? "").trim();
        if (!raw) {
            setLookStatus(node, "There is nothing to import.", true);
            return;
        }
        if (raw.length > MAX_LOOK_PAYLOAD_LENGTH) {
            setLookStatus(node, "That payload is too large to be a look.", true);
            return;
        }
        const envelope = sanitizeLookEnvelope(raw, "Imported look");
        if (!envelope) {
            setLookStatus(node, "That text is not a valid look. Expected JSON with name, creativeTreatment and cinematography.", true);
            return;
        }
        if (!applyLookEnvelope(node, envelope)) {
            setLookStatus(node, "This node has no creative-direction storage to write to.", true);
            return;
        }
        nameInput.value = envelope.name;
        hideTransfer();
        setLookStatus(node, `Imported “${envelope.name}” and applied it. Use “Save current look…” to keep it in this browser.`);
    };

    const copyLook = async () => {
        const presets = readLookPresets();
        const selected = presets[select.value];
        const envelope = selected ?? lookEnvelopeFromNode(node, normalizeLookName(nameInput.value) || "Current look");
        const payload = serializeLookEnvelope(envelope);
        const source = selected ? `saved look “${envelope.name}”` : "current panel state";
        let copied = false;
        if (navigator.clipboard?.writeText) {
            try {
                await navigator.clipboard.writeText(payload);
                copied = true;
            } catch {
                copied = false;
            }
        }
        if (copied) {
            hideTransfer();
            setLookStatus(node, `Copied the ${source} to the clipboard.`);
            return;
        }
        showTransfer("copy", payload);
        setLookStatus(node, `The clipboard is unavailable. The ${source} is selected in the box below — copy it with Ctrl/Cmd+C.`);
    };

    const pasteLook = async () => {
        if (transfer.dataset.mode === "paste" && transfer.value.trim()) {
            importLookText(transfer.value);
            return;
        }
        let text = "";
        if (navigator.clipboard?.readText) {
            try {
                text = String((await navigator.clipboard.readText()) ?? "");
            } catch {
                text = "";
            }
        }
        if (!text.trim()) {
            showTransfer("paste", "");
            setLookStatus(node, "Paste the look JSON into the box below, then press “Paste look” again.");
            return;
        }
        importLookText(text);
    };

    saveButton.addEventListener("click", saveLook);
    applyButton.addEventListener("click", applyLook);
    deleteButton.addEventListener("click", deleteLook);
    copyButton.addEventListener("click", () => {
        // Never let a rejected clipboard promise reach the console.
        copyLook().catch(() => setLookStatus(node, "The look could not be copied.", true));
    });
    pasteButton.addEventListener("click", () => {
        pasteLook().catch(() => setLookStatus(node, "The look could not be read from the clipboard.", true));
    });
    nameInput.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        event.preventDefault();
        saveLook();
    });
    select.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        event.preventDefault();
        applyLook();
    });

    return {
        details,
        summary,
        body,
        nameInput,
        select,
        saveButton,
        applyButton,
        deleteButton,
        copyButton,
        pasteButton,
        transfer,
        status,
    };
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
    const treatmentSummary = createPanelElement("summary", "");
    // The label lives in its own span so the summary can also host the Explore
    // button: updateCreativeTreatmentSummary rewrites the span, never the
    // summary element, which would otherwise wipe the button.
    const exploreButton = createPanelElement("button", "minimax-h3-explore-button", "🎲 Explore");
    exploreButton.type = "button";
    exploreButton.setAttribute("aria-label", "Explore: random creative direction");
    exploreButton.title = "Rolls a random genre, visual language, world and tone (plus a color palette). Shift-click also rolls the full cinematography set.";
    const treatmentSummaryLabel = createPanelElement(
        "span",
        "minimax-h3-summary-label",
        isValidator ? "Creative direction context" : "Creative direction · No preferences",
    );
    treatmentSummary.append(exploreButton, treatmentSummaryLabel);
    treatmentSummary.title = isValidator
        ? "Parses the expected treatment and enables supported literal contract checks; it cannot score aesthetic adherence."
        : "Adds creative direction without rewriting the story or creating cuts.";
    const treatmentBody = createPanelElement("div", "minimax-h3-panel-body");
    const treatmentControls = createPanelElement("div", "minimax-h3-treatment-controls");
    const treatmentHelp = createPanelElement(
        "p",
        "minimax-h3-panel-help",
        isValidator
            ? "Supply the treatment used to build the prompt. The Validator checks configuration and supported literal invariants, not whether the prose aesthetically realizes the style."
            : "Adds directing emphasis for the LLM. It never invents story, dialogue, characters, actions, or cuts.",
    );
    const treatmentGrid = createPanelElement("div", "minimax-h3-treatment-grid");
    const creativeSelects = {};
    const creativeFilters = {};
    for (const definition of CREATIVE_FIELD_DEFINITIONS) {
        const field = createPanelElement(
            definition.key === "visualLanguage" ? "div" : "label",
            "minimax-h3-treatment-field",
        );
        field.title = definition.title;
        field.appendChild(createPanelElement("span", "", definition.label));
        const select = createPanelElement("select", "");
        select.setAttribute("aria-label", definition.label);
        select.title = definition.title;
        if (definition.key === "visualLanguage") {
            field.classList.add("minimax-h3-wide");
            select.id = `minimax-h3-visual-language-${Math.random().toString(36).slice(2)}`;
            addVisualLanguageOptions(select);
            const filter = createVisualLanguageSearch(node, select, definition.label);
            creativeFilters[definition.key] = filter;
            field.append(filter.container);
        } else {
            addSelectOptions(select, CREATIVE_CHOICES[definition.key]);
        }
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
        isValidator
            ? "Supply the Cinematography configuration used to build the prompt. The Validator checks its schema and supported literal invariants, not rendered or aesthetic adherence."
            : "Optional explicit presentation controls. H3 camera movement follows motion type + amplitude + speed. Source facts, references, shot rows, and explicit colors remain authoritative.",
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
            if (key === "cameraMotion" && ["none", "static"].includes(state.cameraMotion)) {
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
    // A look is treatment + cinematography, so the section sits right after the
    // two accordions it captures. It exists wherever the creative-direction
    // section exists, i.e. on every node type that owns the JSON storage
    // widgets, without any extra node-type gate.
    const looks = createLooksDetails(node);
    if (modelSetup) root.appendChild(modelSetup.details);
    if (chainedSettings) root.appendChild(chainedSettings.details);
    root.append(treatmentDetails, cinematographyDetails, looks.details, shotDetails);
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
        treatmentSummaryLabel,
        exploreButton,
        looks,
        treatmentBody,
        treatmentStatus,
        creativeSelects,
        creativeFilters,
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
    observeCreativePanelLayout(node);
    installCreativePanelCleanup(node);
    installCreativePanelCollapseGuard(node);
    syncCreativePanelSuspension(node);
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
    bindAccordion(looks.details, "looks");
    bindAccordion(shotDetails, "shotPlan");
    // The library is shared by every panel in the tab, so re-read it whenever
    // the section is opened instead of on every hydration.
    looks.details.addEventListener("toggle", () => {
        if (looks.details.open) refreshLookPresets(node);
    });
    exploreButton.addEventListener("click", (event) => {
        // Inside a <summary>: without this the click would also toggle the
        // accordion, both for pointer and for keyboard activation.
        event.preventDefault();
        event.stopPropagation();
        runCreativeExplore(node, Boolean(event.shiftKey));
    });
    exploreButton.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") event.stopPropagation();
    });
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

    refreshLookPresets(node);
    hydrateCreativeDirectionPanel(node);
    scheduleCreativePanelLayout(node);
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

// Single request/response contract for both discovery entry points (the canvas
// button and the panel button). Non-JSON answers used to surface as a cryptic
// parser error in the panel; both now get the explicit "backend not loaded"
// diagnosis.
async function requestDiscoveredModels(node) {
    const response = await api.fetchApi("/minimax_h3_prompt_enhancer/models", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            endpoint: node.widgets?.find((widget) => widget.name === "endpoint")?.value ?? "",
            api_key: node.widgets?.find((widget) => widget.name === API_KEY_WIDGET)?.value ?? "",
            allow_remote_endpoint: node.widgets?.find((widget) => widget.name === "allow_remote_endpoint")?.value === true,
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
    if (!response.ok) throw new Error(payload?.error || `HTTP ${response.status}`);
    return Array.isArray(payload?.models) ? payload.models.filter(Boolean) : [];
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
        const previousLabel = refresh.label;
        refresh.label = "Loading models…";
        node.graph?.setDirtyCanvas?.(true, true);
        try {
            const discovered = await requestDiscoveredModels(node);
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
    sanitizeNumberWidget(node, "duration_seconds", 5, 4, MAX_GENERATION_SECONDS);
    sanitizeNumberWidget(node, "temperature", 0.2, 0, 2);
    sanitizeIntegerWidget(node, "max_tokens", 4096, 512, 32768);
    sanitizeIntegerWidget(node, "timeout_seconds", 300, 10, 1800);
    sanitizeIntegerWidget(node, "request_timeout", 300, 10, 1800);
    sanitizeIntegerWidget(node, "repair_attempts", 2, 0, 4);
    sanitizeIntegerWidget(node, "context_size", 16384, 4096, 131072);
    sanitizeIntegerWidget(node, "threads", 0, 0, 256);
    sanitizeIntegerWidget(node, "startup_timeout", 180, 10, 1800);
    sanitizeIntegerWidget(node, "multishot_shot_count", 0, 0, 64);
    sanitizeIntegerWidget(node, "frame_count", 0, 0, MAX_GENERATION_FRAMES);
    sanitizeEnumWidget(node, "ambience_foley_policy", ["auto", "ensure_audible", "off"], "auto");
    sanitizeEnumWidget(node, "background_score_policy", ["follow_prompt", "add_instrumental", "off"], "follow_prompt");
    sanitizeEnumWidget(node, "instrumental_style", [
        ...INSTRUMENTAL_STYLE_CHOICES.map(([value]) => value),
    ], "none");
    sanitizeEnumWidget(node, "acoustic_space", [
        "none", "small_reflective_interior", "large_reverberant_interior", "damped_interior",
        "open_exterior", "urban_exterior", "underwater_muffled",
    ], "none");
    sanitizeEnumWidget(node, "dialogue_coverage", ["off", "on"], "off");
    sanitizeEnumWidget(node, "delivery_target", ["local", "api_v2"], "local");
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
    if (["auto", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"].includes(
        String(manifest?.value ?? "").trim().toLowerCase(),
    )) {
        assignMigratedValue(manifest, "");
    }
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
    const instrumentalActive = score?.value === "add_instrumental";
    const styleProxy = node.__minimaxInstrumentalStyleProxy;
    setWidgetVisible(node.widgets?.find((widget) => widget.name === INSTRUMENTAL_WIDGET), instrumentalActive);
    setWidgetVisible(
        node.widgets?.find((widget) => widget.name === INSTRUMENTAL_STYLE_WIDGET),
        instrumentalActive && !styleProxy,
    );
    if (styleProxy) setWidgetVisible(styleProxy.widget, instrumentalActive);
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

// enforceConditionalVisibility is idempotent, but it walks every widget on every
// call. onDrawForeground runs per frame, so it compares this signature of the
// drivers the function actually reads and re-runs only when one of them changed.
function conditionalVisibilitySignature(node) {
    const value = (name) => node.widgets?.find((widget) => widget.name === name)?.value;
    return [
        node.widgets?.length ?? 0,
        node.__minimaxProxyManagedWidgets?.size ?? 0,
        node.__minimaxInstrumentalStyleProxy ? 1 : 0,
        String(value("use_remote_model")),
        String(value("mode")),
        String(value("background_score_policy")),
        String(value("show_advanced_controls")),
        String(value("reference_context") ?? "").trim() ? 1 : 0,
        String(value("media_manifest") ?? "").trim() ? 1 : 0,
        Number(value("frame_count") ?? 0) > 0 ? 1 : 0,
    ].join("|");
}

function protectApiKeyWidget(node) {
    const widget = node.widgets?.find((candidate) => candidate.name === API_KEY_WIDGET);
    if (!widget || widget.__minimaxApiKeyProtected) return;
    // Saved workflows (and the workflow embedded in generated media) must not
    // carry the key in plain text, but the running graph still needs it.
    // Persistence goes through node.serialize()/asSerialisable(), while
    // graphToPrompt reads widget.serializeValue() directly, so a scope flag set
    // around the serializer separates both callers.
    // serialize stays true on purpose: dropping the widget from widgets_values
    // would shift every later value (see repairLegacyModelDiscoveryShift).
    let guarded = false;
    for (const method of ["serialize", "asSerialisable"]) {
        const original = node[method];
        if (typeof original !== "function") continue;
        guarded = true;
        node[method] = function (...args) {
            const previous = node.__minimaxSerializingWorkflow;
            node.__minimaxSerializingWorkflow = true;
            try {
                return original.apply(this, args);
            } finally {
                node.__minimaxSerializingWorkflow = previous;
            }
        };
    }
    if (!guarded) return;
    widget.__minimaxApiKeyProtected = true;
    const originalSerializeValue = widget.serializeValue;
    widget.serializeValue = function (...args) {
        if (node.__minimaxSerializingWorkflow) return "";
        return originalSerializeValue ? originalSerializeValue.apply(this, args) : widget.value;
    };
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
    const style = node.widgets?.find((widget) => widget.name === INSTRUMENTAL_STYLE_WIDGET);
    const styleProxy = node.__minimaxInstrumentalStyleProxy;
    const active = score?.value === "add_instrumental";
    setWidgetVisible(description, score?.value === "add_instrumental");
    setWidgetVisible(style, active && !styleProxy);
    if (styleProxy) {
        setWidgetVisible(style, false);
        setWidgetVisible(styleProxy.widget, active);
        styleProxy.widget.value = styleProxy.valueToLabel.get(String(style?.value ?? "none"))
            ?? INSTRUMENTAL_STYLE_CHOICES[0][1];
    }
    fitNodeToVisibleWidgets(node);
}

function addInstrumentalStyleProxy(node) {
    if (node.__minimaxInstrumentalStyleProxy || typeof node.addWidget !== "function") return;
    const canonical = node.widgets?.find((widget) => widget.name === INSTRUMENTAL_STYLE_WIDGET);
    const score = node.widgets?.find((widget) => widget.name === "background_score_policy");
    if (!canonical || !score) return;
    const valueToLabel = new Map(INSTRUMENTAL_STYLE_CHOICES);
    const labelToValue = new Map(INSTRUMENTAL_STYLE_CHOICES.map(([value, label]) => [label, value]));
    const proxyWidget = node.addWidget(
        "combo",
        INSTRUMENTAL_STYLE_PROXY_WIDGET,
        valueToLabel.get(String(canonical.value ?? "none")) ?? INSTRUMENTAL_STYLE_CHOICES[0][1],
        (label) => setCanonicalValue(node, canonical, labelToValue.get(String(label)) ?? "none"),
        {
            values: INSTRUMENTAL_STYLE_CHOICES.map(([, label]) => label),
            serialize: false,
            tooltip: canonical.options?.tooltip ?? "Adapt the instrumental arrangement while preserving compatible user direction.",
        },
    );
    proxyWidget.label = "Music genre / style";
    markPanelWidgetNonPersistent(proxyWidget);
    const currentIndex = node.widgets.indexOf(proxyWidget);
    const scoreIndex = node.widgets.indexOf(score);
    if (currentIndex >= 0 && scoreIndex >= 0) {
        node.widgets.splice(currentIndex, 1);
        node.widgets.splice(scoreIndex + 1, 0, proxyWidget);
    }
    node.__minimaxInstrumentalStyleProxy = {
        widget: proxyWidget, canonical, valueToLabel, labelToValue,
    };
    setWidgetVisible(canonical, false);
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
    protectApiKeyWidget(node);
    normalizeMigratedRuntimeWidgets(node);
    addInstrumentalStyleProxy(node);
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

// onDrawForeground is a canvas-only hook: the Vue-nodes frontend may never call
// it, which used to leave legacy workflows unmigrated and conditional widgets
// visible. Both passes are idempotent, so they also run from the lifecycle
// hooks. __minimaxWidgetMigrationComplete is deliberately left untouched here so
// the canvas frontend keeps its original one-shot pass on the first frame, for
// the case where widget values only settle after onConfigure returns.
function applyRuntimeWidgetState(node) {
    normalizeMigratedRuntimeWidgets(node, true);
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
            applyRuntimeWidgetState(this);
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
            applyRuntimeWidgetState(this);
            return result;
        };
        const originalDrawForeground = nodeType.prototype.onDrawForeground;
        nodeType.prototype.onDrawForeground = function () {
            if (!this.__minimaxWidgetMigrationComplete) {
                normalizeMigratedRuntimeWidgets(this, true);
                this.__minimaxWidgetMigrationComplete = true;
            }
            // Per-frame hook: only re-enforce when a driver value changed.
            const visibilitySignature = conditionalVisibilitySignature(this);
            if (this.__minimaxVisibilitySignature !== visibilitySignature) {
                this.__minimaxVisibilitySignature = visibilitySignature;
                enforceConditionalVisibility(this);
            }
            const panel = this.__minimaxCreativePanel;
            if (panel) {
                const expectedWidth = Math.max(240, (Number(this.size?.[0]) || MIN_NODE_WIDTH) - 20);
                if (Math.abs((panel.widget.__minimaxPreferredWidth ?? 0) - expectedWidth) > 1) {
                    scheduleCreativePanelLayout(this);
                }
            }
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
