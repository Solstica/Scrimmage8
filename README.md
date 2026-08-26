# CUMCM 通用协作与论文模板 v1.2

面向数学建模竞赛的三人/多人 + AI 协作模板。模板包含团队多场训练赛中实际使用并修正过的**标题、摘要、目录、正文标题层级、字体、页边距、行距、公式、三线表、插图尺寸、伪代码、代码附录、评价、参考文献和 AI 使用报告样式**，同时提供模块化 Git 协作、结果登记和临时全文预览。

核心原则：**单一真源、章节独立、固定路径、任务可见、结果可追溯、格式统一、责任域临时集成、稳定版本再进入 main。** 多场训练赛形成的操作经验另见 `docs/WORKFLOW_LESSONS.md`。

## 1. 新比赛开局

```bash
# 例：三问题赛题
python scripts/set_questions.py 3 --name 2026CUMCM-A

git add config/project.json paper/main.tex
git commit -m "chore: initialize contest structure"
git push

# 创建所有活动章节的独立分支和 worktree
python scripts/bootstrap_worktrees.py --push
```

模板默认按三问展示；如赛题为 1--4 问，使用 `set_questions.py` 调整。

## 2. 直接编译模板看格式

```bash
cd paper
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

默认应得到一份可直接删改的示例论文：

```text
第1页  标题 + 摘要
第2页  目录
正文第1页起  问题重述、符号说明、模型假设
问题一  完整结构示例：流程图、公式、模型汇总、伪代码、表格、双小图、检验
问题二/三  只保留一级标题
后续  模型评价、参考文献、附录代码示例、AI使用报告
```

目录可在 `paper/settings.tex` 切换：

```tex
\showtoctrue
% \showtocfalse
```

完整论文格式规范见 `docs/PAPER_STYLE_GUIDE.md`；终稿前必须再过一遍 `docs/FINAL_PAPER_CHECKLIST.md`。

## 3. 永久固定的资源路径

| 模块 | 唯一正文/资源位置 | 分支 |
|---|---|---|
| 摘要 | `modules/00_abstract/` | `feature/abstract` |
| 问题重述 | `modules/10_restatement/` | `feature/restatement` |
| 符号说明 | `modules/11_notation/` | `feature/notation` |
| 模型假设 | `modules/12_assumptions/` | `feature/assumptions` |
| 问题一 | `modules/20_q1/` | `feature/q1` |
| 问题二 | `modules/30_q2/` | `feature/q2` |
| 问题三 | `modules/40_q3/` | `feature/q3` |
| 问题四 | `modules/50_q4/` | `feature/q4` |
| 模型评价 | `modules/60_evaluation/` | `feature/evaluation` |
| 参考文献 | `modules/70_references/` | `feature/references` |
| 附录 | `modules/80_appendix/` | `feature/appendix` |
| AI使用报告 | `modules/90_ai_report/` | `feature/ai-report` |
| 跨问共享代码/预览脚本 | `shared/`、`scripts/` | `feature/shared` |
| 标题/目录/页码/公共样式 | `paper/` | `feature/paper-shell` |
| 官方原始附件 | `data/raw/` | 不随章节移动 |
| 外部补充数据 | `data/external/` | 不随章节移动 |
| 模块待办 | `work/tasks/<模块>.md` | 跟随对应模块分支 |
| 正式交付物 | `output/final/` | 稳定集成后生成 |
| 废弃路线 | `work/archive/` | 只读归档 |

更详细的地图见 `docs/RESOURCE_MAP.md`。固定位置不要反复向队友询问；先查资源地图或运行 `workflow.py start`。

## 4. 问题模块内部结构

```text
modules/30_q2/
├─ paper/q2.tex
├─ code/
├─ data/processed/
├─ figures/
│  └─ editable/
├─ tables/
└─ results/registry.csv
```

问题一另提供 `paper/q1_algorithm.tex` 作为伪代码格式示例。跨两个及以上问题共用的数值内核进入 `shared/`，不要复制多份。不要自行创造 `src/` 或并行结果目录。

`paper/` 中只保留唯一正文源及明确拆出的算法文件。不要新建 `q2_final.tex`、`references_final15.tex`、`q3_v2.tex` 等平行真源；旧稿移入 `work/archive/`。

## 5. 分支规则

长期活动分支按责任域，不按人名：

```text
main
├─ feature/shared
├─ feature/abstract
├─ feature/restatement
├─ feature/notation
├─ feature/assumptions
├─ feature/q1
├─ feature/q2
├─ feature/q3
├─ feature/q4
├─ feature/evaluation
├─ feature/references
├─ feature/appendix
├─ feature/ai-report
└─ feature/paper-shell
```

`main` 只保存稳定版本。不要创建 `feature/张三`、`final2`、`真的final` 或第二套 `document.tex`。

`chore/*` 只用于一次集中维护或迁移。若通过 squash merge 进入 `main`，旧 chore 分支通常会显示与 `main` 双向分叉；这并不表示还应再次 merge。先运行：

```bash
python scripts/branch_hygiene.py
```

确认综合提交已覆盖需要保留的内容后删除旧 chore 分支；下一轮维护从最新 `main` 新建新的 chore 分支。

## 6. 每次开工/收工

开始：

```bash
git status
git fetch origin --prune
git pull --ff-only
python scripts/workflow.py start <模块key>
```

结束：

```bash
python scripts/workflow.py finish <模块key>
git diff
git add <明确需要提交的文件>
git commit -m "feat(q2): 完成……"
git push
```

`workflow.py` 会显示固定资源位置和实时待办，并在结束时检查责任域外修改及“改了正文却没同步待办”的情况。

## 7. 实时待办

每个模块都有：

```text
work/tasks/<key>.md
```

新增任务、阻塞、风险、需要复核项和完成项必须实时写入，不只留在聊天中。

需要人工判断的内容统一标记：

```text
NEEDS_REVIEW / 需要复核
```

检查可由管理员或指定复核成员完成，不绑定某个固定角色。

## 8. 结果状态

问题模块 `results/registry.csv` 使用：

- `DRAFT`：正在计算/尚未验证；
- `VALIDATED`：已复算，等待最终检查；
- `FROZEN`：已完成规定检查，可进入正式论文。

另有 `review_state`：`NEEDS_REVIEW` / `CHECKED`。

正文关键数值应来自当前项目的 `FROZEN + CHECKED`。模型或代码改变且影响结果后，受影响结果重新回到 `DRAFT`。

**历史仓库或 `work/archive/` 中的 `FROZEN/CHECKED` 不得继承到当前项目。** 当前结果状态只认当前模块自己的 `results/registry.csv`。

## 9. 临时全文 Preview：责任域 Overlay，不做临时 Merge

多次训练赛已经证明：多个长期 feature 分支历史交叉后，用 `git merge` 临时拼全文会产生大量与正文无关的冲突；失败的 worktree 还可能阻塞下一次预览。因此模板采用：

```text
feature/paper-shell 作为排版底座
→ 对每个责任分支先做越界审计
→ 只把该责任域的 canonical 文件 overlay 到临时 worktree
→ 检查冲突标记、空白、引用、资源路径和结果状态
→ XeLaTeX/latexmk 编译
```

普通入口：

```bash
python scripts/preview_merge.py
```

快速纸面预览：

```bash
python scripts/preview_fast.py
```

最推荐的一键方式是在稳定仓库根目录运行：

```bash
git fetch origin --prune
bash <(git show origin/feature/shared:scripts/preview_latest.sh)
```

它会自动清理上次失败遗留的 controller/preview worktree，并始终使用远端 `feature/shared` 上最新的预览脚本。`preview_merge.py` 也会自动回收带模板 marker 的旧 preview，但不会删除普通目录。临时预览不会修改或合并任何正式 feature 分支。

若编译失败，优先处理日志中的**第一处硬错误**。第一遍 citation/reference warning 在编译被缺图、TeX 拼写或其他错误提前打断时，不等于最终引用失败。

## 10. 论文公共格式

除非比赛官方要求发生变化，默认不重新设计：

- A4，四边 25 mm；
- 中文正文 Windows 优先宋体，英文/数字优先 Times New Roman；
- 正文小四、段首 2 字符、1.38 行距基准；
- 题目三号加粗居中；
- 一级标题中文序号居中；二级 `4.1`；三级 `4.1.1`；
- 摘要标题与论文题目紧凑，摘要标题到正文略放开，各问之间保留小段距；
- 三线表 + 浅蓝表头；符号表额外增加少量行高；
- 单图 `0.44\textwidth`，双图总宽 `0.88\textwidth`，Origin 合成双面板整张 `0.88\textwidth`，流程图约 `1.0\textwidth`，机理图通常 `0.70\textwidth`；
- `algorithm2e` 伪代码；
- 参考文献默认 `\footnotesize`，约 15 条时优先争取一页排完；
- 参考文献、附录、AI使用报告各自另起一页；
- 正文从问题重述开始第 1 页。

详见 `docs/PAPER_STYLE_GUIDE.md` 和 `docs/FINAL_PAPER_CHECKLIST.md`。格式调整只在 `feature/paper-shell` 完成。

## 11. 终稿文字检查

最近几次训练赛形成的统一要求：

- “问题描述/预备工作/算法介绍”不要出现连续五六行以上的纯文字块；按逻辑分点，必要时用定义公式承载信息；
- 模型/算法第一次出现采用“中文名称（英文全称，缩写）”；
- 不把“物理口径、证据边界、统一链路、柔性释放/替代”等内部讨论语言写进正式正文；
- 模型汇总直接给数学模型，不用“目标函数直接写为”等口语引导；
- 算法说明至少给出一个核心排序/更新/定价公式，再接伪代码；
- 每张图表必须被正文引用并解释，图表与文字重复时删其一；
- 摘要只加粗模型、算法和关键结论，不整句加粗；
- 有界可行候选不能写成全局最优；跨问绝对指标在时间范围或终端结算未统一前不要直接解释成增量收益。

完整检查表见 `docs/FINAL_PAPER_CHECKLIST.md`。`final_preflight.py` 会额外检查 Git 冲突标记、可疑 TeX 拼写、缺失资源、平行正文源、过长纯文字段落和未被正文引用的图表标签。

## 12. 代码附录按提交规则二选一

若比赛另交源码：附录列“文件 + 功能”，正文只放必要核心片段。

若比赛**只交 PDF 且代码页不计正文页数**：用 `\lstinputlisting` 直接收入每问最终核心代码，不手工复制，以保证 PDF 与正式代码真源一致。模板 `modules/80_appendix/paper/appendix.tex` 已给两种模式。

## 13. 给普通聊天 AI 的自动交接

队友使用普通 ChatGPT、DeepSeek 等，不能自动读取完整 Git 仓库时，优先使用：

```bash
python scripts/export_handoff.py q2
```

默认生成：

```text
output/handoff/q2_handoff.md
output/handoff/q2_handoff.zip
```

只要单文件 Markdown：

```bash
python scripts/export_handoff.py q2 --format md
```

只要 ZIP：

```bash
python scripts/export_handoff.py q2 --format zip
```

需要附带当前只读参考，例如共享代码：

```bash
python scripts/export_handoff.py q2 --reference shared/code
```

需要迁移旧工程时，把旧资料先放进 `work/archive/`，再显式标记为 legacy：

```bash
python scripts/export_handoff.py q2 \
  --legacy work/archive/imports/s2_snapshot
```

导出包会自动区分：

```text
CURRENT             当前正式模块与实时待办
REFERENCE           当前只读参考
LEGACY_NOT_CURRENT  历史迁移材料
```

并在 `HANDOFF.md` 顶部生成 `HANDOFF_MANIFEST`，明确当前 canonical root、当前 registry 行数和状态、允许写入路径、legacy 路径等。默认不会把历史 registry 原文直接交给普通 AI，而是生成去身份化冲突摘要，避免旧 `FROZEN` 被误认成当前状态。

## 14. 仓库级 AI 与普通 AI 的区别

支持仓库级指令的 AI/Codex：

```text
读 AGENTS.md / README / RESOURCE_MAP / PAPER_STYLE_GUIDE / FINAL_PAPER_CHECKLIST / WORKFLOW_LESSONS
→ workflow.py start <key>
→ 在责任域内实际修改
→ 实时更新 work/tasks/<key>.md
→ workflow.py finish <key>
```

普通聊天 AI 没有仓库执行权限时：

- 不应声称自己已经运行 Git/Python/LaTeX；
- 不应声称已经真正修改仓库；
- 应给出准确仓库相对路径、替换文本/修改建议和 `NEEDS_REVIEW` 项；
- 由协作者落盘。

## 15. 检查层级

1. `scripts/structure_guard.py`：仓库结构、责任域、canonical 正文源和第二套全文源；
2. `scripts/final_preflight.py`：冲突标记、可疑 TeX、资源路径、过长文字段、图表引用、结果状态和 LaTeX 日志；
3. `scripts/preview_fast.py` / `preview_latest.sh`：责任域 overlay 后的全文临时集成；
4. `scripts/branch_hygiene.py`：识别 squash 后遗留或仍有独立提交的临时 chore 分支；
5. `scripts/export_handoff.py`：对普通 AI 隔离当前状态、只读参考和历史材料；
6. 人工检查：模型合理性、结果解释、跨问可比性、图表视觉、论文表达和分页。

机器检查防止灾难性错误，不替代人工判断。
