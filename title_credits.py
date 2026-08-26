# SPDX-License-Identifier: GPL-3.0-only
"""Deterministic cinematic title-sequence briefing for the H3 prompt enhancer."""

from __future__ import annotations

import json


TITLE_RECIPE_DISABLED = "none"

TITLE_RECIPES = {
    "Auto director": (
        "Choose one complete causal production system from the concept. Coordinate material, stage, "
        "typography, camera, lighting, transitions, and sourced sound rather than selecting unrelated effects."
    ),
    "Prestige imprint": (
        "A heavy die presses a tactile substrate and leaves exact embossed, debossed, or foil-stamped "
        "letterforms. The press withdraws, raking light reveals clean relief, and the camera settles "
        "orthogonally for the readable hold. Feed or lift the substrate to transition between cards."
    ),
    "Precision apparatus": (
        "Blank indexed modules, shutters, plates, or machined components perform one deliberate mechanical "
        "movement into exact glyph geometry. Pre-reveal faces remain blank or abstract, never cycling fake "
        "letters. Every mechanism locks physically before the hold and resets causally between cards."
    ),
    "Analog print lab": (
        "Controlled photographic exposure or a practical print pass fixes exact typography into emulsion or "
        "onto paper. Developer, film transport, contact sheets, registration marks, or rollers motivate the "
        "reveal and transition. Contrast settles before a stable editorial hold with living grain."
    ),
    "Unearthed archive": (
        "The exact inscription already exists beneath dust, sediment, salt, ash, oxidation, or patina. Wind, "
        "water, vibration, or a physical tool uncovers it coherently without drawing substitute glyphs. "
        "Residue settles and grazing light reveals stable depth before the hold."
    ),
    "Optical luxury": (
        "Mirrors, prisms, glass, caustics, shadows, or refracted layers begin as abstract light and geometry. "
        "One motivated camera or light movement brings them into precise alignment as the exact lettering, "
        "then alignment, exposure, and camera freeze for an elegant readable hold."
    ),
    "Living material": (
        "Choose one organic, atmospheric, liquid, particulate, or geological material supported by the concept. "
        "Its believable physics owns formation and transitions throughout the sequence. It completes and "
        "stabilizes every glyph before the hold and never disperses the final composition."
    ),
}

TITLE_ENERGIES = {
    "restrained": (
        "Use sparse confident motion, controlled contrast, minimal camera movement, and precise quiet sound."
    ),
    "balanced": (
        "Balance visual development with calm readable holds, motivated camera movement, and a clear sound arc."
    ),
    "spectacular": (
        "Use ambitious scale, layered depth, bold lighting changes, and powerful sourced sound, then simplify "
        "motion completely during every readable hold."
    ),
}


def parse_title(title: str) -> list[str]:
    return [line.strip() for line in str(title or "").splitlines() if line.strip()]


def parse_credits(credits: str) -> list[tuple[str | None, str]]:
    parsed = []
    for line_number, raw_line in enumerate(str(credits or "").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        if "|" not in line:
            parsed.append((None, line))
            continue
        role, name = (part.strip() for part in line.split("|", 1))
        if not role or not name:
            raise ValueError(
                f"Credit line {line_number} must contain text on both sides of '|', for example 'Role | Name'."
            )
        parsed.append((role, name))
    return parsed


def title_cards(title: str, credits: str, placement: str) -> list[dict]:
    title_lines = parse_title(title)
    credit_lines = parse_credits(credits)
    if not title_lines and not credit_lines:
        raise ValueError("Titles & Credits requires a title, credit lines, or both.")
    if placement not in ("after credits", "before credits"):
        raise ValueError("title_placement must be 'after credits' or 'before credits'.")
    main = [{"kind": "title", "lines": title_lines}] if title_lines else []
    cards = [{"kind": "credit", "role": role, "name": name} for role, name in credit_lines]
    return main + cards if placement == "before credits" else cards + main


def _card_strings(card: dict) -> list[str]:
    if card["kind"] == "title":
        return card["lines"]
    return [text for text in (card["role"], card["name"]) if text]


def validate_title_fit(cards: list[dict], aspect_ratio: str) -> None:
    limits = {"21:9": 72, "16:9": 64, "4:3": 52, "1:1": 48, "3:4": 40, "9:16": 36, "auto": 64}
    limit = limits.get(aspect_ratio, limits["auto"])
    for card_number, card in enumerate(cards, 1):
        strings = _card_strings(card)
        if card["kind"] == "title" and len(strings) > 4:
            raise ValueError(
                f"CARD {card_number} has {len(strings)} title lines; use at most 4 lines or split the sequence."
            )
        for line_number, text in enumerate(strings, 1):
            if len(text) > limit:
                remedy = "Add intentional title line breaks or use a wider ratio." if card["kind"] == "title" else "Shorten it or use a wider ratio."
                raise ValueError(
                    f"CARD {card_number} line {line_number} has {len(text)} characters, which is too wide for "
                    f"{aspect_ratio}. {remedy}"
                )


def _reading_hold(card: dict, aspect_ratio: str, final: bool) -> float:
    strings = _card_strings(card)
    longest = max(len(text) for text in strings)
    hold = 1.15 + min(longest, 48) / 32 * 0.4 + max(0, len(strings) - 1) * 0.2
    if card["kind"] == "title":
        hold += 0.2
    if aspect_ratio in ("3:4", "9:16") and longest > 22:
        hold += 0.25
    if final:
        hold += 0.25
    return min(2.95, max(1.4, hold))


def plan_title_beats(cards: list[dict], duration: float, aspect_ratio: str, energy: str) -> list[tuple[float, float, str]]:
    validate_title_fit(cards, aspect_ratio)
    if energy not in TITLE_ENERGIES:
        raise ValueError(f"Unsupported title_sequence_energy: {energy}")
    opening = min(0.8, max(0.5, duration * 0.08))
    formation_min = {"restrained": 0.65, "balanced": 0.75, "spectacular": 0.9}[energy]
    settle = 0.2
    transition = 0.3
    holds = [_reading_hold(card, aspect_ratio, index == len(cards) - 1) for index, card in enumerate(cards)]
    minimums = [formation_min + settle + hold + (0 if index == len(cards) - 1 else transition)
                for index, hold in enumerate(holds)]
    required = opening + sum(minimums)
    if required > duration + 1e-6:
        minimum_duration = int(required + 0.999)
        remedy = (f"Use at least {minimum_duration} seconds or remove a card." if minimum_duration <= 150
                  else "Reduce the cards or split the sequence.")
        raise ValueError(
            f"{duration:g} seconds is too short for {len(cards)} title cards with readable holds. {remedy}"
        )

    beats = [(0.0, opening, "Establish the stage and material system with no visible text.")]
    extra = duration - required
    weights = [1.0 if card["kind"] == "credit" else 1.2 for card in cards]
    weights[-1] += 0.25
    weight_total = sum(weights)
    start = opening
    for index, (card, weight, hold_min, minimum) in enumerate(zip(cards, weights, holds, minimums), 1):
        card_extra = extra * weight / weight_total
        end = duration if index == len(cards) else start + minimum + card_extra
        formation_end = start + formation_min + card_extra * 0.55
        settle_end = formation_end + settle
        hold_end = settle_end + hold_min + card_extra * 0.45
        card_type = "main title" if card["kind"] == "title" else "credit"
        description = (
            f"Reveal CARD {index}, the {card_type}. Formation {start:.1f}-{formation_end:.1f}s: keep interim "
            f"shapes abstract and complete every glyph. Settle {formation_end:.1f}-{settle_end:.1f}s: finish "
            f"camera and material movement. Readable hold {settle_end:.1f}-{hold_end:.1f}s: freeze camera, focus, "
            "exposure, material, and lettering. "
        )
        description += ("Keep it locked through the final frame." if index == len(cards)
                        else f"Transition {hold_end:.1f}-{end:.1f}s through the same causal process.")
        beats.append((start, end, description))
        start = end
    return beats


def _quoted(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def format_cards(cards: list[dict]) -> str:
    sections = []
    for index, card in enumerate(cards, 1):
        if card["kind"] == "title":
            lines = "\n".join(
                f"Line {line_number} exactly: {_quoted(text)}"
                for line_number, text in enumerate(card["lines"], 1)
            )
            sections.append(f"CARD {index} - MAIN TITLE, ONE COMPOSITION\n{lines}")
        elif card["role"] is None:
            sections.append(f"CARD {index} - SINGLE-LEVEL CREDIT\nText exactly: {_quoted(card['name'])}")
        else:
            sections.append(
                f"CARD {index} - HIERARCHICAL CREDIT\nRole exactly: {_quoted(card['role'])}\n"
                f"Name exactly: {_quoted(card['name'])}\nShow role and name together in one composition and hold."
            )
    return "\n\n".join(sections)


def title_briefing(concept: str, recipe: str, energy: str, title: str, credits: str,
                   placement: str, duration: float, aspect_ratio: str) -> tuple[str, list[dict]]:
    if recipe not in TITLE_RECIPES:
        raise ValueError(f"Unsupported title_sequence_recipe: {recipe}")
    if energy not in TITLE_ENERGIES:
        raise ValueError(f"Unsupported title_sequence_energy: {energy}")
    cards = title_cards(title, credits, placement)
    beats = plan_title_beats(cards, float(duration), aspect_ratio, energy)
    ratio_direction = {
        "16:9": "Use a wide cinematic composition with generous lateral negative space.",
        "21:9": "Use protected central text and strong lateral rhythm within the ultra-wide frame.",
        "4:3": "Use a classical compact composition with balanced margins.",
        "1:1": "Use a compact centered composition and controlled line lengths.",
        "3:4": "Use a portrait-safe stacked hierarchy and generous vertical margins.",
        "9:16": "Use a strongly vertical hierarchy, short line measures, and a protected central safe area.",
        "auto": "Derive composition and safe areas from the connected workflow while protecting every line.",
    }.get(aspect_ratio, "Protect every supplied line inside safe margins.")
    sound = {"restrained": "restrained and precise", "balanced": "coherent and measured",
             "spectacular": "bold and dynamically scaled"}[energy]
    storyboard = "\n".join(f"{start:.1f}-{end:.1f}s: {text}" for start, end, text in beats)
    project = str(concept or "").strip() or "Create a premium cinematic title sequence with a coherent identity."
    briefing = (
        f"Create a {duration:g}-second MiniMax H3 cinematic titles and credits sequence in {aspect_ratio}.\n\n"
        f"PROJECT CONCEPT\n{project}\n\n"
        f"CREATIVE RECIPE - {recipe}\n{TITLE_RECIPES[recipe]}\n\n"
        f"ENERGY\n{TITLE_ENERGIES[energy]}\n\n"
        f"FRAME AND TYPOGRAPHIC FIT\n{ratio_direction} Adapt type scale, tracking, leading, and camera distance "
        "without changing, abbreviating, or rewrapping supplied text.\n\n"
        "EXACT ON-SCREEN TEXT\n"
        f"{format_cards(cards)}\n\n"
        f"TIMED STORYBOARD\n{storyboard}\n\n"
        "TITLE DIRECTION\nExpand each beat into a designed cinematic shot with material depth, foreground and "
        "background layers, motivated lighting, a purposeful camera path or deliberate locked state, and a stable "
        "near-frontal endpoint. Show one card at a time. Keep incomplete forms abstract: never cycle wrong letters, "
        "fake words, or invented symbols. Once formed, lettering stays sharp, unobscured, undistorted, and completely "
        "still for the specified hold. Never dissolve or exit the final card. Add no other visible writing.\n\n"
        f"AUDIO\nCreate a {sound} original sound world. Synchronize every mechanical or material sound to a visible "
        "cause and develop the score toward the main title. No dialogue or lyrics."
    )
    return briefing, cards


def append_title_lock(prompt: str, cards: list[dict]) -> str:
    return (
        f"{str(prompt).rstrip()}\n\nSTRICT ON-SCREEN TEXT LOCK - this overrides conflicting text above.\n\n"
        f"{format_cards(cards)}\n\nOnly those strings may appear as visible writing. Quotation marks are delimiters and "
        "must not be rendered. Preserve every character, case choice, punctuation mark, accent, and supplied title "
        "line break. Show one card at a time; a role and name remain together. Freeze completed lettering during "
        "every readable hold and keep the final composition through the last frame. Add no signage, captions, dates, "
        "logos, signatures, watermarks, or invented writing."
    )
