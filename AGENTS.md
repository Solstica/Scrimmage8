# AI / Agent 强制协作规则

本文件适用于所有支持仓库级指令的 AI 编程/写作代理。

## 开始任务前

1. 阅读 `README.md`、`docs/RESOURCE_MAP.md`、`docs/PAPER_STYLE_GUIDE.md`、`docs/FINAL_PAPER_CHECKLIST.md`、`docs/WORKFLOW_LESSONS.md`、`config/project.json`。
2. 如需要完整单文件交接，读取 `docs/AI_HANDOFF_PROMPT.md`。
3. 必须运行 `python scripts/workflow.py start <module-key>`。
4. 必须读取当前模块 `work/tasks/<module-key>.md`，以其中实时待办为工作入口。
5. 文件位置只以资源地图和配置为准；先自行查找固定路径，不要求协作者重复说明已经固定的资源位置。

## 修改边界

- 一个任务只修改一个责任域。
- 当前模块唯一正文源位于其 `modules/.../paper/`；不要在同一目录另建 `_final`、`_v2`、`_old`、`_backup` 等平行正文真源。
- 参考文献唯一正文源是 `modules/70_references/paper/references.tex`；每问唯一正文源是对应 `q?.tex`，伪代码可拆成明确的 `q?_algorithm.tex`。
- `paper/` 仅由 `feature/paper-shell` 修改；章节分支不得编辑全文入口、字体、页边距、标题层级、目录和公共图表样式。
- 跨问共享内核只进入 `shared/`，由 `feature/shared` 维护。
- `work/archive/` 与显式 legacy/import 目录均为只读历史材料；不得在那里继续开发，也不得让正式正文长期引用其中的图、表、代码或结果。
- 历史仓库中的 `FROZEN`、`CHECKED` 等状态不得继承到当前项目。当前结果状态只认当前模块自己的 `results/registry.csv`。
- 问题模块固定使用 `code/`、`data/processed/`、`figures/`、`figures/editable/`、`tables/`、`results/`；不要自行创造 `src/` 等并行结构。
- 不新建第二套全文 TeX、第二套模块树或 `final2/真的final/论文汇总` 等目录。
- 不使用 `git push --force`、`git reset --hard` 处理协作冲突。

## 分支生命周期

- `feature/*` 是长期责任分支；`chore/*` 只用于一次集中维护、迁移或模板升级。
- `chore/*` 若通过 squash merge 进入 `main`，旧分支会与 `main` 显示 diverged，这是正常的历史结果；不得再次直接 merge。
- 需要判断旧临时分支时运行 `python scripts/branch_hygiene.py`，先 compare 再决定是否删除。
- 一轮 chore 完成并确认综合提交进入 `main` 后，应删除旧远端 chore 分支；下一轮从最新 `main` 新建新的 chore 分支。

## 论文格式与表达

- 默认沿用 `docs/PAPER_STYLE_GUIDE.md`；终稿还必须按 `docs/FINAL_PAPER_CHECKLIST.md` 检查，不要自行重新设计。
- 图表、表格、公式、伪代码、代码附录均使用仓库既有示例和宏。
- 非 `paper-shell` 任务若发现公共格式问题，只记录依赖/需要复核项，不直接改全局样式。
- 未验证结果不要先写进正式正文；也不要自行发明 `\TODO{}`、`\placeholder{}` 等模板未定义宏。未完成事项写入当前任务文件。
- 正文避免连续五六行以上的纯文字块；优先按“数据发现/数学量/模型作用”分点、分段或公式化。
- 模型、算法第一次出现优先写成“中文名称（English Full Name，缩写）”，后文保持同一称呼，不随意在中文、英文全称和缩写之间跳换。
- 不把内部讨论语言写进正文，如“物理口径、证据边界、统一链路、柔性释放/替代”等；需要说明范围、可行性或最优性时直接写数学事实。
- 算法小节不能只有一大段自然语言；至少给出决定搜索/更新规则的核心数学量，再接正式伪代码。
- 每张正式图表必须被正文引用并解释；若图表与文字完全重复，应删去其一或压缩文字。
- 大规模整数优化只按已有证书表述：可行候选不能写成全局最优，跨问绝对指标在时间范围或终端结算未统一前不得直接解释为增量收益。

## 待办与检查

- 实际工作出现新任务、阻塞、风险或待复核项时，实时写入当前模块任务文件，不只留在聊天里。
- 需要人工判断的事项写为 `NEEDS_REVIEW` / `需要复核`；检查可由管理员或指定复核成员完成，不绑定固定角色。
- 正文关键结果只能来自当前项目 `FROZEN + CHECKED` 的结果登记。
- 提交前主动检查 `<<<<<<< / ======= / >>>>>>>` 冲突标记、可疑 TeX 拼写以及正文资源路径；最终预检会把其中的硬错误提前拦截。

## 普通聊天 AI 与仓库代理的区别

- 有仓库执行权限的代理按本文件运行命令并落盘。
- 没有仓库执行权限的普通聊天 AI 不得声称已经运行 Git/Python/LaTeX 或已经修改仓库；应返回准确的仓库相对路径、替换文本、补丁建议和需要复核项，由协作者落盘。
- 给普通聊天 AI 交接时，优先运行 `python scripts/export_handoff.py <module-key>` 生成结构化交接包，避免手工拼接当前文件与历史资料。

## 全文预览

章节责任分支不通过长期合并来做日常全文预览。优先从稳定仓库根目录运行：

```bash
git fetch origin --prune
bash <(git show origin/feature/shared:scripts/preview_latest.sh)
```

该流程以 `feature/paper-shell` 为排版底座，对各责任域做文件 overlay，自动清理旧临时 worktree，并在临时目录中执行引用、冲突标记、结果状态、资源路径和 LaTeX 检查。若编译失败，先处理日志中的第一处硬错误；第一遍 citation/reference warning 在编译被其他错误提前打断时不等于最终引用失败。

## 结束任务前

1. 更新当前模块任务文件；
2. 运行 `python scripts/workflow.py finish <module-key>`；
3. 检查 `git diff`、冲突标记、越界修改和是否误建第二正文源；
4. 汇报修改、结果位置、未完成待办、阻塞和需要复核项。
