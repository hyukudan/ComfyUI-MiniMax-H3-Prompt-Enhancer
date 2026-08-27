const finite = (value) => Number.isFinite(Number(value));

export function audioClipDuration(clip) {
    if (!clip || !finite(clip.startSeconds) || !finite(clip.endSeconds)) return 0;
    return Math.max(0, Number(clip.endSeconds) - Number(clip.startSeconds));
}

export function normalizedAudioClip(clip) {
    if (!clip || !finite(clip.startSeconds) || !finite(clip.endSeconds)) return null;
    const startSeconds = Number(clip.startSeconds);
    const endSeconds = Number(clip.endSeconds);
    if (startSeconds < 0 || endSeconds <= startSeconds || endSeconds - startSeconds > 15) return null;
    return { startSeconds, endSeconds };
}

export function applyAudioClipToAsset(asset, clip, sourceDuration = 0) {
    const normalized = normalizedAudioClip(clip);
    if (!normalized) {
        delete asset.audioClip;
        if (finite(sourceDuration) && Number(sourceDuration) > 0 && Number(sourceDuration) <= 15) {
            asset.durationSeconds = Number(sourceDuration);
        }
        return asset;
    }
    asset.audioClip = normalized;
    asset.durationSeconds = audioClipDuration(normalized);
    return asset;
}

function formatTime(value) {
    const seconds = Math.max(0, Number(value) || 0);
    const minutes = Math.floor(seconds / 60);
    return `${minutes}:${(seconds - minutes * 60).toFixed(2).padStart(5, "0")}`;
}

function control(tag, className = "", text = "") {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
}

async function drawWaveform(canvas, url) {
    if (!url || !globalThis.AudioContext) return;
    try {
        const response = await fetch(url);
        if (!response.ok) return;
        const context = new AudioContext();
        const decoded = await context.decodeAudioData(await response.arrayBuffer());
        const samples = decoded.getChannelData(0);
        const width = Math.max(320, canvas.clientWidth || 640);
        const height = 64;
        canvas.width = width; canvas.height = height;
        const graphics = canvas.getContext("2d");
        graphics.clearRect(0, 0, width, height);
        graphics.fillStyle = "rgba(127, 145, 170, .72)";
        const bucket = Math.max(1, Math.floor(samples.length / width));
        for (let x = 0; x < width; x += 1) {
            let peak = 0;
            const start = x * bucket;
            for (let index = start; index < Math.min(samples.length, start + bucket); index += 1) peak = Math.max(peak, Math.abs(samples[index]));
            const bar = Math.max(1, peak * height);
            graphics.fillRect(x, (height - bar) / 2, 1, bar);
        }
        await context.close();
    } catch (_error) {
        // Native audio still provides duration and exact bounded preview when waveform decoding is unavailable.
    }
}

export function renderAudioTrimEditor({ asset, url, label = "Voice sample", onChange } = {}) {
    const section = control("section", "minimax-h3-audio-trim");
    section.setAttribute("aria-label", `${label} trim editor`);
    const heading = control("div", "minimax-h3-audio-trim-heading");
    heading.append(control("strong", "", label), control("small", "", "Only the selected range is sent to H3"));
    const timeline = control("div", "minimax-h3-audio-trim-timeline");
    const canvas = control("canvas", "minimax-h3-audio-waveform");
    canvas.setAttribute("aria-hidden", "true");
    const selection = control("span", "minimax-h3-audio-trim-selection");
    timeline.append(canvas, selection);
    const audio = control("audio"); audio.preload = "metadata"; audio.src = url || "";
    const rangeRow = control("div", "minimax-h3-audio-trim-ranges");
    const startRange = control("input"); startRange.type = "range"; startRange.step = "0.01"; startRange.min = "0"; startRange.setAttribute("aria-label", "Voice trim start");
    const endRange = control("input"); endRange.type = "range"; endRange.step = "0.01"; endRange.min = "0"; endRange.setAttribute("aria-label", "Voice trim end");
    rangeRow.append(startRange, endRange);
    const timeRow = control("div", "minimax-h3-audio-trim-times");
    const startInput = control("input"); startInput.type = "number"; startInput.step = "0.01"; startInput.min = "0"; startInput.setAttribute("aria-label", "Voice trim start seconds");
    const endInput = control("input"); endInput.type = "number"; endInput.step = "0.01"; endInput.min = "0.01"; endInput.setAttribute("aria-label", "Voice trim end seconds");
    const duration = control("strong", "minimax-h3-audio-trim-duration");
    const status = control("small", "minimax-h3-audio-trim-status"); status.setAttribute("role", "status");
    const actions = control("div", "minimax-h3-audio-trim-actions");
    const preview = control("button", "minimax-h3-button minimax-h3-button-secondary", "Preview selection"); preview.type = "button";
    const stop = control("button", "minimax-h3-button minimax-h3-button-secondary", "Stop"); stop.type = "button";
    const reset = control("button", "minimax-h3-director-text-button", "Reset selection"); reset.type = "button";
    actions.append(preview, stop, reset);
    let sourceDuration = Math.max(Number(asset?.audioClip?.endSeconds) || 0, Number(asset?.durationSeconds) || 0, 0.01);
    let start = Number(asset?.audioClip?.startSeconds) || 0;
    let end = Number(asset?.audioClip?.endSeconds) || sourceDuration;
    let previewFrame = 0;
    const update = () => {
        start = Math.max(0, Math.min(Number(startRange.value) || 0, sourceDuration));
        end = Math.max(start + 0.01, Math.min(Number(endRange.value) || sourceDuration, sourceDuration));
        startRange.value = startInput.value = start.toFixed(2);
        endRange.value = endInput.value = end.toFixed(2);
        const startPercent = sourceDuration ? start / sourceDuration * 100 : 0;
        const endPercent = sourceDuration ? end / sourceDuration * 100 : 100;
        selection.style.left = `${startPercent}%`; selection.style.width = `${Math.max(0, endPercent - startPercent)}%`;
        duration.textContent = `${formatTime(start)} → ${formatTime(end)} · ${(end - start).toFixed(2)}s`;
        const valid = end > start && end - start <= 15;
        status.textContent = valid ? "" : "Choose a range longer than 0 and no longer than 15 seconds.";
        status.dataset.valid = String(valid);
        preview.disabled = !url || !valid;
        return valid;
    };
    const commit = () => {
        if (!update()) return;
        const fullRange = start <= 0.005 && Math.abs(end - sourceDuration) <= 0.01 && sourceDuration <= 15;
        onChange?.(fullRange ? null : { startSeconds: start, endSeconds: end }, sourceDuration);
    };
    for (const input of [startRange, endRange]) input.addEventListener("input", update);
    for (const input of [startRange, endRange]) input.addEventListener("change", commit);
    startInput.addEventListener("change", () => { startRange.value = startInput.value; commit(); });
    endInput.addEventListener("change", () => { endRange.value = endInput.value; commit(); });
    const halt = () => { audio.pause(); if (previewFrame) cancelAnimationFrame(previewFrame); previewFrame = 0; };
    const guardPreview = () => {
        if (audio.currentTime >= end || audio.paused) return halt();
        previewFrame = requestAnimationFrame(guardPreview);
    };
    preview.addEventListener("click", async () => {
        halt(); audio.currentTime = start;
        try { await audio.play(); previewFrame = requestAnimationFrame(guardPreview); }
        catch (error) { status.textContent = error?.message || "Preview could not start."; }
    });
    stop.addEventListener("click", halt);
    reset.addEventListener("click", () => { startRange.value = "0"; endRange.value = String(Math.min(sourceDuration, 15)); commit(); });
    audio.addEventListener("loadedmetadata", () => {
        if (Number.isFinite(audio.duration) && audio.duration > 0) sourceDuration = audio.duration;
        startRange.max = endRange.max = startInput.max = endInput.max = String(sourceDuration);
        if (!asset?.audioClip) end = sourceDuration;
        startRange.value = String(start); endRange.value = String(Math.min(end, sourceDuration)); update();
    });
    startRange.max = endRange.max = startInput.max = endInput.max = String(sourceDuration);
    startRange.value = String(start); endRange.value = String(end); update();
    section.append(heading, timeline, rangeRow, timeRow, actions, status, audio);
    timeRow.append(startInput, endInput, duration);
    if (url) queueMicrotask(() => drawWaveform(canvas, url));
    return section;
}
