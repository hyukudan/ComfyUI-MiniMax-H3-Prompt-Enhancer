const SEVERITY_ORDER = ["error", "warning", "advice", "info"];
const SEVERITY_LABELS = { error: "Errors", warning: "Warnings", advice: "Tips", info: "Information" };

export function groupDiagnostics(diagnostics) {
    const groups = new Map();
    for (const diagnostic of diagnostics ?? []) {
        const key = diagnostic.code ?? "unknown";
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(diagnostic);
    }
    return [...groups.entries()].map(([code, items]) => ({ code, items }));
}

export function groupDiagnosticsBySeverity(diagnostics) {
    const groups = new Map(SEVERITY_ORDER.map((severity) => [severity, []]));
    for (const diagnostic of diagnostics ?? []) {
        const severity = groups.has(diagnostic.severity) ? diagnostic.severity : "info";
        groups.get(severity).push(diagnostic);
    }
    return SEVERITY_ORDER.map((severity) => ({ severity, items: groups.get(severity) })).filter((group) => group.items.length);
}

export function diagnosticLocationLabel(location = {}) {
    const parts = [];
    if (location.generationId) parts.push(location.generationId);
    if (location.shotId) parts.push(`Shot ${location.shotId}`);
    else if (Number.isInteger(location.shotIndex)) parts.push(`Shot ${location.shotIndex + 1}`);
    if (location.section) parts.push(location.section);
    if (location.field) parts.push(location.field);
    return parts.join(" · ") || "Project configuration";
}

export function reviewReportState(report) {
    if (report?.diagnostics?.length) return "findings";
    if (report?.stale) return "stale-clean";
    return report && (report.schemaVersion !== undefined || report.summary !== undefined)
        ? "clean"
        : "not-run";
}

function button(label, action) {
    const control = document.createElement("button");
    control.type = "button";
    control.textContent = label;
    control.addEventListener("click", action);
    return control;
}

function diagnosticSection(diagnostic) {
    if (diagnostic.location?.shotId || Number.isInteger(diagnostic.location?.shotIndex)) return "shots";
    const locatedSection = String(diagnostic.location?.section ?? "").toLowerCase();
    if (locatedSection.includes("subject") || locatedSection.includes("appearance")) return "subjects";
    if (locatedSection.includes("environment")) return "environments";
    if (locatedSection.includes("media") || locatedSection.includes("reference") || locatedSection.includes("generation")) return "media";
    if (locatedSection.includes("camera") || locatedSection.includes("look")) return "camera";
    if (diagnostic.category === "reference") return "media";
    if (["camera", "style"].includes(diagnostic.category)) return "camera";
    if (diagnostic.category === "appearance") return "subjects";
    if (diagnostic.category === "environment") return "environments";
    return "overview";
}

function navigateDiagnostic(controller, diagnostic) {
    if (diagnostic.location?.shotId) controller.shotUiState.selectedId = diagnostic.location.shotId;
    controller.navigateStudio?.(diagnosticSection(diagnostic));
}

function renderDiagnostic(diagnostic, report, controller) {
    const card = document.createElement("article");
    card.className = "minimax-h3-review-card";
    card.dataset.severity = diagnostic.severity ?? "info";
    card.dataset.category = diagnostic.category ?? "configuration";
    if (report.stale) card.dataset.stale = "true";
    const resolved = controller.resolvedDiagnosticFingerprints?.has(diagnostic.fingerprint);
    if (resolved) card.dataset.resolved = "true";

    const header = document.createElement("header");
    const title = document.createElement("strong");
    title.textContent = `${diagnostic.severity === "advice" ? "Tip" : diagnostic.severity ?? "Info"} · ${diagnostic.category ?? "configuration"}`;
    const confidence = document.createElement("span");
    confidence.textContent = diagnostic.basis === "heuristic" ? "heuristic" : diagnostic.basis ?? "derived";
    header.append(title, confidence);
    const message = document.createElement("p");
    message.className = "minimax-h3-review-message";
    message.textContent = diagnostic.message ?? "";
    card.append(header, message);

    const location = button(diagnosticLocationLabel(diagnostic.location), () => navigateDiagnostic(controller, diagnostic));
    location.className = "minimax-h3-location-chip";
    location.title = "Open this location in Prompt Studio";
    card.appendChild(location);
    if (diagnostic.location?.excerpt) {
        const excerpt = document.createElement("blockquote");
        excerpt.textContent = diagnostic.location.excerpt;
        card.appendChild(excerpt);
    }
    if (diagnostic.suggestions?.length) {
        const suggestions = document.createElement("ul");
        for (const suggestion of diagnostic.suggestions.slice(0, 3)) {
            const item = document.createElement("li");
            item.textContent = suggestion;
            suggestions.appendChild(item);
        }
        card.appendChild(suggestions);
    }
    if (diagnostic.actions?.length) {
        const actions = document.createElement("div");
        actions.className = "minimax-h3-review-actions";
        for (const safeAction of diagnostic.actions) {
            const control = button(safeAction.label, () => {
                if (!controller.applySafeAction?.(safeAction, diagnostic.fingerprint)) return;
                control.disabled = true;
                control.textContent = "Applied · run again to verify";
                card.dataset.resolved = "true";
            });
            control.disabled = resolved;
            if (resolved) control.textContent = "Applied · run again to verify";
            actions.appendChild(control);
        }
        card.appendChild(actions);
    }
    const meta = document.createElement("footer");
    meta.textContent = `${diagnostic.code ?? "diagnostic"} · ${diagnostic.blocks?.valid ? "blocks run validity" : diagnostic.blocks?.quality ? "blocks quality" : "non-blocking"}`;
    card.appendChild(meta);
    return card;
}

export function renderCoachTab(container, controller) {
    container.replaceChildren();
    const report = controller.diagnostics();
    const header = document.createElement("div");
    header.className = "minimax-h3-studio-toolbar";
    const heading = document.createElement("div");
    heading.innerHTML = "<strong>Review</strong><span>Contract checks and contextual Prompt Coach guidance</span>";
    const summary = report?.summary;
    const status = document.createElement("strong");
    status.className = "minimax-h3-review-summary";
    status.textContent = summary
        ? `${summary.errors ?? 0} errors · ${summary.warnings ?? 0} warnings · ${summary.advice ?? 0} tips`
        : `${report?.diagnostics?.length ?? 0} findings`;
    header.append(heading, status);
    container.appendChild(header);
    if (report?.stale) {
        const stale = document.createElement("div");
        stale.className = "minimax-h3-studio-status";
        stale.dataset.kind = "stale";
        stale.textContent = "This review was written before your latest changes. Run the node again to refresh it; the previous findings stay visible for context.";
        container.appendChild(stale);
    }
    if (!report?.diagnostics?.length) {
        const empty = document.createElement("div");
        empty.className = "minimax-h3-empty-state";
        const state = reviewReportState(report);
        empty.dataset.kind = state;
        if (state === "clean") {
            const success = document.createElement("strong");
            success.textContent = "Review passed";
            const copy = document.createElement("p");
            copy.textContent = "The last run completed with no findings.";
            const families = document.createElement("small");
            families.textContent = "Checked: contract structure, timing, references, dialogue/audio, camera, continuity, appearance and style.";
            empty.append(success, copy, families);
        } else {
            empty.textContent = state === "stale-clean"
                ? "The previous review had no findings. Run the node again to confirm the edited project."
                : "Review has not run yet. Run the node to check the contract and receive Prompt Coach tips; advice never blocks generation.";
        }
        container.appendChild(empty);
        return;
    }
    for (const group of groupDiagnosticsBySeverity(report.diagnostics)) {
        const section = document.createElement("section");
        section.className = "minimax-h3-review-group";
        section.dataset.severity = group.severity;
        const title = document.createElement("h3");
        title.textContent = `${SEVERITY_LABELS[group.severity]} · ${group.items.length}`;
        section.appendChild(title);
        for (const diagnostic of group.items) section.appendChild(renderDiagnostic(diagnostic, report, controller));
        container.appendChild(section);
    }
}
