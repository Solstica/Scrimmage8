# 仓库状态优先级补丁

本补丁覆盖旧 Skill 中与仓库状态、完成状态和重跑有关的旧规则。

## 当前信息优先级

当前用户明确指令 > 当前 module task / manifest / 本轮交接说明 > 当前模型语义文件（model_interface / model_contract / model_spec 等） > 当前结果状态与正式运行/验证文件（result_registry / registry / run report / verification） > 当前代码和数据 > 当前论文 > 历史说明与旧结果。

同一层级再结合当前 branch tip、文件内容和更新时间判断。

## 必须分开的三类状态

MODEL: DRAFT / APPROVED / NEEDS_REVIEW
RESULT: DRAFT / VALIDATED / VERIFIED / FROZEN / NEEDS_REVIEW
PAPER SYNC: CURRENT / STALE / MISSING

MODEL=APPROVED 不自动推出 RESULT=FROZEN；RESULT=VERIFIED 不自动推出 PAPER=CURRENT。

## 必须报警的冲突

1. task 写 NEEDS_REVIEW，旧 registry 仍写 FROZEN/VERIFIED；
2. task 把旧结果降级为阶段结果，但论文仍写成唯一最终答案；
3. 论文写“数值求解后应给出”，但正式结果文件已经存在；
4. model_interface 与当前 task 对目标函数、阈值、参数域或硬约束不同；
5. 代码搜索域与模型说明不一致；
6. 下游仍引用上游已经替代的旧结果。

## Paper 不是模型状态真源

论文缺结果：先查正式结果，不得直接判模型未完成。论文有结果：先查 task / registry 是否允许正式使用。论文模型比代码旧：标记论文 stale，不让代码回退迎合论文。论文出现新方法名：不能据此改模型，先查模型语义源。

## Model Contract 只要求语义，不要求固定文件

若项目已有 model_interface.*、model_contract.*、model_spec.* 或 task 中的完整模型定义，直接复用。不得为了使用 Skill 再创建第二套 contract / registry。

## 重跑规则

数学语义未变：当前模型 → 重跑代码 → 更新正式结果/验证 → 更新项目原生 registry → 更新 task → 最后同步论文。

数学语义改变：先确认模型变更 → 更新已有模型语义源 → 标记受影响旧结果 stale → 重跑 → 复核 → 更新下游 → 论文最后同步。

不要自动新增目标、鲁棒模型、Bootstrap、灵敏度或搜索边界。
