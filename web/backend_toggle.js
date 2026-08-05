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

function refreshBackendWidgets(node) {
    const toggle = node.widgets?.find((widget) => widget.name === "use_remote_model");
    const useRemote = toggle?.value !== false;
    for (const name of REMOTE_WIDGETS) {
        setWidgetVisible(node.widgets?.find((widget) => widget.name === name), useRemote);
    }
    for (const name of LOCAL_WIDGETS) {
        setWidgetVisible(node.widgets?.find((widget) => widget.name === name), !useRemote);
    }
    requestAnimationFrame(() => {
        const computed = node.computeSize();
        const currentWidth = Array.isArray(node.size) ? Number(node.size[0]) : 0;
        node.setSize([Math.max(420, currentWidth, computed[0]), Math.max(260, computed[1] + 48)]);
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
    },
});
