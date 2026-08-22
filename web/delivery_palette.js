// SPDX-License-Identifier: GPL-3.0-only
// One-click delivery shorthand under basic_prompt. Tokens stay unchanged; Python resolves them to
// plain H3 prose and strips them from both spoken words and the echoed prompt.
import { app } from "/scripts/app.js";
import { deliveryStatus, insertDeliveryToken, rovingIndex } from "./delivery_palette_model.js";

const PROMPT_WIDGET = "basic_prompt";
const TARGET_NODES = new Set([
    "MiniMaxH3PromptEnhancer",
    "MiniMaxH3GGUFPromptEnhancer",
    "MiniMaxH3PromptGuideBuilder",
]);

// Keep the literal `{ emoji, tier` prefix: the frontend/backend sync guard parses this array.
const DELIVERY_EMOJI = [
    { emoji: "💬", tier: "verb", segment: "delivery", label: "says", text: "says", title: "Neutral, composed delivery — an explicit choice, not the absence of one. Official H3 verb." },
    { emoji: "🤫", tier: "verb", segment: "delivery", label: "whispers", text: "whispers", title: "Breath-light and close. Official H3 verb." },
    { emoji: "😡", tier: "verb", segment: "delivery", label: "shouts", text: "shouts", title: "Loud and forceful. For an angry shout, add “angry” from Voice color. Official H3 verb." },
    { emoji: "❓", tier: "verb", segment: "delivery", label: "asks", text: "asks", title: "Rising pitch, gaze held on the listener. Official H3 verb." },
    { emoji: "🎤", tier: "verb", segment: "delivery", label: "sings", text: "sings", title: "Sustained pitch, phrasing shaped by breath. Official H3 verb." },
    { emoji: "🎙️", tier: "verb", segment: "channel", label: "V.O.", text: "V.O.", title: "Off-screen voiceover. Lips stay closed; the scene keeps moving under the voice." },
    { emoji: "⏸️", tier: "pause", segment: "timing", label: "pause", text: "pause", title: "A held beat, written as “…” inside the quote. Our convention — H3 has no pause syntax." },
    { emoji: "😠", tier: "prose", group: "Angry & hard", label: "angry, held back" },
    { emoji: "😲", tier: "prose", group: "Shaken", label: "stunned" },
    { emoji: "😨", tier: "prose", group: "Shaken", label: "frightened" },
    { emoji: "😢", tier: "prose", group: "Sad & breaking", label: "near tears" },
    { emoji: "😭", tier: "prose", group: "Sad & breaking", label: "through tears" },
    { emoji: "🥺", tier: "prose", group: "Sad & breaking", label: "pleading" },
    { emoji: "🥰", tier: "prose", group: "Warm & bright", label: "tender" },
    { emoji: "😀", tier: "prose", group: "Warm & bright", label: "bright" },
    { emoji: "😂", tier: "prose", group: "Warm & bright", label: "through laughter" },
    { emoji: "😏", tier: "prose", group: "Flat & dry", label: "sardonic" },
    { emoji: "😐", tier: "prose", group: "Flat & dry", label: "cold, level" },
    { emoji: "🥱", tier: "prose", group: "Flat & dry", label: "weary" },
    { emoji: "⚡", tier: "prose", group: "Pressed", label: "urgent" },
    { emoji: "🫢", tier: "prose", group: "Pressed", label: "conspiratorial", title: "Hushed but not a whisper verb — combine with says or asks." },
    // 📢 remains supported by Python for saved prompts, but is intentionally absent here.
];

const DELIVERY_TOKENS = DELIVERY_EMOJI.map(({ emoji }) => emoji);
let paletteSequence = 0;

function promptWidget(node) {
    return node.widgets?.find((item) => item.name === PROMPT_WIDGET) ?? null;
}

function promptTextarea(node) {
    const widget = promptWidget(node);
    if (!widget) return null;
    for (const candidate of [widget.element, widget.inputEl]) {
        if (!candidate) continue;
        if (candidate.tagName === "TEXTAREA") return candidate;
        const nested = candidate.querySelector?.("textarea");
        if (nested) return nested;
    }
    return null;
}

function setStatus(state, value, confirmation = "") {
    const next = deliveryStatus(value, DELIVERY_TOKENS, confirmation);
    state.status.dataset.kind = next.kind;
    state.status.style.color = next.kind === "warning" ? "var(--h3-warning, #f4c36a)" : "#aeb5bf";
    state.status.textContent = next.text;
}

function existingVerbOnLine(value, caret, incoming) {
    const start = value.lastIndexOf("\n", Math.max(0, caret - 1)) + 1;
    const end = value.indexOf("\n", caret);
    const line = value.slice(start, end < 0 ? value.length : end);
    return DELIVERY_EMOJI.some((mark) => mark.tier === "verb" && mark.emoji !== incoming && line.includes(mark.emoji));
}

function insert(node, state, mark) {
    const widget = promptWidget(node);
    if (!widget) return;
    const textarea = promptTextarea(node);
    if (!textarea) {
        const current = String(widget.value ?? "");
        const result = insertDeliveryToken(current, current.length, current.length, mark.emoji);
        widget.value = result.value;
        node.setDirtyCanvas?.(true, true);
        setStatus(state, result.value, "Added at the end of the prompt.");
        return;
    }
    const start = textarea.selectionStart ?? textarea.value.length;
    const end = textarea.selectionEnd ?? start;
    const alreadyHasVerb = mark.tier === "verb" && existingVerbOnLine(textarea.value, start, mark.emoji);
    const result = insertDeliveryToken(textarea.value, start, end, mark.emoji);
    textarea.value = result.value;
    widget.value = result.value;
    textarea.setSelectionRange(result.selectionStart, result.selectionEnd);
    textarea.focus();
    state.suppressNextInputStatus = true;
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    const confirmation = alreadyHasVerb
        ? "This line already has a Delivery verb. Keep one verb per line."
        : `${mark.emoji} ${mark.label} added — will be written as prose, not shown in the final prompt.`;
    setStatus(state, result.value, confirmation);
}

function focusRing(button) {
    button.addEventListener("focus", () => {
        button.style.outline = "2px solid var(--h3-focus, #7ab8ff)";
        button.style.outlineOffset = "1px";
    });
    button.addEventListener("blur", () => { button.style.outline = "none"; });
    button.addEventListener("pointerdown", (event) => event.stopPropagation());
}

function markButton(node, state, mark, compact = false) {
    const button = document.createElement("button");
    button.type = "button";
    button.title = mark.title ?? mark.label;
    button.setAttribute("aria-label", mark.label);
    button.style.cssText =
        "min-height:32px;min-width:32px;display:inline-flex;align-items:center;justify-content:flex-start;gap:5px;" +
        `padding:3px ${compact ? "7px" : "8px"};border-radius:6px;color:#ddd;font-size:13px;line-height:1.15;cursor:pointer;` +
        (mark.tier === "verb"
            ? "background:rgba(74,222,128,.10);border:2px solid var(--h3-success, #4ade80);"
            : "background:var(--h3-surface, #2a2a2e);border:1px solid #3a3a40;");
    const emoji = document.createElement("span");
    emoji.setAttribute("aria-hidden", "true");
    emoji.textContent = mark.emoji;
    const label = document.createElement("span");
    label.textContent = mark.text ?? mark.label;
    label.style.cssText = `font-size:${compact ? "11px" : "12px"};color:${mark.tier === "verb" ? "#cfe9d6" : "#ddd"};`;
    button.append(emoji, label);
    focusRing(button);
    button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        insert(node, state, mark);
    });
    return button;
}

function segment(label, buttons) {
    const group = document.createElement("div");
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", label);
    group.style.cssText = "display:flex;flex-wrap:wrap;max-width:100%;align-items:flex-end;gap:4px;padding-right:4px;border-right:1px solid #444;";
    const caption = document.createElement("span");
    caption.textContent = label;
    caption.style.cssText = "align-self:center;font-size:9px;line-height:1;color:#999;text-transform:uppercase;letter-spacing:.05em;";
    group.append(caption, ...buttons);
    return group;
}

function installRoving(buttons, columns = 1) {
    buttons.forEach((button, index) => {
        button.tabIndex = index === 0 ? 0 : -1;
        button.addEventListener("focus", () => {
            buttons.forEach((candidate) => { candidate.tabIndex = candidate === button ? 0 : -1; });
        });
        button.addEventListener("keydown", (event) => {
            const next = rovingIndex(index, event.key, buttons.length, columns);
            if (next === index || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
            event.preventDefault();
            buttons[next].focus();
        });
    });
}

function buildPaletteRoot(node) {
    const cleanup = [];
    const root = document.createElement("div");
    root.style.cssText = "position:relative;display:flex;flex-direction:column;gap:5px;padding:5px 2px 0;flex:0 0 auto;";
    const heading = document.createElement("strong");
    heading.textContent = "Delivery";
    heading.style.cssText = "font-size:11px;color:#bbb;font-weight:600;";
    const primary = document.createElement("div");
    primary.style.cssText = "display:flex;flex-wrap:wrap;gap:5px;align-items:flex-end;";
    primary.setAttribute("role", "toolbar");
    primary.setAttribute("aria-label", "Delivery marks");
    const status = document.createElement("p");
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    status.setAttribute("aria-atomic", "true");
    status.style.cssText = "min-height:14px;margin:0;font-size:10px;line-height:1.3;color:#aeb5bf;";
    const state = { root, status, cleanup, timers: new Set() };

    const delivery = DELIVERY_EMOJI.filter((mark) => mark.segment === "delivery").map((mark) => markButton(node, state, mark, true));
    const channel = DELIVERY_EMOJI.filter((mark) => mark.segment === "channel").map((mark) => markButton(node, state, mark, true));
    const timing = DELIVERY_EMOJI.filter((mark) => mark.segment === "timing").map((mark) => markButton(node, state, mark, true));
    const primaryMarks = [...delivery, ...channel, ...timing];
    primary.append(segment("Verbs", delivery), segment("Channel", channel), segment("Timing", timing));
    installRoving(primaryMarks);

    const dialog = document.createElement("div");
    dialog.id = `minimax-h3-voice-color-${++paletteSequence}`;
    dialog.hidden = true;
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-label", "Voice color");
    dialog.style.cssText =
        "display:none;position:fixed;z-index:2000;width:min(340px,calc(100vw - 16px));max-height:70vh;overflow:auto;" +
        "padding:10px;border-radius:9px;background:var(--h3-surface, #1e1e22);border:1px solid #3a3a40;" +
        "box-shadow:0 6px 20px rgba(0,0,0,.55);color:#ddd;";
    document.body.appendChild(dialog);
    const dialogHeader = document.createElement("div");
    dialogHeader.style.cssText = "display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;";
    const dialogTitle = document.createElement("strong");
    dialogTitle.textContent = "Voice color";
    const close = document.createElement("button");
    close.type = "button";
    close.textContent = "×";
    close.setAttribute("aria-label", "Close Voice color");
    close.style.cssText = "min-width:32px;min-height:32px;background:transparent;border:0;color:#ddd;font-size:20px;cursor:pointer;";
    focusRing(close);
    dialogHeader.append(dialogTitle, close);
    const library = document.createElement("div");
    library.style.cssText = "display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;";
    const voiceButtons = [];
    const groups = [...new Set(DELIVERY_EMOJI.filter((mark) => mark.tier === "prose").map((mark) => mark.group))];
    for (const groupName of groups) {
        const family = document.createElement("section");
        family.setAttribute("aria-label", groupName);
        const familyTitle = document.createElement("strong");
        familyTitle.textContent = groupName;
        familyTitle.style.cssText = "display:block;margin-bottom:4px;font-size:9px;color:#aaa;text-transform:uppercase;letter-spacing:.05em;";
        const items = document.createElement("div");
        items.style.cssText = "display:flex;flex-direction:column;gap:4px;";
        for (const mark of DELIVERY_EMOJI.filter((candidate) => candidate.group === groupName)) {
            const control = markButton(node, state, mark);
            control.style.width = "100%";
            voiceButtons.push(control);
            items.appendChild(control);
        }
        family.append(familyTitle, items);
        library.appendChild(family);
    }
    installRoving(voiceButtons, 2);
    const footer = document.createElement("p");
    footer.textContent = "Combines with any Delivery verb. One or two colors read best.";
    footer.style.cssText = "margin:9px 0 0;padding-top:8px;border-top:1px solid #3a3a40;font-size:10px;color:#aaa;";
    dialog.append(dialogHeader, library, footer);

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.textContent = "Voice…";
    toggle.title = "Add a voice color to a line";
    toggle.setAttribute("aria-haspopup", "dialog");
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-controls", dialog.id);
    toggle.style.cssText = "min-height:32px;padding:3px 10px;border-radius:6px;cursor:pointer;font-size:12px;background:#2a2a2e;border:1px dashed #666;color:#ddd;";
    focusRing(toggle);
    primary.appendChild(toggle);

    const positionDialog = () => {
        const anchor = toggle.getBoundingClientRect();
        dialog.hidden = false;
        dialog.style.display = "block";
        dialog.style.visibility = "hidden";
        const rect = dialog.getBoundingClientRect();
        const left = Math.max(8, Math.min(anchor.left, window.innerWidth - rect.width - 8));
        const below = anchor.bottom + 4;
        const top = below + rect.height > window.innerHeight
            ? Math.max(8, anchor.top - rect.height - 4)
            : below;
        dialog.style.left = `${left}px`;
        dialog.style.top = `${top}px`;
        dialog.style.visibility = "visible";
    };
    const closeDialog = (restoreFocus = false) => {
        if (dialog.hidden) return;
        dialog.hidden = true;
        dialog.style.display = "none";
        toggle.setAttribute("aria-expanded", "false");
        if (restoreFocus) toggle.focus();
    };
    const openDialog = () => {
        positionDialog();
        toggle.setAttribute("aria-expanded", "true");
        voiceButtons[0]?.focus();
    };
    toggle.addEventListener("pointerdown", (event) => event.stopPropagation());
    toggle.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (dialog.hidden) openDialog(); else closeDialog(true);
    });
    close.addEventListener("click", () => closeDialog(true));
    voiceButtons.forEach((button) => button.addEventListener("click", () => closeDialog(false)));
    dialog.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            event.preventDefault();
            closeDialog(true);
            return;
        }
        if (event.key !== "Tab") return;
        const focusable = [close, ...voiceButtons];
        const current = focusable.indexOf(document.activeElement);
        const next = event.shiftKey
            ? (current <= 0 ? focusable.length - 1 : current - 1)
            : (current >= focusable.length - 1 ? 0 : current + 1);
        event.preventDefault();
        focusable[next].focus();
    });
    const outside = (event) => {
        if (!root.contains(event.target) && !dialog.contains(event.target)) {
            closeDialog(dialog.contains(document.activeElement));
        }
    };
    const viewportDismiss = () => closeDialog(dialog.contains(document.activeElement));
    document.addEventListener("pointerdown", outside);
    window.addEventListener("scroll", viewportDismiss, true);
    window.addEventListener("resize", viewportDismiss);
    cleanup.push(
        () => document.removeEventListener("pointerdown", outside),
        () => window.removeEventListener("scroll", viewportDismiss, true),
        () => window.removeEventListener("resize", viewportDismiss),
        () => dialog.remove(),
    );

    const help = document.createElement("details");
    help.style.cssText = "font-size:10px;color:#aaa;";
    const helpSummary = document.createElement("summary");
    helpSummary.textContent = "Marks resolve to plain prose — they never appear in the final prompt.";
    helpSummary.style.cursor = "pointer";
    const helpBody = document.createElement("p");
    helpBody.textContent = "Place a mark next to the line it belongs to — beside or inside the quotes. One delivery verb per line; colors combine freely.";
    helpBody.style.cssText = "margin:4px 0 0;line-height:1.35;";
    help.append(helpSummary, helpBody);
    root.append(heading, primary, help, status);

    const textarea = promptTextarea(node);
    if (textarea) {
        let debounce = null;
        const input = () => {
            if (state.suppressNextInputStatus) {
                state.suppressNextInputStatus = false;
                return;
            }
            clearTimeout(debounce);
            debounce = setTimeout(() => setStatus(state, textarea.value), 180);
        };
        textarea.addEventListener("input", input);
        cleanup.push(() => {
            clearTimeout(debounce);
            textarea.removeEventListener("input", input);
        });
    }
    state.destroy = () => {
        cleanup.splice(0).forEach((dispose) => dispose());
        state.timers.forEach(clearTimeout);
        state.timers.clear();
        root.remove();
    };
    return state;
}

function mountPalette(node) {
    if (node.__minimaxDeliveryPaletteDestroyed) return false;
    const widget = promptWidget(node);
    const textarea = promptTextarea(node);
    if (!widget || !textarea) return false;
    const wrapper = [widget.element, widget.inputEl].find(
        (element) => element && element !== textarea && element.contains(textarea),
    ) ?? textarea.parentElement;
    if (!wrapper) return false;
    node.__minimaxDeliveryPalette ??= buildPaletteRoot(node);
    const root = node.__minimaxDeliveryPalette.root;
    if (root.parentElement === wrapper) return true;
    wrapper.style.display = "flex";
    wrapper.style.flexDirection = "column";
    wrapper.style.overflow = "visible";
    textarea.style.flex = "1 1 auto";
    textarea.style.minHeight = "0";
    wrapper.appendChild(root);
    return true;
}

app.registerExtension({
    name: "MiniMaxH3PromptEnhancer.DeliveryPalette",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (!TARGET_NODES.has(nodeData.name)) return;
        const hook = (name) => {
            const original = nodeType.prototype[name];
            nodeType.prototype[name] = function () {
                this.__minimaxDeliveryPaletteDestroyed = false;
                const result = original?.apply(this, arguments);
                let attempts = 0;
                const attempt = () => {
                    if (this.__minimaxDeliveryPaletteDestroyed) return;
                    if (!mountPalette(this) && ++attempts < 10) {
                        const timer = setTimeout(attempt, 100);
                        this.__minimaxDeliveryPalette?.timers?.add(timer);
                    }
                };
                setTimeout(attempt, 0);
                return result;
            };
        };
        hook("onNodeCreated");
        hook("onConfigure");
        const originalRemoved = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function () {
            this.__minimaxDeliveryPaletteDestroyed = true;
            const state = this.__minimaxDeliveryPalette;
            if (state) {
                state.destroyed = true;
                state.destroy?.();
                this.__minimaxDeliveryPalette = null;
            }
            return originalRemoved?.apply(this, arguments);
        };
    },
});
