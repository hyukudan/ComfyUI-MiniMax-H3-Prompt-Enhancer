import { parseStructuredJson, structuredJsonIsEditable } from "./schema.js";

export function createWidgetStore(widget, options = {}) {
    let document = parseStructuredJson(widget?.value, options);
    const listeners = new Set();

    return {
        get document() {
            return document;
        },
        hydrate(value = widget?.value) {
            document = parseStructuredJson(value, options);
            for (const listener of listeners) listener(document);
            return document;
        },
        canEdit() {
            return structuredJsonIsEditable(document);
        },
        commit(raw, write) {
            if (!structuredJsonIsEditable(document)) return false;
            if (typeof raw !== "string") throw new TypeError("Structured JSON commits require a string.");
            const changed = write(raw);
            if (changed !== false) {
                document = parseStructuredJson(raw, options);
                document.dirty = true;
                for (const listener of listeners) listener(document);
            }
            return changed;
        },
        subscribe(listener) {
            listeners.add(listener);
            return () => listeners.delete(listener);
        },
    };
}

export function getWidgetStore(node, widgetName, options = {}) {
    if (!node.__minimaxStructuredWidgetStores) node.__minimaxStructuredWidgetStores = new Map();
    const widget = node.widgets?.find((candidate) => candidate.name === widgetName);
    if (!widget) return null;
    let store = node.__minimaxStructuredWidgetStores.get(widgetName);
    if (!store) {
        store = createWidgetStore(widget, options);
        node.__minimaxStructuredWidgetStores.set(widgetName, store);
    }
    return store;
}
