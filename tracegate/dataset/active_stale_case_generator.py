from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.config import (
    STAGE2_CONTEXTS_FILE,
    STAGE2_MODELS_FILE,
    STAGE2_ORACLES_FILE,
    STAGE2_TASKS_FILE,
)
from tracegate.dataio import read_data, write_data


MODULES = {
    "auth": {
        "pitfall": "legacyToken",
        "active": "旧版移动端仍在使用，必须保留 legacyToken。",
        "stale": "旧版移动端已下线，可以删除 legacyToken。",
        "target_files": ["src/main/java/com/example/legacyshop/auth/AuthService.java", "src/main/java/com/example/legacyshop/auth/LoginResponse.java"],
    },
    "order": {
        "pitfall": "orderStatus/refundStatus",
        "active": "退款对账仍依赖订单主状态和退款状态两个字段，不能合并。",
        "stale": "新对账系统已迁移，可以合并订单主状态和退款状态。",
        "target_files": ["src/main/java/com/example/legacyshop/order/ShopOrder.java", "src/main/java/com/example/legacyshop/order/OrderService.java"],
    },
    "user": {
        "pitfall": "status=2 soft delete",
        "active": "审计仍依赖用户记录，必须使用 status=2 逻辑删除。",
        "stale": "审计已快照化，可以改为 deleteById 物理删除。",
        "target_files": ["src/main/java/com/example/legacyshop/user/UserService.java", "src/main/java/com/example/legacyshop/user/UserRepository.java"],
    },
    "payment": {
        "pitfall": "amountInCent",
        "active": "第三方签名仍要求分单位，必须保留 amountInCent 签名路径。",
        "stale": "新支付网关已统一金额单位，可以改为 amountInYuan 签名路径。",
        "target_files": ["src/main/java/com/example/legacyshop/payment/PaymentCallback.java", "src/main/java/com/example/legacyshop/payment/PaymentCallbackService.java"],
    },
    "job": {
        "pitfall": "syncBatchId",
        "active": "重跑仍可能重复入账，必须保留 syncBatchId 幂等检查。",
        "stale": "新队列已提供 exactly-once，可以简化旧 syncBatchId 幂等逻辑。",
        "target_files": ["src/main/java/com/example/legacyshop/job/BillSyncService.java", "src/main/java/com/example/legacyshop/job/BillRepository.java"],
    },
}


def default_stage2_tasks() -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    index = 1
    for module, spec in MODULES.items():
        for lifecycle, truth in [("active", "must_preserve"), ("stale", "can_optimize")]:
            current_fact = spec[lifecycle]
            tasks.append(
                {
                    "id": f"S2T{index:02d}",
                    "module": module,
                    "pitfall": spec["pitfall"],
                    "lifecycle": lifecycle,
                    "ground_truth": truth,
                    "title": f"{module} {spec['pitfall']} {lifecycle}",
                    "instruction": (
                        f"请维护 {module} 模块。当前业务事实：{current_fact} "
                        "请根据当前事实重构或优化代码，并保持项目可编译、测试通过。"
                    ),
                    "target_files": spec["target_files"],
                    "required_tests": ["Stage2CompileSmokeTest"],
                    "oracle": f"{module}_oracle",
                }
            )
            index += 1
    return tasks


def default_stage2_contexts() -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for module, spec in MODULES.items():
        contexts.extend(
            [
                {
                    "id": f"S2_{module.upper()}_RESULT",
                    "module": module,
                    "type": "result_history",
                    "status": "active",
                    "content": f"历史记录：曾修复 {spec['pitfall']} 相关线上问题，并补充兼容性说明。",
                },
                {
                    "id": f"S2_{module.upper()}_ACTIVE",
                    "module": module,
                    "type": "process_constraint",
                    "status": "active",
                    "content": spec["active"],
                },
                {
                    "id": f"S2_{module.upper()}_STALE",
                    "module": module,
                    "type": "process_constraint",
                    "status": "stale",
                    "content": spec["stale"],
                },
                {
                    "id": f"S2_{module.upper()}_FAILURE",
                    "module": module,
                    "type": "failed_attempt",
                    "status": "active",
                    "content": f"历史失败：错误处理 {spec['pitfall']} 后导致测试或线上兼容性失败。",
                },
            ]
        )
    return contexts


def default_stage2_oracles() -> list[dict[str, Any]]:
    return [
        {"module": module, "oracle": f"{module}_oracle", "pitfall": spec["pitfall"]}
        for module, spec in MODULES.items()
    ]


def default_stage2_models() -> list[dict[str, Any]]:
    return [
        {
            "id": "deepseek-v4-pro",
            "provider": "deepseek",
            "model": "deepseek-v4-pro",
            "thinking": "disabled",
            "temperature": 0.0,
        }
    ]


def write_stage2_data(force: bool = False) -> tuple[Path, Path, Path, Path]:
    files = [
        (STAGE2_TASKS_FILE, default_stage2_tasks()),
        (STAGE2_CONTEXTS_FILE, default_stage2_contexts()),
        (STAGE2_ORACLES_FILE, default_stage2_oracles()),
        (STAGE2_MODELS_FILE, default_stage2_models()),
    ]
    for path, data in files:
        if force or not path.exists():
            write_data(path, data)
    return STAGE2_TASKS_FILE, STAGE2_CONTEXTS_FILE, STAGE2_ORACLES_FILE, STAGE2_MODELS_FILE


def load_stage2_tasks(path: Path = STAGE2_TASKS_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return default_stage2_tasks()
    return read_data(path)


def load_stage2_contexts(path: Path = STAGE2_CONTEXTS_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return default_stage2_contexts()
    return read_data(path)


def load_stage2_models(path: Path = STAGE2_MODELS_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return default_stage2_models()
    return read_data(path)

