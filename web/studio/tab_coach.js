import { renderSourceTools } from "./overview.js";

const SEVERITY_ORDER = ["error", "warning", "advice", "info"];
const SEVERITY_LABELS = { error: "Errors", warning: "Warnings", advice: "Tips", info: "Information" };
const BASIS_LABELS = { contract: "Contract rule", configuration: "Configuration", derived: "Derived check", heuristic: "Heuristic advice" };
export const REVIEW_DISMISSALS_KEY = "minimax_h3_review_dismissals_v1";
const REVIEW_DISMISSALS_VERSION = 1;

export function readReviewDismissals(storage = null) {
    try {
        const parsed = JSON.parse(storage?.getItem(REVIEW_DISMISSALS_KEY) ?? "null");
        if (parsed?.version !== REVIEW_DISMISSALS_VERSION || !Array.isArray(parsed.fingerprints)) return new Set();
        return new Set(parsed.fingerprints.filter((value) => typeof value === "string" && value.length <= 128).slice(-500));
    } catch {
        return new Set();
    }
}

export function writeReviewDismissals(fingerprints, storage = null) {
    try {
        const values = [...fingerprints].filter((value) => typeof value === "string" && value.length <= 128).slice(-500);
        storage?.setItem(REVIEW_DISMISSALS_KEY, JSON.stringify({ version: REVIEW_DISMISSALS_VERSION, fingerprints: values }));
        return true;
    } catch {
        return false;
    }
}

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

export function diagnosticSection(diagnostic) {
    const field = String(diagnostic.location?.field ?? "").toLowerCase();
    if (field.startsWith("cinematography_json.")) return "look";
    if (/\.staging(?:\.|$)/.test(field)) return "staging";
    if (/camerapath|camerastart|cameraend/.test(field)) return "camera";
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

function reviewStorage(controller) {
    if (controller.reviewDismissalStorage !== undefined) return controller.reviewDismissalStorage;
    try { return globalThis.localStorage ?? null; } catch { return null; }
}

function navigateDiagnostic(controller, diagnostic) {
    if (diagnostic.location?.shotId) controller.shotUiState.selectedId = diagnostic.location.shotId;
    const section = diagnosticSection(diagnostic);
    if (controller.navigateStudioLocation) controller.navigateStudioLocation(section, diagnostic.location ?? {});
    else controller.navigateStudio?.(section);
}

function renderDiagnostic(diagnostic, report, controller, { dismissed = false, onDismiss = () => {} } = {}) {
    const card = document.createElement("article");
    card.className = "minimax-h3-review-card";
    card.dataset.severity = diagnostic.severity ?? "info";
    card.dataset.category = diagnostic.category ?? "configuration";
    if (report.stale) card.dataset.stale = "true";
    const resolved = controller.resolvedDiagnosticFingerprints?.has(diagnostic.fingerprint);
    if (resolved) card.dataset.resolved = "true";
    if (dismissed) card.dataset.dismissed = "true";

    const header = document.createElement("header");
    const title = document.createElement("strong");
    title.textContent = `${diagnostic.severity === "advice" ? "Tip" : diagnostic.severity ?? "Info"} · ${diagnostic.category ?? "configuration"}`;
    const confidence = document.createElement("span");
    confidence.textContent = BASIS_LABELS[diagnostic.basis] ?? "Derived check";
    confidence.title = "Why this finding exists";
    const dismiss = button(dismissed ? "Restore" : "Dismiss", () => onDismiss(diagnostic.fingerprint, !dismissed));
    dismiss.className = "minimax-h3-review-dismiss";
    dismiss.title = dismissed ? "Return this finding to the active review" : "Hide this fingerprint in this browser only";
    header.append(title, confidence, dismiss);
    const message = document.createElement("p");
    message.className = "minimax-h3-review-message";
    message.textContent = diagnostic.message ?? "";
    card.append(header, message);

    const location = button(diagnosticLocationLabel(diagnostic.location), () => navigateDiagnostic(controller, diagnostic));
    location.className = "minimax-h3-location-chip";
    location.title = "Open the closest matching control; output-only findings open their related section";
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

function renderPromptBudget(report) {
    const budget = report?.promptBudget;
    if (!budget || !Number.isFinite(Number(budget.totalCharacters))) return null;
    const section = document.createElement("section");
    section.className = "minimax-h3-review-budget";
    const header = document.createElement("header");
    const title = document.createElement("strong");
    title.textContent = "Prompt budget";
    const source = document.createElement("span");
    source.textContent = budget.source === "local_estimate" ? "Local estimate from enhanced prompt" : "Reported";
    header.append(title, source);
    const total = document.createElement("p");
    const limit = Number(budget.limitCharacters);
    total.textContent = Number.isFinite(limit) && limit > 0
        ? `${Number(budget.totalCharacters).toLocaleString()} / ${limit.toLocaleString()} characters`
        : `${Number(budget.totalCharacters).toLocaleString()} characters · no active API limit reported`;
    section.append(header, total);
    const rows = document.createElement("div");
    rows.className = "minimax-h3-review-budget-rows";
    for (const item of budget.sections ?? []) {
        if (!item?.name || !Number.isFinite(Number(item.characters))) continue;
        const row = document.createElement("div");
        row.append(
            Object.assign(document.createElement("span"), { textContent: String(item.name).replaceAll("_", " ") }),
            Object.assign(document.createElement("strong"), { textContent: `${Number(item.characters).toLocaleString()} chars` }),
        );
        rows.appendChild(row);
    }
    section.appendChild(rows);
    return section;
}

export function renderCoachTab(container, controller) {
    container.replaceChildren();
    const report = controller.diagnostics();
    const dismissedStorage = reviewStorage(controller);
    const dismissed = readReviewDismissals(dismissedStorage);
    const diagnostics = report?.diagnostics ?? [];
    const dismissedCount = diagnostics.filter((item) => dismissed.has(item?.fingerprint)).length;
    controller.reviewUiState ??= { showDismissed: false };
    const appendAdvancedTools = () => container.appendChild(renderSourceTools(controller));
    const header = document.createElement("div");
    header.className = "minimax-h3-studio-toolbar";
    const heading = document.createElement("div");
    heading.innerHTML = "<strong>Review</strong><span>Contract checks and contextual Prompt Coach guidance</span>";
    const summary = report?.summary;
    const reportState = reviewReportState(report);
    const status = document.createElement("strong");
    status.className = "minimax-h3-review-summary";
    status.textContent = reportState === "not-run" ? "Not run" : summary
        ? `${summary.errors ?? 0} errors · ${summary.warnings ?? 0} warnings · ${summary.advice ?? 0} tips`
        : `${report?.diagnostics?.length ?? 0} findings`;
    header.append(heading, status);
    if (dismissedCount) {
        const toggle = button(
            controller.reviewUiState.showDismissed ? `Hide dismissed (${dismissedCount})` : `Show dismissed (${dismissedCount})`,
            () => { controller.reviewUiState.showDismissed = !controller.reviewUiState.showDismissed; renderCoachTab(container, controller); },
        );
        toggle.className = "minimax-h3-button minimax-h3-button-secondary minimax-h3-review-dismiss-toggle";
        header.appendChild(toggle);
    }
    container.appendChild(header);
    const runBar = document.createElement("div");
    runBar.className = "minimax-h3-review-run-bar";
    const runCopy = document.createElement("div");
    runCopy.innerHTML = "<strong>Validate the current project</strong><span>Run only Prompt Studio for a fresh review, or queue the complete graph when you are ready to generate.</span>";
    const runActions = document.createElement("div");
    const runFeedback = document.createElement("span"); runFeedback.setAttribute("role", "status");
    const runAction = (label, method, runningLabel, className) => {
        const control = button(label, async () => {
            if (typeof controller[method] !== "function") return;
            control.disabled = true; runFeedback.dataset.valid = "true"; runFeedback.textContent = runningLabel;
            try { await controller[method](); runFeedback.textContent = "Queued. Review will refresh when execution finishes."; }
            catch (error) { runFeedback.dataset.valid = "false"; runFeedback.textContent = error?.message || "Could not queue execution."; }
            finally { control.disabled = false; }
        });
        control.className = className; control.disabled = typeof controller[method] !== "function";
        return control;
    };
    runActions.append(
        runAction("Validate", "runStudioNode", "Validating Prompt Studio…", "minimax-h3-button minimax-h3-button-secondary"),
        runAction("Generate & Queue", "runFullWorkflow", "Generating prompt and queueing workflow…", "minimax-h3-button minimax-h3-button-primary"),
    );
    runBar.append(runCopy, runActions, runFeedback); container.appendChild(runBar);
    if (report?.stale) {
        const stale = document.createElement("div");
        stale.className = "minimax-h3-studio-status";
        stale.dataset.kind = "stale";
        stale.textContent = "This review was written before your latest changes. Run the node again to refresh it; the previous findings stay visible for context.";
        container.appendChild(stale);
    }
    const budget = renderPromptBudget(report);
    if (budget) container.appendChild(budget);
    if (!report?.diagnostics?.length) {
        const empty = document.createElement("div");
        empty.className = "minimax-h3-empty-state";
        const state = reportState;
        empty.dataset.kind = state;
        if (state === "clean") {
            const success = document.createElement("strong");
            success.textContent = "Review passed";
            const copy = document.createElement("p");
            copy.textContent = "The last run completed with no findings.";
            const families = document.createElement("small");
            families.textContent = "Checked: contract structure, timing, references, dialogue/audio, camera, continuity, appearance and style.";
            empty.append(success, copy, families);
        } else if (state === "stale-clean") {
            const staleTitle = document.createElement("strong"); staleTitle.textContent = "Previous review passed · refresh required";
            const staleCopy = document.createElement("p"); staleCopy.textContent = "The project changed after that run. Run Prompt Studio again to validate the current version.";
            empty.append(staleTitle, staleCopy);
        } else {
            const notRun = document.createElement("strong"); notRun.textContent = "Not run";
            const copy = document.createElement("p"); copy.textContent = "Run Prompt Studio to check structure, references, dialogue, camera and continuity.";
            const note = document.createElement("small"); note.textContent = "No result is shown until a real execution completes.";
            empty.append(notRun, copy, note);
        }
        container.appendChild(empty);
        appendAdvancedTools();
        return;
    }
    const visibleDiagnostics = diagnostics.filter((item) => controller.reviewUiState.showDismissed || !dismissed.has(item?.fingerprint));
    if (!visibleDiagnostics.length) {
        const locallyEmpty = document.createElement("div");
        locallyEmpty.className = "minimax-h3-empty-state";
        locallyEmpty.textContent = "All current findings are dismissed in this browser. Use Show dismissed to restore any of them.";
        container.appendChild(locallyEmpty);
        appendAdvancedTools();
        return;
    }
    const onDismiss = (fingerprint, shouldDismiss) => {
        if (!fingerprint) return;
        if (shouldDismiss) dismissed.add(fingerprint); else dismissed.delete(fingerprint);
        writeReviewDismissals(dismissed, dismissedStorage);
        renderCoachTab(container, controller);
    };
    for (const group of groupDiagnosticsBySeverity(visibleDiagnostics)) {
        const section = document.createElement("section");
        section.className = "minimax-h3-review-group";
        section.dataset.severity = group.severity;
        const title = document.createElement("h3");
        title.textContent = `${SEVERITY_LABELS[group.severity]} · ${group.items.length}`;
        section.appendChild(title);
        for (const diagnostic of group.items) section.appendChild(renderDiagnostic(diagnostic, report, controller, {
            dismissed: dismissed.has(diagnostic.fingerprint), onDismiss,
        }));
        container.appendChild(section);
    }
    appendAdvancedTools();
}
