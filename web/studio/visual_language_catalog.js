const TAXONOMY = Object.freeze([
    ["", [["", ["none"]]]],
    ["Japanese manga & anime", [
        ["Print foundations", ["manga_monochrome_print", "japanese_print_animation"]],
        ["Early television cel", ["anime_1960s70s_limited_cel"]],
        ["Classic cel eras", ["anime_retro_dramatic", "anime_retro_gag_family", "mecha_super_robot_cel", "anime_ova_mechanical_detail", "anime_1990s_broadcast_cel"]],
        ["Contemporary animation", ["anime_general", "anime_ultradetailed_cinematic", "anime_shonen", "anime_shojo", "anime_shojo_pastel", "anime_digital_compositing"]],
    ]],
    ["US drawn animation", [
        ["General", ["animation_2d"]],
        ["Theatrical era", ["vintage_rubberhose_2d"]],
        ["Television cel", ["heroic_limited_cel_tv", "midcentury_graphic_cel_comedy", "classic_morning_adventure_cel"]],
        ["Graphic & digital eras", ["cable_angular_graphic_comedy", "contemporary_vector_2d"]],
    ]],
    ["Drawn & painted 2D", [
        ["Painted", ["painterly_2d", "watercolor_2d", "gouache_2d"]],
        ["Graphic narrative", ["american_comic_pastel", "graphic_novel", "graphic_noir"]],
        ["Pixel", ["pixel_art_16bit"]],
    ]],
    ["3D animation", [
        ["Stylized", ["stylized_3d_animation", "cel_shaded_3d", "low_poly_3d"]],
        ["Game cinematics", ["game_3d_cinematic", "game_3d_nextgen"]],
    ]],
    ["Physical animation", [
        ["Frame-by-frame", ["stop_motion_handcrafted", "rotoscope_animation"]],
        ["Puppetry", ["supermarionation"]],
    ]],
    ["Live action", [
        ["General", ["live_action_naturalistic", "live_action_cinematic", "live_action_gritty"]],
        ["Classic cinema", ["silent_era_1920s", "live_action_classic_black_and_white", "live_action_1950s_studio_color", "live_action_midcentury_technicolor_epic", "1970s_new_hollywood"]],
        ["Period television & action", ["live_action_1980s_television", "live_action_latin_american_telenovela", "live_action_1980s_action"]],
        ["Genre traditions", ["live_action_expressionist", "storybook_symmetrical", "live_action_visceral_horror", "giallo", "live_action_classic_chinese_martial_arts", "live_action_classic_western", "live_action_revisionist_western"]],
        ["Practical spectacle", ["tokusatsu_sentai", "kaiju_suitmation"]],
        ["Documentary grammar", ["documentary_observational", "mockumentary_talking_head"]],
    ]],
    ["Recorded media", [
        ["Non-cinema cameras", ["surveillance_found_footage", "home_camcorder_1990s"]],
    ]],
    ["Commercial & presentation", [
        ["Clean presentation", ["clean_commercial"]],
    ]],
]);

const ALIASES = Object.freeze({
    vintage_rubberhose_2d: ["1930s theatrical", "rubber hose", "ink and cel"],
    cable_angular_graphic_comedy: ["1990s", "2000s", "cable era", "angular comedy"],
    contemporary_vector_2d: ["vector", "bezier", "cut out", "digital 2d"],
    manga_monochrome_print: ["manga", "monochrome", "screentone", "black and white print"],
    anime_1960s70s_limited_cel: ["1960s anime", "1970s anime", "early tv cel", "limited animation"],
    mecha_super_robot_cel: ["mecha", "super robot", "robot cel", "1970s", "1980s"],
    anime_ova_mechanical_detail: ["1980s ova", "mechanical detail", "cel anime"],
    anime_1990s_broadcast_cel: ["1990s anime", "broadcast cel", "telecine"],
    anime_digital_compositing: ["contemporary anime", "digital compositing", "2.5d parallax"],
});

const TOKEN_LOCATION = new Map();
for (const [family, branches] of TAXONOMY) {
    for (const [branch, tokens] of branches) {
        for (const token of tokens) TOKEN_LOCATION.set(token, { family, branch });
    }
}

export const VISUAL_LANGUAGE_TAXONOMY = TAXONOMY;

// Preview entries are intentionally empty. Future examples must be original or
// licensed local files and satisfy previewRecordIsValid before the UI displays them.
export const VISUAL_LANGUAGE_PREVIEW_MANIFEST = Object.freeze({ schemaVersion: 1, assets: Object.freeze({}) });

export function visualLanguageMetadata(token) {
    const location = TOKEN_LOCATION.get(token) ?? { family: "Other", branch: "Unclassified" };
    return { ...location, aliases: [...(ALIASES[token] ?? [])] };
}

export function visualLanguageSearchText(token, label) {
    const metadata = visualLanguageMetadata(token);
    return [label, token, metadata.family, metadata.branch, ...metadata.aliases].join(" ");
}

export function visualLanguageHierarchy(choices, query = "", normalize = (value) => String(value ?? "").toLocaleLowerCase()) {
    const terms = normalize(query).trim().split(/\s+/).filter(Boolean);
    const available = new Map(choices ?? []);
    const matches = (token, label) => {
        const searchable = normalize(visualLanguageSearchText(token, label));
        return terms.every((term) => searchable.includes(term));
    };
    const hierarchy = [];
    const included = new Set();
    for (const [family, branches] of TAXONOMY) {
        const resultBranches = [];
        for (const [branch, tokens] of branches) {
            const branchChoices = tokens
                .filter((token) => available.has(token) && matches(token, available.get(token)))
                .map((token) => [token, available.get(token)]);
            for (const [token] of branchChoices) included.add(token);
            if (branchChoices.length) resultBranches.push({ branch, choices: branchChoices });
        }
        if (resultBranches.length) hierarchy.push({ family, branches: resultBranches });
    }
    const other = [...available]
        .filter(([token, label]) => !included.has(token) && matches(token, label));
    if (other.length) hierarchy.push({ family: "Other", branches: [{ branch: "Unclassified", choices: other }] });
    return hierarchy;
}

export function previewRecordIsValid(record) {
    const source = record?.src ?? "";
    const relativePath = source.startsWith("./previews/") ? source.slice("./previews/".length) : "";
    return Boolean(
        record
        && ["original", "licensed"].includes(record.kind)
        && /^\.\/previews\/[a-z0-9][a-z0-9._/-]*\.(?:avif|jpe?g|png|webp)$/i.test(source)
        && !relativePath.split("/").includes("..")
        && typeof record.alt === "string" && record.alt.trim()
        && typeof record.provenance?.creator === "string" && record.provenance.creator.trim()
        && typeof record.provenance?.source === "string" && record.provenance.source.trim()
        && typeof record.provenance?.license === "string" && record.provenance.license.trim()
        && /^[a-f0-9]{64}$/i.test(record.provenance?.sha256 ?? "")
    );
}

export function visualLanguagePreview(token, manifest = VISUAL_LANGUAGE_PREVIEW_MANIFEST) {
    const record = manifest?.assets?.[token];
    if (previewRecordIsValid(record)) return { status: "available", ...record };
    return {
        status: "placeholder",
        label: "No sample installed",
        disclosure: "No bundled image claims to predict H3 output. Add only original or licensed examples with provenance.",
    };
}
