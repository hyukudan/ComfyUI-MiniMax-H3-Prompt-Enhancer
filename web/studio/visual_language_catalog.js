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

const ORIGINAL_SAMPLE_PROVENANCE = Object.freeze({
    creator: "OpenAI image generation, directed for this project",
    source: "Generated specifically for this repository on 2026-08-22; not an H3 output",
    license: "GPL-3.0-only project-original asset",
});

function originalPreview(src, alt, sha256) {
    return Object.freeze({
        kind: "original", src, alt,
        provenance: Object.freeze({ ...ORIGINAL_SAMPLE_PROVENANCE, sha256 }),
    });
}

export const VISUAL_LANGUAGE_PREVIEW_MANIFEST = Object.freeze({
    schemaVersion: 1,
    assets: Object.freeze({
        vintage_rubberhose_2d: originalPreview("./previews/vintage_rubberhose_2d.webp", "Original clockwork bird sample with rounded ink-and-cel forms and elastic theatrical-era drawing.", "0e1d7cae634ff4b3c08cae512bf82c469156196a1156cb27b396a076389d9512"),
        cable_angular_graphic_comedy: originalPreview("./previews/cable_angular_graphic_comedy.webp", "Original clockwork bird sample built from angular saturated television-graphic shapes.", "6013b105d797189eae7bcdf18685ec6397833227e71116cb359845a8b975dd14"),
        contemporary_vector_2d: originalPreview("./previews/contemporary_vector_2d.webp", "Original clockwork bird sample with crisp modular vector construction and controlled gradients.", "47e6d43334a4e7d596e0de426841fb4a3b4dc101c89f94993b51f9422a81bd93"),
        manga_monochrome_print: originalPreview("./previews/manga_monochrome_print.webp", "Original monochrome clockwork bird sample using ink, hatching, screentone and open white space.", "697232435515e0025846efd00b2abeb3d92480b599fe102d5a362248f507048f"),
        anime_1960s70s_limited_cel: originalPreview("./previews/anime_1960s70s_limited_cel.webp", "Original clockwork bird sample with a short early-television cel palette and economical held-pose construction.", "cf6f2f089b2226680cc0c0cd67574b1e9d196fb9fd932ec7f7ed88ca318cfae2"),
        mecha_super_robot_cel: originalPreview("./previews/mecha_super_robot_cel.webp", "Original mechanical bird sample with bold classic robot-cel silhouette, joints and shadow bands.", "036c16ca6de6e32d9b30ec2bba9d1ef3153f00165e6e053164f77be821420745"),
        anime_ova_mechanical_detail: originalPreview("./previews/anime_ova_mechanical_detail.webp", "Original clockwork bird sample with dense mechanical linework, material wear and multi-band cel shadows.", "f2802b5c611711268fbac09ba6b95cb0f416a11ad06599864b4da192cb058e39"),
        anime_1990s_broadcast_cel: originalPreview("./previews/anime_1990s_broadcast_cel.webp", "Original clockwork bird sample with warm broadcast-cel color, compact shadows and painted background.", "dc6e708dd631b3c897e4b0d6b86bbd11afeabb888a91e2493650d6d32748e6dc"),
        anime_digital_compositing: originalPreview("./previews/anime_digital_compositing.webp", "Original clockwork bird sample with contemporary digital linework, restrained gradients and layered depth.", "e77e60d90675bbfc861dbc1a2c15a7a695cb8ed5f58813dac26a45c6272692b5"),
    }),
});

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
