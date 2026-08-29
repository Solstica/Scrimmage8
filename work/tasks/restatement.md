# restatement 实时待办

## TODO

## NEEDS_REVIEW
- [ ] 问题背景与问题提出的措辞基于 main.pdf 中已确认赛题内容重写，待全文集成后复核与正文各问描述及符号定义的一致性。

## DONE
- [x] 按模板结构重写问题重述（问题背景 + 问题提出），使用 \subsection 子章节。
- [x] 插入成果背景图（问题背景.png）到问题背景小节，使用 \FigureMechanismWidth 宽度。
- [x] 背景图路径已改为 `\ProjectRoot/modules/10_restatement/paper/问题背景.png`，避免全文从 `paper/` 编译时相对路径失效。
- [x] 根据 main.pdf 实际赛题逐问重写"问题提出"，替换 Q1--Q3 通用模板措辞并补齐问题四。
- [x] 问题背景按实际对象（人体—三层防护服—环境瞬态传热）重写，保留成果背景图。
- [x] 每问按"给定什么、要求确定/优化什么、关键条件、输出形式"四要素组织，符号与 q1 正文约定一致（$T_{\rm in}(t)=T_1(0,t)$、$t_{15}/t_{10}$ 等）。
- [x] audit_paper.py 通过：语言 HARD = 0，STRUCT_HARD = 0。
- [x] preview_section 局部编译通过，新正文与背景图正常渲染。
