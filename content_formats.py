# SPDX-License-Identifier: GPL-3.0-only
"""Source-grounded production-format bibles for MiniMax H3 prompts.

Content formats describe what a short *does* and how its supplied information is
organized.  They are deliberately independent from genre, visual language,
world aesthetic, tone, cinematography, title styling, and H3 input mode.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any


CONTENT_FORMAT_CATALOG_VERSION = 1
CONTENT_FORMAT_DIMENSIONS = (
    "editing_and_pacing",
    "camera_and_framing",
    "lighting_and_color",
    "production_design",
    "blocking_and_performance",
    "sound_treatment",
    "may_fill_unspecified",
    "must_not_invent",
)


def _format(*, signature: str = "", editing_and_pacing=(), camera_and_framing=(),
            lighting_and_color=(), production_design=(), blocking_and_performance=(),
            sound_treatment=(), may_fill_unspecified=(), must_not_invent=(), version: int = 1):
    def items(value):
        return (value,) if isinstance(value, str) else tuple(value)

    return {
        "version": int(version),
        "signature": str(signature).strip(),
        **{name: items(locals_value) for name, locals_value in (
            ("editing_and_pacing", editing_and_pacing),
            ("camera_and_framing", camera_and_framing),
            ("lighting_and_color", lighting_and_color),
            ("production_design", production_design),
            ("blocking_and_performance", blocking_and_performance),
            ("sound_treatment", sound_treatment),
            ("may_fill_unspecified", may_fill_unspecified),
            ("must_not_invent", must_not_invent),
        )},
    }


CONTENT_FORMAT_PROFILES = {
    "none": _format(),
    "narrative_animation_short": _format(
        signature=("Organize only the supplied events as a compact causal short: establish the initial state, "
                   "make the supplied trigger or goal legible, stage each assigned action and response in order, "
                   "and hold the supplied consequence or payoff long enough to read while preserving continuity."),
        editing_and_pacing="Shape supplied events into initial state, supplied trigger or goal, ordered action and response, and supplied consequence; beats are emphasis, never automatic cuts.",
        camera_and_framing="Establish spatial context and change viewpoint only to clarify a supplied decision, contact, reaction, reveal, or consequence; preserve screen direction, eyelines, possession, and landmarks.",
        lighting_and_color="Maintain source-consistent light and color continuity while keeping actions, contact points, expressions, and resulting states readable.",
        production_design="Use only supplied or reference-bound environments, characters, props, materials, and continuity landmarks.",
        blocking_and_performance="Stage each supplied action as preparation, onset, contact or turning point, response, follow-through, and settled result without changing its count or order.",
        sound_treatment="Inside active audio gates, synchronize exact supplied speech and only permitted physically caused sound with its visible beat.",
        may_fill_unspecified="Relative beat emphasis, neutral orientation, screen direction, physical follow-through, continuity handoffs, and a short hold on an existing result.",
        must_not_invent="Goals, conflicts, obstacles, stakes, twists, reveals, outcomes, callbacks, characters, props, locations, cuts, dialogue, titles, music, a rendering medium, or animation traits.",
    ),
    "brand_promo": _format(
        signature=("Arrange the supplied brand or product facts as a concise cause-and-effect promotion: open on "
                   "a relevant hook, make one supplied action or mechanism and its supported result readable, then "
                   "settle on the supplied payoff and only when authorized the exact logo or call to action."),
        editing_and_pacing="Organize supplied campaign facts as hook, optional need or setup, readable interaction or mechanism, supported evidence or result, payoff, and exact authorized close; preserve explicit cuts and order.",
        camera_and_framing="Give each beat one supplied visual owner and frame only what is needed to read interaction, evidence, result, and exact copy.",
        lighting_and_color="Preserve explicit brand, product, UI, skin, and source-light colors while maintaining evidence and copy legibility.",
        production_design="Use only supplied or verified logo, UI, packaging, product, people, environments, and proof assets; no fake interface, chart, metric, variant, or branded set.",
        blocking_and_performance="Stage a readable supplied cause-and-effect chain with clear contacts and restrained reactions; add no spokesperson, testimonial, celebration, or use case.",
        sound_treatment="Inside active gates, synchronize only source-supported speech and physically caused product or UI sounds; no announcer, slogan, jingle, or triumphant hit.",
        may_fill_unspecified="Duration-aware beat timing, selection among supplied facts for the hook, readable holds, causal transition timing, and stable final composition.",
        must_not_invent="Brand facts, logos, UI, features, mechanisms, uses, proof, metrics, awards, prices, comparisons, testimonials, slogans, claims, CTA wording, disclaimers, dialogue, narration, or music.",
    ),
    "co_op_game_intro": _format(
        signature=("Stage a two-player cooperative game opening as one readable state progression: establish both "
                   "distinct player slots, make one supplied readiness or configuration change legible for each, "
                   "converge on one joint confirmation, and end together in the supplied final state."),
        editing_and_pacing="Organize only the supplied sequence as shared establishment, one legible state for each of two players, one joint commit, and one shared payoff; merge beats rather than omit a player.",
        camera_and_framing="Keep both identity-to-slot mappings and shared interface geography legible; return to a joint composition for the payoff.",
        lighting_and_color="Maintain readable separation between both players, interface states, and background while preserving the supplied palette.",
        production_design="Keep one coherent source-compatible menu or HUD system whose hierarchy, placement, exact text, and state changes remain continuous.",
        blocking_and_performance="Stage two distinct supplied participants with stable slots, individually readable readiness behavior, and one causally shared confirmation.",
        sound_treatment="When permitted, synchronize restrained interface navigation, state-change, confirmation, and transition sounds only with visible events.",
        may_fill_unspecified="Stable screen-side assignment, neutral idle reactions, order of readiness, nonlexical feedback, and fallback beat allocation.",
        must_not_invent="A third player, names, titles, menu copy, equipment, weapons, powers, missions, gameplay, world details, dialogue, narration, music, branding, or logos.",
    ),
    "handdrawn_live_fusion": _format(
        signature=("Maintain one photographed host layer and one visibly hand-drawn 2D entity layer in the same "
                   "space, with coherent shared scale, depth, occlusion, motion, and contact; preserve the same "
                   "entity through every continuous morph by a persistent trace."),
        editing_and_pacing="Use a continuous causal progression: establish both supplied layers, make contact legible, preserve a trace through supplied transformation, and settle in a shared spatial state; do not add cuts.",
        camera_and_framing="Keep the contact and both layers legible; let the drawn entity lead any compatible camera response, subject to explicit cinematography.",
        lighting_and_color="Preserve source lighting and colors and add only local separation needed to read the two layers; do not infer glow or emission.",
        production_design="Co-register scale, perspective, depth, and occlusion on existing surfaces; create no route, prop, or location.",
        blocking_and_performance="Preserve the same supplied entity and trace through approach, contact, response, release, and settled result; human participation requires source authority.",
        sound_treatment="Use only policy-permitted room tone and physically present manipulation or contact sounds; no magical or cartoon sound.",
        may_fill_unspecified="Timing, a contact point on a supplied anchor, an abstract nonsemantic trace, a short route across contiguous existing surfaces, and compatible occlusion.",
        must_not_invent="Hands, people, objects, locations, creatures, semantic forms, glow, light or sound sources, cuts, spatial jumps, jokes, or a replacement entity.",
    ),
    "minimalist_product_ad": _format(
        signature=("Organize the supplied physical product as an immediate exact-product establishment, "
                   "source-supported detail or interaction beats scaled to the duration, and a stable product "
                   "close; preserve every supplied product, brand, claim, and visible-copy fact exactly."),
        editing_and_pacing="Use immediate product establishment, one primary supplied fact or action per beat, readable holds, and a stable product close; beats do not require cuts.",
        camera_and_framing="Keep the exact supplied product as visual owner and reveal only its supported form, material, marking, action, or variant; do not impose macro, symmetry, or negative space.",
        lighting_and_color="Add no palette or lighting style; preserve authoritative product, packaging, label, logo, and variant colors.",
        production_design="Preserve exact geometry, proportions, packaging, controls, markings, typography, and materials; create no campaign world or support object.",
        blocking_and_performance="Show a complete plausible interaction only when authorized; otherwise keep the product unhandled and add no hands, actors, presenters, or demonstrations.",
        sound_treatment="Use only policy-permitted sound physically caused by supplied product actions; no voice-over, slogan, sonic logo, or advertising music.",
        may_fill_unspecified="Beat allocation among supplied details, hold length, shot scale, continuity, product-dominant composition, and restrained caused foley.",
        must_not_invent="Product identity, geometry, color, variant, feature, use, benefit, claim, metric, price, offer, logo, copy, CTA, spokesperson, demonstration, voice-over, or music.",
    ),
    "lyric_music_video": _format(
        signature=("Render the supplied material as a lyric-led music video, timing existing action and exact "
                   "source-authorized lyric typography to supplied musical phrasing and accents, with readable "
                   "spatial text, protected faces, and one coherent typography-motion system."),
        editing_and_pacing="Inside authorized boundaries, shape supplied music and exact lyrics into readable phrase events with entrance, hold, exit, and settlement; rhythmic emphasis creates no cut or lyric occurrence.",
        camera_and_framing="Compose existing subjects and authorized lyric typography together with readable space and protected faces; require mouth coverage only for authorized on-camera vocals.",
        lighting_and_color="Use source-compatible exposure and separation for lyric readability without inventing flashes, palette, or light sources.",
        production_design="Treat authorized lyric text as a spatial graphic layer whose wording remains exact and whose typography follows only supplied direction.",
        blocking_and_performance="For authorized vocals, coordinate existing mouth, jaw, breath, gaze, and gesture with the exact supplied line without adding choreography.",
        sound_treatment="Use only an explicitly identified permitted master track, preserving its window, order, vocal source, words, and accents; do not remix or replace it.",
        may_fill_unspecified="Phrase-level staging, readable text timing and placement, non-narrative emphasis on supplied accents, and typography-motion continuity.",
        must_not_invent="Lyrics, translations, captions, titles, credits, logos, performers, instruments, music, BPM, drops, cuts, locations, wardrobe, choreography, VFX, or a forced music-video look.",
    ),
    "progressive_metaphor_explainer": _format(
        signature=("Organize only the supplied concept as a progressive visual explanation: establish one readable "
                   "idea, reveal source-grounded elements in meaningful order, make their relationship unmistakable, "
                   "and settle on a concise comprehension hold."),
        editing_and_pacing="Use progressive semantic disclosure and comprehension pauses; rhetorical beats never authorize cuts.",
        camera_and_framing="Maintain a clear hierarchy and stable relational geography without forcing tabletop, macro, or top-down views.",
        lighting_and_color="Use clarity and separation only; preserve supplied palette and light sources and add no material default.",
        production_design="Use source-grounded explanatory components; a nonfactual metaphorical carrier is allowed only when the source requests metaphor.",
        blocking_and_performance="Introduce supplied components in meaningful order, complete their authorized contacts or changes, and settle the resolved relationship.",
        sound_treatment="The format grants no audio; permitted foley must follow a visible authorized cause.",
        may_fill_unspecified="Grouping, emphasis, reveal order, a neutral requested-metaphor carrier, timing, hierarchy, and final hold.",
        must_not_invent="Claims, causal links, examples, statistics, authorities, terminology, labels, copy, narrator, dialogue, CTA, cuts, soundtrack, or material style.",
    ),
    "mechanism_explainer": _format(
        signature=("Arrange only supplied explanatory content as a readable initial state, relevant part or cause, "
                   "visible operation or state change, and supplied outcome, with one causal step per beat and a "
                   "hold after each information-bearing state."),
        editing_and_pacing="Arrange supplied content as initial state, cause or part, operation or state change, and outcome; one causal step per beat, never an automatic cut.",
        camera_and_framing="Maintain stable explanatory geography and show the existing whole and relevant detail only within authorized boundaries.",
        lighting_and_color="Prioritize stable figure-ground and state legibility without inventing semantic color coding, palette, or light source.",
        production_design="Arrange supplied subjects and parts as a legible model, diagram, or demonstration space without selecting a rendering medium.",
        blocking_and_performance="Give supplied parts and actions a clear setup, actuation, response, and settle cycle; add no host, pointing gesture, or personification.",
        sound_treatment="The format authorizes no sound; permitted sound must be restrained, caused, and synchronized to a visible supplied action.",
        may_fill_unspecified="Causal emphasis, pause length, stable geography, state-to-state legibility, and result-hold duration.",
        must_not_invent="Facts, intermediate steps, causality, parts, arrows, labels, numbers, hosts, props, dialogue, narration, music, SFX, results, or a papercraft medium.",
    ),
    "general_educational_explainer": _format(
        signature=("Present the supplied explanation as a concise learning arc that establishes the topic, maps "
                   "each source-supported idea to a stable visual anchor, develops the relationships in cumulative "
                   "order, and gives the supplied takeaway a clear comprehension hold."),
        editing_and_pacing="Build a cumulative learning arc from orientation through supplied relationships to a supplied takeaway; information beats never create cuts.",
        camera_and_framing="Establish the whole and stable relationships before relevant detail, using only compatible reframing to clarify the supplied explanation.",
        lighting_and_color="Maintain clear figure-ground and stable grouping, preserve authoritative colors, and attach no unsupplied meaning to color.",
        production_design="Keep supplied subjects, objects, environments, diagrams, and exact copy legible and consistently mapped without adding explanatory props or labels.",
        blocking_and_performance="Align a supplied presenter with the current element; otherwise explain through supplied states and relationships without inventing a host.",
        sound_treatment="When allowed, keep authorized narration intelligible and synchronize only physically caused sound; the format grants no narrator or music.",
        may_fill_unspecified="Order among supplied propositions, visual hierarchy, stable mapping, neutral transitions, framing emphasis, and comprehension holds.",
        must_not_invent="Facts, definitions, mechanisms, claims, statistics, dates, examples, conclusions, research, citations, labels, diagrams, presenters, narration, steps, metaphors, titles, CTA, or music.",
    ),
    "product_demo_tutorial": _format(
        signature=("Stage only the assigned source-supported task span: begin on its concrete incoming product "
                   "state, show every assigned operation once in exact order as a readable contact or control "
                   "followed by its observable state change, and hold on its outgoing verification state."),
        editing_and_pacing="Use concrete pre-state, supplied operations in exact order, observable verification, and settled end state; add no intro, unboxing, montage, recap, hero reveal, or sales beat.",
        camera_and_framing="Keep orientation, contact, exact control, and resulting state readable; use inserts only when functionally necessary and allowed by the shot plan.",
        lighting_and_color="Preserve accurate product, material, UI, indicator, and reference colors; clarity outranks advertising gloss.",
        production_design="Preserve exact geometry, controls, labels, ports, UI, accessories, and workspace; add no tool, consumable, or campaign set.",
        blocking_and_performance="Use precise neutral operation with readable contact and state change; no spokesperson flourish or endorsement gesture.",
        sound_treatment="Use only policy-authorized, source-supported handling or device feedback; narration, tutorial patter, music, and sonic branding require explicit authority.",
        may_fill_unspecified="Shot scale, placement, focus, timing, holds, continuity, hand placement, and directly caused foley around existing steps.",
        must_not_invent="Functions, steps, controls, settings, quantities, accessories, ingredients, safety advice, verification messages, claims, captions, arrows, UI copy, narration, music, CTA, logo, or slogan.",
    ),
    "cinematic_teaser": _format(
        signature=("The sequence opens on an already-supplied visual or action, progressively releases only "
                   "source-authorized information, and ends on a concise hold on an already-authorized beat without "
                   "adding plot, copy, titles, dialogue, cuts, or sound sources."),
        editing_and_pacing="Use a compact information arc of supplied hook, progressive disclosure, and authorized closing hold; never create a trailer montage or automatic edit.",
        camera_and_framing="Use a readable supplied opening anchor, progressive attention, and final hold while explicit cinematography remains authoritative.",
        lighting_and_color="Add only source-compatible legibility and emphasis; do not force darkness, flashes, palette shifts, or a blockbuster grade.",
        production_design="Reuse existing locations, objects, and brand assets as anchors; add no symbol, prop, logo, or set.",
        blocking_and_performance="Clarify supplied action and reaction without adding heroic, threatening, romantic, or hype performance.",
        sound_treatment="Shape only audio already permitted; no automatic riser, boom, hit, ticking, whoosh, narration, or score.",
        may_fill_unspecified="Relative beat duration, attention order among supplied facts, brief holds, and compatible intra-shot emphasis.",
        must_not_invent="Plot, stakes, conflict, mystery, twist, spoiler, climax, outcome, tagline, CTA, claim, title, text, logo, dialogue, sound source, cut, transition, or spectacle.",
    ),
    "interview_mini_profile": _format(
        signature=("Shape the supplied material as a concise source-led interview mini-profile: keep every assigned "
                   "exact soundbite intact and attributable, use restrained speaker coverage, and place only "
                   "supplied context in already authorized cutaways."),
        editing_and_pacing="Center existing authorized coverage on the complete attributed soundbite; use only source- or shot-plan-authorized cutaways.",
        camera_and_framing="Use clear restrained speaker coverage and a source-consistent eyeline; frame only supplied context in authorized cutaways.",
        lighting_and_color="Keep the face legibly exposed with source-consistent practical light and contained grading; infer no glamour, archive, or era.",
        production_design="Use only supplied location, objects, wardrobe, and exact text; biography or occupation authorizes no set, uniform, tools, awards, or lower third.",
        blocking_and_performance="Use natural delivery, pauses, and restrained gestures; add no interviewer, question, reaction, or biographical behavior.",
        sound_treatment="Keep the stable speaker or audio label, language, and exact dialogue once with source-consistent room perspective; audio gates remain absolute.",
        may_fill_unspecified="Scale, distance, focus, neutral eyeline, pause length, and sound perspective among already supplied details.",
        must_not_invent="Quotes, transcript, identity, biography, profession, employer, achievements, dates, location, B-roll, archive, interviewer, questions, narration, lower thirds, logos, audio, or music.",
    ),
    "performance_music_video": _format(
        signature=("Cut complementary coverage of the source-authorized performance to audible phrase boundaries "
                   "and accents in the supplied continuous master audio. Maintain exact performer identity, role, "
                   "action, lip-and-hand synchronization, and continuity across every handoff."),
        editing_and_pacing="Use one permitted continuous master as the clock and align existing performance coverage to supplied phrase boundaries and accents; explicit shot boundaries win.",
        camera_and_framing="Use complementary coverage of the same supplied performance while preserving geography, screen direction, faces, mouths, hands, and contacts.",
        lighting_and_color="Preserve source exposure and colors for skin, wardrobe, instrument, and venue; add no strobe, concert light, or chromatic change.",
        production_design="Use only supplied venue, stage, equipment, instruments, microphones, props, and audience; cutaways require existing elements.",
        blocking_and_performance="Lock identity, count, role, wardrobe, ownership, and handedness; synchronize only authorized singing, playing, dancing, or action.",
        sound_treatment="Preserve the permitted master signal, timing, mix, vocal, and exact lyrics; do not remix, loop, stretch, transpose, replace, or add crowd sound.",
        may_fill_unspecified="Compatible coverage order, framing, focus timing at supplied accents, continuity staging, breath, gaze, balance, and neutral connective movement.",
        must_not_invent="Song, lyrics, BPM, arrangement, instruments, performance roles, performers, crowd, stage, microphones, choreography, costumes, applause, pyrotechnics, VFX, or visible instruments inferred from audio.",
    ),
    "seamless_loop": _format(
        signature=("Design the supplied action as a seamless audiovisual loop whose ending restores the exact "
                   "opening composition, subject pose and motion phase, object states, camera state, lighting, and "
                   "permitted audio phase without inserting an unrelated reset event."),
        editing_and_pacing="Plan backward from the supplied opening state so the final state and motion phase converge continuously; use no hidden cut or unrelated reset event.",
        camera_and_framing="Return exact framing, camera position, orientation, focal state, and authorized movement phase to the opening values at the endpoint.",
        lighting_and_color="Keep illumination, exposure, color, shadows, and practical-source states temporally continuous across the seam.",
        production_design="Restore every supplied object, prop, interface, surface, and environmental state required at the opening without disappearance or substitution.",
        blocking_and_performance="Use cyclic movement whose final pose, gaze, contact, balance, and velocity phase match the opening while preserving the supplied action.",
        sound_treatment="When audio is allowed, align ambience and physically caused sound so waveform-scale phase is not claimed; use perceptually compatible tail-to-head cadence without inventing a source.",
        may_fill_unspecified="Cycle timing, neutral recovery motion within the supplied action, endpoint hold length, and perceptually compatible audio cadence.",
        must_not_invent="A reset gesture, occluder, flash, blink, camera whip, object, action, sound, cut, transition, reverse playback, morph, disappearance, duplicate subject, or story event merely to conceal the seam.",
    ),
}


def content_format_choices() -> tuple[str, ...]:
    return tuple(CONTENT_FORMAT_PROFILES)


def _digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_content_format(name: str, *, enabled: bool, source_prompt: str,
                           voice_performance: str, background_score_policy: str,
                           mode: str) -> dict[str, Any]:
    selected = str(name or "none").strip().lower()
    if selected not in CONTENT_FORMAT_PROFILES:
        raise ValueError(
            f"Unsupported content format {selected!r}; choose one of: "
            + ", ".join(CONTENT_FORMAT_PROFILES)
        )
    profile = CONTENT_FORMAT_PROFILES[selected]
    requested = selected != "none"
    reason = ""
    if requested and not enabled:
        reason = "description_enhancement_disabled"
    source = str(source_prompt or "")
    if requested and enabled and selected == "interview_mini_profile":
        if voice_performance != "audible":
            reason = "audio_policy_conflict"
        elif not re.search(r'["“][^"”]+["”]|<d>\[[^]]+\].+?</d>', source, re.IGNORECASE):
            reason = "missing_attributed_soundbite"
    if requested and enabled and selected in {"lyric_music_video", "performance_music_video"}:
        if background_score_policy == "off":
            reason = "audio_policy_conflict"
    applied = requested and enabled and not reason
    dimensions = {
        key: list(dict.fromkeys(str(item).strip() for item in profile[key] if str(item).strip()))
        if applied else []
        for key in CONTENT_FORMAT_DIMENSIONS
    }
    canonical = {"contentFormat": selected}
    payload = {
        "catalogVersion": CONTENT_FORMAT_CATALOG_VERSION,
        "selection": canonical,
        "profileVersion": int(profile["version"]),
        "signature": profile["signature"],
        "dimensions": dimensions,
    }
    return {
        "schemaVersion": 1,
        "catalogVersion": CONTENT_FORMAT_CATALOG_VERSION,
        "contentFormat": selected,
        "requested": requested,
        "applied": applied,
        "notAppliedReason": reason,
        "profileId": f"content_format:{selected}" if requested else "",
        "profileVersion": int(profile["version"]),
        "signature": profile["signature"] if applied else "",
        "dimensions": dimensions,
        "digest": _digest(payload),
        "canonicalJson": json.dumps(canonical, sort_keys=True, separators=(",", ":")),
        "mode": str(mode),
    }


def content_format_instruction(resolved: Mapping[str, Any]) -> str:
    if not resolved.get("applied"):
        return ""
    headings = {
        "editing_and_pacing": "INFORMATION ARCHITECTURE AND PACING",
        "camera_and_framing": "CAMERA AND FRAMING",
        "lighting_and_color": "LIGHTING AND COLOR",
        "production_design": "PRODUCTION DESIGN",
        "blocking_and_performance": "BLOCKING AND PERFORMANCE",
        "sound_treatment": "SOUND TREATMENT",
        "may_fill_unspecified": "MAY FILL ONLY WHEN UNSPECIFIED",
        "must_not_invent": "MUST NOT INVENT",
    }
    lines = [
        "SOURCE-GROUNDED CONTENT / PRODUCTION FORMAT — STRUCTURE, NOT LOOK:",
        "Apply the fully expanded production bible below without emitting its preset name or ID. It organizes only "
        "facts, actions, text, references, and audio already authorized by the source. It never chooses a visual "
        "medium, genre, world, tone, palette, camera preset, title, dialogue, music, fact, claim, or story event.",
        "Source and reference facts, exact text/dialogue, media roles, audio gates, explicit shot rows and timing, "
        "and explicit cinematography remain authoritative. Format beats are information emphasis, not permission "
        "to create, delete, merge, or reorder cuts. Translate every compatible directive into observable prompt "
        "wording; do not merely name the format.",
    ]
    if str(resolved.get("mode")) == "chained_multishot":
        first, middle, last = content_format_signatures(resolved, 3)
        lines.extend((
            "CHAINED ROLE LOCKS — use exactly one applicable sentence per autonomous item; do not repeat the "
            "whole format arc inside every item:",
            "- First item: " + first,
            "- Each middle item: " + middle,
            "- Final item: " + last,
        ))
    else:
        lines.extend((
            "CANONICAL DELIVERY LOCK — include this exact declarative sentence in the visual timeline:",
            str(resolved["signature"]),
        ))
    for key in CONTENT_FORMAT_DIMENSIONS:
        values = resolved.get("dimensions", {}).get(key, ())
        if values:
            lines.append(headings[key] + ":")
            lines.extend(f"- {item}" for item in values)
    return "\n".join(lines)


_CHAINED_ROLE_SIGNATURES = {
    "narrative_animation_short": (
        "Establish only the supplied opening state and first assigned causal beat, ending on a concrete handoff state.",
        "Inherit the exact prior state, advance only this segment's assigned supplied causal beat, and end on a concrete handoff state.",
        "Inherit the exact prior state, complete only the remaining supplied causal beat, and hold the supplied ending long enough to read.",
    ),
    "brand_promo": (
        "Establish the supplied promotional owner and hook without introducing a claim, logo, or call to action absent from the source.",
        "Advance exactly one assigned supplied mechanism, capability, result, or evidence beat and end in a concrete handoff state.",
        "Complete the supplied evidence or payoff and use the exact logo or call to action only when it is explicitly authorized.",
    ),
    "cinematic_teaser": (
        "Open on one already-supplied visual or action and release only the first assigned source-authorized information.",
        "Inherit the prior state and release only this segment's distinct assigned source-authorized information without resolving hidden facts.",
        "Complete only the remaining authorized disclosure and end on a concise hold on an already-authorized beat without adding title, copy, plot, or sound.",
    ),
    "lyric_music_video": (
        "Establish the supplied master-audio identity and render only this first assigned exact lyric window with readable authorized typography.",
        "Use the next contiguous supplied master-audio window and only its assigned exact lyrics, preserving typography and visual continuity.",
        "Use the final contiguous supplied master-audio window and exact assigned lyrics, then settle the authorized typography and visual endpoint.",
    ),
    "performance_music_video": (
        "Establish the supplied continuous master and exact performer identities, roles, actions, and ownership in the first assigned audio window.",
        "Use the next contiguous supplied master-audio window and complementary coverage of only the assigned authorized performance.",
        "Use the final contiguous supplied master-audio window, preserve exact performance synchronization, and settle on the supplied endpoint.",
    ),
    "seamless_loop": (
        "Establish the exact global loop opening: composition, subjects, object states, camera, lighting, motion phase, and permitted audio state.",
        "Inherit the exact prior state and advance the supplied action without resetting, self-looping, or duplicating the global opening.",
        "Inherit the exact prior state and converge on the first segment's exact global opening state and phase without a reset, cut, fade, occlusion, flash, or added sound cue.",
    ),
}


def content_format_signatures(resolved: Mapping[str, Any], count: int) -> list[str]:
    """Return autonomous-item locks without making every chained item a full arc."""
    total = max(0, int(count))
    if not resolved.get("applied") or total == 0:
        return []
    name = str(resolved.get("contentFormat", "none"))
    roles = _CHAINED_ROLE_SIGNATURES.get(name)
    if not roles or total == 1:
        return [str(resolved.get("signature", ""))] * total
    first, middle, last = roles
    return [first if index == 0 else last if index == total - 1 else middle for index in range(total)]
