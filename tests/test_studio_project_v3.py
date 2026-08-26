import json

import pytest

from studio_project import compile_studio_project, empty_studio_project, parse_studio_project


def _source(name, kind):
    return {
        "storage": "comfy_input",
        "file": f"minimax_h3_reference_director/{name} [input]",
        "sha256": "a" * 64,
        "mediaType": kind,
        "originalName": name,
        "sizeBytes": 42,
    }


def _project():
    project = empty_studio_project()
    project["project"].update({"name": "Ana at the lighthouse", "mode": "ref2va"})
    project["files"] = [
        {"id": "ana.face", "type": "picture", "name": "Ana identity", "source": _source("ana.webp", "picture")},
        {"id": "ana.voice", "type": "audio", "name": "Ana voice", "source": _source("ana.wav", "audio")},
        {"id": "cliff.view", "type": "picture", "name": "Cliff", "source": _source("cliff.webp", "picture")},
        {"id": "score", "type": "audio", "name": "Score", "source": _source("score.wav", "audio")},
    ]
    project["subjects"] = [{
        "id": "ana", "h3Index": 1, "name": "Ana", "description": "A woman with dark hair.",
        "identityFileIds": ["ana.face"], "defaultVoiceFileId": "ana.voice",
    }]
    project["environments"] = [{
        "id": "cliff", "name": "Cliff", "permanent": {"geography": "A steep Atlantic cliff."},
        "views": [{"id": "wide", "name": "Wide cliff", "role": "overview", "fileId": "cliff.view"}],
    }]
    project["shots"] = [{
        "id": "s1", "generationId": "g1", "title": "The lighthouse finds Ana",
        "action": "The lighthouse beam crosses the cliff and reveals Ana.",
        "cast": [{"subjectId": "ana", "presence": "present"}],
        "environment": {"environmentId": "cliff", "viewId": "wide"},
        "actionBeats": [{
            "id": "beat1", "at": 0.5,
            "dialogue": {"speakerId": "ana", "text": "There it is.", "delivery": "whispers"},
        }],
        "referenceBindings": [{"fileId": "score", "role": "soundtrack"}],
    }]
    return project


def test_empty_v3_project_is_valid_and_neutral():
    parsed = parse_studio_project(empty_studio_project())
    assert parsed["valid"] is True
    compiled = compile_studio_project(parsed["value"])
    assert compiled["mediaProject"]["schemaVersion"] == 2
    assert compiled["shotPlan"] == {"schemaVersion": 2, "timingMode": "auto", "shots": []}
    assert compiled["inputMap"] == {}


def test_v3_compiles_subject_voice_environment_and_shot_audio_from_one_source():
    compiled = compile_studio_project(_project())
    assert compiled["inputMap"] == {
        "ana.face": "<Picture 1>",
        "cliff.view": "<Picture 2>",
        "ana.voice": "<Audio 1>",
        "score": "<Audio 2>",
    }
    assert compiled["socketMap"] == {
        "ana.face": "ref_image_1",
        "cliff.view": "ref_image_2",
        "ana.voice": "ref_audio_1",
        "score": "ref_audio_2",
    }
    shot = compiled["shotPlan"]["shots"][0]
    assert shot["subjects"] == [{"subjectId": "ana", "presence": "present"}]
    assert shot["environment"] == {"environmentId": "cliff", "viewIds": ["wide"]}
    assert shot["referenceUses"] == [{"assetId": "score", "role": "soundtrack"}]
    assert "Ana" in compiled["referenceContext"]
    assert compiled["referenceProject"]["digest"]
    assert compiled["digest"]


def test_v3_compilation_is_deterministic_for_json_and_object_inputs():
    project = _project()
    first = compile_studio_project(project)
    second = compile_studio_project(json.dumps(project))
    assert first["digest"] == second["digest"]
    assert first["referenceProject"]["digest"] == second["referenceProject"]["digest"]


def test_v3_rejects_missing_files_before_slot_assignment():
    project = _project()
    project["subjects"][0]["identityFileIds"] = ["missing"]
    with pytest.raises(ValueError, match="missing identity file"):
        compile_studio_project(project)


def test_v3_enforces_real_h3_video_limit_of_three():
    project = _project()
    project["files"] = [
        {"id": f"video.{index}", "type": "video", "name": f"Video {index}", "source": _source(f"v{index}.mp4", "video")}
        for index in range(4)
    ]
    project["subjects"] = []
    project["environments"] = []
    project["shots"][0]["cast"] = []
    project["shots"][0].pop("environment")
    project["shots"][0]["actionBeats"] = []
    project["shots"][0]["referenceBindings"] = [
        {"fileId": f"video.{index}", "role": "continuity"} for index in range(4)
    ]
    with pytest.raises(ValueError, match="allows 3"):
        compile_studio_project(project)


def test_v3_keeps_video_soundtrack_aligned_without_consuming_an_audio_slot():
    project = _project()
    project["files"].insert(0, {
        "id": "motion", "type": "video", "name": "Motion with sound",
        "audioMode": "paired", "source": _source("motion.mp4", "video"),
    })
    project["shots"][0]["referenceBindings"].insert(0, {"fileId": "motion", "role": "performance"})
    compiled = compile_studio_project(project)
    assert compiled["inputMap"]["motion"] == "<Video 1>"
    assert compiled["inputMap"]["motion:soundtrack"] == "<Video 1> soundtrack"
    assert compiled["inputMap"]["ana.voice"] == "<Audio 1>"
    assert compiled["socketMap"]["motion"] == "ref_video_1"
    assert compiled["socketMap"]["motion:soundtrack"] == "ref_video_audio_1"
    assert compiled["socketMap"]["ana.voice"] == "ref_audio_1"
    assert compiled["quotas"]["g1"]["videoAudio"] == 1


def test_v3_never_invents_a_missing_shot_action_at_compile_time():
    project = _project()
    project["shots"][0]["action"] = ""
    with pytest.raises(ValueError, match="needs a visible action"):
        compile_studio_project(project)


def test_v3_generation_roots_activate_a_subject_without_casting_a_shot():
    project = _project()
    project["shots"][0]["cast"] = []
    project["shots"][0]["actionBeats"] = []
    project["shots"][0].pop("environment")
    project["generations"][0]["activation"] = {"mode": "explicit", "roots": [{"kind": "subject", "id": "ana"}]}
    compiled = compile_studio_project(project)
    assert compiled["inputMap"] == {
        "ana.face": "<Picture 1>",
        "ana.voice": "<Audio 1>",
        "score": "<Audio 2>",
    }
