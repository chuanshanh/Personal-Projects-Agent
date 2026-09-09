# Project Agent 🌱

个人使用的项目管理 MVP：Python + Streamlit + SQLite + OpenAI Agents SDK，单 Agent。

## 启动

Python 3.13，在项目根目录运行（PowerShell）：

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
$env:OPENAI_API_KEY = '你的 OpenAI API Key'
.venv/Scripts/python -m streamlit run app.py
```

打开 http://localhost:8501 。不配置 Key 也可以使用完整手动项目/任务管理。
也可复制 `.streamlit/secrets.toml.example` 为 `.streamlit/secrets.toml` 填写 Key。
默认模型 `gpt-4.1-mini`，用 `OPENAI_MODEL` 切换为账号可用且支持工具调用的模型。
Key 不要放入聊天、Git 或截图；本地 secrets 已被忽略。

### 切换模型供应商

模型配置独立于数据库和工具，环境变量优先于项目内 `.streamlit/secrets.toml`：

```toml
LLM_PROVIDER = "openai-compatible"
LLM_MODEL = "供应商提供的支持工具调用的模型名称"
LLM_BASE_URL = "https://供应商的API根地址/v1"
LLM_API_KEY = "供应商的API密钥"
```

`openai` 使用 Responses API；`openai-compatible` 使用兼容 Chat Completions 的接口。
切回 OpenAI 时设置 provider 为 `openai`、base URL 为 `https://api.openai.com/v1`，并替换 model 和 key。
旧的 `OPENAI_MODEL` / `OPENAI_API_KEY` 在 OpenAI 模式下仍可使用；`LLM_*` 同名用途配置优先。
兼容模式不会隐式使用 OpenAI 密钥。仅保证 OpenAI 兼容的工具调用协议接入；具体供应商仍需运行真实验收脚本，未接入非兼容协议或自动选择供应商。
修改配置后刷新应用；切换模型前清空对话，避免旧上下文影响验收。

## 使用

- **Today**：默认显示 3 个进行中项目、3 个今日/逾期待办；任务按高优先级、日期、ID 排序，其余折叠。任务显示所属项目，完整项目列表在 Projects。
- **Projects**：创建/编辑/删除项目；添加/修改/勾选完成/重新打开/删除任务。
- **Explore**：预留入口。
- **数据与备份**：下载一致性 SQLite 快照。

先输入：“最近我想准备 Agent 实习。我先做这个项目管理 Agent，不想一开始系统学很多东西，帮我建立一个项目。”
再输入：“第二个已经完成了，但是今天比较累，把第三个推迟一下。”
Agent 会读取真实 ID，调用工具更新，重新读取验证；页面在每轮结束后刷新。
未指定延期日期默认明天，未来任务则在原日期上加一天。日期按 Asia/Shanghai 处理。
相对延期由 `postpone_task` 读取 SQLite 当前截止日期计算，避免旧对话中的日期覆盖真实状态；回复必须包含最终保存的完整日期，且只有日期差准确时才使用“明天/后天”。
任务的空日期表示未排期，修改工具中 null 保持不变、空字符串清空。

## 数据与运行边界

默认数据库 `data/project-agent.sqlite3`，可通过 `PROJECT_AGENT_DB` 指定绝对路径。
每次工具操作独立事务提交；程序重启后同一路径的数据仍在。中途 API 失败可能已完成部分写入，界面会提醒并刷新，重试前应查看状态。
旧版数据库首次打开会自动升级为不复用删除 ID 的结构，保留原有字段、ID 和关系；升级前保留同目录 `.pre-v01.sqlite3` 备份。升级失败回滚，不清空数据。升级前已经被删除的历史 ID 无法追溯，首次升级后建议清空旧对话。
聊天上下文只在浏览器当前 Streamlit 会话内保留；项目与任务持久化。
不要同时发送多条 Agent 操作或在多个设备同时修改同一任务，此 MVP 未加入并发编辑冲突处理。

## 手机访问与部署

同一 Wi-Fi 下，本机运行：

```powershell
.venv/Scripts/python -m streamlit run app.py --server.address 0.0.0.0
```

iPhone Safari 打开 `http://电脑局域网IP:8501`，电脑需保持运行，防火墙需允许私有网络的此端口。
Safari 分享菜单可添加到主屏幕；这仍是网页，需要网络连接。

GitHub / Streamlit Community Cloud 部署步骤：

1. 将代码提交到自己的 GitHub 仓库，不提交数据库、Key 或 `.venv`。
2. 在 Community Cloud 选择仓库、分支、入口 `app.py`；Advanced settings 选择 Python 3.13。
3. 在应用 Secrets 粘贴本地 `.streamlit/secrets.toml` 的四个 `LLM_*` 配置，不上传该文件（OpenAI 模式仍兼容旧配置）。
4. 手机打开部署网址。

**托管限制**：不要把 Community Cloud 的本地 SQLite 当作长期可靠存储；重建/重新部署可能丢失文件。当前版本适合本地持久使用与云端试用，重要数据定期下载备份。需要可靠云端持久化时，把同一个应用部署到提供持久磁盘的主机，并设置 `PROJECT_AGENT_DB`，无需改数据库实现。

本产品没有登录系统。公开部署网址的访问者可以修改同一个数据库并使用服务器 API Key；个人使用应限制托管平台访问范围，或仅在可信局域网运行。
恢复备份：停止应用，用备份替换配置的 SQLite 文件后启动。不要在运行时覆盖数据库。

## 验证

```powershell
.venv/Scripts/python -m pip install pytest
.venv/Scripts/python -m pytest -q
# 配好环境变量或本地 secrets 后，运行真实模型验收（使用临时数据库，不改个人数据）
.venv/Scripts/python scripts/live_smoke.py
```

自动测试覆盖 CRUD、校验、跨进程持久化、备份、UI，以及 SDK 工具调度闭环。离线调度测试使用脚本化模型，不能代替真实模型验收。
验收缺口与证据见 [V0.1 审查记录](V0_1_REVIEW.md)。达到 PROJECT.md 的完成标准后停止扩展，进入真实使用。

## 文件

`app.py` 界面；`database.py` SQLite；`models.py` 校验与日期；`config.py` 模型配置；`tools.py` 十个数据库工具；`agent.py` 单 Agent 和会话；`tests/` 测试；`scripts/live_smoke.py` 真实模型验收。

Agent 采用官方 [Agents SDK](https://developers.openai.com/api/docs/guides/agents) 的 Agent、Runner 和 function_tool；未使用 React、FastAPI、多 Agent 或 Docker。
