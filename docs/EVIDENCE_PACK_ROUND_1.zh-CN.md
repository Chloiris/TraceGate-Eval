# Evidence Pack Round 1 中文伴读版

这份文件是 `docs/EVIDENCE_PACK_ROUND_1.md` 的中文人工审核辅助版。它只解释 AI 生成的草稿建议，不能当作人工确认标签。

保留英文原值的字段包括：`candidate_id`、`repo`、`pr_url`、`suspected_status`、`recommended_action`、`recommended_label`、`recommended_expected_decision`、文件路径、代码片段和 GitHub URL。

## 总览

- evidence_packs: `10`
- promote 草稿建议: `3`
- reject 草稿建议: `0`
- needs_more_evidence 草稿建议: `7`
- 推荐标签分布: `none=7`, `stale=2`, `unknown=1`, `conflicting=0`
- label_source: 只能是 `ai_suggested`
- 是否修改 `manual_labels.jsonl`: `false`
- 是否修改 `cases.jsonl`: `false`
- 是否使用 mock/synthetic/fallback: `false`

## 怎么读

- `promote` 在这里只表示“AI 建议人类可以考虑提升为正式标签”，不是已经提升。
- `needs_more_evidence` 表示证据还不够，应该继续找证据或人工判断。
- `none` 表示目前不建议打 `unknown` / `conflicting` / `stale` 标签。
- `verify_first` 表示先验证，再决定是否接受改动。
- `detect_conflict` 表示需要识别和处理互相冲突的证据。

## 1. `hard_candidate:psf__requests:pull:7555`

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7555
- suspected_status: `conflicting`
- PR 标题: `HTTPDigestAuth: use urlsplit for the digest URI`
- 改动文件: `src/requests/auth.py`, `src/requests/structures.py`, `tests/test_lowlevel.py`, `tests/test_structures.py`
- 推荐操作: `needs_more_evidence`
- 推荐标签: `none`
- 推荐 expected_decision: `none`
- confidence: `0.5`

中文速读：这个 PR 想把 digest authentication 里 URL path 的解析从 `urlparse` 调整为 `urlsplit`，核心风险点在认证 URI 是否会被错误截断。队列把它怀疑成 `conflicting`，主要因为文本里出现了 regression 相关词。

为什么还不能确认：目前证据只说明“有一个修复意图”和相关 commit，但没有找到两个互相冲突的证据 URL，例如一条说不会破坏兼容性，另一条明确指出会破坏。

人工只需要确认：
- 是否真的存在“支持方”和“反对方”两条证据？
- 这个问题是实际兼容性冲突，还是只是普通 bug fix？
- 如果找不到冲突证据，应保持 `needs_more_evidence` 或 reject。

## 2. `hard_candidate:psf__requests:pull:7549`

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7549
- suspected_status: `conflicting`
- PR 标题: `Remove method cookies set to None`
- 改动文件: `src/requests/sessions.py`, `tests/test_requests.py`
- 关联 issue: https://github.com/psf/requests/issues/2716
- 推荐操作: `needs_more_evidence`
- 推荐标签: `none`
- 推荐 expected_decision: `none`
- confidence: `0.5`

中文速读：这个 PR 处理 method-level cookie 值为 `None` 时的行为，并补了 regression 测试。它看起来更像针对 cookie header 的 bug fix。

为什么还不能确认：虽然 PR 文本里有 regression，但目前没看到真正互相冲突的 review/comment 证据。只有关键词不能支撑 `conflicting` 标签。

人工只需要确认：
- issue `#2716` 是否说明了历史行为约束？
- 是否有人在 review/comment 里明确反对这个行为？
- 如果没有冲突双方，建议不要提升为 `conflicting`。

## 3. `hard_candidate:psf__requests:pull:7546`

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7546
- suspected_status: `conflicting`
- PR 标题: `[Fix] response.content losing read errors on second access (#4965)`
- 改动文件: `src/requests/models.py`, `tests/test_lowlevel.py`
- 关联 issue: https://github.com/psf/requests/issues/4965
- 推荐操作: `needs_more_evidence`
- 推荐标签: `none`
- 推荐 expected_decision: `none`
- confidence: `0.5`

中文速读：这个 PR 说 `response.content` 第一次读取发生 stream error 后，第二次读取不应该静默返回空内容。它更像异常处理语义的 bug fix。

为什么还不能确认：目前只有 PR 自己的解释、commit 和 issue 链接，没有找到两条互相矛盾的证据。因此不能仅凭 regression 关键词提升为 `conflicting`。

人工只需要确认：
- issue `#4965` 是否有明确历史约束？
- 是否有 reviewer 认为该修复会破坏现有行为？
- 如果没有冲突证据，应继续保持 `needs_more_evidence`。

## 4. `hard_candidate:psf__requests:pull:7424`

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7424
- suspected_status: `unknown`
- PR 标题: `Fix HTTPDigestAuth failing on non-ASCII credentials`
- 改动文件: `src/requests/auth.py`
- 关联 issue: https://github.com/psf/requests/issues/6102
- 推荐操作: `promote`
- 推荐标签: `unknown`
- 推荐 expected_decision: `verify_first`
- confidence: `0.72`

中文速读：这个 PR 改的是 `HTTPDigestAuth` 非 ASCII 用户名/密码的处理，属于认证相关高风险区域。评论里有人指出该 PR 没有解决 `#6102`，还可能破坏 latin-1 默认场景。

为什么建议作为草稿提升到 `unknown`：这是 auth 相关改动，并且现有 PR body/comment 没有足够证据证明该改动安全。这里不需要证明代码一定错，只需要证明“证据不足，需要先验证”。

人工只需要确认：
- 是否确实缺少兼容性测试或维护者确认？
- latin-1 默认场景是否是必须保留的历史约束？
- 如果确认证据不足，可以考虑 `unknown` + `verify_first`。

## 5. `hard_candidate:psf__requests:pull:7355`

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7355
- suspected_status: `stale`
- PR 标题: `Add missing stacklevel to all warnings.warn() calls`
- 改动文件: `src/requests/__init__.py`, `src/requests/adapters.py`, `src/requests/auth.py`, `src/requests/utils.py`
- 推荐操作: `promote`
- 推荐标签: `stale`
- 推荐 expected_decision: `verify_first`
- confidence: `0.74`

中文速读：这个 PR 给多个 `warnings.warn()` 增加 `stacklevel`，让 warning 指向调用者代码，而不是 requests 内部代码。PR 和评论都围绕 deprecation warning 的输出位置变化。

为什么建议作为草稿提升到 `stale`：这里有旧 warning 行为、后续清理意图和评论中的测试说明，AI 判断它可能是“旧声明/旧行为被新证据更新”的候选。

人工只需要确认：
- 旧 claim URL 是哪一条？
- 新 superseding evidence URL 是哪一条？
- 两条证据的时间顺序是否清楚？如果不清楚，不能正式打 `stale`。

## 6. `hard_candidate:psf__requests:pull:7466`

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7466
- suspected_status: `conflicting`
- PR 标题: `fix: broaden JsonType to accept Sequence[Any] and Mapping[str, Any]`
- 改动文件: `src/requests/_types.py`
- 关联 issue: https://github.com/psf/requests/issues/7443
- 推荐操作: `needs_more_evidence`
- 推荐标签: `none`
- 推荐 expected_decision: `none`
- confidence: `0.5`

中文速读：这个 PR 是类型标注修复，想让 `JsonType` 接受更宽的 `Sequence[Any]` 和 `Mapping[str, Any]`，主要解决 mypy 类型报错。

为什么还不能确认：文本里有 incompatible 关键词，但当前证据更像“类型系统不兼容”的修复说明，不等于有两方互相冲突的证据。

人工只需要确认：
- issue `#7443` 是否包含与 PR 说法冲突的证据？
- 是否有 reviewer 认为这个放宽类型会破坏别的类型约束？
- 没有两条冲突证据时，不应提升为 `conflicting`。

## 7. `hard_candidate:psf__requests:pull:7467`

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7467
- suspected_status: `conflicting`
- PR 标题: `fix: broaden JsonType to accept Sequence[Any] and Mapping[str, Any]`
- 改动文件: `src/requests/_types.py`
- 关联 issue: https://github.com/psf/requests/issues/7443
- 推荐操作: `needs_more_evidence`
- 推荐标签: `none`
- 推荐 expected_decision: `none`
- confidence: `0.5`

中文速读：这个候选和 PR `7466` 非常相似，都是围绕 `JsonType` 类型别名放宽的问题。

为什么还不能确认：同样缺少两条互相冲突的 evidence URL。现在只能说明它可能和兼容性/类型约束有关，但不能直接判为 `conflicting`。

人工只需要确认：
- 这是否是 `7466` 的重复或同源 PR？
- issue `#7443` 中是否出现明确相反观点？
- 如果只是重复候选，应考虑 reject 或保留一个代表性候选。

## 8. `hard_candidate:psf__requests:pull:7441`

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7441
- suspected_status: `conflicting`
- PR 标题: `Move Request.headers back to Mapping`
- 改动文件: `src/requests/_types.py`, `src/requests/models.py`
- 关联 issue: https://github.com/psf/requests/issues/7442
- 推荐操作: `needs_more_evidence`
- 推荐标签: `none`
- 推荐 expected_decision: `none`
- confidence: `0.5`

中文速读：这个 PR 部分 revert 了 `#7431`，把 `Request.headers` 从 `MutableMapping` 改回 `Mapping`。这里确实有“回滚/取舍”的味道，可能和类型兼容有关。

为什么还不能确认：虽然 PR 自身说这是 tradeoff，但 evidence pack 没抓到有内容的 review/comment 来形成明确冲突。空 review 链接不能算冲突证据。

人工只需要确认：
- `#7431` 和 `#7441` 是否构成明确的旧新冲突？
- issue `#7442` 是否给出反方向证据？
- 如果能找到两条相反证据，才考虑 `conflicting` + `detect_conflict`。

## 9. `hard_candidate:psf__requests:pull:7492`

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/7492
- suspected_status: `conflicting`
- PR 标题: `Bump github/codeql-action from 4.35.1 to 4.36.0 in the actions group`
- 改动文件: `.github/workflows/codeql-analysis.yml`
- 推荐操作: `needs_more_evidence`
- 推荐标签: `none`
- 推荐 expected_decision: `none`
- confidence: `0.5`

中文速读：这是依赖升级 PR，把 `github/codeql-action` 升级到新版本。release notes 里提到 breaking change，所以被关键词命中。

为什么还不能确认：这里的 breaking change 来自上游 release notes，不一定代表本仓库真的产生冲突。没有看到本仓库 reviewer/comment 明确说“会破坏”或“不会破坏”。

人工只需要确认：
- CodeQL bundle 最低版本变化是否影响本仓库 CI？
- 是否有 CI 失败或维护者确认？
- 如果没有仓库内真实风险，可能应 reject，而不是 `conflicting`。

## 10. `hard_candidate:psf__requests:pull:6265`

- repo: `psf/requests`
- pr_url: https://github.com/psf/requests/pull/6265
- suspected_status: `stale`
- PR 标题: `Fix setuptools deprecation warnings`
- 改动文件: `setup.cfg`
- 推荐操作: `promote`
- 推荐标签: `stale`
- 推荐 expected_decision: `verify_first`
- confidence: `0.74`

中文速读：这个 PR 处理 `setuptools` 的弃用 warning，把一些 dash-separated 配置名改成 underscore 形式。后续评论说它已经被 `#7012` 取代，并且 `setup.cfg` 不再相关。

为什么建议作为草稿提升到 `stale`：这里有较清晰的旧问题、后续替代证据和“不再相关”的评论，比较符合 stale 的判断模式。

人工只需要确认：
- 旧 claim 是否就是 `setup.cfg` 中这些 deprecated key？
- `#7012` 或相关评论是否是新的 superseding evidence？
- 时间顺序确认后，才可以正式考虑 `stale` + `verify_first`。

## 人工审核优先级建议

1. 优先看 `7424`：它涉及 auth，且已有评论指出可能破坏 latin-1 默认场景。
2. 再看 `6265`：stale 证据相对清楚，适合人工快速确认旧证据和新证据。
3. 再看 `7355`：可能是 stale，但需要人工补齐旧 claim URL 和新 evidence URL。
4. `7555`、`7549`、`7546`、`7466`、`7467`、`7441`、`7492` 暂时都不应直接提升为 `conflicting`，除非能补到至少两条互相冲突的 evidence URL。

## 安全边界

- 本文件不是正式 label 文件。
- 本文件不修改 `datasets/real_min/labels/manual_labels.jsonl`。
- 本文件不修改 `datasets/real_min/cases.jsonl`。
- 本文件不把 draft 计入 scored metrics。
- 所有 `promote` 都只是 `ai_suggested` 草稿建议，必须由人类确认。
