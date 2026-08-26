// SPDX-License-Identifier: GPL-3.0-only

export function insertSubjectMention(value, selectionStart, selectionEnd, mention) {
    const source = String(value ?? "");
    const existing = source.indexOf(mention);
    if (existing >= 0) {
        const escaped = mention.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const deduped = source.replace(new RegExp(`(${escaped})(?:\\s+${escaped})+`, "g"), "$1");
        const cursor = existing + mention.length;
        return { value: deduped, selectionStart: cursor, selectionEnd: cursor, existing: true };
    }
    const start = Math.max(0, Math.min(source.length, Number(selectionStart) || 0));
    const end = Math.max(start, Math.min(source.length, Number(selectionEnd) || start));
    const before = source.slice(0, start);
    const after = source.slice(end);
    const lead = before && !/\s$/.test(before) ? " " : "";
    const tail = after && !/^\s/.test(after) ? " " : "";
    const inserted = `${lead}${mention}${tail}`;
    const cursor = before.length + inserted.length;
    return { value: `${before}${inserted}${after}`, selectionStart: cursor, selectionEnd: cursor };
}
