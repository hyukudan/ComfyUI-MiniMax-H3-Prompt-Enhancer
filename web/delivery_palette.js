// SPDX-License-Identifier: GPL-3.0-only
// One-click delivery shorthand under basic_prompt.
//
// H3 has no emotion-tag syntax: its published skill puts delivery in prose OUTSIDE <d> and allows
// only the language tag plus the exact words inside it. So these emoji never reach the model --
// prompt_guides.py resolves each one into the documented prose form and strips it from both the
// spoken words and the echoed prompt. The palette is purely an authoring affordance; the meaning
// lives in DELIVERY_EMOJI on the Python side, and the two lists must stay in step.
import { app } from "/scripts/app.js";

const PROMPT_WIDGET = "basic_prompt";
const MIN_PALETTE_HEIGHT = 58;
const PALETTE_PADDING = 8;
const PALETTE_WIDGET = "minimax_h3_delivery_palette";
const TARGET_NODES = new Set([
    "MiniMaxH3PromptEnhancer",
    "MiniMaxH3GGUFPromptEnhancer",
    "MiniMaxH3PromptGuideBuilder",
]);

// tier "verb" marks the ones the official guide spells out as vocal verbs, which is why they are
// listed first: a documented verb is a safer instruction than an invented adverb.
const DELIVERY_EMOJI = [
    { emoji: "💬", tier: "verb", label: "says — neutral" },
    { emoji: "🤫", tier: "verb", label: "whispers" },
    { emoji: "😡", tier: "verb", label: "shouts" },
    { emoji: "❓", tier: "verb", label: "asks" },
    { emoji: "🎤", tier: "verb", label: "sings" },
    { emoji: "📢", tier: "verb", label: "off-screen voiceover" },
    { emoji: "😠", tier: "prose", label: "hard, angry voice" },
    { emoji: "😢", tier: "prose", label: "low, unsteady, close to tears" },
    { emoji: "😭", tier: "prose", label: "through tears" },
    { emoji: "😨", tier: "prose", label: "thin, frightened voice" },
    { emoji: "😀", tier: "prose", label: "bright, warm voice" },
    { emoji: "😂", tier: "prose", label: "through laughter" },
    { emoji: "😏", tier: "prose", label: "flat, sardonic tone" },
    { emoji: "😐", tier: "prose", label: "cold, level voice" },
    { emoji: "🥱", tier: "prose", label: "slow, weary voice" },
    { emoji: "⚡", tier: "prose", label: "quick, urgent voice" },
    { emoji: "🫢", tier: "prose", label: "hushed, breathy voice" },
    { emoji: "⏸️", tier: "pause", label: "pause (our convention: H3 documents none)" },
];

function promptTextarea(node) {
    // The multiline widget is not itself a textarea: element and inputEl are both DIV wrappers
    // with the real control nested inside. Requiring a textarea at the top level made every click
    // a silent no-op, so search downward and only then give up.
    const widget = node.widgets?.find((item) => item.name === PROMPT_WIDGET);
    if (!widget) return null;
    for (const candidate of [widget.element, widget.inputEl]) {
        if (!candidate) continue;
        if (candidate.tagName === "TEXTAREA") return candidate;
        const nested = candidate.querySelector?.("textarea");
        if (nested) return nested;
    }
    return null;
}

// Padding matters: marks bind to a line by proximity on the Python side, so a bare token glued to
// the previous word would read as part of it.
function padded(token, before, after) {
    const lead = before && !/\s$/.test(before) ? " " : "";
    const tail = after && !/^\s/.test(after) ? " " : "";
    return `${lead}${token}${tail}`;
}

function insert(node, token) {
    const widget = node.widgets?.find((item) => item.name === PROMPT_WIDGET);
    if (!widget) return;
    const textarea = promptTextarea(node);
    if (!textarea) {
        // Still better than doing nothing: append to the widget value so the mark is at least
        // usable, even on a frontend whose DOM we cannot walk.
        const current = String(widget.value ?? "");
        widget.value = current + padded(token, current, "");
        widget.callback?.(widget.value);
        node.setDirtyCanvas?.(true, true);
        return;
    }
    const start = textarea.selectionStart ?? textarea.value.length;
    const end = textarea.selectionEnd ?? start;
    const before = textarea.value.slice(0, start);
    const after = textarea.value.slice(end);
    const injected = padded(token, before, after);
    textarea.value = `${before}${injected}${after}`;
    widget.value = textarea.value;
    const caret = start + injected.length;
    textarea.setSelectionRange(caret, caret);
    textarea.focus();
    // The Vue-backed widget syncs from input events, so the value would otherwise revert on redraw.
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    widget.callback?.(textarea.value);
}

function placePaletteUnderPrompt(node) {
    // addDOMWidget appends, which on a node with ~47 inputs strands the palette at the very bottom,
    // nowhere near the box it types into. Other extensions on these nodes also reorder and hide
    // widgets on refresh, so the position is re-asserted rather than set once at build time.
    const widget = node.__minimaxDeliveryPalette?.widget;
    const widgets = node.widgets;
    if (!widget || !widgets) return;
    const promptIndex = widgets.findIndex((item) => item.name === PROMPT_WIDGET);
    const paletteIndex = widgets.indexOf(widget);
    if (promptIndex === -1 || paletteIndex === -1) return;
    if (paletteIndex === promptIndex + 1) return;
    widgets.splice(paletteIndex, 1);
    const target = widgets.findIndex((item) => item.name === PROMPT_WIDGET) + 1;
    widgets.splice(target, 0, widget);
    node.setDirtyCanvas?.(true, true);
}

function buildPalette(node) {
    if (node.__minimaxDeliveryPalette) return;
    if (typeof node.addDOMWidget !== "function") return;
    if (!node.widgets?.some((item) => item.name === PROMPT_WIDGET)) return;

    const root = document.createElement("div");
    root.style.cssText = "display:flex;flex-direction:column;gap:4px;padding:2px 4px;";

    const caption = document.createElement("div");
    caption.textContent = "Delivery — click to insert beside a quoted line";
    caption.style.cssText = "font-size:10px;opacity:0.65;";
    root.appendChild(caption);

    const row = document.createElement("div");
    row.style.cssText = "display:flex;flex-wrap:wrap;gap:3px;";
    for (const { emoji, tier, label } of DELIVERY_EMOJI) {
        const button = document.createElement("button");
        button.textContent = emoji;
        button.title = tier === "verb" ? `${label}  (official H3 verb)` : label;
        button.style.cssText =
            "font-size:15px;line-height:1;padding:3px 5px;cursor:pointer;border-radius:4px;" +
            "background:var(--comfy-input-bg,#222);color:inherit;border:1px solid " +
            (tier === "verb" ? "rgba(120,200,120,0.55)" : "rgba(255,255,255,0.14)") + ";";
        button.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            insert(node, emoji);
        });
        // Without this the canvas swallows the press and starts dragging the node instead.
        button.addEventListener("pointerdown", (event) => event.stopPropagation());
        row.appendChild(button);
    }
    root.appendChild(row);

    const widget = node.addDOMWidget(PALETTE_WIDGET, "minimaxH3DeliveryPalette", root, {
        serialize: false,
        hideOnZoom: false,
    });
    if (widget) {
        // Measured, not hardcoded: the buttons wrap, so the row count depends on node width. A
        // fixed height let the second row overlap the widgets underneath as soon as it existed.
        widget.computeSize = (width) => {
            const measured = root.scrollHeight || root.offsetHeight || 0;
            return [width ?? 0, Math.max(MIN_PALETTE_HEIGHT, measured + PALETTE_PADDING)];
        };
        // Never persist: this is chrome, and a serialized DOM widget shifts every widget index
        // after it when an old workflow is loaded.
        widget.serialize = false;
    }
    node.__minimaxDeliveryPalette = { root, widget };
    placePaletteUnderPrompt(node);

    // The button row rewraps whenever the node is resized, so the height has to be re-measured
    // rather than computed once. Without this the node keeps the height of the old row count.
    if (typeof ResizeObserver === "function") {
        let lastHeight = 0;
        const observer = new ResizeObserver(() => {
            const height = root.scrollHeight || 0;
            if (Math.abs(height - lastHeight) < 2) return;
            lastHeight = height;
            node.setSize?.(node.computeSize?.() ?? node.size);
            node.setDirtyCanvas?.(true, true);
        });
        observer.observe(root);
        node.__minimaxDeliveryPalette.observer = observer;
    }
}

app.registerExtension({
    name: "MiniMaxH3PromptEnhancer.DeliveryPalette",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (!TARGET_NODES.has(nodeData.name)) return;
        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalCreated?.apply(this, arguments);
            // The prompt widget is built by the base implementation, so defer until it exists.
            setTimeout(() => {
                buildPalette(this);
                placePaletteUnderPrompt(this);
            }, 0);
            return result;
        };
        const originalConfigured = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = originalConfigured?.apply(this, arguments);
            setTimeout(() => {
                buildPalette(this);
                placePaletteUnderPrompt(this);
            }, 0);
            return result;
        };
    },
});
