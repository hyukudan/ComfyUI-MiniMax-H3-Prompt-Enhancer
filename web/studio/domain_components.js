export function element(tag, className = "", text = "") {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
}

export function textInput(value = "", { type = "text", placeholder = "" } = {}) {
    const control = document.createElement("input");
    control.type = type;
    control.value = value ?? "";
    if (placeholder) control.placeholder = placeholder;
    return control;
}

export function textArea(value = "", placeholder = "") {
    const control = document.createElement("textarea");
    control.value = value ?? "";
    if (placeholder) control.placeholder = placeholder;
    return control;
}

export function selectInput(value, choices, { ariaLabel = "" } = {}) {
    const control = document.createElement("select");
    for (const choice of choices) {
        const [token, label, disabled = false] = choice;
        const option = document.createElement("option");
        option.value = token;
        option.textContent = label;
        option.disabled = disabled;
        control.appendChild(option);
    }
    control.value = value ?? "";
    if (ariaLabel) control.setAttribute("aria-label", ariaLabel);
    return control;
}

export function field(label, control, hint = "") {
    const wrapper = element("label", "minimax-h3-studio-field");
    wrapper.appendChild(element("span", "", label));
    wrapper.appendChild(control);
    if (hint) wrapper.appendChild(element("small", "minimax-h3-field-hint", hint));
    return wrapper;
}

export function inspectorSection(title, summary = "", open = true) {
    const details = element("details", "minimax-h3-inspector-section");
    details.open = open;
    const heading = element("summary", "minimax-h3-inspector-heading");
    heading.append(element("span", "", title));
    if (summary) heading.append(element("small", "", summary));
    const body = element("div", "minimax-h3-inspector-body");
    details.append(heading, body);
    return { details, body };
}

export function actionButton(label, onClick, { danger = false, disabled = false } = {}) {
    const button = element("button", danger ? "minimax-h3-danger" : "", label);
    button.type = "button";
    button.disabled = disabled;
    button.addEventListener("click", onClick);
    return button;
}

export function emptyState(title, copy, action = null) {
    const root = element("div", "minimax-h3-empty-state");
    root.append(element("h3", "", title), element("p", "", copy));
    if (action) root.appendChild(action);
    return root;
}

export function createMasterDetail() {
    const grid = element("div", "minimax-h3-studio-grid minimax-h3-master-detail");
    const master = element("div", "minimax-h3-master-list");
    master.setAttribute("role", "listbox");
    const inspector = element("div", "minimax-h3-studio-editor minimax-h3-inspector");
    grid.append(master, inspector);
    return { grid, master, inspector };
}

export function masterRow(label, meta, selected, onClick) {
    const row = element("button", "minimax-h3-master-row");
    row.type = "button";
    row.setAttribute("role", "option");
    row.setAttribute("aria-selected", String(selected));
    row.append(element("span", "", label), element("small", "", meta));
    row.addEventListener("click", onClick);
    return row;
}

export function checkboxPicker(items, selectedIds, onChange, ariaLabel) {
    const root = element("div", "minimax-h3-picker-list");
    root.setAttribute("role", "group");
    root.setAttribute("aria-label", ariaLabel);
    const selected = new Set(selectedIds ?? []);
    for (const item of items) {
        const label = element("label", "minimax-h3-picker-option");
        const control = document.createElement("input");
        control.type = "checkbox";
        control.checked = selected.has(item.id);
        control.addEventListener("change", () => {
            if (control.checked) selected.add(item.id); else selected.delete(item.id);
            onChange([...selected]);
        });
        label.append(control, element("span", "", item.label ?? item.name ?? item.id));
        root.appendChild(label);
    }
    if (!items.length) root.appendChild(element("p", "minimax-h3-field-hint", "No compatible items are available yet."));
    return root;
}

export function tokenList(value, onChange, placeholder = "Add an item") {
    const root = element("div", "minimax-h3-token-editor");
    const values = Array.isArray(value) ? value : [];
    for (const [index, token] of values.entries()) {
        const row = element("div", "minimax-h3-token-row");
        row.append(element("span", "", token), actionButton("Remove", () => {
            const next = [...values]; next.splice(index, 1); onChange(next);
        }));
        root.appendChild(row);
    }
    const addRow = element("div", "minimax-h3-token-row");
    const input = textInput("", { placeholder });
    const add = actionButton("Add", () => {
        const token = input.value.trim();
        if (!token || values.includes(token)) return;
        onChange([...values, token]);
    });
    input.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        event.preventDefault(); add.click();
    });
    addRow.append(input, add); root.appendChild(addRow);
    return root;
}

export function bindCommit(control, update, commit, eventName = "change") {
    control.addEventListener(eventName, () => {
        update(control.type === "checkbox" ? control.checked : control.value);
        commit();
    });
    return control;
}

export function setOptional(target, key, value) {
    if (value === "" || value === undefined || value === null) delete target[key];
    else target[key] = value;
}
