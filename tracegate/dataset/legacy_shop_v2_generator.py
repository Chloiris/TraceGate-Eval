from __future__ import annotations

import shutil
from pathlib import Path

from tracegate.config import SAMPLE_REPO_V2_DIR
from tracegate.dataset.legacy_shop_generator import LEGACY_SHOP_FILES, _write


SMOKE_TEST = """
package com.example.legacyshop;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;

@SpringBootTest
class Stage2CompileSmokeTest {
    @Autowired
    private ApplicationContext context;

    @Test
    void contextLoads() {
        assertThat(context).isNotNull();
    }
}
"""


def generate_legacy_shop_v2(destination: Path = SAMPLE_REPO_V2_DIR, force: bool = False) -> Path:
    if destination.exists():
        if not force:
            return destination
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for relative_path, content in LEGACY_SHOP_FILES.items():
        if relative_path.startswith("src/test/"):
            continue
        _write(destination, relative_path, content)
    _write(destination, "src/test/java/com/example/legacyshop/Stage2CompileSmokeTest.java", SMOKE_TEST)
    _write(
        destination,
        "TRACEGATE_STAGE2.md",
        """
        # TraceGate Stage2

        This repository starts with active legacy behavior. Stage2 tasks decide whether each historical constraint is still active or stale.
        Execution tests verify the project still compiles and starts; semantic correctness is checked by TraceGate oracles.
        """,
    )
    return destination

