import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

const NODE_NAME = "MiniMaxH3PromptEnhancer";
const AUDIO_NODE_NAMES = new Set([
    NODE_NAME,
    "MiniMaxH3GGUFPromptEnhancer",
    "MiniMaxH3PromptGuideBuilder",
    "MiniMaxH3PromptValidator",
]);
const API_MODEL_REFRESH = "Refresh API model list";
const API_MODEL_PICKER = "Available API models";
const AUTOMATIC_MODEL = "(automatic selection)";
const REMOTE_WIDGETS = [
    "endpoint",
    "model",
    "api_key",
    "allow_remote_endpoint",
    API_MODEL_REFRESH,
    API_MODEL_PICKER,
];
const LOCAL_WIDGETS = [
    "local_model",
    "llama_server_path",
    "gpu_layers",
    "context_size",
    "threads",
    "startup_timeout",
    "keep_server_loaded",
];
const INSTRUMENTAL_WIDGET = "instrumental_description";
const MIN_NODE_WIDTH = 560;
const MIN_NODE_HEIGHT = 320;
const DISPLAY_LABELS = {
    basic_prompt: "Describe your video",
    duration_seconds: "Duration (seconds)",
    reference_context: "Reference notes (optional)",
    endpoint: "API endpoint",
    model: "API model ID (blank = auto)",
    local_model: "Local GGUF model",
    llama_server_path: "llama.cpp server",
    gpu_layers: "GPU layers (auto recommended)",
    context_size: "LLM context size",
    threads: "CPU threads (0 = auto)",
    startup_timeout: "Local model startup timeout",
    enhance_description: "Enhance description",
    ambience_foley_policy: "Scene sounds (ambience & foley)",
    background_score_policy: "Background score",
    instrumental_description: "Instrumental description",
    voice_performance: "Voice performance",
    aspect_ratio: "Aspect ratio",
    media_manifest: "Media metadata JSON (optional)",
    multishot_shot_count: "Multishot count",
    frame_count: "Exact frames (0 = use duration)",
    multishot_identity_lock: "Multishot identity lock",
    multishot_voice_lock: "Multishot voice lock",
    multishot_setting_lock: "Multishot setting lock",
    use_remote_model: "Use LM Studio / API model",
    allow_remote_endpoint: "Allow non-local endpoint",
    keep_server_loaded: "Keep local model loaded",
    show_advanced_controls: "Show advanced controls",
};
const DISPLAY_PLACEHOLDERS = {
    basic_prompt: "Describe the video you want: subject, action, setting, camera, dialogue and sound…",
    reference_context: "Example: Picture 1 supplies the character identity; Audio 1 supplies the Spanish voice…",
    instrumental_description: "Example: low strings, 90 BPM, sparse percussion, gradual crescendo…",
    media_manifest: '{"items":[{"type":"picture","role":"identity"}]}',
    multishot_identity_lock: "Identity, wardrobe and appearance that every chained prompt must preserve…",
    multishot_voice_lock: "Voice, language and delivery that every chained prompt must preserve…",
    multishot_setting_lock: "Location, lighting and continuity that every chained prompt must preserve…",
};
const MULTILINE_TITLES = {
    basic_prompt: "Video description",
    prompt: "H3 prompt to validate",
    source_prompt: "Original request",
    reference_context: "Reference notes (optional)",
    instrumental_description: "Instrumental direction (optional)",
    media_manifest: "Media metadata JSON (optional)",
    multishot_identity_lock: "Identity continuity (optional)",
    multishot_voice_lock: "Voice continuity (optional)",
    multishot_setting_lock: "Setting continuity (optional)",
};
const FIELD_STYLE_ID = "minimax-h3-field-styles";

function ensureFieldTitleStyles() {
    if (document.getElementById(FIELD_STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = FIELD_STYLE_ID;
    style.textContent = `
        .minimax-h3-field {
            display: flex;
            flex-direction: column;
            gap: 4px;
            width: 100%;
            height: 100%;
            min-height: 0;
            overflow: hidden;
            box-sizing: border-box;
        }
        .minimax-h3-field-title {
            flex: 0 0 auto;
            padding: 0 2px;
            overflow: hidden;
            color: var(--descrip-text, #aaa);
            font-size: 11px;
            font-weight: 600;
            line-height: 16px;
            text-overflow: ellipsis;
            white-space: nowrap;
            user-select: none;
        }
        .minimax-h3-field > textarea {
            flex: 1 1 auto;
            width: 100%;
            height: auto;
            min-height: 0;
            box-sizing: border-box;
        }
        .widget-item .minimax-h3-field-title {
            display: none;
        }
    `;
    document.head.appendChild(style);
}

function widgetTextElement(widget) {
    if (widget?.__minimaxTextInput instanceof HTMLTextAreaElement) return widget.__minimaxTextInput;
    if (widget?.element instanceof HTMLTextAreaElement) return widget.element;
    if (widget?.inputEl instanceof HTMLTextAreaElement) return widget.inputEl;
    return null;
}

function addMultilineTitle(widget, title) {
    const textarea = widgetTextElement(widget);
    if (!textarea) return;
    ensureFieldTitleStyles();
    if (widget.__minimaxFieldWrapper) {
        widget.__minimaxFieldTitle.textContent = title;
        return;
    }
    const wrapper = document.createElement("div");
    wrapper.className = "minimax-h3-field";
    const heading = document.createElement("div");
    heading.className = "minimax-h3-field-title";
    heading.textContent = title;
    const headingId = `minimax-h3-field-${widget.name}-${Math.random().toString(36).slice(2)}`;
    heading.id = headingId;
    textarea.setAttribute("aria-labelledby", headingId);
    const parent = textarea.parentNode;
    if (parent) parent.replaceChild(wrapper, textarea);
    wrapper.append(heading, textarea);
    widget.__minimaxTextInput = textarea;
    widget.__minimaxFieldTitle = heading;
    widget.__minimaxFieldWrapper = wrapper;
    // ComfyUI positions/mounts widget.element. The value callbacks still close
    // over the original textarea, so wrapping changes presentation only.
    widget.element = wrapper;
}

function applyMultilineTitles(node) {
    for (const [name, title] of Object.entries(MULTILINE_TITLES)) {
        const widget = node.widgets?.find((candidate) => candidate.name === name);
        if (widget) addMultilineTitle(widget, title);
    }
}

function setWidgetVisible(widget, visible) {
    if (!widget) return;
    if (!widget.__minimaxOriginal) {
        widget.__minimaxOriginal = {
            type: widget.type,
            computeSize: widget.computeSize,
            hidden: Boolean(widget.hidden),
            optionsHidden: Boolean(widget.options?.hidden),
            inputDisplay: widget.inputEl?.style?.display ?? "",
            elementDisplay: widget.element?.style?.display ?? "",
        };
    }
    if (!widget.options) widget.options = {};
    if (visible) {
        widget.hidden = false;
        widget.options.hidden = false;
        widget.type = widget.__minimaxOriginal.type;
        widget.computeSize = widget.__minimaxOriginal.computeSize;
        if (widget.inputEl?.style) widget.inputEl.style.display = widget.__minimaxOriginal.inputDisplay;
        if (widget.element?.style) widget.element.style.display = widget.__minimaxOriginal.elementDisplay;
    } else {
        // Canvas nodes read widget.hidden; Vue nodes read widget.options.hidden.
        // Set both so remote/local controls are genuinely mutually exclusive.
        widget.hidden = true;
        widget.options.hidden = true;
        if (!window.LiteGraph?.vueNodesMode) {
            widget.type = "converted-widget";
            widget.computeSize = () => [0, -4];
        }
        if (widget.inputEl?.style) widget.inputEl.style.display = "none";
        if (widget.element?.style) widget.element.style.display = "none";
    }
}

function normalizeDynamicCombo(node, name) {
    const widget = node.widgets?.find((candidate) => candidate.name === name);
    const values = widget?.options?.values;
    if (!widget || !Array.isArray(values) || values.length === 0) return;
    if (!values.includes(widget.value)) widget.value = values[0];
}

function notifyModelDiscoveryError(message) {
    const toast = app.extensionManager?.toast;
    if (toast?.add) {
        toast.add({ severity: "error", summary: "Model discovery failed", detail: message, life: 6000 });
    } else {
        window.alert(`Model discovery failed: ${message}`);
    }
}

function addRemoteModelDiscovery(node) {
    if (node.__minimaxModelDiscoveryAdded) return;
    node.__minimaxModelDiscoveryAdded = true;
    const modelWidget = node.widgets?.find((widget) => widget.name === "model");
    if (!modelWidget || !node.addWidget) return;

    const picker = node.addWidget("combo", API_MODEL_PICKER, AUTOMATIC_MODEL, (value) => {
        modelWidget.value = value === AUTOMATIC_MODEL ? "" : value;
        modelWidget.callback?.(modelWidget.value);
        node.graph?.setDirtyCanvas?.(true, true);
    }, { values: [AUTOMATIC_MODEL], serialize: false });
    picker.serialize = false;
    picker.serializeValue = () => undefined;
    picker.label = "Choose discovered model";

    const refresh = node.addWidget("button", API_MODEL_REFRESH, null, async () => {
        const endpoint = node.widgets?.find((widget) => widget.name === "endpoint")?.value ?? "";
        const apiKey = node.widgets?.find((widget) => widget.name === "api_key")?.value ?? "";
        const allowRemote = node.widgets?.find((widget) => widget.name === "allow_remote_endpoint")?.value === true;
        const previousLabel = refresh.label;
        refresh.label = "Loading models…";
        node.graph?.setDirtyCanvas?.(true, true);
        try {
            const response = await api.fetchApi("/minimax_h3_prompt_enhancer/models", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    endpoint,
                    api_key: apiKey,
                    allow_remote_endpoint: allowRemote,
                }),
            });
            const rawResponse = await response.text();
            let payload;
            try {
                payload = JSON.parse(rawResponse);
            } catch {
                if ([404, 405].includes(response.status)) {
                    throw new Error("The model-list backend is not loaded. Restart ComfyUI, then refresh the page.");
                }
                throw new Error(`The server returned a non-JSON response (HTTP ${response.status}).`);
            }
            if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
            const discovered = Array.isArray(payload.models) ? payload.models.filter(Boolean) : [];
            const current = String(modelWidget.value ?? "").trim();
            const values = [AUTOMATIC_MODEL, ...discovered];
            if (current && !values.includes(current)) values.push(current);
            picker.options.values = values;
            picker.value = current || AUTOMATIC_MODEL;
            if (!discovered.length) notifyModelDiscoveryError("The endpoint returned no chat-capable models.");
        } catch (error) {
            notifyModelDiscoveryError(error?.message || String(error));
        } finally {
            refresh.label = previousLabel;
            // Model discovery changes choices, not layout. Resizing here made
            // multiline DOM widgets feed their stretched height back into the
            // node on every refresh, causing unbounded vertical growth.
            node.graph?.setDirtyCanvas?.(true, true);
            node.setDirtyCanvas?.(true, true);
        }
    }, { serialize: false });
    refresh.serialize = false;
    refresh.serializeValue = () => undefined;
    refresh.label = API_MODEL_REFRESH;
}

function repairLegacyModelDiscoveryShift(node, info) {
    const values = info?.widgets_values;
    if (!Array.isArray(values)) return false;
    const persistentWidgets = (node.widgets ?? []).filter((widget) => widget.serialize !== false);
    const extraCount = values.length - persistentWidgets.length;
    const modelIndex = persistentWidgets.findIndex((widget) => widget.name === "model");
    if (extraCount !== 2 || modelIndex < 0) return false;
    const legacyButtonValue = values[modelIndex + 1];
    const legacyPickerValue = values[modelIndex + 2];
    if (legacyButtonValue != null || typeof legacyPickerValue !== "string") return false;
    const repairedValues = [
        ...values.slice(0, modelIndex + 1),
        ...values.slice(modelIndex + 3),
    ];
    persistentWidgets.forEach((widget, index) => {
        if (index < repairedValues.length) widget.value = repairedValues[index];
    });
    info.widgets_values = repairedValues;
    return true;
}

function visibleWidgetHeight(node) {
    const width = Math.max(MIN_NODE_WIDTH, Number(node.size?.[0]) || 0);
    let height = 88 + Math.max(0, (node.outputs?.length ?? 0) - 1) * 20;
    for (const widget of node.widgets ?? []) {
        if (widget.hidden || widget.options?.hidden || widget.type === "converted-widget") continue;
        const computed = widget.computeSize?.(width);
        const computedHeight = Array.isArray(computed) && Number.isFinite(computed[1])
            ? computed[1]
            : 0;
        // Never use DOM client/scroll height here: multiline controls stretch
        // with the node and would create a positive resize feedback loop.
        const widgetHeight = Math.max(24, computedHeight);
        height += widgetHeight + 4;
    }
    return height;
}

function fitNodeToVisibleWidgets(node) {
    requestAnimationFrame(() => requestAnimationFrame(() => {
        const computed = node.computeSize?.() ?? [MIN_NODE_WIDTH, MIN_NODE_HEIGHT];
        const width = Math.max(MIN_NODE_WIDTH, Number(node.size?.[0]) || 0, Number(computed[0]) || 0);
        const requiredHeight = Math.max(
            MIN_NODE_HEIGHT,
            Number(computed[1]) || 0,
            visibleWidgetHeight(node),
        );
        node.setSize([width, requiredHeight]);
        node.graph?.setDirtyCanvas?.(true, true);
        node.setDirtyCanvas?.(true, true);
    }));
}

function normalizeMigratedRuntimeWidgets(node, repairDisplacedDescription = false) {
    const context = node.widgets?.find((widget) => widget.name === "context_size");
    const startup = node.widgets?.find((widget) => widget.name === "startup_timeout");
    const instrumental = node.widgets?.find((widget) => widget.name === INSTRUMENTAL_WIDGET);
    const displacedContext = String(instrumental?.value ?? "").trim();
    if (repairDisplacedDescription && /^\d{4,6}$/.test(displacedContext) && Number(displacedContext) >= 4096) {
        if (context) context.value = Number(displacedContext);
        instrumental.value = "";
    }
    if (context && Number(context.value) < 4096) context.value = 16384;
    if (startup && Number(startup.value) < 10) startup.value = 180;
    const voice = node.widgets?.find((widget) => widget.name === "voice_performance");
    if (voice && !["audible", "silent_mouth_acting_experimental", "none"].includes(voice.value)) {
        voice.value = "audible";
    }
    widgetTextElement(instrumental)?.setAttribute("aria-label", "Instrumental score description");
    const reference = node.widgets?.find((widget) => widget.name === "reference_context");
    widgetTextElement(reference)?.setAttribute("aria-label", "Optional reference notes");
    const manifest = node.widgets?.find((widget) => widget.name === "media_manifest");
    widgetTextElement(manifest)?.setAttribute("aria-label", "Advanced media metadata JSON");
}

function enforceConditionalVisibility(node) {
    const backendValue = node.widgets?.find((widget) => widget.name === "use_remote_model")?.value;
    const useRemote = backendValue === undefined || backendValue === true || backendValue === 1
        || String(backendValue).toLowerCase() === "true";
    for (const name of REMOTE_WIDGETS) setWidgetVisible(node.widgets?.find((widget) => widget.name === name), useRemote);
    for (const name of LOCAL_WIDGETS) setWidgetVisible(node.widgets?.find((widget) => widget.name === name), !useRemote);
    const score = node.widgets?.find((widget) => widget.name === "background_score_policy");
    setWidgetVisible(node.widgets?.find((widget) => widget.name === INSTRUMENTAL_WIDGET), score?.value === "add_instrumental");
    const modeWidget = node.widgets?.find((widget) => widget.name === "mode");
    if (modeWidget) {
        const multishot = modeWidget.value === "chained_multishot";
        for (const name of ["multishot_shot_count", "multishot_identity_lock", "multishot_voice_lock", "multishot_setting_lock"]) {
            setWidgetVisible(node.widgets?.find((widget) => widget.name === name), multishot);
        }
        const advanced = node.widgets?.find((widget) => widget.name === "show_advanced_controls")?.value === true;
        const reference = node.widgets?.find((widget) => widget.name === "reference_context");
        const manifest = node.widgets?.find((widget) => widget.name === "media_manifest");
        const frames = node.widgets?.find((widget) => widget.name === "frame_count");
        const hasReferenceNotes = String(reference?.value ?? "").trim().length > 0;
        const hasManifest = String(manifest?.value ?? "").trim().length > 0;
        setWidgetVisible(reference, modeWidget.value === "ref2va" || advanced || hasReferenceNotes);
        setWidgetVisible(manifest, advanced || hasManifest);
        setWidgetVisible(frames, advanced || Number(frames?.value ?? 0) > 0);
    }
}

function applyLabels(node) {
    for (const [name, label] of Object.entries(DISPLAY_LABELS)) {
        const widget = node.widgets?.find((candidate) => candidate.name === name);
        if (widget) widget.label = label;
    }
    for (const [name, placeholder] of Object.entries(DISPLAY_PLACEHOLDERS)) {
        const widget = node.widgets?.find((candidate) => candidate.name === name);
        if (!widget) continue;
        if (!widget.options) widget.options = {};
        widget.options.placeholder = placeholder;
        const input = widgetTextElement(widget);
        if (input) input.placeholder = placeholder;
    }
}

function refreshInstrumentalWidget(node) {
    const score = node.widgets?.find((widget) => widget.name === "background_score_policy");
    const description = node.widgets?.find((widget) => widget.name === INSTRUMENTAL_WIDGET);
    setWidgetVisible(description, score?.value === "add_instrumental");
    fitNodeToVisibleWidgets(node);
}

function refreshBackendWidgets(node) {
    normalizeMigratedRuntimeWidgets(node);
    const toggle = node.widgets?.find((widget) => widget.name === "use_remote_model");
    const useRemote = toggle?.value === undefined || toggle?.value === true || toggle?.value === 1
        || String(toggle?.value).toLowerCase() === "true";
    for (const name of REMOTE_WIDGETS) {
        setWidgetVisible(node.widgets?.find((widget) => widget.name === name), useRemote);
    }
    for (const name of LOCAL_WIDGETS) {
        setWidgetVisible(node.widgets?.find((widget) => widget.name === name), !useRemote);
    }
    normalizeDynamicCombo(node, "local_model");
    normalizeDynamicCombo(node, "llama_server_path");
    applyLabels(node);
    enforceConditionalVisibility(node);
    refreshInstrumentalWidget(node);
}

function wrapRefreshCallback(node, widgetName, refresh) {
    const widget = node.widgets?.find((candidate) => candidate.name === widgetName);
    if (!widget || widget.__minimaxRefreshWrapped) return;
    widget.__minimaxRefreshWrapped = true;
    const originalCallback = widget.callback;
    widget.callback = function (...args) {
        const callbackResult = originalCallback?.apply(this, args);
        refresh(node);
        return callbackResult;
    };
}

function configureAudioNode(node) {
    applyMultilineTitles(node);
    applyLabels(node);
    normalizeMigratedRuntimeWidgets(node);
    wrapRefreshCallback(node, "background_score_policy", refreshInstrumentalWidget);
    wrapRefreshCallback(node, "mode", (target) => {
        enforceConditionalVisibility(target);
        fitNodeToVisibleWidgets(target);
    });
    wrapRefreshCallback(node, "show_advanced_controls", (target) => {
        enforceConditionalVisibility(target);
        fitNodeToVisibleWidgets(target);
    });
    refreshInstrumentalWidget(node);
    enforceConditionalVisibility(node);
}

app.registerExtension({
    name: "MiniMaxH3PromptEnhancer.BackendToggle",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_NAME) return;
        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalCreated?.apply(this, arguments);
            this.__minimaxWidgetMigrationComplete = false;
            addRemoteModelDiscovery(this);
            wrapRefreshCallback(this, "use_remote_model", refreshBackendWidgets);
            configureAudioNode(this);
            refreshBackendWidgets(this);
            return result;
        };
        const originalConfigured = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = originalConfigured?.apply(this, arguments);
            this.__minimaxWidgetMigrationComplete = false;
            addRemoteModelDiscovery(this);
            repairLegacyModelDiscoveryShift(this, arguments[0]);
            wrapRefreshCallback(this, "use_remote_model", refreshBackendWidgets);
            configureAudioNode(this);
            refreshBackendWidgets(this);
            return result;
        };
        const originalDrawForeground = nodeType.prototype.onDrawForeground;
        nodeType.prototype.onDrawForeground = function () {
            if (!this.__minimaxWidgetMigrationComplete) {
                normalizeMigratedRuntimeWidgets(this, true);
                this.__minimaxWidgetMigrationComplete = true;
            }
            enforceConditionalVisibility(this);
            const result = originalDrawForeground?.apply(this, arguments);
            const requiredHeight = Math.max(MIN_NODE_HEIGHT, visibleWidgetHeight(this));
            if (Array.isArray(this.size) && this.size[1] + 2 < requiredHeight) {
                this.setSize([Math.max(MIN_NODE_WIDTH, this.size[0]), requiredHeight]);
            }
            return result;
        };
    },
});

app.registerExtension({
    name: "MiniMaxH3PromptEnhancer.AudioPolicyLabels",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (!AUDIO_NODE_NAMES.has(nodeData.name) || nodeData.name === NODE_NAME) return;
        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalCreated?.apply(this, arguments);
            configureAudioNode(this);
            return result;
        };
        const originalConfigured = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = originalConfigured?.apply(this, arguments);
            configureAudioNode(this);
            return result;
        };
    },
});
