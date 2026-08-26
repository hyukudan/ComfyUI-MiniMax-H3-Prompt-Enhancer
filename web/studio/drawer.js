import { renderCameraLookTab } from "./tab_camera_look.js";
import { renderCameraTab } from "./tab_camera.js";
import { renderCoachTab } from "./tab_coach.js";
import { renderEnvironmentsTab } from "./tab_environments.js";
import { renderReferencesTab } from "./tab_references.js";
import { renderShotsTab } from "./tab_shots.js";
import { renderSubjectsTab } from "./tab_subjects.js";
import { renderStagingTab } from "./tab_staging.js";
import { createStudioIcon } from "./components/icons.js";
import { createSourceStateCard, normalizedSourceState } from "./components/source_state.js";
import { renderOverview } from "./overview.js";
import { ensureStudioStyles } from "./styles.js";
import { STUDIO_MAX_WIDTH, STUDIO_MIN_WIDTH, STUDIO_UI_LEGACY_STORAGE_KEY, STUDIO_UI_STORAGE_KEY } from "./tokens.js";

export function createPanelElement(tagName, className, textContent = "") {
    const element = document.createElement(tagName);
    if (className) element.className = className;
    if (textContent) element.textContent = textContent;
    return element;
}

export const STUDIO_SECTIONS = Object.freeze([
    { id: "overview", label: "Overview", icon: "overview", render: renderOverview },
    { id: "shots", label: "Shots", icon: "shots", render: renderShotsTab },
    { id: "staging", label: "Staging", icon: "subjects", render: renderStagingTab },
    { id: "subjects", label: "Subjects", icon: "subjects", render: renderSubjectsTab },
    { id: "environments", label: "Environments", icon: "environments", render: renderEnvironmentsTab },
    { id: "media", label: "Media", icon: "media", render: renderReferencesTab },
    { id: "camera", label: "Camera", icon: "camera", render: renderCameraTab },
    { id: "look", label: "Look", icon: "look", render: renderCameraLookTab },
]);

const SECTION_ALIASES = Object.freeze({ references: "media", camera_look: "look", coach: "review" });
const SECTION_IDS = new Set(STUDIO_SECTIONS.map((item) => item.id));

export function normalizeStudioSection(section) {
    const normalized = SECTION_ALIASES[section] ?? section;
    return SECTION_IDS.has(normalized) || normalized === "review" ? normalized : "overview";
}

export function diagnosticFieldLabels(field) {
    const parts = String(field ?? "").replaceAll("[", ".").replaceAll("]", "").split(".").filter(Boolean);
    const leaf = parts.at(-1) ?? "";
    const aliases = {
        action: ["Action", "Action / reaction"], openingState: ["Opening state"],
        cutContext: ["Describe cut context"], durationSeconds: ["Duration (seconds)"], transitionIn: ["Transition in"],
        cameraMotion: ["Camera motion"], cameraStart: ["Framing", "Angle", "Viewpoint"], cameraEnd: ["Framing", "Angle", "Viewpoint"],
        framing: ["Framing"], angle: ["Angle"], viewpoint: ["Viewpoint"], composition: ["Composition"], focus: ["Focus"],
        optics: ["Optics"], lensEffects: ["Lens effects"], bindings: ["File slot", "Reference"], activation: ["Activation"],
        dialogue: ["Spoken words", "Dialogue at this beat"], text: ["Spoken words"],
        subjectId: ["Subject"], environmentId: ["Environment"], toStateId: ["To"],
        trigger: ["Trigger"], mechanism: ["Mechanism"], stateId: ["State"],
    };
    return aliases[leaf] ?? (leaf ? [leaf.replace(/([a-z])([A-Z])/g, "$1 $2")] : []);
}

export function focusDiagnosticLocation(panel, location = {}) {
    if (String(location.scope ?? "").toLowerCase() === "output") {
        return { found: false, reason: "This finding refers to generated output, not an editable Studio control." };
    }
    const fieldName = String(location.field ?? "");
    let target = null;
    if (/\.action$|\]\.action$/.test(fieldName)) target = panel.querySelector?.("[data-shot-action]");
    if (!target && /\.staging(?:\.|$)/.test(fieldName)) target = panel.querySelector?.(".minimax-h3-staging-stage, .minimax-h3-staging-inspector");
    if (!target && /cameraPath/.test(fieldName)) target = panel.querySelector?.(".minimax-h3-camera-planner, .minimax-h3-spatial-camera-editor");
    const wanted = new Set(diagnosticFieldLabels(fieldName).map((value) => value.toLowerCase()));
    if (!target && wanted.size) {
        for (const wrapper of panel.querySelectorAll?.(".minimax-h3-studio-field") ?? []) {
            const label = String(wrapper.firstElementChild?.textContent ?? "").trim().toLowerCase();
            if (!wanted.has(label)) continue;
            target = wrapper.querySelector?.("input, textarea, select, button, [tabindex]") ?? wrapper;
            break;
        }
    }
    if (!target) return { found: false, reason: "Opened the related section, but this report location has no exact editable control." };
    for (let ancestor = target.parentElement; ancestor && ancestor !== panel; ancestor = ancestor.parentElement) {
        if (ancestor.tagName === "DETAILS") ancestor.open = true;
    }
    const highlight = target.closest?.(".minimax-h3-studio-field, .minimax-h3-inspector-section") ?? target;
    highlight.classList?.add("minimax-h3-diagnostic-target");
    target.scrollIntoView?.({ block: "center", behavior: "smooth" });
    target.focus?.({ preventScroll: true });
    const timeout = globalThis.setTimeout?.(() => highlight.classList?.remove("minimax-h3-diagnostic-target"), 2600);
    timeout?.unref?.();
    return { found: true, target };
}

export function defaultDrawerWidth(
    viewportWidth = globalThis.innerWidth ?? 2560,
    viewportHeight = globalThis.innerHeight ?? Math.round(viewportWidth * 9 / 16),
) {
    if (viewportWidth >= 3200 || viewportHeight >= 1800) return 920;
    if (viewportWidth >= 2200) return 820;
    return 720;
}

export function drawerWidthBounds(viewportWidth = globalThis.innerWidth ?? 1440) {
    if (viewportWidth < 700) return { minimum: viewportWidth, maximum: viewportWidth };
    return {
        minimum: STUDIO_MIN_WIDTH,
        maximum: Math.max(STUDIO_MIN_WIDTH, Math.min(STUDIO_MAX_WIDTH, viewportWidth * 0.6)),
    };
}

export function clampDrawerWidth(width, viewportWidth = globalThis.innerWidth ?? 1440) {
    const { minimum, maximum } = drawerWidthBounds(viewportWidth);
    const fallback = Math.min(maximum, Math.max(minimum, defaultDrawerWidth(viewportWidth)));
    if (width === null || width === undefined || width === "") return fallback;
    const numeric = Number(width);
    return Number.isFinite(numeric) ? Math.min(maximum, Math.max(minimum, Math.round(numeric))) : fallback;
}

const DEFAULT_PREFS = Object.freeze({
    width: null,
    lastSection: "overview",
    railCollapsed: false,
    detailMode: "guided",
    collapsedBlocks: {},
});

export function normalizeStudioDetailMode(value) {
    return value === "advanced" ? "advanced" : "guided";
}

function storageOrNull(storage) {
    if (storage !== undefined) return storage;
    try { return globalThis.localStorage ?? null; } catch { return null; }
}

export function normalizeStudioPrefs(value = {}) {
    const lastSection = normalizeStudioSection(value?.lastSection);
    const storedWidth = value?.width;
    return {
        width: storedWidth !== null && storedWidth !== undefined && storedWidth !== "" && Number.isFinite(Number(storedWidth))
            ? Number(storedWidth)
            : DEFAULT_PREFS.width,
        lastSection: lastSection === "review" ? DEFAULT_PREFS.lastSection : lastSection,
        railCollapsed: Boolean(value?.railCollapsed),
        detailMode: normalizeStudioDetailMode(value?.detailMode),
        collapsedBlocks: value?.collapsedBlocks && typeof value.collapsedBlocks === "object" && !Array.isArray(value.collapsedBlocks)
            ? { ...value.collapsedBlocks }
            : {},
    };
}

export function readStudioPrefs(storage = undefined) {
    const target = storageOrNull(storage);
    if (!target?.getItem) return { ...DEFAULT_PREFS };
    try {
        const current = target.getItem(STUDIO_UI_STORAGE_KEY);
        if (current !== null) return normalizeStudioPrefs(JSON.parse(current));
        const legacy = JSON.parse(target.getItem(STUDIO_UI_LEGACY_STORAGE_KEY) ?? "{}");
        if (legacy?.lastSection === "camera") legacy.lastSection = "look";
        return normalizeStudioPrefs(legacy);
    } catch {
        return { ...DEFAULT_PREFS };
    }
}

export function writeStudioPrefs(prefs, storage = undefined) {
    const normalized = normalizeStudioPrefs(prefs);
    const target = storageOrNull(storage);
    if (!target?.setItem) return normalized;
    try { target.setItem(STUDIO_UI_STORAGE_KEY, JSON.stringify(normalized)); } catch { /* preference storage is optional */ }
    return normalized;
}

let activeDrawer = null;

export function closeStudioDrawer(nodeId = null) {
    if (!activeDrawer || (nodeId !== null && activeDrawer.nodeId !== nodeId)) return false;
    const closing = activeDrawer;
    activeDrawer = null;
    closing.cleanup?.();
    closing.element.remove();
    closing.node?.__minimaxStudioDashboard?.refresh?.();
    closing.returnFocus?.focus?.();
    return true;
}

export function studioDrawerIsOpenFor(nodeId) {
    return activeDrawer?.nodeId === nodeId;
}

function safeDocument(read) {
    try { return normalizedSourceState(read?.()); } catch { return normalizedSourceState(null); }
}

function sourceDocuments(controller) {
    return {
        shot: safeDocument(() => controller.shotDocument()),
        project: safeDocument(() => controller.projectDocument()),
        camera: safeDocument(() => controller.cinematographyDocument()),
    };
}

function reportCounts(controller) {
    const result = { errors: 0, warnings: 0, tips: 0, total: 0, stale: false };
    const report = controller.diagnostics?.() ?? {};
    result.stale = Boolean(report.stale);
    for (const item of report.diagnostics ?? []) {
        result.total += 1;
        if (item?.severity === "error") result.errors += 1;
        else if (item?.severity === "warning") result.warnings += 1;
        else result.tips += 1;
    }
    return result;
}

export function productionContext(controller) {
    const shot = safeDocument(() => controller.shotDocument());
    const project = safeDocument(() => controller.projectDocument());
    const shots = Array.isArray(shot.value?.shots) ? shot.value.shots : [];
    const exact = shot.value?.timingMode === "exact";
    const duration = exact
        ? shots.reduce((total, item) => total + Math.max(0, Number(item?.durationSeconds) || 0), 0)
        : null;
    const projectValue = project.kind === "v2" ? project.value : null;
    const generatedTiming = controller.generationTiming?.() ?? null;
    const seconds = exact ? duration : Number(generatedTiming?.seconds);
    const frames = exact ? Math.round(duration * 24) : Number(generatedTiming?.frames);
    const requestedMode = String(controller.mode?.() ?? projectValue?.mode ?? "auto").toLowerCase();
    const resolvedMode = String(controller.resolvedMode?.() ?? "").toLowerCase();
    const mode = requestedMode === "auto" && resolvedMode && resolvedMode !== "auto"
        ? `AUTO → ${resolvedMode.toUpperCase()}`
        : requestedMode.toUpperCase();
    return {
        mode,
        shots: shots.length,
        timing: Number.isFinite(seconds) && seconds > 0
            ? `${seconds.toFixed(2)} s · ${Number.isFinite(frames) && frames > 0 ? Math.round(frames) : Math.round(seconds * 24)}f`
            : "Auto",
        generations: Array.isArray(projectValue?.generations) ? projectValue.generations.length : 0,
        media: Array.isArray(projectValue?.assets) ? projectValue.assets.length : 0,
    };
}

function createIconButton(icon, label, className = "minimax-h3-icon-button") {
    const button = createPanelElement("button", className);
    button.type = "button";
    button.setAttribute("aria-label", label);
    button.title = label;
    button.appendChild(createStudioIcon(icon));
    return button;
}

function createHeader(controller, onReview, onClose) {
    const header = createPanelElement("header", "minimax-h3-studio-header");
    const main = createPanelElement("div", "minimax-h3-header-main");
    const identity = createPanelElement("div", "minimax-h3-header-identity");
    const title = createPanelElement("h2", "", "Prompt Studio");
    const context = createPanelElement("p", "minimax-h3-header-context");
    identity.append(title, context);
    const state = createPanelElement("div", "minimax-h3-header-state");
    const saved = createPanelElement("span", "minimax-h3-saved-state", "Saved automatically to workflow");
    saved.title = "Every explicit edit is stored immediately in this node's Project v2 data.";
    const review = createPanelElement("button", "minimax-h3-review-button");
    review.type = "button";
    review.append(createStudioIcon("review"), createPanelElement("span", "minimax-h3-review-label", "Review"));
    review.setAttribute("aria-live", "polite");
    review.addEventListener("click", onReview);
    const help = createIconButton("help", "Keyboard shortcuts");
    help.setAttribute("aria-expanded", "false");
    const close = createIconButton("close", "Close Prompt Studio");
    close.addEventListener("click", onClose);
    state.append(saved, review, help, close);
    main.append(identity, state);

    const shortcuts = createPanelElement("section", "minimax-h3-shortcuts");
    shortcuts.hidden = true;
    shortcuts.setAttribute("aria-label", "Prompt Studio keyboard shortcuts");
    shortcuts.appendChild(createPanelElement("h3", "", "Keyboard shortcuts"));
    const list = createPanelElement("dl", "");
    for (const [keys, action] of [
        ["1–8", "Open a section"],
        ["↑ / ↓", "Move through section navigation"],
        ["Ctrl + Enter", "Add an item in the active editor"],
        ["Ctrl + D", "Duplicate the selection"],
        ["Ctrl + Z", "Undo the last Studio change"],
        ["Esc", "Return from Review or close Studio"],
    ]) {
        list.append(createPanelElement("dt", "", keys), createPanelElement("dd", "", action));
    }
    shortcuts.appendChild(list);
    const setShortcutsOpen = (open) => {
        shortcuts.hidden = !open;
        help.setAttribute("aria-expanded", String(open));
    };
    help.addEventListener("click", () => setShortcutsOpen(shortcuts.hidden));
    const production = createPanelElement("div", "minimax-h3-production-context");
    production.setAttribute("role", "group");
    production.setAttribute("aria-label", "Production context");
    const productionFields = new Map();
    for (const [key, label] of [
        ["mode", "Mode"], ["shots", "Shots"], ["timing", "Duration"],
        ["generations", "Generations"], ["media", "Media"],
    ]) {
        const item = createPanelElement("span", "minimax-h3-production-context-item");
        item.dataset.contextKey = key;
        item.append(
            createPanelElement("small", "", label),
            createPanelElement("strong", "", "—"),
        );
        productionFields.set(key, item.querySelector("strong"));
        production.appendChild(item);
    }
    header.append(main, production, shortcuts);

    const refresh = () => {
        const project = safeDocument(() => controller.projectDocument());
        const mode = project.kind === "v2" ? project.value?.mode ?? "auto" : "project v2";
        const generations = project.kind === "v2" ? project.value?.generations?.length ?? 0 : 0;
        context.textContent = project.kind === "v2" ? `${mode} · ${generations || 1} generation${generations === 1 ? "" : "s"}` : "Project v2 workspace";
        const counts = reportCounts(controller);
        review.dataset.state = counts.stale ? "stale" : counts.errors ? "error" : counts.warnings ? "warning" : "ready";
        review.querySelector(".minimax-h3-review-label").textContent = counts.stale
            ? `Review · stale`
            : counts.total ? `Review · ${counts.errors} errors · ${counts.warnings + counts.tips} notes` : "Review";
        const contextModel = productionContext(controller);
        for (const [key, target] of productionFields) target.textContent = String(contextModel[key]);
    };
    return { header, shortcuts, setShortcutsOpen, refresh, close };
}

function createNavigation(node, onNavigate, onCollapse) {
    const rail = createPanelElement("nav", "minimax-h3-studio-rail");
    rail.setAttribute("aria-label", "Prompt Studio sections");
    const tablist = createPanelElement("div", "minimax-h3-studio-tabs");
    tablist.setAttribute("role", "tablist");
    tablist.setAttribute("aria-orientation", "vertical");
    const buttons = new Map();
    STUDIO_SECTIONS.forEach(({ id, label, icon }) => {
        const button = createPanelElement("button", "minimax-h3-studio-tab");
        button.type = "button";
        button.id = `minimax-h3-tab-${node.id}-${id}`;
        button.setAttribute("role", "tab");
        button.setAttribute("aria-label", label);
        button.title = label;
        button.append(createStudioIcon(icon, 20), createPanelElement("span", "minimax-h3-tab-label", label));
        button.addEventListener("click", () => onNavigate(id));
        button.addEventListener("keydown", (event) => {
            if (!["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
            event.preventDefault();
            const current = STUDIO_SECTIONS.findIndex((item) => item.id === id);
            const forward = ["ArrowDown", "ArrowRight"].includes(event.key);
            const next = event.key === "Home" ? 0 : event.key === "End" ? STUDIO_SECTIONS.length - 1
                : (current + (forward ? 1 : -1) + STUDIO_SECTIONS.length) % STUDIO_SECTIONS.length;
            const nextId = STUDIO_SECTIONS[next].id;
            buttons.get(nextId)?.focus();
            onNavigate(nextId);
        });
        buttons.set(id, button);
        tablist.appendChild(button);
    });
    const collapse = createIconButton("chevronLeft", "Collapse section rail", "minimax-h3-rail-collapse");
    collapse.addEventListener("click", onCollapse);
    rail.append(tablist, collapse);
    return { rail, buttons, collapse };
}

function sourceGate(sectionId, controller, panel) {
    const documents = sourceDocuments(controller);
    if (["shots", "staging", "camera"].includes(sectionId) && ["malformed", "future"].includes(documents.shot.kind)) {
        panel.appendChild(createSourceStateCard({
            name: "Shot plan",
            documentState: documents.shot,
            acceptedVersions: [1, 2],
            onApplyRaw: controller.replaceShotRaw ? (raw) => controller.replaceShotRaw(raw) : null,
        }));
        return true;
    }
    if (["subjects", "environments", "media", "staging"].includes(sectionId) && documents.project.kind === "v1") {
        panel.classList.add("minimax-h3-source-gated");
        const unavailable = createPanelElement("section", "minimax-h3-empty-state minimax-h3-source-unavailable");
        unavailable.append(
            createPanelElement("h3", "", "Project v2 workspace"),
            createPanelElement("p", "", "This section becomes editable when a Project v2 source is connected."),
        );
        const tools = createPanelElement("details", "minimax-h3-source-tools minimax-h3-source-tools-gate");
        tools.append(
            createPanelElement("summary", "", "Import & source tools"),
            createSourceStateCard({
                name: "Media project",
                documentState: documents.project,
                acceptedVersions: [2],
                legacyDescription: "This legacy manifest is preserved unchanged. Prompt Studio edits Project v2 only.",
            }),
        );
        panel.append(unavailable, tools);
        return true;
    }
    if (["subjects", "environments", "media", "staging"].includes(sectionId) && ["malformed", "future"].includes(documents.project.kind)) {
        panel.appendChild(createSourceStateCard({
            name: "Media project",
            documentState: documents.project,
            acceptedVersions: [2],
            legacyDescription: "This legacy manifest is preserved unchanged. Prompt Studio edits Project v2 only.",
            onApplyRaw: controller.replaceProjectRaw ? (raw) => controller.replaceProjectRaw(raw) : null,
        }));
        return true;
    }
    return false;
}

function isEditingTarget(target) {
    return target instanceof HTMLElement
        && (target.matches("input, textarea, select") || target.isContentEditable);
}

export function openStudioDrawer(node, controller, initialTab = null, returnFocus = null) {
    closeStudioDrawer();
    ensureStudioStyles();
    let prefs = readStudioPrefs();
    const drawer = createPanelElement("section", "minimax-h3-studio");
    drawer.setAttribute("role", "dialog");
    drawer.setAttribute("aria-modal", "false");
    drawer.setAttribute("aria-label", "MiniMax H3 Prompt Studio");
    drawer.dataset.railCollapsed = String(prefs.railCollapsed);
    drawer.dataset.detailMode = prefs.detailMode;
    drawer.style.width = `${clampDrawerWidth(prefs.width, globalThis.innerWidth)}px`;

    const resizer = createPanelElement("div", "minimax-h3-studio-resizer");
    resizer.tabIndex = 0;
    resizer.setAttribute("role", "separator");
    resizer.setAttribute("aria-label", "Resize Prompt Studio");
    resizer.setAttribute("aria-orientation", "vertical");
    const body = createPanelElement("div", "minimax-h3-studio-body");
    const panel = createPanelElement("main", "minimax-h3-studio-panel");
    panel.setAttribute("role", "tabpanel");
    panel.tabIndex = -1;
    let previousSection = normalizeStudioSection(initialTab ?? prefs.lastSection);
    if (previousSection === "review") previousSection = prefs.lastSection;
    let currentSection = previousSection;

    const savePrefs = (patch) => {
        prefs = writeStudioPrefs({ ...prefs, ...patch });
        return prefs;
    };
    const updateResizer = () => {
        const { minimum, maximum } = drawerWidthBounds(globalThis.innerWidth);
        const width = clampDrawerWidth(parseFloat(drawer.style.width), globalThis.innerWidth);
        resizer.setAttribute("aria-valuemin", String(minimum));
        resizer.setAttribute("aria-valuemax", String(maximum));
        resizer.setAttribute("aria-valuenow", String(width));
    };

    let render = () => {};
    let applyDetailMode = () => {};
    const previousDetailMode = controller.studioDetailMode;
    controller.studioDetailMode = prefs.detailMode;
    const header = createHeader(
        controller,
        () => render("review"),
        () => closeStudioDrawer(node.id),
    );
    const navigation = createNavigation(node, (id) => render(id), () => {
        const collapsed = drawer.dataset.railCollapsed !== "true";
        drawer.dataset.railCollapsed = String(collapsed);
        navigation.collapse.setAttribute("aria-label", collapsed ? "Expand section rail" : "Collapse section rail");
        savePrefs({ railCollapsed: collapsed });
    });

    const renderReview = () => {
        const toolbar = createPanelElement("div", "minimax-h3-review-toolbar");
        const back = createPanelElement("button", "minimax-h3-button minimax-h3-button-secondary", "Back to workspace");
        back.type = "button";
        back.prepend(createStudioIcon("chevronLeft"));
        back.addEventListener("click", () => render(previousSection));
        const title = createPanelElement("h2", "", "Review");
        toolbar.append(back, title);
        panel.appendChild(toolbar);
        const content = createPanelElement("div", "minimax-h3-review-content");
        panel.appendChild(content);
        renderCoachTab(content, controller);
    };

    render = (requestedSection) => {
        const sectionId = normalizeStudioSection(requestedSection);
        currentSection = sectionId;
        panel.replaceChildren();
        panel.className = `minimax-h3-studio-panel minimax-h3-section-${sectionId}`;
        if (sectionId === "review") renderReview();
        else {
            previousSection = sectionId;
            savePrefs({ lastSection: sectionId });
            const section = STUDIO_SECTIONS.find((item) => item.id === sectionId) ?? STUDIO_SECTIONS[0];
            panel.removeAttribute("aria-label");
            panel.setAttribute("aria-labelledby", `minimax-h3-tab-${node.id}-${section.id}`);
            if (section.id === "overview") {
                renderOverview(panel, controller, { navigate: render, openReview: () => render("review") });
            } else if (!sourceGate(section.id, controller, panel)) section.render(panel, controller);
        }
        if (sectionId === "review") {
            panel.removeAttribute("aria-labelledby");
            panel.setAttribute("aria-label", "Prompt Studio Review");
        }
        for (const [id, button] of navigation.buttons) {
            const selected = id === sectionId;
            button.setAttribute("aria-selected", String(selected));
            button.tabIndex = selected ? 0 : -1;
        }
        header.refresh();
        if (activeDrawer) activeDrawer.tabId = sectionId;
    };

    applyDetailMode = (requestedMode) => {
        const mode = normalizeStudioDetailMode(requestedMode);
        if (mode === prefs.detailMode) return;
        savePrefs({ detailMode: mode });
        drawer.dataset.detailMode = mode;
        controller.studioDetailMode = mode;
        render(currentSection);
    };

    const applyWidth = (width, persist = false) => {
        const value = clampDrawerWidth(width, globalThis.innerWidth);
        drawer.style.width = `${value}px`;
        updateResizer();
        if (persist && globalThis.innerWidth >= 700) savePrefs({ width: value });
    };
    let resizeStart = null;
    const onPointerMove = (event) => {
        if (!resizeStart) return;
        applyWidth(resizeStart.width + resizeStart.x - event.clientX);
    };
    const onPointerUp = (event) => {
        if (!resizeStart) return;
        onPointerMove(event);
        resizeStart = null;
        drawer.dataset.resizing = "false";
        applyWidth(parseFloat(drawer.style.width), true);
    };
    resizer.addEventListener("pointerdown", (event) => {
        if (globalThis.innerWidth < 700) return;
        event.preventDefault();
        resizeStart = { x: event.clientX, width: drawer.getBoundingClientRect().width };
        drawer.dataset.resizing = "true";
        resizer.setPointerCapture?.(event.pointerId);
    });
    resizer.addEventListener("dblclick", () => applyWidth(defaultDrawerWidth(globalThis.innerWidth), true));
    resizer.addEventListener("keydown", (event) => {
        if (!["ArrowLeft", "ArrowRight"].includes(event.key) || globalThis.innerWidth < 700) return;
        event.preventDefault();
        const step = event.shiftKey ? 64 : 16;
        const direction = event.key === "ArrowLeft" ? 1 : -1;
        applyWidth(parseFloat(drawer.style.width) + direction * step, true);
    });
    const onViewportResize = () => applyWidth(prefs.width);
    const onKeydown = (event) => {
        if (event.key === "Escape") {
            if (!header.shortcuts.hidden) {
                header.setShortcutsOpen(false);
                return;
            }
            if (activeDrawer?.tabId === "review") {
                event.preventDefault();
                render(previousSection);
                return;
            }
            closeStudioDrawer(node.id);
            return;
        }
        if (isEditingTarget(event.target) || event.ctrlKey || event.metaKey || event.altKey) return;
        if (/^[1-9]$/.test(event.key) && Number(event.key) <= STUDIO_SECTIONS.length) {
            event.preventDefault();
            render(STUDIO_SECTIONS[Number(event.key) - 1].id);
            return;
        }
        if (event.key === "?") {
            event.preventDefault();
            header.setShortcutsOpen(header.shortcuts.hidden);
        }
    };
    globalThis.addEventListener("pointermove", onPointerMove);
    globalThis.addEventListener("pointerup", onPointerUp);
    globalThis.addEventListener("resize", onViewportResize);
    drawer.addEventListener("keydown", onKeydown);
    const refreshHeaderSoon = () => queueMicrotask(header.refresh);
    body.addEventListener("change", refreshHeaderSoon);
    body.addEventListener("blur", refreshHeaderSoon, true);
    body.addEventListener("click", refreshHeaderSoon);

    body.append(navigation.rail, panel);
    drawer.append(resizer, header.header, body);
    document.body.appendChild(drawer);
    const previousNavigateStudio = controller.navigateStudio;
    const previousNavigateStudioLocation = controller.navigateStudioLocation;
    const previousSetStudioDetailMode = controller.setStudioDetailMode;
    controller.navigateStudio = render;
    controller.setStudioDetailMode = applyDetailMode;
    const navigateStudioLocation = (section, location = {}) => {
        render(section);
        queueMicrotask(() => {
            const result = focusDiagnosticLocation(panel, location);
            if (result.found) return;
            const feedback = createPanelElement("div", "minimax-h3-studio-status", result.reason);
            feedback.dataset.kind = "navigation-fallback";
            panel.prepend(feedback);
        });
    };
    controller.navigateStudioLocation = navigateStudioLocation;
    const cleanup = () => {
        globalThis.removeEventListener("pointermove", onPointerMove);
        globalThis.removeEventListener("pointerup", onPointerUp);
        globalThis.removeEventListener("resize", onViewportResize);
        if (controller.navigateStudio === render) {
            if (previousNavigateStudio === undefined) delete controller.navigateStudio;
            else controller.navigateStudio = previousNavigateStudio;
        }
        if (controller.navigateStudioLocation === navigateStudioLocation) {
            if (previousNavigateStudioLocation === undefined) delete controller.navigateStudioLocation;
            else controller.navigateStudioLocation = previousNavigateStudioLocation;
        }
        if (controller.setStudioDetailMode === applyDetailMode) {
            if (previousSetStudioDetailMode === undefined) delete controller.setStudioDetailMode;
            else controller.setStudioDetailMode = previousSetStudioDetailMode;
        }
        if (controller.studioDetailMode === prefs.detailMode) {
            if (previousDetailMode === undefined) delete controller.studioDetailMode;
            else controller.studioDetailMode = previousDetailMode;
        }
    };
    activeDrawer = { nodeId: node.id, node, element: drawer, controller, returnFocus, tabId: previousSection, render, cleanup };
    node.__minimaxStudioDashboard?.refresh?.();
    updateResizer();
    render(initialTab ?? prefs.lastSection);
    header.close.focus();
    return drawer;
}

export function refreshStudioDrawer(nodeId) {
    if (activeDrawer?.nodeId !== nodeId) return;
    activeDrawer.render(activeDrawer.tabId);
}

export function dashboardSummaries(controller) {
    const shot = controller.shotDocument();
    const project = controller.projectDocument();
    const shots = shot?.value?.shots?.length ?? 0;
    const staged = shot?.value?.shots?.reduce((count, item) => count + (item?.staging?.length ?? 0), 0) ?? 0;
    const subjects = project?.value?.subjects?.length ?? 0;
    const environments = project?.value?.environments?.length ?? 0;
    const assets = project?.value?.assets?.length ?? 0;
    const active = project?.value?.generations?.reduce((count, generation) => count + (generation?.bindings?.length ?? 0), 0) ?? 0;
    const diagnostics = controller.diagnostics()?.diagnostics?.length ?? 0;
    return { shots, staged, subjects, environments, assets, active, diagnostics };
}

export function createStudioDashboard(node, controller) {
    ensureStudioStyles();
    const root = createPanelElement("div", "minimax-h3-dashboard");
    const open = createPanelElement("button", "minimax-h3-dashboard-open");
    open.type = "button";
    open.append(createStudioIcon("overview", 20), createPanelElement("span", "", "Open Studio"));
    open.addEventListener("click", () => {
        if (studioDrawerIsOpenFor(node.id)) closeStudioDrawer(node.id);
        else openStudioDrawer(node, controller, null, open);
    });
    root.appendChild(open);
    const strip = createPanelElement("div", "minimax-h3-dashboard-links");
    const definitions = [
        ["shots", "Shots", "shots", (summary) => summary.shots],
        ["staging", "Staging", "subjects", (summary) => summary.staged],
        ["subjects", "Subjects", "subjects", (summary) => summary.subjects],
        ["environments", "Environments", "environments", (summary) => summary.environments],
        ["media", "Media", "media", (summary) => `${summary.active}/${summary.assets}`],
        ["camera", "Camera", "camera", () => ""],
        ["look", "Look", "look", () => ""],
        ["review", "Review", "review", (summary) => summary.diagnostics],
    ];
    const refresh = () => {
        const summary = dashboardSummaries(controller);
        const isOpen = studioDrawerIsOpenFor(node.id);
        open.querySelector("span").textContent = isOpen ? "Close Studio" : "Open Studio";
        open.setAttribute("aria-pressed", String(isOpen));
        open.title = isOpen ? "Close Prompt Studio and return to the workflow" : "Open Prompt Studio";
        for (const [id, label, , value] of definitions) {
            const chip = root.querySelector(`[data-studio-tab="${id}"]`);
            if (!chip) continue;
            const count = value(summary);
            chip.querySelector(".minimax-h3-chip-count").textContent = String(count);
            chip.setAttribute("aria-label", count === "" ? label : `${label}: ${count}`);
        }
    };
    for (const [id, label, icon] of definitions) {
        const chip = createPanelElement("button", "minimax-h3-chip");
        chip.type = "button";
        chip.dataset.studioTab = id;
        chip.title = label;
        chip.append(createStudioIcon(icon, 16), createPanelElement("span", "minimax-h3-chip-count"));
        chip.addEventListener("click", () => openStudioDrawer(node, controller, id, chip));
        strip.appendChild(chip);
    }
    root.appendChild(strip);
    refresh();
    return { root, refresh };
}
