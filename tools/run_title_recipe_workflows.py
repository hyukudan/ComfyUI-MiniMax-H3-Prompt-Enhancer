#!/usr/bin/env python3

import argparse
import copy
import json
import time
import urllib.request
from pathlib import Path


RECIPES = (
    "Auto director",
    "Prestige imprint",
    "Precision apparatus",
    "Analog print lab",
    "Unearthed archive",
    "Optical luxury",
    "Living material",
)
SLUGS = (
    "01_Auto_Director",
    "02_Prestige_Imprint",
    "03_Precision_Apparatus",
    "04_Analog_Print_Lab",
    "05_Unearthed_Archive",
    "06_Optical_Luxury",
    "07_Living_Material",
)
WORKFLOW = Path(__file__).resolve().parents[3] / "user/default/workflows/Video/MiniMax H3/6 Titles & Credits/60 Titles & Credits - Seven Recipe Test.api.json"


def request_json(url, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def wait_for_result(server, prompt_id):
    while True:
        history = request_json(f"{server}/history/{prompt_id}")
        if prompt_id in history:
            result = history[prompt_id]
            if result.get("status", {}).get("status_str") != "success":
                raise RuntimeError(json.dumps(result.get("status", {}), ensure_ascii=False))
            return result
        time.sleep(5)


def main():
    parser = argparse.ArgumentParser(description="Run all seven local H3 title recipe workflows sequentially.")
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    parser.add_argument("--start", type=int, default=1, choices=range(1, 8))
    args = parser.parse_args()

    template = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    for index, (recipe, slug) in enumerate(zip(RECIPES, SLUGS), 1):
        if index < args.start:
            continue
        workflow = copy.deepcopy(template)
        workflow["137"]["inputs"]["title_sequence_recipe"] = recipe
        workflow["129"]["inputs"]["noise_seed"] = 20260824
        workflow["92"]["inputs"]["filename_prefix"] = f"video/Title_Recipe_Tests/{slug}"
        queued = request_json(
            f"{args.server}/prompt",
            {"prompt": workflow, "client_id": "title-recipe-workflow-tests"},
        )
        prompt_id = queued["prompt_id"]
        print(f"[{index}/7] {recipe}: queued {prompt_id}", flush=True)
        result = wait_for_result(args.server, prompt_id)
        outputs = result.get("outputs", {}).get("92", {})
        print(f"[{index}/7] {recipe}: complete {json.dumps(outputs, ensure_ascii=False)}", flush=True)


if __name__ == "__main__":
    main()
