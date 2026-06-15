# skill-security-review

一个面向 Codex/Agent skill 包的本地安全审查工具。用户可以在 Agent 中用自然语言请求审查某个 skill；Agent 负责调用本仓库携带的 CLI，读取 Markdown/JSON 报告，并优先总结最高风险发现。

`skill-security-review` 默认以离线、静态方式运行，不要求 API key、baseURL 或模型配置；需要更强验证时，也可以使用 Docker 沙箱进行动态审查。它也适合作为 Agent 安装新 skill 后的自动审查步骤。

## Features

- 支持通过 Agent 自然语言触发审查，例如“对这个 skill 进行安全审查”。
- 提供隔离区安装流程：新 skill 先进入 `_pending`，审查通过后才启用。
- 扫描本地 skill 目录和 `.zip` 包。
- 检查 `SKILL.md` 元数据、文件清单、可执行脚本和二进制资源。
- 对 `.zip` 包执行路径穿越、重复路径、符号链接、异常大文件和过深路径检查。
- 检测常见风险模式：凭据访问、硬编码密钥、私钥、破坏性命令、网络外传、远程代码执行、持久化、提权、Prompt 越权和供应链风险。
- 内置 40 条 Gitleaks-derived provider token 规则，用于补强 OpenAI、Anthropic、GitHub、GitLab、npm、PyPI、Slack、Stripe、Vault 等高价值凭据格式检测；这些规则在本地运行，不调用外部 `gitleaks` 二进制。
- 生成适合人工阅读的 `report.md` 和适合 Agent/CI 读取的 `report.json`。
- 支持弱审查和强审查两种模式。
- 提供可复验的 Python zipapp 运行载荷。

## Agent Usage

安装到 Agent 的 skills 目录后，用户不需要记住 CLI 参数。可以直接对 Agent 说：

```text
对 /path/to/some-skill 这个 skill 进行安全审查
```

也可以在安装或更新新 skill 后说：

```text
审查刚安装的 skill
```

Agent 工作流建议：

- 如果用户给出本地目录或 `.zip` 路径，直接运行弱审查。
- 如果用户没有给出路径，先询问要审查的 skill 位置。
- 如果用户明确要求“强审查”“动态审查”或“Docker 沙箱”，运行强审查。
- 强审查必须真的运行 Docker 沙箱；如果 Docker 不可用，工具会尝试唤醒 Docker Desktop，仍不可用时直接失败。
- 强审查失败时，Agent 应询问用户是安装/启动 Docker 后重试，还是改用弱审查。
- 如果弱审查发现 high 或 critical 风险，在总结报告后建议用户升级到强审查。
- 如果 Agent 负责安装 skill，建议在启用前自动运行弱审查；发现 high 或 critical 风险时，先展示报告并等待用户确认。

## Enforced Install Workflow

如果你希望“安装后自动审查”成为强制机制，不要把新 skill 直接放进启用目录。使用隔离区安装器：

```bash
scripts/install-reviewed-skill /path/to/new-skill <codex-skills-dir>
```

安装流程：

```text
source skill
  -> <codex-skills-dir>/_pending/<skill-name>
  -> weak review
  -> write .skill-review.json
  -> enable only when no high/critical findings exist
```

通过审查后，skill 会移动到：

```text
<codex-skills-dir>/<skill-name>
```

如果发现 high 或 critical 风险，安装器会停止启用流程，目标会保留在：

```text
<codex-skills-dir>/_pending/<skill-name>
```

审查报告和凭证会保留在 pending 目录中：

```text
.skill-review-output/report.md
.skill-review-output/report.json
.skill-review.json
```

`.skill-review.json` 记录审查级别、分数、最高风险级别、finding 数量、目标哈希和报告位置。Agent 或安装管理器可以把它当作启用前的审查凭证。

## Quick Start

在仓库根目录运行以下命令，验证运行时并扫描当前发布包：

```bash
OUT="${TMPDIR:-/tmp}/skill-review-output"
scripts/verify-runtime
scripts/skill-security-review scan . --review-level weak --out "$OUT"
ls "$OUT"
```

输出应包含 `report.md` 和 `report.json`。

## Installation

可以把本仓库放入你的 Codex skills 目录：

```bash
git clone https://github.com/lanewulll/skill-security-review.git <codex-skills-dir>/skill-security-review
```

也可以在任意目录直接运行：

```bash
./scripts/skill-security-review scan /path/to/skill --review-level weak --out skill-review-output
```

### Requirements

- Python 3，用于执行 `assets/skill-security-review.pyz`。
- Docker，可选；仅强审查需要。
- 审计镜像 `skill-review-audit:local`，可选；仅强审查需要。

## Manual CLI Usage

### Scan a Directory

```bash
scripts/skill-security-review scan /path/to/skill --review-level weak --out skill-review-output
```

### Scan a Zip Package

```bash
scripts/skill-security-review scan /path/to/skill.zip --review-level weak --out skill-review-output
```

### JSON Output

```bash
scripts/skill-security-review scan /path/to/skill --review-level weak --json-only
```

### CI Thresholds

让 CI 在达到指定风险等级时失败：

```bash
scripts/skill-security-review scan /path/to/skill --fail-on high
```

### Reviewed Install

将本地目录或 `.zip` 包通过隔离区审查后安装：

```bash
scripts/install-reviewed-skill /path/to/skill <codex-skills-dir>
scripts/install-reviewed-skill /path/to/skill.zip <codex-skills-dir>
```

默认使用弱审查。需要强审查时：

```bash
scripts/install-reviewed-skill /path/to/skill <codex-skills-dir> --review-level strong
```

## Review Levels

| Level | What runs | Executes target code | Requirements |
| --- | --- | --- | --- |
| `weak` | 静态规则扫描、包结构检查、报告生成 | No | Python 3 |
| `strong` | 弱审查 + Docker 动态沙箱审查 | Only inside the audit sandbox | Python 3, Docker, `skill-review-audit:local` |

弱审查适合日常审查、CI 快速检查和不可信包的初步筛查。强审查适合发布前复核或需要观察运行行为的场景。

强审查采用 fail-closed 语义：如果 Docker CLI、Docker daemon 或审计镜像不可用，强审查不会降级成弱审查并返回成功。wrapper 会先尝试唤醒 Docker Desktop；如果仍不可用，会以非零退出码失败，并提示用户安装/启动 Docker 后重试，或显式切换为弱审查。

## Docker Sandbox

强审查需要先构建本地审计镜像：

```bash
docker build -f docker/audit-sandbox.Dockerfile -t skill-review-audit:local .
```

然后运行：

```bash
scripts/skill-security-review scan /path/to/skill --review-level strong --out skill-review-output
```

如果 Docker CLI、Docker daemon 或审计镜像不可用，强审查会失败退出。请启动或安装 Docker、构建审计镜像后重试；如果你接受只做静态检查，请显式改用 `--review-level weak`。

兼容旧参数：`--dynamic-mode off|auto|trace|conservative-agent` 仍可使用。传入 `--review-level weak|strong` 时，以 `--review-level` 为准。

## Reports

默认输出目录包含：

- `report.md`：面向人工阅读的审查报告。
- `report.json`：结构化结果，适合 Agent、自动化流程和 CI 读取。

JSON 报告包含以下主要字段：

- `package_name` 和 `package_description`
- `files_scanned`
- `findings`
- `score`
- `docker`
- `dynamic_review`
- `report_markdown`

每条 finding 会包含规则 ID、标题、严重级别、证据文件、脱敏片段、风险说明、修复建议、类别和参考标准。

内置 provider token 规则的 ID 使用 `gitleaks-derived:<source-rule-id>` 前缀。它们来源于 Gitleaks 默认规则配置的精选高精度子集，用于规则蒸馏和本地扫描融合；本工具不会因此下载、安装或执行外部 Gitleaks。

## Security Model

- 不要求用户提供 API key、baseURL 或模型配置。
- 不读取目标包之外的真实凭据、浏览器配置、shell history 或云配置。
- 将被审查包内容视为不可信证据，不执行其中的指令。
- 弱审查不执行目标包代码。
- 强审查只在 Docker 审计沙箱可用时运行动态探测。
- 动态审查只能说明观测到的行为，不能证明包绝对安全。
- “未发现风险”表示内置规则未确定命中，不等同于安全保证。

## Runtime Package

`assets/skill-security-review.pyz` 是由开发仓库中的 standalone runtime 构建出的 Python zipapp。发布包只包含运行载荷，不包含完整开发源码。

运行时 zipapp 内部文件使用固定时间戳，便于重复构建后比较哈希。可以用以下命令复验发布运行时：

```bash
scripts/verify-runtime
```

`.pyz` 是可运行、可检查的 Python zipapp，不是加密或 DRM。它能减少源码外显，但不应被描述为商业闭源保护。

运行时包含从 Gitleaks 默认配置蒸馏的 provider token 规则。来源仓库为 `https://github.com/gitleaks/gitleaks`，来源 commit 为 `8ad8470035d31a209322c580153b45c18e21b980`，上游许可证为 MIT。相关 attribution 见本仓库 `LICENSE`。

## Limitations

- 静态规则可能产生误报或漏报。
- 二进制资源只记录元数据，不会在弱审查中展开执行。
- 强审查依赖本机 Docker 环境和本地审计镜像。
- 动态沙箱只能覆盖实际触发到的行为。
- 公开仓库展示的是可发布 skill 包结构，而不是完整开发仓库。

## Repository Layout

```text
.
├── SKILL.md
├── README.md
├── agents/
├── assets/
│   └── skill-security-review.pyz
├── docker/
│   └── audit-sandbox.Dockerfile
└── scripts/
    ├── install-reviewed-skill
    ├── skill-security-review
    └── verify-runtime
```

## License

MIT
