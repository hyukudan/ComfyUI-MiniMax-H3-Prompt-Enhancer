// SPDX-License-Identifier: GPL-3.0-only
// Pure authoring helpers shared by the delivery palette and its Node tests.

function paddedToken(token, before, after) {
    const lead = before && !/\s$/.test(before) ? " " : "";
    const tail = after && !/^\s/.test(after) ? " " : "";
    return `${lead}${token}${tail}`;
}

export function insertDeliveryToken(value, selectionStart, selectionEnd, token) {
    const source = String(value ?? "");
    const start = Math.max(0, Math.min(source.length, Number(selectionStart) || 0));
    const end = Math.max(start, Math.min(source.length, Number(selectionEnd) || start));
    const before = source.slice(0, start);
    // Insert at the leading edge; selected dialogue remains byte-for-byte intact.
    const after = source.slice(start);
    const inserted = paddedToken(token, before, after);
    return {
        value: `${before}${inserted}${after}`,
        selectionStart: start + inserted.length,
        selectionEnd: end + inserted.length,
        inserted,
    };
}

export function hasQuotedDialogue(value) {
    const source = String(value ?? "");
    return /<d>\s*\[[^\]]+\]/i.test(source)
        || /"[^"\r\n]+"/.test(source)
        || /“[^”\r\n]+”/.test(source);
}

export function deliveryStatus(value, deliveryTokens, confirmation) {
    const source = String(value ?? "");
    const hasMark = deliveryTokens.some((token) => source.includes(token));
    if (hasMark && !hasQuotedDialogue(source)) {
        return {
            kind: "warning",
            text: "Marks apply to quoted dialogue. Add the line in quotes or the mark will be dropped.",
        };
    }
    return { kind: "info", text: confirmation ?? "" };
}

export function rovingIndex(current, key, count, columns = 1) {
    if (count <= 0) return -1;
    if (key === "Home") return 0;
    if (key === "End") return count - 1;
    const delta = {
        ArrowLeft: -1,
        ArrowRight: 1,
        ArrowUp: -Math.max(1, columns),
        ArrowDown: Math.max(1, columns),
    }[key];
    if (!delta) return current;
    return (current + delta + count) % count;
}
