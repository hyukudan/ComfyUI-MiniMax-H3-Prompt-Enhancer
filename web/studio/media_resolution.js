const DEFAULT_DIMENSIONS = Object.freeze({
    "16:9": [1280, 720],
    "9:16": [720, 1280],
    "1:1": [1080, 1080],
    "4:3": [960, 720],
    "3:4": [720, 960],
    "21:9": [1680, 720],
    auto: [1280, 720],
});

const ASPECT_VALUES = Object.freeze({
    "16:9": 16 / 9,
    "9:16": 9 / 16,
    "1:1": 1,
    "4:3": 4 / 3,
    "3:4": 3 / 4,
    "21:9": 21 / 9,
    auto: 16 / 9,
});

// Python round() uses ties-to-even; matching it keeps the live preview exact at
// the rare half-step boundaries before dimensions are aligned to 16 pixels.
function roundHalfEven(value) {
    const floor = Math.floor(value);
    const fraction = value - floor;
    const tolerance = Number.EPSILON * Math.max(1, Math.abs(value)) * 4;
    if (Math.abs(fraction - 0.5) <= tolerance) return floor % 2 === 0 ? floor : floor + 1;
    return Math.round(value);
}

export function effectiveH3Resolution(aspectRatio, targetMegapixels = 0, multipleOf = 16) {
    const ratioKey = String(aspectRatio ?? "").trim().toLocaleLowerCase();
    const megapixels = Number(targetMegapixels);
    if (!Number.isFinite(megapixels) || megapixels <= 0) {
        const [width, height] = DEFAULT_DIMENSIONS[ratioKey] ?? DEFAULT_DIMENSIONS.auto;
        return { width, height, megapixels: (width * height) / 1_000_000, automatic: true };
    }
    const ratio = ASPECT_VALUES[ratioKey] ?? ASPECT_VALUES.auto;
    const alignment = Number.isInteger(multipleOf) && multipleOf > 0 ? multipleOf : 16;
    const rawHeight = Math.sqrt((megapixels * 1_000_000) / ratio);
    const rawWidth = rawHeight * ratio;
    const width = Math.max(alignment, roundHalfEven(rawWidth / alignment) * alignment);
    const height = Math.max(alignment, roundHalfEven(rawHeight / alignment) * alignment);
    return { width, height, megapixels: (width * height) / 1_000_000, automatic: false };
}

export function formatResolutionLabel(resolution) {
    const megapixels = Number(resolution?.megapixels ?? 0);
    const formattedMp = Number.isFinite(megapixels)
        ? megapixels.toFixed(2).replace(/\.00$/, "").replace(/(\.\d)0$/, "$1")
        : "0";
    return `${resolution?.width ?? 0}×${resolution?.height ?? 0} · ${formattedMp} MP`;
}
