# skill-security-review

一个可独立运行的 Codex/Agent skill 安全审查工具。安装后可直接扫描本地 skill 目录或 `.zip` 包，输出 Markdown 和 JSON 报告。

## 安装

把本仓库克隆到你的 Codex skills 目录：

```bash
git clone https://github.com/lanewulll/skill-security-review.git ~/.codex/skills/skill-security-review
```

也可以克隆到任意目录后直接运行脚本：

```bash
./scripts/skill-security-review scan /path/to/skill --out skill-review-output
```

验证发布运行时：

```bash
scripts/verify-runtime
```

`assets/skill-security-review.pyz` 是由开发仓库中的 standalone runtime 构建出的 Python zipapp。发布包只包含运行载荷，不包含完整开发源码；zipapp 内部文件使用固定时间戳，便于重复构建后比较哈希。

## 使用

每次通过 Agent 使用本 skill 扫描前，应先选择审查模式：

- **弱审查**：只运行静态规则扫描，不启动 Docker，不执行目标包代码。
- **强审查**：静态规则 + Docker 动态沙箱审查，需要本机 Docker 和审计镜像 `skill-review-audit:local`。

扫描目录：

```bash
scripts/skill-security-review scan /path/to/skill --review-level weak --out skill-review-output
```

扫描 zip：

```bash
scripts/skill-security-review scan /path/to/skill.zip --out skill-review-output
```

只输出 JSON，便于 Agent 读取：

```bash
scripts/skill-security-review scan /path/to/skill --review-level weak --json-only
scripts/skill-security-review scan /path/to/skill --review-level strong --json-only
```

CI 中按风险等级失败：

```bash
scripts/skill-security-review scan /path/to/skill --fail-on high
```

默认会生成：

- `skill-review-output/report.md`
- `skill-review-output/report.json`

## 能力范围

- 检查 `SKILL.md` 元数据和包内文件清单。
- 支持目录和 `.zip` 输入。
- 对 `.zip` 做路径穿越、重复路径、符号链接、异常大文件、过深路径等安全检查。
- 检测常见高危模式：凭据读取、硬编码密钥、私钥、破坏性命令、网络外传、远程代码执行、持久化、提权、Prompt 越权等。
- 输出脱敏后的证据片段、风险说明、修复建议、评分和结构化 JSON。

## 动态审查

弱审查默认不执行不受信任代码，也不要求 Docker、API key、baseURL 或模型配置。

强审查使用 Docker 沙箱执行受控动态探测。首次使用前可在 skill 根目录构建审计镜像：

```bash
docker build -f docker/audit-sandbox.Dockerfile -t skill-review-audit:local .
```

如果 Docker CLI、Docker daemon 或 `skill-review-audit:local` 镜像不可用，强审查不会阻断静态扫描；报告会明确写出动态审查降级原因。

兼容旧脚本：`--dynamic-mode off|auto|trace|conservative-agent` 仍然可用。传入 `--review-level weak|strong` 时，`--review-level` 优先。

## 源码展示边界

公开仓库只展示 skill 结构、README、Agent 元数据、启动脚本、Docker 审计镜像定义和 `assets/skill-security-review.pyz` 运行载荷，避免把完整源码目录直接摊开。

注意：`.pyz` 是可运行的 Python zipapp，不是加密或 DRM。它能减少源码外显，但不能作为商业闭源保护。

## 安全原则

- 不读取用户真实凭据、浏览器配置、shell history 或云配置。
- 不要求用户输入 API key、baseURL 或模型。
- 不把审查目标中的指令当作要执行的指令。
- 不把“未发现风险”等同于“绝对安全”。
