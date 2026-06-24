from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from tracegate.config import (
    CLAIM_CONTEXTS_FILE,
    CLAIM_EVIDENCE_STATUSES,
    CLAIM_MODELS_FILE,
    CLAIM_TASKS_FILE,
    CLAIMS_FILE,
    SAMPLE_REPO_CLAIM_DIR,
)
from tracegate.dataio import read_data, write_data
from tracegate.dataset.claim_case_templates import MODULE_CLAIMS, expected_decision
from tracegate.dataset.legacy_shop_generator import LEGACY_SHOP_FILES, _write


CLAIM_SMOKE_TEST = """
package com.example.legacyshop;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;

@SpringBootTest
class ClaimBenchSmokeTest {
    @Autowired
    private ApplicationContext context;

    @Test
    void contextLoads() {
        assertThat(context).isNotNull();
    }
}
"""


def generate_claim_sample_repo(destination: Path = SAMPLE_REPO_CLAIM_DIR, force: bool = False) -> Path:
    if destination.exists():
        if not force:
            return destination
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for relative_path, content in LEGACY_SHOP_FILES.items():
        if relative_path.startswith("src/test/") or relative_path in {"README.md", "TRACEGATE_HISTORY.md"}:
            continue
        _write(destination, relative_path, content)
    _write(
        destination,
        "README.md",
        """
        # legacy-shop-spring-claim

        Controlled Spring Boot project for TraceGate ClaimBench.

        The code contains compatibility paths whose current validity must be inferred from the benchmark context.
        Do not assume that every legacy path is still required or that every legacy path is safe to remove.

        Run:

        ```bash
        mvn test
        ```
        """,
    )
    _write(
        destination,
        "TRACEGATE_CLAIMS.md",
        """
        # TraceGate ClaimBench

        Historical experience is represented as a claim plus evidence. A claim may be supported, weakened,
        under-evidenced, or disputed by the supplied context. The safest coding action depends on that evidence,
        not on the presence of a legacy-looking branch alone.
        """,
    )
    _write(destination, "src/test/java/com/example/legacyshop/ClaimBenchSmokeTest.java", CLAIM_SMOKE_TEST)
    return destination


def default_claims() -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for module, spec in MODULE_CLAIMS.items():
        claims.append(
            {
                "id": f"CLAIM_{module.upper()}",
                "module": module,
                "pitfall": spec["pitfall"],
                "claim_text": spec["claim_text"],
                "validity_condition": spec["validity_condition"],
                "key_terms": spec["key_terms"],
            }
        )
    return claims


def default_claim_tasks() -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    index = 1
    for module, spec in MODULE_CLAIMS.items():
        for evidence_status in CLAIM_EVIDENCE_STATUSES:
            tasks.append(
                {
                    "id": f"C3T{index:02d}",
                    "module": module,
                    "pitfall": spec["pitfall"],
                    "title": f"{module} {spec['pitfall']} claim review",
                    "instruction": spec["instruction"],
                    "claim_id": f"CLAIM_{module.upper()}",
                    "claim_text": spec["claim_text"],
                    "validity_condition": spec["validity_condition"],
                    "evidence_status": evidence_status,
                    "expected_decision": expected_decision(evidence_status),
                    "evidence": spec["evidence"][evidence_status],
                    "misleading_evidence": spec["misleading"][evidence_status],
                    "target_files": spec["target_files"],
                    "key_terms": spec["key_terms"],
                    "required_tests": ["ClaimBenchSmokeTest"],
                    "oracle": f"{module}_claim_oracle",
                }
            )
            index += 1
    return tasks


def default_claim_contexts() -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for module, spec in MODULE_CLAIMS.items():
        contexts.extend(
            [
                {
                    "id": f"C3_{module.upper()}_RESULT_HISTORY",
                    "module": module,
                    "type": "result_history",
                    "content": (
                        f"Prior cleanup attempts around {spec['pitfall']} caused compatibility regressions. "
                        "The note did not record whether the same external dependency still exists today."
                    ),
                },
                {
                    "id": f"C3_{module.upper()}_PLAIN_CLAIM",
                    "module": module,
                    "type": "plain_claim",
                    "content": spec["claim_text"],
                },
                {
                    "id": f"C3_{module.upper()}_VALIDITY",
                    "module": module,
                    "type": "validity_condition",
                    "content": spec["validity_condition"],
                },
            ]
        )
    return contexts


def default_claim_models() -> list[dict[str, Any]]:
    return [
        {
            "id": "deepseek-v4-pro",
            "provider": "deepseek",
            "model": "deepseek-v4-pro",
            "thinking": "disabled",
            "temperature": 0.0,
        }
    ]


def write_claimbench_data(force: bool = False) -> tuple[Path, Path, Path, Path]:
    files = [
        (CLAIM_TASKS_FILE, default_claim_tasks()),
        (CLAIMS_FILE, default_claims()),
        (CLAIM_CONTEXTS_FILE, default_claim_contexts()),
        (CLAIM_MODELS_FILE, default_claim_models()),
    ]
    for path, data in files:
        if force or not path.exists():
            write_data(path, data)
    return CLAIM_TASKS_FILE, CLAIMS_FILE, CLAIM_CONTEXTS_FILE, CLAIM_MODELS_FILE


def load_claim_tasks(path: Path = CLAIM_TASKS_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return default_claim_tasks()
    return read_data(path)


def load_claims(path: Path = CLAIMS_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return default_claims()
    return read_data(path)


def load_claim_contexts(path: Path = CLAIM_CONTEXTS_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return default_claim_contexts()
    return read_data(path)


def load_claim_models(path: Path = CLAIM_MODELS_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return default_claim_models()
    return read_data(path)
