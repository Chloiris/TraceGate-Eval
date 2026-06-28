# 仓库体检记录

日期：2026-06-28

这次体检的目标是让 TraceGate Eval 更适合 GitHub 展示和技术实习面试：面试官 clone 后能安装、能跑 smoke test、能看到最小 demo，并且能快速理解这个仓库还缺什么。所有修改都保持小修补，不改 benchmark 的研究设定。

## 发现的问题

- 仓库已经具备核心 package、CLI、Stage3 结果产物、FastAPI demo 和基础 API 测试。
- README 里的安装命令混用了 `bash` 代码块和 PowerShell 激活命令，复制到不同 shell 时容易误导。
- 本机默认 `python` 指向 LibreOffice Python，缺少 `pytest`；仓库虚拟环境可正常运行。因此 README 需要更明确地强调虚拟环境。
- `requirements.txt` 已包含测试和绘图依赖，但没有分组说明；`pyproject.toml` 也没有暴露 `dev` / `plots` 这类安装 extras。
- 现有测试主要覆盖 Web/API demo，没有直接覆盖 Stage3 ClaimBench 的 prompt/request 核心流程。
- `examples/` 里已有案例说明，但没有一个文件名明确的最小输入样例和最小输出样例。

## 已做修改

- 整理 `requirements.txt`，把运行依赖、测试依赖、绘图依赖分组标注，方便 reviewer 判断依赖用途。
- 补充 `pyproject.toml` 的 optional dependencies：`dev`、`plots`、`all`。这让 `python -m pip install -e ".[all]"` 成为真实可执行的完整安装命令。
- 新增 `tests/test_smoke_flow.py`。该测试在临时目录生成一个 ClaimBench 样例仓库，构造 `tracegate_verify_first` 上下文，执行 DeepSeek dry-run 请求生成流程，并检查输出请求文件。它不联网、不跑 Maven，但能覆盖核心流程是否能从任务进入 prompt/request。
- 新增 `examples/minimal_input.json` 和 `examples/minimal_output.md`，用于展示最小输入和符合协议的最小输出。
- 更新 README：拆分 Windows PowerShell 与 macOS/Linux 安装命令，补充 smoke test 命令、最小 no-network demo 命令、examples 链接和本审计文档链接。
- 补充 `.env.example` 注释，说明 dry-run 和本地 dashboard 不需要真实 API key。

## 已验证命令

以下命令已在仓库虚拟环境中验证：

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m tracegate --help
.\.venv\Scripts\python.exe -m tracegate run-claimbench --model deepseek-v4-pro --limit 1 --dry-run --workers 1
.\.venv\Scripts\python.exe -m tracegate collect-claim-results
.\.venv\Scripts\python.exe -m tracegate report-claimbench
```

结果：`pytest` 通过，CLI help、dry-run、结果收集和报告生成命令均可执行。

## 未改内容

- 未修改 Stage3 的任务设定、证据状态、context group、指标口径和已有结果摘要。
- 未重构 Java sample repositories。
- 未把真实 DeepSeek API 调用变成默认测试；真实模型调用仍需要 `DEEPSEEK_API_KEY`。
- 未把 Maven 测试纳入 Python smoke test，避免 clone 后的最小测试依赖 Java/Maven 环境。
- 未处理仓库中原本未跟踪的 `docs/TraceGate_Eval_Interview_Guide.*` 文件。

## 后续可增强

- 增加 GitHub Actions，在 Windows 和 Linux 上执行 `python -m pytest`。
- 在有 Java/Maven 的 CI 环境中增加一个可选 Maven smoke test。
- 为 Web dashboard 增加截图或短 demo GIF，降低面试讲解成本。
- 如果准备公开发布，可拆分重量级历史 run artifacts 与最小可运行 package。
- 为 `conflicting` evidence 增加更强的案例，继续区分 `verify_first` 与 `conflict_detected`。
