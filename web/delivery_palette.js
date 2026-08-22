// SPDX-License-Identifier: GPL-3.0-only
// One-click delivery shorthand under basic_prompt. Tokens stay unchanged; Python resolves them to
// plain H3 prose and strips them from both spoken words and the echoed prompt.
import { app } from "/scripts/app.js";
import {
    clearDeliveryMarksOnLine,
    deliveryStatus,
    editDeliveryMark,
    rovingIndex,
    updateRecentDeliveryMarks,
} from "./delivery_palette_model.js";

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
const DELIVERY_VERBS = DELIVERY_EMOJI.filter(({ tier }) => tier === "verb");
const RECENT_STORAGE_KEY = "minimax_h3_delivery_recent_v1";
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

function markForToken(token) {
    return DELIVERY_EMOJI.find(({ emoji }) => emoji === token);
}

function readRecentMarks() {
    try {
        const parsed = JSON.parse(localStorage.getItem(RECENT_STORAGE_KEY) ?? "[]");
        return Array.isArray(parsed)
            ? parsed.filter((token) => markForToken(token)?.tier === "prose").slice(0, 3)
            : [];
    } catch {
        return [];
    }
}

function writeRecentMarks(tokens) {
    try {
        localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(tokens));
    } catch {
        // Browser storage is an optional convenience; authoring must still work when unavailable.
    }
}

function currentLine(value, caret) {
    const source = String(value ?? "");
    const cursor = Math.max(0, Math.min(source.length, Number(caret) || 0));
    const start = source.lastIndexOf("\n", Math.max(0, cursor - 1)) + 1;
    const newline = source.indexOf("\n", cursor);
    return source.slice(start, newline < 0 ? source.length : newline);
}

function resultMessage(result, mark) {
    if (result.action === "removed") return `Removed ${mark.label} from this line.`;
    if (result.action === "replaced") {
        return `Replaced ${markForToken(result.oldToken)?.label ?? "the previous Delivery verb"} with ${mark.label} on this line.`;
    }
    if (result.action === "cleaned") return `Kept ${mark.label} and removed the conflicting Delivery mark on this line.`;
    if (result.action === "unchanged") return `${mark.label} is already set on this line.`;
    return `${mark.emoji} ${mark.label} added — will be written as prose, not shown in the final prompt.`;
}

function commitTextareaResult(node, state, textarea, result, confirmation) {
    const widget = promptWidget(node);
    if (!widget) return;
    textarea.value = result.value;
    widget.value = result.value;
    textarea.setSelectionRange(result.selectionStart, result.selectionEnd);
    textarea.focus();
    state.suppressNextInputStatus = true;
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    setStatus(state, result.value, confirmation);
    state.syncPressed?.();
}

function applyMark(node, state, mark) {
    const widget = promptWidget(node);
    if (!widget) return;
    const textarea = promptTextarea(node);
    const source = textarea?.value ?? String(widget.value ?? "");
    const start = textarea?.selectionStart ?? source.length;
    const end = textarea?.selectionEnd ?? start;
    const result = editDeliveryMark(source, start, end, mark, DELIVERY_VERBS);
    if (textarea) commitTextareaResult(node, state, textarea, result, resultMessage(result, mark));
    else {
        widget.value = result.value;
        node.setDirtyCanvas?.(true, true);
        setStatus(state, result.value, result.action === "added" ? "Added at the end of the prompt." : resultMessage(result, mark));
    }
    if (mark.tier === "prose" && result.action === "added") state.rememberRecent?.(mark.emoji);
}

function clearCurrentLine(node, state) {
    const widget = promptWidget(node);
    const textarea = promptTextarea(node);
    if (!widget || !textarea) return;
    const result = clearDeliveryMarksOnLine(
        textarea.value,
        textarea.selectionStart ?? textarea.value.length,
        textarea.selectionEnd ?? textarea.selectionStart ?? textarea.value.length,
        DELIVERY_TOKENS,
    );
    const message = result.count
        ? `Cleared ${result.count} ${result.count === 1 ? "mark" : "marks"} from this line.`
        : "This line has no Delivery or Voice color marks.";
    if (result.count) commitTextareaResult(node, state, textarea, result, message);
    else setStatus(state, textarea.value, message);
}

function focusRing(button) {
    button.addEventListener("focus", () => {
        button.style.outline = "2px solid var(--h3-focus, #7ab8ff)";
        button.style.outlineOffset = "1px";
    });
    button.addEventListener("blur", () => { button.style.outline = "none"; });
    button.addEventListener("pointerdown", (event) => event.stopPropagation());
}

function markButton(node, state, mark, compact = false, recent = false) {
    const button = document.createElement("button");
    button.type = "button";
    button.title = mark.title ?? mark.label;
    button.setAttribute("aria-label", recent ? `Recent: ${mark.label}` : mark.label);
    button.setAttribute("aria-pressed", "false");
    button.dataset.deliveryToken = mark.emoji;
    button.style.cssText =
        "min-height:32px;min-width:32px;display:inline-flex;align-items:center;justify-content:flex-start;gap:5px;" +
        `padding:3px ${compact ? "7px" : "8px"};border-radius:6px;color:#ddd;font-size:13px;line-height:1.15;cursor:pointer;` +
        (mark.segment === "channel"
            ? "background:var(--h3-surface, #2a2a2e);border:1px solid #5b6470;"
            : mark.segment === "timing"
                ? "background:var(--h3-surface, #2a2a2e);border:1px dashed #6a6254;"
                : "background:var(--h3-surface, #2a2a2e);border:1px solid #50545c;");
    const restingBackground = button.style.background;
    button.addEventListener("pointerenter", () => { button.style.background = "#343740"; });
    button.addEventListener("pointerleave", () => { button.style.background = restingBackground; });
    const emoji = document.createElement("span");
    emoji.setAttribute("aria-hidden", "true");
    emoji.textContent = mark.emoji;
    const label = document.createElement("span");
    label.textContent = mark.text ?? mark.label;
    label.style.cssText = `font-size:${compact ? "11px" : "12px"};color:#ddd;`;
    button.append(emoji, label);
    if (recent) label.style.display = "none";
    const controls = state.markButtons.get(mark.emoji) ?? [];
    controls.push(button);
    state.markButtons.set(mark.emoji, controls);
    focusRing(button);
    button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        applyMark(node, state, mark);
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
    const state = {
        root,
        status,
        cleanup,
        timers: new Set(),
        markButtons: new Map(),
        recent: readRecentMarks(),
    };
    state.syncPressed = () => {
        const textarea = promptTextarea(node);
        const line = currentLine(textarea?.value ?? promptWidget(node)?.value, textarea?.selectionStart ?? 0);
        for (const [token, controls] of state.markButtons) {
            const selected = line.includes(token);
            for (const control of controls) {
                control.setAttribute("aria-pressed", String(selected));
                control.dataset.selected = String(selected);
                control.style.boxShadow = selected ? "inset 0 0 0 2px var(--h3-focus, #7ab8ff)" : "none";
            }
        }
    };

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
    const footer = document.createElement("div");
    footer.style.cssText = "display:flex;flex-direction:column;align-items:stretch;gap:8px;margin:9px 0 0;padding-top:8px;border-top:1px solid #3a3a40;font-size:10px;color:#aaa;";
    const footerCopy = document.createElement("span");
    footerCopy.textContent = "Combines with any Delivery verb. One or two colors read best.";
    const clearLine = document.createElement("button");
    clearLine.type = "button";
    clearLine.textContent = "Clear marks on this line";
    clearLine.style.cssText = "min-height:30px;align-self:flex-end;padding:3px 9px;border:1px solid #50545c;border-radius:5px;background:#292b30;color:#ddd;cursor:pointer;";
    focusRing(clearLine);
    footer.append(footerCopy, clearLine);
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

    const recent = document.createElement("div");
    recent.setAttribute("role", "group");
    recent.setAttribute("aria-label", "Recent Voice colors");
    recent.style.cssText = "display:flex;gap:4px;align-items:center;";
    state.syncRecentVisibility = () => {
        recent.hidden = !recent.childElementCount || root.getBoundingClientRect().width < 420;
    };
    const renderRecent = () => {
        for (const control of recent.querySelectorAll("button[data-delivery-token]")) {
            const controls = state.markButtons.get(control.dataset.deliveryToken) ?? [];
            state.markButtons.set(control.dataset.deliveryToken, controls.filter((candidate) => candidate !== control));
        }
        recent.replaceChildren();
        for (const token of state.recent) {
            const mark = markForToken(token);
            if (mark) recent.appendChild(markButton(node, state, mark, true, true));
        }
        state.syncRecentVisibility();
        state.syncPressed();
    };
    state.rememberRecent = (token) => {
        state.recent = updateRecentDeliveryMarks(state.recent, token);
        writeRecentMarks(state.recent);
        renderRecent();
    };
    primary.appendChild(recent);
    renderRecent();
    if (typeof ResizeObserver === "function") {
        const observer = new ResizeObserver(() => state.syncRecentVisibility());
        observer.observe(root);
        cleanup.push(() => observer.disconnect());
    }

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
        closeHelp(false);
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
    clearLine.addEventListener("click", () => {
        clearCurrentLine(node, state);
        closeDialog(false);
    });
    dialog.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            event.preventDefault();
            closeDialog(true);
            return;
        }
        if (event.key !== "Tab") return;
        const focusable = [close, ...voiceButtons, clearLine];
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

    const helpButton = document.createElement("button");
    helpButton.type = "button";
    helpButton.textContent = "How marks work";
    helpButton.title = "Delivery marks are converted to prose and removed from the final prompt";
    helpButton.setAttribute("aria-haspopup", "dialog");
    helpButton.setAttribute("aria-expanded", "false");
    helpButton.style.cssText = "min-height:32px;padding:3px 8px;border:0;background:transparent;color:#aeb5bf;text-decoration:underline;text-underline-offset:2px;cursor:pointer;";
    focusRing(helpButton);
    primary.appendChild(helpButton);
    const help = document.createElement("div");
    help.id = `minimax-h3-delivery-help-${paletteSequence}`;
    help.hidden = true;
    help.tabIndex = -1;
    help.setAttribute("role", "dialog");
    help.setAttribute("aria-label", "How Delivery marks work");
    help.style.cssText = "display:none;position:fixed;z-index:2001;width:min(300px,calc(100vw - 16px));padding:10px;border:1px solid #50545c;border-radius:8px;background:var(--h3-surface-raised,#24262b);box-shadow:0 6px 18px rgba(0,0,0,.5);color:#ddd;font-size:11px;line-height:1.4;";
    const helpLead = document.createElement("strong");
    helpLead.textContent = "Marks resolve to plain prose — they never appear in the final prompt.";
    const helpBody = document.createElement("p");
    helpBody.textContent = "Place a mark next to the line it belongs to — beside or inside the quotes. One delivery verb per line; colors combine freely. Voice colors also guide visible performance.";
    helpBody.style.cssText = "margin:6px 0 0;";
    help.append(helpLead, helpBody);
    document.body.appendChild(help);
    helpButton.setAttribute("aria-controls", help.id);
    const closeHelp = (restoreFocus = false) => {
        if (help.hidden) return;
        help.hidden = true;
        help.style.display = "none";
        helpButton.setAttribute("aria-expanded", "false");
        if (restoreFocus) helpButton.focus();
    };
    const openHelp = () => {
        closeDialog(false);
        const anchor = helpButton.getBoundingClientRect();
        help.hidden = false;
        help.style.display = "block";
        help.style.visibility = "hidden";
        const rect = help.getBoundingClientRect();
        help.style.left = `${Math.max(8, Math.min(anchor.left, window.innerWidth - rect.width - 8))}px`;
        help.style.top = `${anchor.bottom + rect.height + 4 > window.innerHeight ? Math.max(8, anchor.top - rect.height - 4) : anchor.bottom + 4}px`;
        help.style.visibility = "visible";
        helpButton.setAttribute("aria-expanded", "true");
        help.focus();
    };
    helpButton.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (help.hidden) openHelp(); else closeHelp(true);
    });
    help.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            event.preventDefault();
            closeHelp(true);
        }
    });
    const outsideHelp = (event) => {
        if (!helpButton.contains(event.target) && !help.contains(event.target)) closeHelp(false);
    };
    const viewportDismissHelp = () => closeHelp(help.contains(document.activeElement));
    document.addEventListener("pointerdown", outsideHelp);
    window.addEventListener("scroll", viewportDismissHelp, true);
    window.addEventListener("resize", viewportDismissHelp);
    cleanup.push(
        () => document.removeEventListener("pointerdown", outsideHelp),
        () => window.removeEventListener("scroll", viewportDismissHelp, true),
        () => window.removeEventListener("resize", viewportDismissHelp),
        () => help.remove(),
    );
    root.append(heading, primary, status);

    const textarea = promptTextarea(node);
    if (textarea) {
        let debounce = null;
        const input = () => {
            state.syncPressed();
            if (state.suppressNextInputStatus) {
                state.suppressNextInputStatus = false;
                return;
            }
            clearTimeout(debounce);
            debounce = setTimeout(() => setStatus(state, textarea.value), 180);
        };
        const caretChanged = () => state.syncPressed();
        textarea.addEventListener("input", input);
        for (const eventName of ["click", "keyup", "select", "focus"]) textarea.addEventListener(eventName, caretChanged);
        state.syncPressed();
        cleanup.push(() => {
            clearTimeout(debounce);
            textarea.removeEventListener("input", input);
            for (const eventName of ["click", "keyup", "select", "focus"]) textarea.removeEventListener(eventName, caretChanged);
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
