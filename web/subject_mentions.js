// SPDX-License-Identifier: GPL-3.0-only
// Visual, cursor-aware Subject mentions below the main prompt.
import { app } from "/scripts/app.js";
import { sourcePreviewUrl } from "./studio/reference_sources.js";
import { parseStudioProjectV3, STUDIO_PROJECT_WIDGET } from "./studio/studio_project_v3.js";
import { insertSubjectMention } from "./subject_mentions_model.js";

const TARGET_NODES = new Set(["MiniMaxH3PromptEnhancer", "MiniMaxH3GGUFPromptEnhancer"]);

function installStyles() {
    if (document.getElementById("minimax-h3-subject-mention-styles")) return;
    const style = document.createElement("style"); style.id = "minimax-h3-subject-mention-styles";
    style.textContent = `
        .minimax-h3-subject-mentions { position: relative; display: none; flex: 0 0 auto; align-items: center; gap: 6px; min-width: 0; padding: 6px 0 2px; color: #c8ced8; font: 11px/1.25 Inter, system-ui, sans-serif; }
        .minimax-h3-subject-mentions[data-ready="true"] { display: flex; }
        .minimax-h3-subject-mentions > strong { flex: 0 0 auto; color: #9aa4b3; font-size: 10px; letter-spacing: .06em; text-transform: uppercase; }
        .minimax-h3-subject-mention-list { display: flex; min-width: 0; flex-wrap: wrap; gap: 5px; }
        .minimax-h3-subject-mention { position: relative; display: inline-flex; align-items: center; gap: 5px; min-height: 25px; border: 1px solid #4a5668; border-radius: 999px; padding: 3px 8px 3px 4px; background: #242a33; color: #edf2f8; cursor: pointer; }
        .minimax-h3-subject-mention:hover, .minimax-h3-subject-mention:focus-visible { border-color: #62a9e9; background: #293747; outline: none; }
        .minimax-h3-subject-mention-avatar { display: grid; width: 18px; height: 18px; place-items: center; overflow: hidden; border-radius: 50%; background: #14181e; color: #8e9aab; font-size: 9px; }
        .minimax-h3-subject-mention-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .minimax-h3-subject-mention code { color: #8ec8ff; font-size: 9px; }
        .minimax-h3-subject-popover { position: absolute; z-index: 1200; left: 0; bottom: calc(100% + 7px); display: none; width: 250px; grid-template-columns: 68px minmax(0,1fr); gap: 9px; border: 1px solid #536177; border-radius: 9px; padding: 9px; background: #171b22; box-shadow: 0 12px 30px #000a; color: #eef3f9; pointer-events: none; text-align: left; }
        .minimax-h3-subject-mention:hover .minimax-h3-subject-popover, .minimax-h3-subject-mention:focus-visible .minimax-h3-subject-popover { display: grid; }
        .minimax-h3-subject-popover-preview { display: grid; width: 68px; height: 68px; place-items: center; overflow: hidden; border-radius: 7px; background: #0e1116; color: #788598; }
        .minimax-h3-subject-popover-preview img { width: 100%; height: 100%; object-fit: cover; }
        .minimax-h3-subject-popover-copy { display: grid; min-width: 0; align-content: start; gap: 3px; }
        .minimax-h3-subject-popover-copy b { font-size: 12px; }
        .minimax-h3-subject-popover-copy span { color: #aab4c2; font-size: 10px; overflow-wrap: anywhere; }
    `;
    document.head.appendChild(style);
}

function promptWidget(node) { return node.widgets?.find((item) => item.name === "basic_prompt") ?? null; }
function promptTextarea(node) {
    const widget = promptWidget(node);
    for (const candidate of [widget?.element, widget?.inputEl]) {
        if (candidate?.tagName === "TEXTAREA") return candidate;
        const nested = candidate?.querySelector?.("textarea"); if (nested) return nested;
    }
    return null;
}

function studioProject(node) {
    const raw = node.widgets?.find((item) => item.name === STUDIO_PROJECT_WIDGET)?.value ?? "";
    const parsed = parseStudioProjectV3(raw);
    return parsed.kind === "v3" ? parsed.value : null;
}

function commitMention(node, mention) {
    const widget = promptWidget(node); const textarea = promptTextarea(node);
    if (!widget || !textarea) return;
    const result = insertSubjectMention(textarea.value, textarea.selectionStart, textarea.selectionEnd, mention);
    textarea.value = result.value; widget.value = result.value;
    textarea.setSelectionRange(result.selectionStart, result.selectionEnd); textarea.focus();
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    node.setDirtyCanvas?.(true, true); node.graph?.setDirtyCanvas?.(true, true);
}

function subjectButton(node, subject, files) {
    const mention = `<Subject ${subject.h3Index}>`;
    const button = document.createElement("button"); button.type = "button"; button.className = "minimax-h3-subject-mention";
    button.setAttribute("aria-label", `Insert ${subject.name || mention}, ${mention}`);
    const identity = files.get(subject.identityFileIds?.[0]);
    const voice = files.get(subject.defaultVoiceFileId);
    const avatar = document.createElement("span"); avatar.className = "minimax-h3-subject-mention-avatar";
    const imageUrl = sourcePreviewUrl(identity?.source);
    if (imageUrl) { const image = document.createElement("img"); image.src = imageUrl; image.alt = ""; avatar.appendChild(image); }
    else avatar.textContent = String(subject.name || "S").slice(0, 1).toUpperCase();
    const name = document.createElement("span"); name.textContent = subject.name || mention;
    const alias = document.createElement("code"); alias.textContent = mention;
    const popover = document.createElement("span"); popover.className = "minimax-h3-subject-popover"; popover.setAttribute("role", "tooltip");
    const preview = document.createElement("span"); preview.className = "minimax-h3-subject-popover-preview";
    if (imageUrl) { const image = document.createElement("img"); image.src = imageUrl; image.alt = subject.name || mention; preview.appendChild(image); }
    else preview.textContent = "No image";
    const copy = document.createElement("span"); copy.className = "minimax-h3-subject-popover-copy";
    const heading = document.createElement("b"); heading.textContent = `${subject.name || mention} · ${mention}`;
    const description = document.createElement("span"); description.textContent = subject.description || "No identity description yet.";
    const voiceCopy = document.createElement("span"); voiceCopy.textContent = voice ? `Voice: ${voice.name || voice.id}` : "No default voice";
    copy.append(heading, description, voiceCopy); popover.append(preview, copy);
    button.append(avatar, name, alias, popover);
    button.addEventListener("pointerdown", (event) => event.stopPropagation());
    button.addEventListener("click", () => commitMention(node, mention));
    return button;
}

function build(node) {
    installStyles();
    const root = document.createElement("div"); root.className = "minimax-h3-subject-mentions";
    const title = document.createElement("strong"); title.textContent = "Insert subject";
    const list = document.createElement("div"); list.className = "minimax-h3-subject-mention-list";
    root.append(title, list);
    const state = { root, refresh() {
        const project = studioProject(node); const subjects = project?.subjects ?? [];
        const files = new Map((project?.files ?? []).map((file) => [file.id, file]));
        list.replaceChildren(...subjects.map((subject) => subjectButton(node, subject, files)));
        root.dataset.ready = String(subjects.length > 0);
    }, destroy() { root.remove(); } };
    state.refresh(); return state;
}

function mount(node) {
    const widget = promptWidget(node); const textarea = promptTextarea(node);
    if (!widget || !textarea) return false;
    const wrapper = [widget.element, widget.inputEl].find((item) => item && item !== textarea && item.contains(textarea)) ?? textarea.parentElement;
    if (!wrapper) return false;
    node.__minimaxSubjectMentions ??= build(node);
    const root = node.__minimaxSubjectMentions.root;
    if (root.parentElement !== wrapper) wrapper.insertBefore(root, node.__minimaxDeliveryPalette?.root ?? null);
    node.__minimaxSubjectMentions.refresh(); return true;
}

app.registerExtension({
    name: "MiniMaxH3PromptEnhancer.SubjectMentions",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (!TARGET_NODES.has(nodeData.name)) return;
        for (const hookName of ["onNodeCreated", "onConfigure"]) {
            const original = nodeType.prototype[hookName];
            nodeType.prototype[hookName] = function () {
                const result = original?.apply(this, arguments); let attempts = 0;
                const attempt = () => { if (!mount(this) && ++attempts < 10) setTimeout(attempt, 100); };
                setTimeout(attempt, 0); return result;
            };
        }
        const removed = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function () {
            this.__minimaxSubjectMentions?.destroy(); this.__minimaxSubjectMentions = null;
            return removed?.apply(this, arguments);
        };
    },
});
