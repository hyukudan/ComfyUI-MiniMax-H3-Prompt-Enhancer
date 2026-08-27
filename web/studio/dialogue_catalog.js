export const DIALOGUE_DELIVERY_CHOICES = Object.freeze([
    ["says", "Says"],
    ["whispers", "Whispers"],
    ["shouts", "Shouts"],
    ["asks", "Asks"],
    ["sings", "Sings"],
    ["calls_out", "Calls out"],
]);

export const DIALOGUE_CHANNEL_CHOICES = Object.freeze([
    ["on_screen", "On-screen"],
    ["voice_over", "V.O. · voice-over"],
]);

// Keep these labels aligned with the one-click Voice color palette on basic_prompt.
// Structured shots store the plain-language value, never the authoring emoji.
export const DIALOGUE_VOICE_COLOR_CHOICES = Object.freeze([
    ["", "Natural / unspecified"],
    ["angry, held back", "😠 Angry, held back"],
    ["stunned", "😲 Stunned"],
    ["frightened", "😨 Frightened"],
    ["trembling", "😰 Trembling"],
    ["near tears", "😢 Near tears"],
    ["through tears", "😭 Through tears"],
    ["pleading", "🥺 Pleading"],
    ["tender", "🥰 Tender"],
    ["bright", "😀 Bright"],
    ["through laughter", "😂 Through laughter"],
    ["sardonic", "😏 Sardonic"],
    ["cold, level", "😐 Cold, level"],
    ["weary", "🥱 Weary"],
    ["calm, steady", "😌 Calm, steady"],
    ["urgent", "⚡ Urgent"],
    ["conspiratorial", "🫢 Conspiratorial"],
]);

export function normalizedDialogueControls(dialogue = {}) {
    const legacyVoiceOver = dialogue.delivery === "voice_over";
    const delivery = DIALOGUE_DELIVERY_CHOICES.some(([value]) => value === dialogue.delivery)
        ? dialogue.delivery
        : "says";
    const channel = dialogue.channel === "voice_over" || legacyVoiceOver ? "voice_over" : "on_screen";
    return { delivery, channel, mood: String(dialogue.mood ?? "") };
}

export function voiceColorChoices(current = "") {
    const value = String(current ?? "").trim();
    if (!value || DIALOGUE_VOICE_COLOR_CHOICES.some(([choice]) => choice === value)) {
        return [...DIALOGUE_VOICE_COLOR_CHOICES];
    }
    return [[value, `Custom · ${value}`], ...DIALOGUE_VOICE_COLOR_CHOICES];
}
