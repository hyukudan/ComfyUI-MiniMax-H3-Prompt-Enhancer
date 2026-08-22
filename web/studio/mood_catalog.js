export const MOOD_DESCRIPTIONS = Object.freeze({
    none: "Leave scene-wide mood unspecified.",
    epic: "Scale and escalation without inventing triumph or music.",
    intimate: "Close, patient and tactile without implying romance.",
    dark: "Visual weight, not threat or new danger.",
    tense: "Anticipation without inventing danger.",
    hopeful: "Opening clarity without forcing triumph.",
    melancholic: "Reflective pace without invented sorrow.",
    playful: "Buoyant timing without invented smiles or gags.",
    restrained: "Editorial economy and controlled emphasis.",
    serene: "Settled spatial calm without adding nature or silence.",
    eerie: "Quiet unfamiliarity without anything supernatural.",
    whimsical: "Graceful charm without inventing comedy or gags.",
    surreal: "Perception shifts while the supplied facts stay intact.",
    clinical: "Procedural precision without implying medicine or hospitals.",
    raw: "Immediate and direct, not damaged, noisy or unstable.",
    kinetic: "Sharper cadence for motion that already exists.",
    pulp_heightened: "Bold graphic emphasis without camp or new drama.",
    stoic: "Contained performance without implying coldness.",
});

export const MOOD_GROUPS = Object.freeze([
    ["Energy & scale", ["epic", "kinetic", "pulp_heightened"]],
    ["Warmth & play", ["hopeful", "playful", "whimsical", "serene"]],
    ["Closeness & feeling", ["intimate", "melancholic"]],
    ["Weight & unease", ["dark", "tense", "eerie", "surreal"]],
    ["Restraint & precision", ["restrained", "stoic", "clinical", "raw"]],
]);

export const MOOD_GUARDRAIL = "Mood shapes staging, camera, light, performance and mix. It never adds facts, dialogue or music.";

export function normalizedMoodSearchText(value) {
    return String(value ?? "")
        .normalize("NFKD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[_-]+/g, " ")
        .toLocaleLowerCase();
}

export function moodChoiceGroups(choices, selectedValue = "none", query = "") {
    const labels = new Map(choices ?? []);
    if (selectedValue && !labels.has(selectedValue)) labels.set(selectedValue, `Unavailable — ${selectedValue}`);
    const terms = normalizedMoodSearchText(query).trim().split(/\s+/).filter(Boolean);
    const knownGroup = new Map(MOOD_GROUPS.flatMap(([group, tokens]) => tokens.map((token) => [token, group])));
    const order = ["", ...MOOD_GROUPS.map(([group]) => group), "Current workflow", "Other"];
    const grouped = new Map(order.map((group) => [group, []]));
    for (const [token, label] of labels) {
        const group = token === "none" ? "" : knownGroup.get(token) ?? (token === selectedValue ? "Current workflow" : "Other");
        const description = MOOD_DESCRIPTIONS[token]
            ?? "Stored value is not in this version's catalog; it remains unchanged until you choose another mood.";
        const searchable = normalizedMoodSearchText(`${token} ${label} ${group} ${description}`);
        if (terms.every((term) => searchable.includes(term))) grouped.get(group).push({ token, label, description });
    }
    return order.map((group) => ({ group, choices: grouped.get(group) })).filter(({ choices: entries }) => entries.length);
}
