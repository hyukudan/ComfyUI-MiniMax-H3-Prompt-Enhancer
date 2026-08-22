# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path


ROOT = Path(__file__).parents[1]
WEB = ROOT / "web"


def test_frontend_entrypoint_delegates_structured_state_to_esm_modules():
    entrypoint = (WEB / "backend_toggle.js").read_text(encoding="utf-8")
    assert 'from "./studio/catalogs.js"' in entrypoint
    assert 'from "./studio/drawer.js"' in entrypoint
    assert 'from "./studio/widget_store.js"' in entrypoint
    assert 'from "./schema.js"' in (WEB / "studio" / "widget_store.js").read_text(encoding="utf-8")


def test_ci_checks_javascript_recursively_and_runs_node_tests():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "find web -type f -name '*.js' -print0" in workflow
    assert "xargs -0 -n1 node --check" in workflow
    assert "node --test web/studio/tests/*.test.mjs" in workflow
    assert "for file in web/*.js" not in workflow


def test_web_package_uses_native_esm_without_runtime_dependencies():
    package = (WEB / "package.json").read_text(encoding="utf-8")
    assert package == '{\n  "private": true,\n  "type": "module"\n}\n'
