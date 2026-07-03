# TraceGate Eval 中文 README

[English README](../README.md)

TraceGate Eval 是一个 v0.3-alpha prototype，用来评估 AI coding agent
在处理历史工程上下文时是否能做出更安全的维护决策。

它关注的问题不是普通测试通过率，而是：

- 历史经验现在是否仍然有效？
- 旧的兼容性约束应该保留、优化、先验证，还是标记为冲突？
- 错误、过期、缺失或冲突的上下文会不会污染 LLM 的补丁？

## 如何阅读这个仓库

这个仓库目前有两条 evaluation track 和两种 advisory mode。

Evaluation tracks:

- Controlled ClaimBench：离线 160-run 研究实验，用来测试历史上下文对
  AI coding-agent 行为的影响。
- Real-data hard benchmark：离线真实 GitHub Pull Request 小型 benchmark，
  当前有 19 条 scored cases。

Advisory modes:

- Rule advisory：不调用 LLM 的 changed-file / `tracegate.yml` live PR
  baseline。
- DeepSeek semantic advisory：调用真实 DeepSeek API 的 live PR semantic
  advisory，目前是 warning-only。

完整结构图见：[PROJECT_MAP.md](PROJECT_MAP.md)。

## 当前状态

```text
active=12
stale=2
unknown=3
conflicting=2
scored_cases=19
hard_benchmark_ready=true
```

## 版本边界

- v0.2-alpha：重点是 real-data hard benchmark readiness。
- v0.3-alpha：新增 DeepSeek Semantic PR Advisor，用于 live PR evidence-aware
  advisory。

TraceGate 目前不是企业级平台，不是通用 code review bot，也不会默认阻止
Pull Request 合并。它更像是一个小型、可复现、强调证据状态的研究和
advisory prototype。
