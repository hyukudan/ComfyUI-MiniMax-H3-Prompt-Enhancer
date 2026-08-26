const SVG_NS = "http://www.w3.org/2000/svg";

const ICONS = Object.freeze({
    overview: ["M3 12h7V3H3z", "M14 21h7v-9h-7z", "M14 3h7v5h-7z", "M3 16h7v5H3z"],
    shots: ["M4 4h16v16H4z", "m9 9 6 3-6 3z"],
    subjects: ["M20 21a8 8 0 0 0-16 0", "M12 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10z"],
    environments: ["M3 21h18", "M5 21V9l7-6 7 6v12", "M9 21v-6h6v6"],
    media: ["M4 5h16v14H4z", "m4 15 4-4 3 3 3-4 6 6", "M9 9h.01"],
    wiring: ["M5 7h6", "M13 7h6", "M5 17h6", "M13 17h6", "M8 7v10", "M16 7v10"],
    camera: ["M14.5 4 16 7h4v13H4V7h4l1.5-3z", "M12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"],
    look: ["M12 3a9 9 0 1 0 9 9", "M12 7a5 5 0 1 0 5 5", "M12 10a2 2 0 1 0 2 2"],
    review: ["M9 11l3 3L22 4", "M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"],
    close: ["M18 6 6 18", "m6-12 12 12"],
    help: ["M9.1 9a3 3 0 1 1 5.8 1c0 2-3 2-3 4", "M12 18h.01", "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z"],
    chevronLeft: ["m15 18-6-6 6-6"],
});

export function createStudioIcon(name, size = 18) {
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("width", String(size));
    svg.setAttribute("height", String(size));
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "1.5");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("aria-hidden", "true");
    svg.classList.add("minimax-h3-icon");
    for (const pathData of ICONS[name] ?? ICONS.overview) {
        const path = document.createElementNS(SVG_NS, "path");
        path.setAttribute("d", pathData);
        svg.appendChild(path);
    }
    return svg;
}
