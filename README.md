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

## 使用

扫描目录：

```bash
scripts/skill-security-review scan /path/to/skill --out skill-review-output
```

扫描 zip：

```bash
scripts/skill-security-review scan /path/to/skill.zip --out skill-review-output
```

只输出 JSON，便于 Agent 读取：

```bash
scripts/skill-security-review scan /path/to/skill --dynamic-mode off --json-only
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

公开版为了让别人安装后立刻能独立扫描，默认不执行不受信任代码，也不要求 Docker、API key、baseURL 或模型配置。

`--dynamic-mode auto|trace|conservative-agent` 会在报告中记录动态审查降级原因；基础审查不会因此阻断。需要真正 Docker 沙箱执行时，应在私有完整版或后续增强版中扩展。

## 源码展示边界

公开仓库只展示 skill 结构、README、Agent 元数据、启动脚本和 `assets/skill-security-review.pyz` 运行载荷，避免把完整源码目录直接摊开。

注意：`.pyz` 是可运行的 Python zipapp，不是加密或 DRM。它能减少源码外显，但不能作为商业闭源保护。

## 安全原则

- 不读取用户真实凭据、浏览器配置、shell history 或云配置。
- 不要求用户输入 API key、baseURL 或模型。
- 不把审查目标中的指令当作要执行的指令。
- 不把“未发现风险”等同于“绝对安全”。
