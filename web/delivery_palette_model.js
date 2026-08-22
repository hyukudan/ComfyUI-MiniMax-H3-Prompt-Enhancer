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

function lineRange(source, caret) {
    const cursor = Math.max(0, Math.min(source.length, Number(caret) || 0));
    const start = source.lastIndexOf("\n", Math.max(0, cursor - 1)) + 1;
    const newline = source.indexOf("\n", cursor);
    return { start, end: newline < 0 ? source.length : newline };
}

function removeTokenAt(source, index, token) {
    let start = index;
    let end = index + token.length;
    const before = source[start - 1] ?? "";
    const after = source[end] ?? "";
    if (/[^\S\r\n]/.test(before) && /[^\S\r\n]/.test(after)) end += 1;
    else if ((start === 0 || source[start - 1] === "\n") && /[^\S\r\n]/.test(after)) end += 1;
    else if ((end === source.length || source[end] === "\n") && /[^\S\r\n]/.test(before)) start -= 1;
    return { value: source.slice(0, start) + source.slice(end), start, removed: end - start };
}

function shifted(position, editStart, removed, added = 0) {
    if (position <= editStart) return position;
    if (position <= editStart + removed) return editStart + added;
    return position + added - removed;
}

export function editDeliveryMark(value, selectionStart, selectionEnd, mark, verbMarks) {
    let source = String(value ?? "");
    let start = Math.max(0, Math.min(source.length, Number(selectionStart) || 0));
    let end = Math.max(start, Math.min(source.length, Number(selectionEnd) || start));
    const range = lineRange(source, start);
    const line = source.slice(range.start, range.end);

    if (mark.tier === "prose") {
        const local = line.indexOf(mark.emoji);
        if (local >= 0) {
            const edit = removeTokenAt(source, range.start + local, mark.emoji);
            start = shifted(start, edit.start, edit.removed);
            end = shifted(end, edit.start, edit.removed);
            return { value: edit.value, selectionStart: start, selectionEnd: end, action: "removed", oldToken: mark.emoji };
        }
    }

    if (mark.tier === "verb") {
        const existing = verbMarks
            .map((candidate) => ({ candidate, index: line.indexOf(candidate.emoji) }))
            .filter(({ index }) => index >= 0)
            .sort((a, b) => a.index - b.index);
        const same = existing.find(({ candidate }) => candidate.emoji === mark.emoji);
        if (same && existing.length === 1) {
            return { value: source, selectionStart: start, selectionEnd: end, action: "unchanged", oldToken: mark.emoji };
        }
        if (existing.length) {
            const first = existing[0];
            const absolute = range.start + first.index;
            source = source.slice(0, absolute) + mark.emoji + source.slice(absolute + first.candidate.emoji.length);
            start = shifted(start, absolute, first.candidate.emoji.length, mark.emoji.length);
            end = shifted(end, absolute, first.candidate.emoji.length, mark.emoji.length);
            // Clean up any additional, contradictory verb marks already present on this line.
            for (const extra of existing.slice(1).reverse()) {
                const offsetDelta = mark.emoji.length - first.candidate.emoji.length;
                const edit = removeTokenAt(source, range.start + extra.index + offsetDelta, extra.candidate.emoji);
                source = edit.value;
                start = shifted(start, edit.start, edit.removed);
                end = shifted(end, edit.start, edit.removed);
            }
            return {
                value: source,
                selectionStart: start,
                selectionEnd: end,
                action: first.candidate.emoji === mark.emoji ? "cleaned" : "replaced",
                oldToken: first.candidate.emoji,
            };
        }
    }

    const inserted = insertDeliveryToken(source, start, end, mark.emoji);
    return { ...inserted, action: "added" };
}

export function clearDeliveryMarksOnLine(value, selectionStart, selectionEnd, tokens) {
    let source = String(value ?? "");
    let start = Math.max(0, Math.min(source.length, Number(selectionStart) || 0));
    let end = Math.max(start, Math.min(source.length, Number(selectionEnd) || start));
    const initialRange = lineRange(source, start);
    let count = 0;
    for (const token of tokens) {
        let local = source.slice(initialRange.start, lineRange(source, start).end).indexOf(token);
        while (local >= 0) {
            const edit = removeTokenAt(source, initialRange.start + local, token);
            source = edit.value;
            start = shifted(start, edit.start, edit.removed);
            end = shifted(end, edit.start, edit.removed);
            count += 1;
            local = source.slice(initialRange.start, lineRange(source, start).end).indexOf(token);
        }
    }
    return { value: source, selectionStart: start, selectionEnd: end, count };
}

export function updateRecentDeliveryMarks(recent, token, limit = 3) {
    return [token, ...recent.filter((candidate) => candidate !== token)].slice(0, limit);
}

export function normalizedDeliverySearchText(value) {
    return String(value ?? "")
        .normalize("NFKD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLocaleLowerCase();
}

export function filterVoiceColorMarks(marks, query) {
    const needle = normalizedDeliverySearchText(query).trim();
    if (!needle) return [...marks];
    return marks.filter((mark) => normalizedDeliverySearchText(
        [mark.label, mark.group, ...(mark.aliases ?? [])].join(" "),
    ).includes(needle));
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
