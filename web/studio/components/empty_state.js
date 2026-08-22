export function createEmptyState({ title, description, actionLabel, onAction, secondaryLabel, onSecondary } = {}) {
    const empty = document.createElement("section");
    empty.className = "minimax-h3-empty-state";
    empty.setAttribute("aria-labelledby", `minimax-h3-empty-${Math.random().toString(36).slice(2)}`);
    const heading = document.createElement("h3");
    heading.id = empty.getAttribute("aria-labelledby");
    heading.textContent = title ?? "Nothing here yet";
    const copy = document.createElement("p");
    copy.textContent = description ?? "Add the first item when you are ready.";
    const actions = document.createElement("div");
    actions.className = "minimax-h3-empty-actions";
    if (actionLabel && onAction) {
        const action = document.createElement("button");
        action.type = "button";
        action.className = "minimax-h3-button minimax-h3-button-primary";
        action.textContent = actionLabel;
        action.addEventListener("click", onAction);
        actions.appendChild(action);
    }
    if (secondaryLabel && onSecondary) {
        const secondary = document.createElement("button");
        secondary.type = "button";
        secondary.className = "minimax-h3-button minimax-h3-button-secondary";
        secondary.textContent = secondaryLabel;
        secondary.addEventListener("click", onSecondary);
        actions.appendChild(secondary);
    }
    empty.append(heading, copy, actions);
    return empty;
}

