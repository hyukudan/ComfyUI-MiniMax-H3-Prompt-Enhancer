import { app } from "/scripts/app.js";

const NODE_NAME = "MiniMaxH3PromptEnhancer";
const AUDIO_NODE_NAMES = new Set([
    NODE_NAME,
    "MiniMaxH3GGUFPromptEnhancer",
    "MiniMaxH3PromptGuideBuilder",
    "MiniMaxH3PromptValidator",
]);
const REMOTE_WIDGETS = ["endpoint", "model", "api_key", "allow_remote_endpoint"];
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
const MIN_NODE_WIDTH = 520;
const MIN_NODE_HEIGHT = 320;
const DISPLAY_LABELS = {
    enhance_description: "Enhance description",
    ambience_foley_policy: "Ambience & foley",
    background_score_policy: "Background score",
    instrumental_description: "Instrumental description",
    voice_performance: "Voice performance",
    use_remote_model: "Use remote model",
    allow_remote_endpoint: "Allow non-local endpoint",
};

function setWidgetVisible(widget, visible) {
    if (!widget) return;
    if (!widget.__minimaxOriginal) {
        widget.__minimaxOriginal = {
            type: widget.type,
            computeSize: widget.computeSize,
            inputDisplay: widget.inputEl?.style?.display ?? "",
        };
    }
    if (visible) {
        widget.type = widget.__minimaxOriginal.type;
        widget.computeSize = widget.__minimaxOriginal.computeSize;
        if (widget.inputEl?.style) widget.inputEl.style.display = widget.__minimaxOriginal.inputDisplay;
    } else {
        widget.type = "converted-widget";
        widget.computeSize = () => [0, -4];
        if (widget.inputEl?.style) widget.inputEl.style.display = "none";
    }
}

function normalizeDynamicCombo(node, name) {
    const widget = node.widgets?.find((candidate) => candidate.name === name);
    const values = widget?.options?.values;
    if (!widget || !Array.isArray(values) || values.length === 0) return;
    if (!values.includes(widget.value)) widget.value = values[0];
}

function visibleWidgetHeight(node) {
    const width = Math.max(MIN_NODE_WIDTH, Number(node.size?.[0]) || 0);
    let height = 88 + Math.max(0, (node.outputs?.length ?? 0) - 1) * 20;
    let renderedBottom = 0;
    for (const widget of node.widgets ?? []) {
        if (widget.type === "converted-widget") continue;
        const computed = widget.computeSize?.(width);
        const computedHeight = Array.isArray(computed) && Number.isFinite(computed[1])
            ? computed[1]
            : 0;
        const domHeight = Math.max(
            Number(widget.inputEl?.getBoundingClientRect?.().height) || 0,
            Number(widget.inputEl?.scrollHeight) || 0,
        );
        const widgetHeight = Math.max(24, computedHeight, domHeight);
        height += widgetHeight + 4;
        if (Number.isFinite(Number(widget.last_y))) {
            renderedBottom = Math.max(renderedBottom, Number(widget.last_y) + widgetHeight + 16);
        }
    }
    return Math.max(height, renderedBottom);
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

function normalizeMigratedRuntimeWidgets(node) {
    const context = node.widgets?.find((widget) => widget.name === "context_size");
    const startup = node.widgets?.find((widget) => widget.name === "startup_timeout");
    if (context && Number(context.value) < 4096) context.value = 16384;
    if (startup && Number(startup.value) < 10) startup.value = 180;
}

function applyLabels(node) {
    for (const [name, label] of Object.entries(DISPLAY_LABELS)) {
        const widget = node.widgets?.find((candidate) => candidate.name === name);
        if (widget) widget.label = label;
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
    const useRemote = toggle?.value !== false;
    for (const name of REMOTE_WIDGETS) {
        setWidgetVisible(node.widgets?.find((widget) => widget.name === name), useRemote);
    }
    for (const name of LOCAL_WIDGETS) {
        setWidgetVisible(node.widgets?.find((widget) => widget.name === name), !useRemote);
    }
    normalizeDynamicCombo(node, "local_model");
    normalizeDynamicCombo(node, "llama_server_path");
    applyLabels(node);
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
    applyLabels(node);
    wrapRefreshCallback(node, "background_score_policy", refreshInstrumentalWidget);
    refreshInstrumentalWidget(node);
}

app.registerExtension({
    name: "MiniMaxH3PromptEnhancer.BackendToggle",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_NAME) return;
        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalCreated?.apply(this, arguments);
            wrapRefreshCallback(this, "use_remote_model", refreshBackendWidgets);
            configureAudioNode(this);
            refreshBackendWidgets(this);
            return result;
        };
        const originalConfigured = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = originalConfigured?.apply(this, arguments);
            wrapRefreshCallback(this, "use_remote_model", refreshBackendWidgets);
            configureAudioNode(this);
            refreshBackendWidgets(this);
            return result;
        };
        const originalDrawForeground = nodeType.prototype.onDrawForeground;
        nodeType.prototype.onDrawForeground = function () {
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
