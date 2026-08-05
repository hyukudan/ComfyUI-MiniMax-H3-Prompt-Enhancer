import { app } from "/scripts/app.js";

const NODE_NAME = "MiniMaxH3PromptEnhancer";
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
const DISPLAY_LABELS = {
    enhance_description: "Enhance description",
    ambience_foley_policy: "Ambience & foley",
    background_score_policy: "Background score",
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
        };
    }
    if (visible) {
        widget.type = widget.__minimaxOriginal.type;
        widget.computeSize = widget.__minimaxOriginal.computeSize;
    } else {
        widget.type = "converted-widget";
        widget.computeSize = () => [0, -4];
    }
}

function normalizeDynamicCombo(node, name) {
    const widget = node.widgets?.find((candidate) => candidate.name === name);
    const values = widget?.options?.values;
    if (!widget || !Array.isArray(values) || values.length === 0) return;
    if (!values.includes(widget.value)) widget.value = values[0];
}

function visibleWidgetHeight(node) {
    let height = 92;
    for (const widget of node.widgets ?? []) {
        if (widget.type === "converted-widget") continue;
        const computed = widget.computeSize?.(node.size?.[0] ?? 460);
        height += Array.isArray(computed) && Number.isFinite(computed[1])
            ? Math.max(24, computed[1])
            : 28;
    }
    return height;
}

function refreshBackendWidgets(node) {
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
    for (const [name, label] of Object.entries(DISPLAY_LABELS)) {
        const widget = node.widgets?.find((candidate) => candidate.name === name);
        if (widget) widget.label = label;
    }
    requestAnimationFrame(() => {
        const computed = node.computeSize();
        const currentWidth = Array.isArray(node.size) ? Number(node.size[0]) : 0;
        const requiredHeight = Math.max(computed[1] + 72, visibleWidgetHeight(node));
        node.setSize([Math.max(460, currentWidth, computed[0]), Math.max(320, requiredHeight)]);
        node.onResize?.(node.size);
        node.setDirtyCanvas(true, true);
    });
}

app.registerExtension({
    name: "MiniMaxH3PromptEnhancer.BackendToggle",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_NAME) return;
        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalCreated?.apply(this, arguments);
            const toggle = this.widgets?.find((widget) => widget.name === "use_remote_model");
            if (toggle) {
                const originalCallback = toggle.callback;
                toggle.callback = (...args) => {
                    const callbackResult = originalCallback?.apply(toggle, args);
                    refreshBackendWidgets(this);
                    return callbackResult;
                };
            }
            refreshBackendWidgets(this);
            return result;
        };
        const originalConfigured = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = originalConfigured?.apply(this, arguments);
            refreshBackendWidgets(this);
            return result;
        };
        const originalDrawForeground = nodeType.prototype.onDrawForeground;
        nodeType.prototype.onDrawForeground = function () {
            const result = originalDrawForeground?.apply(this, arguments);
            const requiredHeight = visibleWidgetHeight(this);
            if (Array.isArray(this.size) && this.size[1] + 2 < requiredHeight) {
                this.setSize([Math.max(460, this.size[0]), requiredHeight]);
            }
            return result;
        };
    },
});

app.registerExtension({
    name: "MiniMaxH3PromptEnhancer.AudioPolicyLabels",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (!["MiniMaxH3GGUFPromptEnhancer", "MiniMaxH3PromptGuideBuilder", "MiniMaxH3PromptValidator"].includes(nodeData.name)) return;
        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalCreated?.apply(this, arguments);
            for (const [name, label] of Object.entries(DISPLAY_LABELS)) {
                const widget = this.widgets?.find((candidate) => candidate.name === name);
                if (widget) widget.label = label;
            }
            requestAnimationFrame(() => {
                const computed = this.computeSize();
                this.setSize([Math.max(460, this.size?.[0] ?? 0, computed[0]), Math.max(320, computed[1] + 72)]);
                this.setDirtyCanvas(true, true);
            });
            return result;
        };
    },
});
