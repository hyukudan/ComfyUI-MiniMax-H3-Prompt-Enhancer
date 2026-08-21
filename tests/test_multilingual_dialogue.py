# SPDX-License-Identifier: GPL-3.0-only

import json
import pytest

from prompt_guides import (
    _detect_language,
    _source_dialogue_contracts,
    _extract_source_quotes,
    build_user_request,
    DIALOGUE_LANGUAGE_CHOICES,
    SYSTEM_PROMPT,
)
import prompt_enhancer
from prompt_enhancer_node import (
    MiniMaxH3PromptValidator,
)


def test_dialogue_language_choices_catalog_includes_all_h3_languages():
    expected = [
        "auto", "Spanish", "English", "French", "German", "Italian",
        "Portuguese", "Japanese", "Chinese", "Korean", "Russian",
        "Arabic", "Cantonese", "Catalan", "Dutch", "Polish", "Turkish", "Hindi",
    ]
    for lang in expected:
        assert lang in DIALOGUE_LANGUAGE_CHOICES


@pytest.mark.parametrize("text,expected", [
    ("Un científico que explica la física cuántica", "Spanish"),
    ("Un cientifico que explica la teoria de cuerdas", "Spanish"),
    ("Un scientifique qui explique la physique", "French"),
    ("Ein Wissenschaftler der die Quantenphysik erklärt", "German"),
    ("Uno scienziato che spiega la fisica quantistica", "Italian"),
    ("Um cientista que explica a física quântica", "Portuguese"),
    ("Un científic que explica la física quàntica", "Catalan"),
    ("A scientist who explains quantum physics", "English"),
    ("量子力学を説明する科学者", "Japanese"),
    ("양자 물리학을 설명하는 과학者", "Korean"),
    ("解释量子物理学的科学家", "Chinese"),
    ("解釋廣東話量子力學嘅科學家", "Cantonese"),
    ("Ученый объясняет квантовую физику", "Russian"),
    ("عالم يشرح فيزياء الكم", "Arabic"),
])
def test_detect_language_identifies_major_languages_with_and_without_diacritics(text, expected):
    assert _detect_language(text) == expected


def test_multilingual_quotes_extraction_handles_european_and_asian_brackets():
    text = (
        'English "Hello", French «Bonjour», German „Guten Tag“, '
        'Japanese 「こんにちは」, Chinese 『你好』.'
    )
    extracted = _extract_source_quotes(text)
    assert extracted == ["Hello", "Bonjour", "Guten Tag", "こんにちは", "你好"]


def test_spanish_unaccented_dialogue_is_detected_and_canonically_tagged():
    source = 'Un hombre que habla de fisica dice "Hola amigos, bienvenidos al laboratorio".'
    contracts = _source_dialogue_contracts(source)
    assert contracts == [("Spanish", "Hola amigos, bienvenidos al laboratorio", False)]

    request = build_user_request(source, "t2va", 5.0)
    assert "<d>[Spanish] Hola amigos, bienvenidos al laboratorio</d>" in request
    assert "strictly in English" in SYSTEM_PROMPT


def test_french_guillemets_dialogue_is_detected_and_canonically_tagged():
    source = 'Un détective entre et dit «Ne bougez pas, la police arrive».'
    contracts = _source_dialogue_contracts(source)
    assert contracts == [("French", "Ne bougez pas, la police arrive", False)]

    request = build_user_request(source, "t2va", 5.0)
    assert "<d>[French] Ne bougez pas, la police arrive</d>" in request


def test_german_dialogue_is_detected_and_canonically_tagged():
    source = 'Ein Polizist kommt herein und sagt „Bleiben Sie stehen!“.'
    contracts = _source_dialogue_contracts(source)
    assert contracts == [("German", "Bleiben Sie stehen!", False)]

    request = build_user_request(source, "t2va", 5.0)
    assert "<d>[German] Bleiben Sie stehen!</d>" in request


def test_japanese_dialogue_is_detected_and_canonically_tagged():
    source = '侍が刀を構えて「覚悟しろ」と言う。'
    contracts = _source_dialogue_contracts(source)
    assert contracts == [("Japanese", "覚悟しろ", False)]

    request = build_user_request(source, "t2va", 5.0)
    assert "<d>[Japanese] 覚悟しろ</d>" in request


def test_chinese_dialogue_is_detected_and_canonically_tagged():
    source = '将军拔出宝剑大喊『冲锋！』。'
    contracts = _source_dialogue_contracts(source)
    assert contracts == [("Chinese", "冲锋！", False)]

    request = build_user_request(source, "t2va", 5.0)
    assert "<d>[Chinese] 冲锋！</d>" in request


def test_dialogue_language_widget_override_overrules_auto_detection():
    source = 'A man speaks into a microphone "Hello world".'
    # Force Spanish via widget override
    contracts = _source_dialogue_contracts(source, override_language="Spanish")
    assert contracts == [("Spanish", "Hello world", False)]

    request = build_user_request(source, "t2va", 5.0, dialogue_language="Spanish")
    assert "<d>[Spanish] Hello world</d>" in request


def test_prompt_enhancer_manifest_records_detected_or_requested_dialogue_language():
    source = 'Un científico dice "Hola mundo". No music.'
    omitted = """integrated_multimodal_description:
[Shot 1] Live-action, a scientist in a laboratory opens the experiment chamber. The scientist (S1) delivers the line: <d>[Spanish] Hola mundo</d>.

overall_soundscape:
Lab equipment hums quietly.

non_diegetic_music:
N/A"""
    result, validation, manifest = prompt_enhancer.enhance_prompt_with_completion(
        source, "t2va", 5.0, "", lambda _messages: omitted, 0, {"provider": "test"},
        dialogue_language="auto",
    )
    assert "<d>[Spanish] Hola mundo</d>" in result
    assert validation["valid"]
    assert manifest["dialogueLanguage"] == "Spanish"


def test_validator_node_accepts_valid_multilingual_prompt_with_dialogue_language_widget():
    source = 'Un détective dit «Arrêtez-vous!».'
    prompt = """integrated_multimodal_description:
[Shot 1] Live-action, a detective in a trench coat draws a flashlight in a dark corridor. The detective (S1) shouts: <d>[French] Arrêtez-vous!</d>.

overall_soundscape:
Echoing footsteps on wet pavement.

non_diegetic_music:
N/A"""
    node = MiniMaxH3PromptValidator()
    result = node.validate(prompt, "t2va", 5.0, source, "", dialogue_language="French")
    normalized, valid, report_json = result["result"]
    report = json.loads(report_json)
    assert valid is True
    assert report["valid"] is True
    assert report["errors"] == []


@pytest.mark.parametrize("prompt_text,expected_lang", [
    ('Dice en castellano: "Buenos días"', "Spanish"),
    ('Dice en español de españa: "Hoy no, gracias"', "Spanish"),
    ('Dice en español latino: "¿Cómo estás, amigo?"', "Spanish"),
    ('Diu en valencià: "Bon dia"', "Catalan"),
    ('Dit en québécois: "Bonjour tout le monde"', "French"),
    ('Sagt auf österreichischem Deutsch: "Guten Tag"', "German"),
    ('Diz em português do brasil: "Tudo bem?"', "Portuguese"),
    ('Says in mandarin chinese: "你好"', "Chinese"),
    ('Says in yue cantonese: "早晨"', "Cantonese"),
    ('Zegt in het vlaams: "Goededag"', "Dutch"),
])
def test_dialect_and_regional_variants_resolve_to_canonical_h3_languages(prompt_text, expected_lang):
    contracts = _source_dialogue_contracts(prompt_text)
    assert contracts[0][0] == expected_lang


def test_audio_reference_binding_to_character_in_spanish_and_english():
    from prompt_guides import _official_reference_model

    source1 = 'En imagen 1 una mujer rubia, en imagen 2 un hombre moreno. La mujer habla con la voz de audio 1 y el hombre con audio 2.'
    model1 = _official_reference_model(source1)
    audio1_def = next(d for d in model1["definitions"] if d["label"] == "<Audio 1>")
    audio2_def = next(d for d in model1["definitions"] if d["label"] == "<Audio 2>")
    assert "<Subject 1> (S1)" in audio1_def["line"]
    assert "<Subject 2> (S2)" in audio2_def["line"]

    source2 = 'The character in image 1 has audio 1 as his voice.'
    model2 = _official_reference_model(source2)
    audio_def2 = next(d for d in model2["definitions"] if d["label"] == "<Audio 1>")
    assert "<Subject 1> (S1)" in audio_def2["line"]

    source3 = 'El personaje de imagen 1 usa el audio 1 para su voz.'
    model3 = _official_reference_model(source3)
    audio_def3 = next(d for d in model3["definitions"] if d["label"] == "<Audio 1>")
    assert "<Subject 1> (S1)" in audio_def3["line"]


def test_visible_text_on_door_sign_not_confused_with_spoken_dialogue():
    from prompt_guides import normalize_source_dialogue

    source = (
        'The man enters a prostitute bar with a big title card on the door saying "XYZ bar". '
        'Inside, a woman approaches him and says in spanish from Spain "hola, cariño, quieres un baile privado". '
        'He says "hoy no, gracias". Then a huge hammer with "1T" written on it hits his head.'
    )
    contracts = _source_dialogue_contracts(source)
    assert len(contracts) == 2
    assert contracts[0] == ("Spanish", "hola, cariño, quieres un baile privado", False)
    assert contracts[1] == ("Spanish", "hoy no, gracias", False)

    mock_llm_output = (
        "detailed_description:\n"
        '[Shot 1] The sign on the door reads <d>[Original language] XYZ bar</d>. '
        'The woman (S1) says <d>[Spanish] hola, cariño, quieres un baile privado</d>. '
        'The man (S2) replies <d>[Spanish] hoy no, gracias</d>.\n\n'
        "overall_soundscape:\n"
        "Ambience in bar.\n\n"
        "non_diegetic_music:\n"
        "N/A"
    )
    normalized = normalize_source_dialogue(mock_llm_output, source, "ref2va")
    assert '[Original language]' not in normalized
    assert '"XYZ bar"' in normalized or "XYZ bar" in normalized
    assert '<d>[Original language] XYZ bar</d>' not in normalized




SHORT_DIALOGUE_CORPUS = [
    # The <d> line that exposed the bug: "no" belonged to Portuguese only, so one shared
    # function word decided a Spanish line and H3 would have voiced it with Portuguese phonetics.
    ("No pienso decir nada.", "Spanish"),
    ("Se donde estuviste esa noche.", "Spanish"),
    ("No me lo esperaba.", "Spanish"),
    ("No puedo mas.", "Spanish"),
    ("No quiero hablar contigo.", "Spanish"),
    ("Dejame en paz.", "Spanish"),
    ("No es lo que parece.", "Spanish"),
    ("Nunca te lo dije.", "Spanish"),
    ("Nao vou dizer nada.", "Portuguese"),
    ("Eu sei onde voce esteve.", "Portuguese"),
    ("Nao consigo mais.", "Portuguese"),
    ("Non ho niente da dire.", "Italian"),
    ("So dove sei stato quella notte.", "Italian"),
    ("Non e quello che sembra.", "Italian"),
    ("No pense dir res.", "Catalan"),
    ("Vine amb mi ara.", "Catalan"),
    ("Je ne dirai rien.", "French"),
    ("Je sais ou tu etais.", "French"),
    ("I am not saying anything.", "English"),
    ("I know where you were that night.", "English"),
]


@pytest.mark.parametrize("text,expected", SHORT_DIALOGUE_CORPUS)
def test_short_dialogue_lines_resolve_to_the_spoken_language(text, expected):
    """A <d> line is a few words long, which is exactly where detection used to break."""
    assert _detect_language(text) == expected
