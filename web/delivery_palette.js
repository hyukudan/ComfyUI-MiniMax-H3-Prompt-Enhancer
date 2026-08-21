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
const TARGET_NODES = new Set([
    "MiniMaxH3PromptEnhancer",
    "MiniMaxH3GGUFPromptEnhancer",
    "MiniMaxH3PromptGuideBuilder",
]);

// tier "verb" marks the ones the official guide spells out as vocal verbs, which is why they are
// listed first: a documented verb is a safer instruction than an invented adverb.
const DELIVERY_EMOJI = [
    // Row 1, always visible: the marks that resolve to a verb the H3 skill documents, plus the
    // pause. These carry a text label because an emoji alone sends you hunting through tooltips,
    // and because a 1px green border — the old way of marking them as the safest — was invisible
    // against a dark canvas.
    { emoji: "💬", tier: "verb", label: "says — neutral", text: "says" },
    { emoji: "🤫", tier: "verb", label: "whispers", text: "whisper" },
    { emoji: "😡", tier: "verb", label: "shouts", text: "shout" },
    { emoji: "❓", tier: "verb", label: "asks", text: "ask" },
    { emoji: "🎤", tier: "verb", label: "sings", text: "sing" },
    { emoji: "🎙️", tier: "verb", label: "off-screen voiceover (lips stay closed)", text: "V.O." },
    { emoji: "⏸️", tier: "pause", label: "pause (our convention: H3 documents none)", text: "pause" },
    // Row 2, collapsed behind "+ tone": fourteen faces that read as one yellow wall at 20px, so
    // they are grouped by family and kept out of the way until asked for.
    { emoji: "😠", tier: "prose", group: "hard", label: "hard, angry voice" },
    { emoji: "😲", tier: "prose", group: "hard", label: "stunned, words coming late" },
    { emoji: "😨", tier: "prose", group: "hard", label: "thin, frightened voice" },
    { emoji: "😢", tier: "prose", group: "soft", label: "low, unsteady, close to tears" },
    { emoji: "😭", tier: "prose", group: "soft", label: "through tears" },
    { emoji: "🥺", tier: "prose", group: "soft", label: "pleading, high and wavering" },
    { emoji: "🥰", tier: "prose", group: "soft", label: "tender, low and unhurried" },
    { emoji: "😀", tier: "prose", group: "warm", label: "bright, warm voice" },
    { emoji: "😂", tier: "prose", group: "warm", label: "through laughter" },
    { emoji: "😏", tier: "prose", group: "cool", label: "flat, sardonic tone" },
    { emoji: "😐", tier: "prose", group: "cool", label: "cold, level voice" },
    { emoji: "🥱", tier: "prose", group: "cool", label: "slow, weary voice" },
    { emoji: "⚡", tier: "prose", group: "urgent", label: "quick, urgent, pitch raised" },
    { emoji: "🫢", tier: "prose", group: "urgent", label: "hushed, conspiratorial" },
    // 📢 stays mapped in the backend for anything already typed, but is off the palette: people
    // reach for it meaning "announces", and 🎙️ reads as voiceover without the ambiguity.
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
    // The Vue-backed widget syncs from this input event and fires widget.callback itself; calling
    // it here as well ran every extension-wrapped callback twice.
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
}

function makeButton(node, mark) {
    const button = document.createElement("button");
    button.type = "button";
    button.title = mark.tier === "verb" ? `${mark.label}  (official H3 verb)` : mark.label;
    button.setAttribute("aria-label", mark.label);
    button.textContent = mark.emoji;
    if (mark.text) {
        const caption = document.createElement("span");
        caption.textContent = mark.text;
        caption.style.cssText = "font-size:11px;color:#cfe9d6;";
        button.appendChild(caption);
    }
    // Green marks a documented H3 vocal verb. The pause is neither verb nor emotion -- and is our
    // own convention, not a documented one -- so it must not borrow the reliability signal.
    const accent = mark.tier === "verb"
        ? "background:rgba(74,222,128,0.10);border:2px solid #4ade80;"
        : "background:#2a2a2e;border:1px solid #3a3a40;";
    button.style.cssText =
        // 32px minimum: the old buttons were ~26px, below a comfortable pointer target.
        "min-height:32px;min-width:32px;display:inline-flex;align-items:center;gap:4px;" +
        "padding:2px 8px;border-radius:6px;color:#ddd;font-size:14px;line-height:1;cursor:pointer;" +
        accent;
    button.addEventListener("focus", () => {
        // ComfyUI resets the default outline, so focus would otherwise be invisible.
        button.style.outline = "2px solid #7ab8ff";
        button.style.outlineOffset = "1px";
    });
    button.addEventListener("blur", () => { button.style.outline = "none"; });
    button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        insert(node, mark.emoji);
    });
    // Without this the canvas swallows the press and starts dragging the node instead.
    button.addEventListener("pointerdown", (event) => event.stopPropagation());
    return button;
}

function separator() {
    const line = document.createElement("span");
    line.style.cssText = "width:1px;height:20px;background:#444;margin:0 2px;";
    return line;
}

function buildPaletteRoot(node) {
    const root = document.createElement("div");
    root.style.cssText = "position:relative;display:flex;flex-direction:column;gap:4px;padding:4px 2px 0;flex:0 0 auto;";

    const primary = document.createElement("div");
    primary.style.cssText = "display:flex;flex-wrap:wrap;gap:4px;align-items:center;";
    primary.setAttribute("role", "toolbar");
    primary.setAttribute("aria-label", "Vocal delivery");
    for (const mark of DELIVERY_EMOJI.filter((m) => m.tier !== "prose")) {
        primary.appendChild(makeButton(node, mark));
    }

    // Parented to document.body, not to the palette. The prompt widget's wrapper is
    // overflow:hidden and the palette already sits flush against its bottom edge, so anything
    // expanding inside it is clipped away -- which is what happened to this panel and to the
    // second button row before it. position:fixed against the viewport escapes that entirely.
    const tones = document.createElement("div");
    tones.style.cssText =
        "display:none;position:fixed;z-index:2000;flex-wrap:wrap;gap:4px;align-items:center;" +
        "max-width:340px;padding:6px;border-radius:8px;background:#1e1e22;" +
        "border:1px solid #3a3a40;box-shadow:0 6px 20px rgba(0,0,0,0.55);";
    document.body.appendChild(tones);
    tones.setAttribute("role", "toolbar");
    tones.setAttribute("aria-label", "Emotional tone");
    let previousGroup = null;
    for (const mark of DELIVERY_EMOJI.filter((m) => m.tier === "prose")) {
        if (previousGroup && mark.group !== previousGroup) tones.appendChild(separator());
        previousGroup = mark.group;
        tones.appendChild(makeButton(node, mark));
    }

    // Built by hand rather than through makeButton: that helper wires a click handler that inserts
    // its mark, and this button inserts nothing.
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.textContent = "+ tone";
    toggle.title = "Show the emotional tone marks";
    toggle.setAttribute("aria-expanded", "false");
    toggle.style.cssText =
        "min-height:32px;padding:2px 10px;border-radius:6px;cursor:pointer;font-size:12px;" +
        "background:#2a2a2e;border:1px dashed #55555c;color:#bbb;";
    toggle.addEventListener("focus", () => {
        toggle.style.outline = "2px solid #7ab8ff";
        toggle.style.outlineOffset = "1px";
    });
    toggle.addEventListener("blur", () => { toggle.style.outline = "none"; });
    toggle.addEventListener("pointerdown", (event) => event.stopPropagation());
    toggle.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        const open = tones.style.display === "none";
        if (open) {
            // Viewport coordinates, since the panel hangs off document.body. Flip above the
            // button when there is no room below.
            const anchor = toggle.getBoundingClientRect();
            tones.style.visibility = "hidden";
            tones.style.display = "flex";
            const height = tones.getBoundingClientRect().height;
            tones.style.left = `${Math.min(anchor.left, window.innerWidth - 356)}px`;
            const below = anchor.bottom + 4;
            tones.style.top = `${below + height > window.innerHeight ? anchor.top - height - 4 : below}px`;
            tones.style.visibility = "visible";
        }
        tones.style.display = open ? "flex" : "none";
        toggle.setAttribute("aria-expanded", String(open));
        toggle.textContent = open ? "− tone" : "+ tone";
        toggle.title = open ? "Hide the emotional tone marks" : "Show the emotional tone marks";
    });
    primary.appendChild(separator());
    primary.appendChild(toggle);

    const closeTones = () => {
        if (tones.style.display === "none") return;
        tones.style.display = "none";
        toggle.setAttribute("aria-expanded", "false");
        toggle.textContent = "+ tone";
    };
    // Picking a tone is the end of the interaction, so the panel gets out of the way by itself.
    tones.addEventListener("click", (event) => {
        if (event.target.closest("button")) closeTones();
    });
    // And a click anywhere else dismisses it, the way any floating panel is expected to behave.
    document.addEventListener("pointerdown", (event) => {
        if (!root.contains(event.target)) closeTones();
    });

    root.appendChild(primary);
    return root;
}

// Mounted INSIDE the prompt widget's own wrapper, below the textarea, rather than as a sibling
// widget. The frontend positions and sizes that wrapper every frame, so the palette inherits both
// for free. As a sibling it needed four separate repairs: a splice to sit next to the prompt on a
// 47-input node, a measured computeSize once the buttons wrapped onto two rows and overlapped the
// widgets below, a ResizeObserver because the row count changes with node width, and a grow-only
// guard after feeding computeSize() back into setSize() collapsed the node and discarded manual
// resizes. Living in the wrapper removes all four, and the observer leak with them.
// Idempotent: safe to call from any hook, and re-mounts if a frontend re-render evicts it.
function mountPalette(node) {
    const widget = node.widgets?.find((item) => item.name === PROMPT_WIDGET);
    const textarea = promptTextarea(node);
    if (!widget || !textarea) return false;

    const wrapper = [widget.element, widget.inputEl].find(
        (element) => element && element !== textarea && element.contains(textarea),
    ) ?? textarea.parentElement;
    if (!wrapper) return false;

    node.__minimaxDeliveryPalette ??= { root: buildPaletteRoot(node) };
    const root = node.__minimaxDeliveryPalette.root;
    if (root.parentElement === wrapper) return true;

    // Stack vertically and let the textarea absorb whatever height the buttons leave.
    wrapper.style.display = "flex";
    wrapper.style.flexDirection = "column";
    // The wrapper ships as overflow:hidden and the palette sits flush against its bottom edge, so
    // a button row that wrapped onto a second line was simply cut off. The textarea keeps its own
    // scrolling; this only stops the wrapper from clipping its children.
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
                const result = original?.apply(this, arguments);
                // The prompt widget's DOM is built lazily, so retry briefly until it exists.
                let attempts = 0;
                const attempt = () => {
                    if (!mountPalette(this) && ++attempts < 10) setTimeout(attempt, 100);
                };
                setTimeout(attempt, 0);
                return result;
            };
        };
        hook("onNodeCreated");
        hook("onConfigure");
    },
});
