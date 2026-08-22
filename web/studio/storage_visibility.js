// Canonical JSON widgets remain ordinary persistent ComfyUI inputs. Prompt
// Studio owns their presentation, so hiding them must never convert the widget,
// disable serialization or replace serializeValue (all of which can shift the
// API/workflow contract).
export function hideCanonicalJsonWidget(widget) {
    if (!widget) return false;
    if (!widget.__minimaxJsonStorageHidden) {
        widget.__minimaxJsonStorageHidden = true;
        widget.__minimaxJsonStorageComputeSize = widget.computeSize;
    }
    if (!widget.options) widget.options = {};
    widget.hidden = true;
    widget.options.hidden = true;
    widget.computeSize = () => [0, -4];
    if (widget.inputEl?.style) widget.inputEl.style.display = "none";
    if (widget.element?.style) widget.element.style.display = "none";
    return true;
}
