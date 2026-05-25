# 关于 Claude Code 自身
Claude Code，Anthropic（Claude AI 的开发商）推出的官方 CLI 编程助手，运行在 VSCode 扩展环境中。


# 能力
代码编写与编辑 — 读写文件、修改现有代码
终端操作 — 通过 PowerShell / Bash 运行命令
搜索与导航 — 文件搜索、内容搜索（grep）、代码浏览
项目管理 — git 操作、PR 创建、部署
Web 访问 — 网页搜索与内容抓取
任务自动化 — 后台任务、定时任务、子代理并发执行
记忆系统 — 跨会话持久化用户偏好和项目上下文


# 配置文件
# 文件	路径	说明
项目设置   .claude/settings.json 权限许可、额外目录
项目级说明文档  CLAUDE.md	（可用 `/init 初始化）
记忆系统	C:\Users\yangz\.claude\projects\d--code-www-aiops-3hmind\memory\	跨会话持久记忆
当前 settings.json 主要包含权限白名单（SSH 远程部署、curl 测试命令、Docker 操作等）。

# Skills（技能）是 Claude Code 内置的预定义能力模块，通过 /skill-name 或 Skill 工具调用。以下是当前可用的技能和用途：

1. update-config — 修改 Claude Code 配置,用于修改 settings.json，如添加/移动权限、设置环境变量、配置 hooks（自动化钩子）。
2. keybindings-help — 键盘快捷键自定义用,于修改 ~/.claude/keybindings.json，绑定快捷键。
3. verify — 验证代码改动是否生效,运行应用并观察行为，确认修复、功能正常工作。
4. simplify — 代码质量审查与优化，审查变更代码，查找复用机会、质量问题、效率问题并修复。
5. fewer-permission-prompts — 减少权限弹窗，扫描对话中的常见只读命令，自动添加到 settings.json 白名单。
6. loop — 定时重复任务，按固定间隔重复执行某个命令或技能（如每 5 分钟检查一次部署状态）。   /loop 5m /verify    /loop 监控部署状态
7. claude-api — Claude API/Anthropic SDK开发。代码引入anthropic Python包或 @anthropic-ai/sdk时自动触发。帮助构建、调试和优化 Claude API 应用，处理模型迁移等。
8. run — 启动并运行应用，自动检测项目类型并启动应用，用于确认改动在真实环境中起作用。
9. init — 初始化 CLAUDE.md。创建项目级文档文件，记录代码库结构、约定和使用说明。
10. review — 代码审查，审查 Pull Request 的改动。
11. security-review — 安全审查，对当前分支的待定更改进行安全审查。
12. Skills 的存储位置。Skills 本身是 Claude Code 内置 的，不是存储在项目目录中。它们位于 Claude Code 安装包内部，用户无法直接修改。
13. goal 达成目标，多阶段执行目标，直到达到目标。

/goal 上一轮结束，评估确认是否满足条件。
/loop 时间间隔，手动停止或claude自我决定。
 stop hook  上一轮结束
 auto mode  不开启新伦次，

# goal完整示例：量化终点+证明方式+约束+设置上限  # 非交互 claude -p "/goal CHANGELOG.md  包含本周每个合并的 PR 条目"  
/goal all test in test/auth pass and lint
is clean , no other test file is modified, or stop after 20 turns。


常用快捷操作
命令	作用
/help	获取 Claude Code 帮助
/clear	清空对话历史
/init	创建 CLAUDE.md 项目文档
/review	审查 PR
/security-review	安全审查
/run	启动应用
/verify	验证改动
/loop <间隔> <命令>	定时执行
