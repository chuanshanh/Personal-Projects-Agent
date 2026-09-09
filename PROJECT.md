# Project Agent

## 1. Product Positioning

Project Agent 是一个面向个人使用的：

**项目管理 + 自我探索 Agent**

核心目标不是做复杂的传统项目管理软件，而是解决这个问题：

> ChatGPT 能给出很多规划和建议，但这些内容容易埋在聊天记录里，难以真正执行、打勾、修改、调整和复盘。

Project Agent 要把：

**建议 → 任务 → 执行 → 状态变化 → 复盘**

连接成一个持续运行的系统。

第一阶段只服务单个用户，不考虑商业化、多用户和复杂权限。

---

## 2. Core Product Principles

### 2.1 Reduce Cognitive Load

Agent 的首要目标是：

**减少用户认知负担，而不是制造更多任务。**

默认行为：

- 优先读取已有项目和任务
- 不轻易创建大量新任务
- 对模糊目标默认最多给出 3 个 next actions
- 如果待办过多，优先建议删除、延期、休眠或降低优先级
- 计划可以随时调整
- 不追求严格执行原计划

---

### 2.2 State Over Chat

重要建议不能只停留在聊天文本中。

如果 Agent 建议：

- 创建任务
- 完成任务
- 修改任务
- 延期任务
- 删除任务
- 修改项目

应该尽量通过真实 tool call 更新系统状态。

核心原则：

> Advice should become state.

---

### 2.3 Mobile First

产品主要使用场景是：

**手机上随手打开，快速查看、完成、调整任务。**

目标体验：

用户应尽量可以在几十秒内完成一次操作。

例如：

> “把今天的 Tool Calling 标记完成，明天新增一个部署任务。”

Agent 执行后，页面立即更新。

---

## 3. MVP Scope

当前目标不是完整 Personal OS。

### V0.1 必须实现

- 创建项目
- 查看项目
- 编辑项目
- 删除项目
- 创建任务
- 修改任务
- 完成任务
- 删除任务
- Dashboard 查看当前项目和任务
- 数据持久化
- 手机端基本可用

### V0.1 Agent 能力

用户可以通过自然语言：

- 创建项目
- 创建任务
- 修改任务
- 完成任务
- 删除任务
- 查询项目状态

Agent 必须调用真实工具修改数据，而不是只返回建议。

---

## 4. Core User Story

用户输入：

> 最近我想准备 Agent 实习。我先做这个项目管理 Agent，不想一开始系统学很多东西，帮我建立一个项目。

Agent 创建：

Project:

- Agent Internship Preparation

Tasks:

- 定义 Project Agent MVP
- 跑通 Agent + Tool Calling
- 完成自然语言修改任务

之后用户输入：

> 第二个已经完成了，但是今天比较累，把第三个推迟一下。

Agent 应：

- 完成第二个任务
- 修改第三个任务
- 保存真实状态
- 刷新 UI

---

## 5. Main Views

### Today

用于每天快速打开。

优先显示：

- 当前重点项目
- 今日最重要任务
- 最多展示少量任务，避免信息过载
- Agent 快速输入框

---

### Projects

显示：

- 项目名称
- Goal
- Status
- Progress
- Tasks

支持：

- 新增
- 修改
- 完成
- 删除

---

### Explore

这是 Project Agent 区别于普通 Todo 软件的重要方向。

当前版本可以先保持简单。

未来用于记录：

- 我想探索什么
- 我的假设是什么
- 我做了哪些真实尝试
- 每次体验如何
- 是否还想继续
- Agent 基于长期行为进行总结

示例：

> “我是否真的喜欢 Agent 开发？”

---

## 6. Exploration Concept

未来支持 Experiment。

Experiment 包含：

- title
- hypothesis
- start date
- end date
- status

Check-in 可以记录：

- 做了什么
- mood
- interest
- want_to_continue
- note

重点不是“情绪日记”。

重点是：

> 用真实行为积累关于自己的证据。

---

## 7. Data Model

当前优先保持简单。

### Project

- id
- name
- description
- goal
- status
- created_at

### Task

- id
- project_id
- title
- status
- priority
- due_date
- created_at
- completed_at

未来再增加：

- Experiment
- CheckIn
- Review

---

## 8. Agent Tools

第一阶段优先支持：

- create_project
- get_projects
- update_project
- delete_project
- create_task
- update_task
- complete_task
- delete_task
- get_project_status

所有 tool 必须真实操作数据库。

---

## 9. Model Strategy

不要把系统强绑定到单一模型供应商。

目标：

**provider-agnostic**

模型配置至少应可独立修改：

- provider
- model name
- base URL
- API key

优先选择：

- 成本低
- 支持 tool/function calling
- 国内方便充值
- 后续容易切换 OpenAI

普通任务优先走低成本模型。

复杂规划和复盘未来可以单独使用更强模型。

---

## 10. Current Technical Direction

MVP 优先：

- Python
- Streamlit
- SQLite

根据需要加入：

- LLM API
- Tool Calling

暂时不要因为“架构更先进”主动增加：

- LangGraph
- Multi-Agent
- Docker
- Kubernetes
- 微服务
- 复杂前后端分离

除非真实需求已经证明有必要。

---

## 11. Not Now

当前明确不做：

- 多用户
- 登录系统
- 社交
- 团队协作
- 原生 iOS App
- Android App
- 复杂日历系统
- 完整知识管理
- 多 Agent 编排
- 成长等级
- 游戏化
- AI 自动规划整个人生
- 商业化
- 复杂数据分析

---

## 12. Development Philosophy

开发顺序：

**可运行 > 好看**

**真实使用 > 功能数量**

**解决痛点 > 技术炫技**

**用户行为 > 产品想象**

每个版本优先保证：

1. 能运行
2. 能使用
3. 数据不会丢
4. 可以真实解决一个问题

然后再增加功能。

---

## 13. Iteration Rule

真实使用过程中发现的问题统一记录为：

### Pain Points

例如：

- 首页任务太多，让人有压力
- Agent 总是创建太多 Todo
- 想快速延期任务但操作复杂
- 手机端输入体验不好
- 不知道这一周真正推进了什么

不要一发现问题就马上加入复杂功能。

先观察它是否重复发生。

真实出现多次的问题，才提升为 Product Requirement。

---

## 14. Current Priority

当前最高优先级：

> **让 Project Agent 达到“我愿意每天在手机上真实使用”的状态。**

当前开发优先级顺序：

1. Project / Task 基础功能稳定
2. 手机端 UI 可用
3. 数据持久保存
4. 自然语言 Agent 操作 Task
5. 开始真实使用
6. 收集 Pain Points
7. 再决定下一版本

---

## 15. Definition of MVP Done

以下条件全部满足后，停止继续扩展 V0.1：

- [x] 能创建 Project
- [x] 能创建 Task
- [x] 能完成 Task
- [x] 能修改 Task
- [x] 能删除 Task
- [x] Dashboard 能查看状态
- [x] 数据重启后仍存在
- [ ] 手机网页可正常使用
- [x] Agent 可以通过自然语言修改真实 Task

2026-09-09 验收证据与剩余缺口见 `V0_1_REVIEW.md`。自然语言真实模型 API 验收已通过；手机网页仍须实际操作后勾选。

达到以后：

**立即进入真实使用，而不是继续增加功能。**
