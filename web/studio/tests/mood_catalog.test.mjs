import assert from "node:assert/strict";
import test from "node:test";

import { MOOD_DESCRIPTIONS, MOOD_GROUPS, moodChoiceGroups } from "../mood_catalog.js";

const CHOICES = [
    ["none", "No preference"], ["epic", "Epic"], ["intimate", "Intimate"], ["dark", "Dark"],
    ["tense", "Tense"], ["hopeful", "Hopeful"], ["melancholic", "Melancholic"], ["playful", "Playful"],
    ["restrained", "Restrained"], ["serene", "Serene"], ["eerie", "Eerie"], ["whimsical", "Whimsical"],
    ["surreal", "Surreal"], ["clinical", "Clinical"], ["raw", "Raw"], ["kinetic", "Kinetic"],
    ["pulp_heightened", "Heightened (pulp)"], ["stoic", "Stoic"],
];

test("Mood taxonomy covers the frontend catalog exactly once with visible descriptions", () => {
    const taxonomyTokens = ["none", ...MOOD_GROUPS.flatMap(([, tokens]) => tokens)];
    assert.deepEqual(new Set(taxonomyTokens), new Set(CHOICES.map(([token]) => token)));
    assert.equal(taxonomyTokens.length, new Set(taxonomyTokens).size);
    for (const [token] of CHOICES) assert.ok(MOOD_DESCRIPTIONS[token]?.length > 20, `${token} has useful option copy`);
    const groups = moodChoiceGroups(CHOICES, "none");
    assert.equal(groups[0].group, "");
    assert.equal(groups[0].choices[0].token, "none");
});

test("Mood search indexes labels, tokens, groups and guardrail descriptions", () => {
    for (const query of ["pulp", "heightened"]) {
        const matches = moodChoiceGroups(CHOICES, "none", query).flatMap(({ choices }) => choices);
        assert.deepEqual(matches.map(({ token }) => token), ["pulp_heightened"]);
    }
    assert.deepEqual(
        moodChoiceGroups(CHOICES, "none", "hospital").flatMap(({ choices }) => choices).map(({ token }) => token),
        ["clinical"],
    );
    assert.deepEqual(
        moodChoiceGroups(CHOICES, "none", "energy scale").flatMap(({ choices }) => choices).map(({ token }) => token),
        ["epic", "kinetic", "pulp_heightened"],
    );
});

test("Unknown Mood values stay visible and searchable until explicitly replaced", () => {
    const unknown = moodChoiceGroups(CHOICES, "future_mood");
    const current = unknown.find(({ group }) => group === "Current workflow")?.choices[0];
    assert.deepEqual(current, {
        token: "future_mood",
        label: "Unavailable — future_mood",
        description: "Stored value is not in this version's catalog; it remains unchanged until you choose another mood.",
    });
    assert.equal(moodChoiceGroups(CHOICES, "future_mood", "future mood")[0].choices[0].token, "future_mood");
});
