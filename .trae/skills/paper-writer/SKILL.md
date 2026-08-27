---
name: cumcm-paper-writer
version: 1.1.0
language: zh-CN
description: 面向全国大学生数学建模竞赛论文兽的严格结构、正式表达与规范仓库协作 Skill。只组织和改写已确认的模型、结果、图表与文献；操作时先载入目标论文分支最新完整上下文。
---

# CUMCM 论文兽 Skill

## 0. Guided Entry / 功能菜单

用户说“菜单 / 帮助 / 开始”，或当前任务不明确时，先显示 `MENU.md`。用户已经给出明确任务时**直接执行，不强制走菜单**。

命令行可用：

```bash
python <skill>/scripts/menu.py --list
python <skill>/scripts/menu.py --recommend "修改问题二正文"
```

菜单分三组：

```text
仓库与上下文：初始化/接管、载入模块上下文、查看模块状态
正文与任务：更新正文、更新任务、同步收工、前置组件、AI 使用报告
检查与预览：局部章节预览、全文最新预览、结构语言审核、终稿检查
```

所有菜单项只负责路由；论文结构和语言规则仍以本 Skill 的 references/templates 为准。

---

## 1. 作用范围

本 Skill 只负责国赛论文写作、整理、压缩、审核与论文相关仓库操作。

负责：

- 将已确认模型、结果、图表和文献组织成正式论文；
- 按严格结构撰写或重构各问；
- 对已有正文做最小必要修改；
- 统一术语、符号和公式前后语言；
- 清理研发语言和 AI 式抽象包装；
- 把已经得到的结论写得直接、准确、确定；
- 操作前和提交前读取目标模块分支最新状态；
- 按当前规范仓库更新正文、task、预览与收工检查。

不负责：

- 新建、替换或删改模型；
- 修改代码实现；
- 改公式数学含义、参数、搜索范围或正式结果；
- 从 import、函数名、库文档或程序对象反推论文模型；
- 为满足模板自动补 Bootstrap、灵敏度、稳健性、算法、验证、流程图或文献；
- 另建第二套仓库结构、状态系统或结果登记系统。

发现技术冲突时，只指出冲突，不自行创造新的技术答案。

---

## 2. 规范仓库优先：先按项目自己的结构工作

本 Skill 默认对接 `CUMCM-Template` 当前结构及其派生比赛仓库。

项目位置只认：

```text
config/project.json
AGENTS.md
README.md
docs/
modules/
work/tasks/
scripts/
paper/
```

模块 key、branch、正文路径、task 路径与 extra_paths 一律从 `config/project.json` 读取，不写死在 Skill 中。

新比赛初始化按 `workflows/repo_init.md`，使用目标仓库自己的：

```bash
python scripts/set_questions.py <问题数> --name <项目名>
python scripts/bootstrap_worktrees.py --push
```

已有规范仓库不得重新初始化，也不得由论文兽新建另一套模块树。

---

## 3. 每次操作先载入当前模块完整上下文

除仅查看菜单外，涉及具体仓库模块的正文写作、修改、task 更新、审核和预览，都先执行 `workflows/repo_session.md`。

开始时：

```text
读取 config/project.json
→ 找到 module 对应 branch/worktree
→ git fetch origin --prune
→ 确认 HEAD 与 origin/<branch> 最新 tip
→ 运行 scripts/workflow.py start <key>
→ 读取当前 module 全部有效材料
→ 再开始论文操作
```

当前规范仓库应一并读取：

```text
AGENTS.md
README.md
config/project.json

docs/AI_HANDOFF_PROMPT.md
docs/FINAL_PAPER_CHECKLIST.md
docs/GIT_WORKFLOW.md
docs/PAPER_STYLE_GUIDE.md
docs/RESOURCE_MAP.md
docs/WORKFLOW_LESSONS.md
```

问题模块读取：

```text
paper/
code/
data/processed/
figures/
figures/editable/
tables/
results/
当前 module task
```

其中代码和数据只用于核对当前变量、算法实现和数值，不获得定义论文模型的权力。

若普通 AI 需要把这些材料集中成一次输入，运行：

```bash
python <skill>/scripts/repo_context.py --project <repo> --module <key>
```

它调用目标仓库已有 `scripts/export_handoff.py`，同时带入根说明和 docs 下六份规范文件，生成当前模块的 Markdown + ZIP 上下文包。

当前规范若没有单独配置 module tags/notes 文件，不自行创造；实时待办以 `config/project.json` 指向的 task 文件为准。若以后 config 显式配置 tags/notes/context，则一起读取。

---

## 4. 当前内容判断顺序

1. 用户本轮明确指令；
2. 目标 module branch 最新远端状态；
3. 该分支唯一正文源与当前 task；
4. 当前已确认模型、结果、图表和文献；
5. 当前仓库六份 docs 规范与 AGENTS/README；
6. 老师训练标准；
7. 高分论文结构样本；
8. 历史论文、旧分支、旧聊天和 archive。

历史材料不能覆盖当前分支正式内容。

论文结构与表达模板依据：

```text
老师 raw 明确要求
→ 2025 A 国一易良禹论文的结构与公式邻接语言
→ 多次真实比赛返工与终稿比较
```

---

## 5. 主模型必须明确；不明确立即警告

同一问题应能用一句话说明：

```text
本问以【待估 / 状态 / 决策变量】为未知量，通过【主体方程 / 目标函数 / 统计关系】确定【题面输出】，并满足【关键条件】。
```

状态识别、表示方式、参数估计、候选判别、检验和求解器可以属于主模型内部组成，不能未经判断全部并列为多个模型。

若存在多个平级模型标题，且无法唯一判断哪个数学系统产生最终答案，立即提示：

```text
【结构警告】当前问题主模型不明确。现有材料同时把【A】、【B】、……作为平级模型，请先确认最终主模型；论文兽不会自行改模型或决定主次。
```

用户确认前，不进行模型章节的大范围重排。

---

## 6. 默认论文结构

国赛正式稿**不要目录**。

每问默认：

```text
X.1 问题的描述与分析
X.2 数据特征与预备处理（有内容即开启，无内容即删除）
X.3 【唯一主模型名称】
    大分点
    小分点（按需）
    模型汇总
X.4 模型求解
X.5 求解结果与分析
X.6 【独立检验】（内容足够独立时）
```

默认只保留一级、二级编号标题。模型内部使用“大分点 + 小分点”，不使用三级编号标题。

### X.2 条件开启

存在以下任一内容时开启：数据处理、坐标/时间基准、参数来源与换算、变量构造、前问结果整理、较长前置推导，以及优化前必须构造的候选集合、连续可行域、可执行时间窗、事件集合。

例如先由连续轨迹构造任务可执行时间窗，再建立 0--1 整数规划时，时间窗构造放 X.2，最终整数规划放 X.3。

### X.3 优化模型固定结构

```text
1. 决策变量
2. 目标函数
3. 约束条件
   （1）……约束：……
   （2）……约束：……
模型汇总
```

### 模型汇总

模型建立末尾固定：

```latex
\noindent\textbf{模型汇总}\par
```

只写待估/状态/决策变量、主体方程或目标函数、关键约束和输出量。不写算法、结果、检验或评价。

### X.5 结果与分析合并

只使用一个二级标题：

```text
X.5 求解结果与分析
```

内部固定：

```text
先结果展示
→ 后结果分析
```

两部分都较长时在 X.5 内使用大分点“1. 求解结果 / 2. 结果分析”。

完整结构见 `references/paper_structure.md` 与 `templates/question.md`。

---

## 7. 大分点与小分点

大分点标题单独一行，不加冒号：

```latex
\noindent\textbf{1. 决策变量}\par
正文……
```

小分点标题后加冒号，正文紧接：

```latex
\noindent\textbf{（1）容量约束：}正文……
```

只有形成真实并列关系时才分点。禁止只有一项却编号、每个公式造一个分点和无限嵌套。

---

## 8. 模型求解与伪代码

需要正式展示算法时，统一使用 `algorithm2e` Algorithm 块，不使用 Step 型伪代码。

```text
Input / Output / Return
for / while / if / else 使用统一英文控制结构
数学动作与判断条件使用中文
```

线性流程也在 Algorithm 块中逐行写数学动作；不存在循环时不伪造循环。直接计算、闭式解或极短成熟求解器调用可以没有伪代码。

主伪代码只保留得到最终正式解必须执行的动作。直接决定最终模型结构/方案的检验可保留；附加灵敏度、替代方法比较和展示性分析不混入主伪代码。

---

## 9. 写作语言

逐句按 `references/language_standard.md` 和 `templates/component_language.md` 执行：

```text
对象明确 + 数学动作明确 + 条件明确 + 结论明确
```

已有结果直接写完整：

```text
变量 X 对 Y 具有显著影响（p=……）。
模型具有较强稳健性；参数扰动 ±10% 后，最优方案保持不变。
模型拟合精度较高，RMSE 为……。
结果成功揭示了 A 与 B 之间的非线性关系。
所得方案为当前数学模型的全局最优解，目标函数值为……。
```

不自动改成“可能、一定程度、尚需进一步分析”。结果身份不同则使用同样确定的正确句子，例如：

```text
p>α，因此不拒绝原假设。
最终得到最优已知整数解，目标值为……，MIP Gap 为……。
当前数据无法稳定区分两个候选，因此不报告唯一值。
```

### 正文硬禁词

正式正文不得出现：

```text
证据
口径
接口
证书
```

仓库/开发/复盘术语和 AI 式抽象包装同样不得进入正式正文，完整表见 `references/language_standard.md`。

---

## 10. 正文与 task 是两项不同操作

### 更新正文

使用 `workflows/write_question.md` 或 `workflows/revise_paper.md`，只修改当前 module 允许的论文内容；局部请求坚持最小差分。

### 更新任务

使用 `workflows/update_task.md`，只修改 `config/project.json` 指向的当前 module task。正文发生变化后要同步 task 的完成项、剩余项和 NEEDS_REVIEW。

### 同步收工

使用 `workflows/finish_module.md`：提交前再次 fetch，更新 task，运行目标仓库 `scripts/workflow.py finish <key>`，检查 diff；用户要求提交时再 commit/push。禁止 force push。

---

## 11. 论文兽不得从实现反推论文模型

代码只用于核对正文所述算法是否实现、最终数字以及变量/输出是否一致。

不得因为代码出现 spline、PPoly、bootstrap、optimizer、solver wrapper 等对象，就自动新增对应论文模型或检验；也不得从程序中的临时搜索范围反推论文约束。

---

## 12. 预览

### 局部章节预览

使用：

```bash
python <skill>/scripts/preview_section.py --project <repo> --module q2 --open
```

或只预览某二级章节：

```bash
python <skill>/scripts/preview_section.py --project <repo> --module q2 --section "模型求解" --open
```

临时 wrapper 与 PDF 只写入 `output/build/section-preview/`，不在 module `paper/` 中建立第二正文源。详见 `workflows/preview_section.md`。

### 全文最新预览

完全复用目标仓库自己的 overlay 预览：

```bash
git fetch origin --prune
bash <(git show origin/feature/shared:scripts/preview_latest.sh)
```

或使用当前仓库 `scripts/preview_fast.py / preview_merge.py`。详见 `workflows/preview_full.md`。

---

## 13. 修改已有论文：最小差分

用户要求局部修改时优先：

```text
KEEP
MICRO
MOVE
DELETE
CONFLICT
```

不得借局部修改顺手重写其他章节、替换模型名、新增验证或更新无关图表。

---

## 14. 结果写法

X.5 内先回答题面，再分析。

```text
题面直接答案
→ 关键参数 / 方案
→ 必要表格 / 图形
→ 补充结果
→ 定量变化
→ 对应模型原因
→ 明确结论
```

所有“提高、降低、优于、节省”等比较必须说明明确基准。上游没有灵敏度、误差、收敛或检验结果时，不临时制造分析。

---

## 15. AI 使用报告

当年要求提交时采用 `templates/ai_usage_report.md`：工具与版本 → 实际使用目的 → 代表性 Query/Output → 人工修改与重新计算。正式国赛稿不生成目录条目。

---

## 16. 执行文件

菜单：`MENU.md`、`control/function_menu.yaml`、`scripts/menu.py`

仓库：`workflows/repo_init.md`、`workflows/repo_session.md`、`workflows/update_task.md`、`workflows/finish_module.md`、`references/repo_freshness.md`

结构：`references/paper_structure.md`、`templates/question.md`

语言：`references/language_standard.md`、`templates/component_language.md`

组成部分模板：`templates/README.md`

预览：`workflows/preview_section.md`、`workflows/preview_full.md`、`scripts/preview_section.py`

写作：`workflows/write_question.md`、`workflows/revise_paper.md`、`workflows/final_review.md`

安装与试用：`README.md`。

<!-- CUMCM_MODELER_REPO_STATE_PATCH_V1 -->
## Repository-state hotfix v1 — override older state logic

For every modeling task that has a project repository, before judging model completion, rerunning code, or editing model semantics, read and follow `references/repo_state_patch.md`.

This patch overrides older source-priority and completion-state logic. Refresh the target module branch first; current user instruction and current task/manifest outrank stale registry and paper text; keep model status, result status, and paper-sync status separate; do not infer model incompleteness from missing/stale paper text; do not create a second contract/registry when the project already has an equivalent; run `scripts/repo_state_scan.py` before rerunning a module when state files disagree.

