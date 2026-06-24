
---

# 一、实验目标

项目暂定名：

**TraceGate Eval：面向 AI Coding Agent 的编码过程上下文评测框架**

核心问题：

> 在 AI coding agent 执行遗留代码维护任务时，额外提供“编码过程上下文”是否能降低重复踩历史坑的概率？
> 如果提供太多、过期或无关上下文，是否会造成上下文污染？

这里不要证明“我比 Codex 上下文管理强”。Codex 本身已经支持 `AGENTS.md`，官方文档说明 Codex 会在开始工作前读取这些项目级指导；Codex 也支持 skills，把 instructions、resources 和 scripts 打包成可复用能力。([OpenAI开发者][1])

你的项目要证明的是：

> **外部编码过程上下文，在经过筛选后，是否能作为 Codex/Claude/Cursor 这类 Agent 的补充记忆。**

---

# 二、第一版用什么 AI？

## 结论：第一版用“闭源大模型 + 可替换接口”，不要一开始本地小模型

建议分三层：

### 第一层：Codex 负责写实验框架代码

你现在就是让 Codex 写：

* 数据集生成器；
* 上下文生成器；
* prompt 生成器；
* 实验运行脚本；
* 指标统计；
* Markdown/HTML 报告。

也就是说，Codex 先作为**开发工具**。

---

### 第二层：实验对象优先用闭源大模型或 Codex

你最终要评估的是 Codex 类 coding agent，所以主实验对象应该是：

* Codex；
* 或 GPT 系列 API；
* 或 Claude Code；
* 或 DeepSeek API 作为低成本对照。

如果你只用本地 7B/14B 小模型，可能会出现一个问题：

> 模型本身 coding 能力太弱，导致上下文有没有用都被模型能力噪声淹没。

所以第一版不要以本地模型为主。

---

### 第三层：DeepSeek API 适合做自动化低成本跑批

DeepSeek API 现在有 `deepseek-v4-flash` / `deepseek-v4-pro` 等模型线，官方文档也说明旧的 `deepseek-chat`、`deepseek-reasoner` 会逐步转为兼容别名。([深度寻找API文档][2])

所以第一版可以这样安排：

| 用途      | 推荐模型                      |
| ------- | ------------------------- |
| 写实验框架代码 | Codex                     |
| 小规模自动跑批 | DeepSeek API              |
| 最终展示效果  | Codex / GPT / Claude Code |
| 本地模型    | 只做附加对照，不做主实验              |

本地模型可以后面用 Ollama 跑 Qwen2.5-Coder 等模型。Ollama 上 Qwen2.5-Coder 有 0.5B、1.5B、3B、7B、14B、32B 等尺寸，但它更适合做“本地模型是否也受上下文影响”的附加实验，不适合作为第一版主实验。([Ollama][3])

---

# 三、第一版不要碰真实大项目，先做可控模拟仓库

你现在最需要的是**可验证结果**，不是大而全。

第一版准备一个模拟遗留项目：

## 项目名

**legacy-shop-spring**

技术栈：

* Java 17
* Spring Boot
* Maven
* H2 内存数据库
* JUnit 5
* MockMvc
* MyBatis 或 Spring Data JPA 二选一

我建议第一版用 **Spring Boot + H2 + JUnit**，不要一开始连 MySQL，避免环境问题。

---

# 四、模拟什么业务场景？

模拟一个“陈年电商/后台管理系统”，里面有 5 类历史坑。

## 模块 1：登录兼容坑 Auth

业务设定：

* 老版本移动端仍然依赖 `legacyToken`；
* 新版系统使用 `accessToken`；
* 看起来可以删掉 `legacyToken`，但删了旧版兼容测试会失败。

隐藏坑：

> AI 很可能会觉得 `legacyToken` 是冗余字段并删掉。

测试：

* `LoginCompatibilityTest`
* `LegacyTokenStillSupportedTest`

编码过程上下文示例：

```md
曾尝试删除 legacyToken，导致旧版移动端登录失败。
修改 AuthService 时必须保留 legacyToken 生成逻辑。
修改后必须运行 LoginCompatibilityTest。
```

---

## 模块 2：订单状态坑 Order

业务设定：

* `order_status` 表示订单主状态；
* `refund_status` 表示退款状态；
* 两个字段看起来可以合并，但历史上合并后导致退款对账错误。

隐藏坑：

> AI 可能会“优化设计”，把两个状态字段合并。

测试：

* `RefundStatusIndependenceTest`
* `OrderRefundAccountingTest`

编码过程上下文示例：

```md
曾尝试合并 order_status 和 refund_status，导致退款对账逻辑错误。
两个状态字段必须保持独立。
```

---

## 模块 3：软删除坑 User

业务设定：

* `status = 2` 表示逻辑删除；
* 不能物理删除用户；
* 审计模块仍然依赖被删除用户的历史记录。

隐藏坑：

> AI 可能会把 deleteUser 改成 repository.deleteById。

测试：

* `SoftDeleteUserTest`
* `AuditLogStillReferencesDeletedUserTest`

编码过程上下文示例：

```md
用户删除必须使用 status=2 逻辑删除。
不要调用 deleteById 物理删除用户，否则审计记录会断链。
```

---

## 模块 4：支付回调坑 Payment

业务设定：

* 第三方支付平台要求原始金额字段 `amountInCent`；
* 项目内部有 `amountInYuan`；
* 看起来可以统一单位，但历史上统一后导致签名校验失败。

隐藏坑：

> AI 可能会统一金额单位，破坏签名。

测试：

* `PaymentSignatureTest`
* `AmountUnitCompatibilityTest`

编码过程上下文示例：

```md
不要把 amountInCent 改成 amountInYuan 参与签名。
支付平台签名要求使用分为单位的原始金额。
```

---

## 模块 5：定时任务幂等坑 Job

业务设定：

* 每天凌晨同步账单；
* 失败后可能重复执行；
* 必须用 `sync_batch_id` 防止重复入账。

隐藏坑：

> AI 可能只看当前代码，觉得重复判断多余，把幂等逻辑删掉。

测试：

* `BillSyncIdempotentTest`
* `DuplicateBillShouldNotBeInsertedTest`

编码过程上下文示例：

```md
账单同步必须保留 sync_batch_id 幂等检查。
曾删除该检查，导致重复入账。
```

---

# 五、准备 4 类上下文

你要比较的不是“有上下文 vs 没上下文”这么简单，而是至少 5 组。

## A 组：No Context

只给任务，不给任何历史。

示例：

```md
请重构 AuthService，使登录逻辑更清晰，并保持所有测试通过。
```

---

## B 组：Result-History Context

给普通历史结果上下文。

比如：

* README；
* issue 摘要；
* PR 摘要；
* commit message；
* release note。

示例：

```md
历史记录：
- 修复旧版移动端登录兼容问题。
- 优化 token 生成逻辑。
- 增加登录兼容测试。
```

这类上下文比较模糊，接近真实 Git/PR 信息。

---

## C 组：Full Process Context

给完整编码过程上下文。

示例：

```md
完整历史：
- 第一次尝试删除 legacyToken，LoginCompatibilityTest 失败。
- 第二次尝试只保留 accessToken，旧版客户端无法登录。
- 第三次保留 legacyToken 与 accessToken 双轨逻辑，测试通过。
- 人工备注：legacyToken 暂时不能删除，直到旧版客户端完全下线。
```

这个组可能有用，也可能污染。

---

## D 组：Routed Process Context

给筛选后的相关过程上下文。

比如当前任务改 Auth，就只给 Auth 相关历史。

示例：

```md
Auth 模块关键约束：
- legacyToken 仍被旧版移动端依赖，不要删除。
- 修改后必须运行 LoginCompatibilityTest。
```

这是你项目真正主打的组。

---

## E 组：Irrelevant / Stale Context

故意给无关或过期上下文。

示例：

```md
订单模块历史：
- 不要合并 order_status 和 refund_status。
- 退款对账依赖 refund_status。
```

但当前任务其实是 Auth。

这个组用来验证：

> 无关上下文会不会造成污染。

---

# 六、实验任务怎么设计？

第一版每个模块设计 2 个任务，一共 10 个任务就够。

## Auth 任务

任务 1：

```md
请重构 AuthService，把 token 生成逻辑拆分得更清晰，保持所有测试通过。
```

预期风险：

* AI 删除 legacyToken；
* AI 只保留 accessToken；
* AI 忘记旧版兼容。

任务 2：

```md
请为登录接口增加 rememberMe 参数，并保持旧版客户端兼容。
```

---

## Order 任务

任务 3：

```md
请优化订单状态判断逻辑，减少重复 if-else。
```

预期风险：

* 合并 order_status 和 refund_status。

任务 4：

```md
请增加订单退款中的 PARTIAL_REFUND 状态。
```

---

## User 任务

任务 5：

```md
请重构用户删除逻辑，使代码更符合 Repository 风格。
```

预期风险：

* 改成物理删除。

任务 6：

```md
请增加批量删除用户功能。
```

---

## Payment 任务

任务 7：

```md
请统一支付模块中的金额字段命名。
```

预期风险：

* 破坏 amountInCent 签名。

任务 8：

```md
请增加支付回调参数校验。
```

---

## Job 任务

任务 9：

```md
请优化账单同步任务，减少重复查询。
```

预期风险：

* 删除幂等检查。

任务 10：

```md
请增加手动重跑账单同步功能。
```

预期风险：

* 重跑导致重复入账。

---

# 七、每轮实验怎么跑？

第一版流程如下：

## Step 1：生成基准仓库

Codex 要写一个脚本：

```bash
python scripts/create_legacy_shop.py
```

生成：

```text
sample_repos/legacy-shop-spring/
```

里面包含：

* Spring Boot 项目；
* 5 个模块；
* 对应测试；
* 初始 README；
* 模拟历史上下文；
* 模拟编码过程上下文。

---

## Step 2：生成实验副本

每个任务、每种上下文一个独立副本：

```text
runs/
  task_01_auth_refactor/
    no_context/
    result_history/
    full_process/
    routed_process/
    irrelevant_context/
```

这样避免不同实验互相污染。

---

## Step 3：生成 prompt

每组生成一个 prompt 文件：

```text
runs/task_01_auth_refactor/routed_process/prompt.md
```

内容包括：

1. 任务说明；
2. 当前上下文组；
3. 必须遵守的输出要求；
4. 要运行的测试命令；
5. 不要修改测试，除非任务要求。

示例：

```md
你正在维护一个 Spring Boot 遗留项目。

任务：
请重构 AuthService，把 token 生成逻辑拆分得更清晰，并保持所有测试通过。

相关历史上下文：
- legacyToken 仍被旧版移动端依赖，不要删除。
- 修改后必须运行 LoginCompatibilityTest。

要求：
1. 不要删除已有测试。
2. 不要修改测试来绕过失败。
3. 修改后运行 mvn test。
4. 如果测试失败，请继续修复直到通过。
```

---

## Step 4：让 AI 执行任务

第一版可以有两种方式。

### 方式 A：Codex 手动跑

你进入某个实验目录，把 prompt 粘给 Codex。

优点：

* 最贴近你真正关心的 Codex；
* 能观察它 goal 模式下会不会自己修。

缺点：

* 不容易批量跑；
* 每组需要人工记录结果。

---

### 方式 B：DeepSeek API 自动跑

写一个模型适配器：

```text
model_adapters/
  deepseek_adapter.py
  openai_adapter.py
  manual_adapter.py
```

DeepSeek API 用来自动生成 patch，然后脚本应用 patch、跑测试、统计结果。

优点：

* 能跑批；
* 成本低；
* 能快速得到初步数据。

缺点：

* 它不是 Codex；
* 不能完全代表 Codex goal 模式。

所以我建议第一版：

> 用 DeepSeek API 自动跑出初步结果；
> 再挑 2～3 个典型任务用 Codex 手动复测。

---

## Step 5：运行测试

每轮执行：

```bash
mvn test
```

记录：

* 是否编译通过；
* 是否测试通过；
* 失败测试名称；
* 错误日志；
* 修改文件列表；
* 修改行数；
* 是否触发历史坑。

---

## Step 6：统计指标

第一版至少统计这些：

| 指标                          | 含义                |
| --------------------------- | ----------------- |
| success                     | 所有测试是否通过          |
| violated_history_constraint | 是否违反历史约束          |
| repeated_failed_attempt     | 是否重复历史失败方案        |
| touched_files_count         | 修改文件数量            |
| patch_lines_added           | 新增行数              |
| patch_lines_deleted         | 删除行数              |
| test_fail_count             | 失败测试数             |
| retry_count                 | 返工轮数，第一版可以先不做自动返工 |
| context_tokens              | 上下文 token 估计      |
| pollution_flag              | 是否因为无关/过期上下文导致错误  |

其中最重要的是：

> **D 组 routed_process 是否比 B 组 result_history 更少违反历史约束。**

---

# 八、第一版输出什么结果才算成功？

不要期待第一版就证明很强。

只要能得到这种初步结果就够：

```text
共 10 个任务 × 5 种上下文 = 50 次实验。

No Context：
- 成功 5/10
- 历史约束违反 4 次

Result History：
- 成功 6/10
- 历史约束违反 3 次

Full Process：
- 成功 6/10
- 历史约束违反 2 次
- 出现上下文污染 1 次

Routed Process：
- 成功 8/10
- 历史约束违反 1 次
- token 成本低于 Full Process

Irrelevant Context：
- 成功 4/10
- 出现上下文污染 3 次
```

哪怕数据是模拟的，也能说明你的研究方向：

> 全量上下文不一定最好；
> 相关、压缩、模块级注入的过程上下文可能更稳；
> 无关上下文会污染。

---

# 九、Codex 初版代码应该实现哪些目录？

让 Codex 生成这个项目结构：

```text
tracegate-eval/
  README.md
  requirements.txt
  pyproject.toml

  tracegate/
    __init__.py
    cli.py
    config.py

    dataset/
      legacy_shop_generator.py
      task_generator.py
      context_generator.py

    context/
      selector.py
      compressor.py
      token_estimator.py

    prompts/
      prompt_builder.py
      templates/
        base_prompt.md
        no_context.md
        result_history.md
        full_process.md
        routed_process.md
        irrelevant_context.md

    runners/
      manual_runner.py
      deepseek_runner.py
      command_runner.py

    metrics/
      junit_parser.py
      git_diff_analyzer.py
      constraint_checker.py
      result_collector.py

    reports/
      markdown_report.py
      csv_report.py
      html_report.py

  sample_repos/
    legacy-shop-spring/

  experiments/
    tasks.yaml
    context_items.yaml
    historical_failures.yaml

  runs/
    .gitkeep

  scripts/
    create_dataset.py
    create_runs.py
    run_tests.py
    collect_results.py
    generate_report.py
```

---

# 十、核心数据文件怎么设计？

## tasks.yaml

```yaml
- id: T01
  module: auth
  title: 重构 AuthService token 生成逻辑
  instruction: 请重构 AuthService，把 token 生成逻辑拆分得更清晰，并保持所有测试通过。
  target_files:
    - src/main/java/com/example/legacyshop/auth/AuthService.java
  required_tests:
    - LoginCompatibilityTest
    - LegacyTokenStillSupportedTest
  hidden_constraints:
    - keep_legacy_token
```

---

## context_items.yaml

```yaml
- id: C_AUTH_001
  module: auth
  type: retained_constraint
  content: legacyToken 仍被旧版移动端依赖，不要删除。
  evidence: failed_attempt_auth_legacy_token
  status: active
  relevance_files:
    - AuthService.java
    - LoginController.java
```

---

## historical_failures.yaml

```yaml
- id: F_AUTH_001
  module: auth
  failed_attempt: 删除 legacyToken，仅保留 accessToken。
  failure_reason: LoginCompatibilityTest 失败，旧版客户端无法登录。
  final_decision: 保留 legacyToken 与 accessToken 双轨逻辑。
  verification:
    - mvn test -Dtest=LoginCompatibilityTest
```

---

# 十一、上下文选择器怎么做？

第一版不要复杂。

规则：

1. 如果任务指定 module，就选同 module 的 context；
2. 如果 target_files 命中文件名，也选相关 context；
3. 只选 status = active；
4. 最多选 3 条 context；
5. 每条压缩成 1～2 句话。

伪逻辑：

```text
score = 0
if context.module == task.module: +3
if target_file in context.relevance_files: +3
if context.status == active: +1
if context.type == retained_constraint: +2
if context.type == failed_attempt: +1
```

取分数最高的 3 条。

这就是最初版 context routing。

---

# 十二、上下文污染怎么模拟？

你要专门造两个污染场景。

## 场景 1：无关污染

当前任务是 Auth，但注入 Order 历史。

观察 AI 是否因为无关上下文乱改订单模块，或者忽略 Auth 真正约束。

---

## 场景 2：过期污染

比如旧上下文写：

```md
旧版移动端仍依赖 legacyToken，不要删除。
```

但任务设定是：

```md
旧版移动端已下线，请移除 legacyToken。
```

如果 AI 还死守旧上下文，就是过期污染。

所以 context_items.yaml 里要有：

```yaml
status: active | stale | deprecated
```

第一版 selector 默认过滤 stale/deprecated。
Full Process 组故意不过滤，用来观察污染。

---

# 十三、给 Codex 的完整任务提示词

你可以直接复制下面这段给 Codex：

```md
你要帮我实现一个 Python 项目，项目名为 tracegate-eval。

项目目标：
构建一个面向 AI Coding Agent 的编码过程上下文评测框架，用来比较 no-context、result-history-context、full-process-context、routed-process-context、irrelevant-context 五种上下文条件下，AI 修改遗留代码任务的表现差异。

请先实现一个能跑出初步结果的 MVP，不要做复杂插件。

技术要求：
1. 使用 Python 3.11+。
2. 使用 Typer 或 argparse 实现 CLI。
3. 生成一个 sample Spring Boot 遗留项目 legacy-shop-spring。
4. 该 Spring Boot 项目包含 auth、order、user、payment、job 五个模块。
5. 每个模块包含一个故意设计的历史坑，并配套 JUnit 测试。
6. Python 框架需要能生成 10 个维护任务。
7. 每个任务生成 5 种上下文版本：
   - no_context
   - result_history
   - full_process
   - routed_process
   - irrelevant_context
8. 每个实验版本生成独立 runs 目录和 prompt.md。
9. 暂时不需要自动调用 Codex；请实现 manual_runner，让用户手动把 prompt 给 AI 后，把结果放回对应目录。
10. 同时预留 deepseek_runner.py，接口先写清楚，可以后续填 API。
11. 实现 mvn test 运行器，收集测试结果。
12. 实现 git diff 分析，统计修改文件数量、新增行数、删除行数。
13. 实现 constraint_checker，检查是否违反历史约束，例如删除 legacyToken、合并 order_status/refund_status、物理删除用户等。
14. 实现 markdown_report 和 csv_report，输出实验结果汇总。
15. README 里写清楚完整运行流程。

第一版命令设计：
- python -m tracegate create-dataset
- python -m tracegate create-runs
- python -m tracegate run-tests --run-dir runs/xxx
- python -m tracegate collect-results
- python -m tracegate report

请先生成完整项目骨架、核心代码、示例数据和 README。
优先保证能跑通，不要过度设计。
```

---

# 十四、你第一阶段要得到什么

第一阶段的交付物不是论文，也不是完整产品，而是：

1. 一个 GitHub 仓库；
2. 一个能生成模拟遗留项目的脚本；
3. 10 个任务；
4. 5 种上下文条件；
5. 若干 prompt；
6. 能跑测试；
7. 能统计结果；
8. 能生成报告。

做到这里，你就已经有初步成果了。

---

# 十五、后续怎么升级

第一版跑通后，再做三次升级：

## 第二版：接 DeepSeek API 自动跑

让系统自动调用 DeepSeek API，批量跑 50 次实验。

---

## 第三版：接 Codex 手动复测

挑 3 个最典型任务，用 Codex goal 模式人工复测：

* no_context；
* full_process；
* routed_process。

看 Codex 是否真的会受影响。

---

## 第四版：做成上下文生成工具

实验有效后，再把它变成工具：

```bash
tracegate note auth "legacyToken 不能删除"
tracegate context --files AuthService.java
tracegate export-agents-md
```

这时候才从“评测框架”升级为“项目上下文路由工具”。

---

# 最终建议

你现在不要让 Codex 直接写“产品”。
你应该让 Codex 先写：

> **实验框架 + 模拟数据 + 对照组 + 指标统计。**

因为你现在最大的不确定性不是“能不能写工具”，而是：

> **编码过程上下文到底有没有增量价值，会不会污染 Codex。**

所以第一版的目标就是跑出初步实验结果。
结果好，再产品化。
结果一般，也能转成一篇很像样的项目调研和实验报告。

[1]: https://developers.openai.com/codex/guides/agents-md?utm_source=chatgpt.com "Custom instructions with AGENTS.md – Codex"
[2]: https://api-docs.deepseek.com/quick_start/pricing?utm_source=chatgpt.com "Models & Pricing | DeepSeek API Docs"
[3]: https://ollama.com/?utm_source=chatgpt.com "Ollama"
