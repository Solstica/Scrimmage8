# references 实时待办

## 当前新增文献
- `gbt42841`：GB/T 42841--2023《热环境的人类工效学 人体冷热应激评估与管理》。
  - 官方状态：现行，2023-08-06发布并实施；全国人类工效学标准化技术委员会归口。
  - 采标关系：非等效采用 ISO 7933:2004、ISO 15265:2004、ISO 15743:2008、ISO 9886:2004、ISO 11079:2007、ISO 12894:2001、ISO 9920:2009。
  - 进入Q1的位置：支撑人体冷热应激评价与人体热平衡建模框架；不把官方公开页面未展示的具体数值参数写成“国标网页直接给出”。
- `hao2016phs`：Hao X, Guo C, Lin Y, Wang H, Liu H. Analysis of Heat Stress and the Indoor Climate Control Requirements for Movable Refuge Chambers. IJERPH, 2016, 13(5): 518, DOI: 10.3390/ijerph13050518。
  - 支持范围：公开说明ISO 7933采用的PHS热平衡模型，并给出人体比热约 `3470 J/(kg·K)`；Q1据此与GB/T 42841--2023的采标体系共同确定人体等效热容参数。
- `li2018extended`：李长玉等，《基于拓展分离变量法的层合材料瞬态传热分析》，物理学报，2018，67(21): 214401，DOI: 10.7498/aps.67.20180743。
  - 支持范围：层合材料按微小时间段推进；界面温度在小时间段内作线性近似；各层分别采用分离变量法；界面温度连续与热流连续用于确定界面参数。
  - 不支持：温度相关 PCM 放热曲线的冻结或线性化处理。
- `li2021protective`：李长玉等，《热防护服-空气-皮肤热传导模型及其解析解》，应用数学和力学，2021，42(2): 162--169，DOI: 10.21656/1000-0887.400290。
  - 支持范围：将上述微小时间段分离变量方法用于热防护服--空气--皮肤层合传热，并通过循环得到全时域温度场。
  - 不支持：本题附件 DSC 曲线直接作为温度相关内部放热源的具体处理。
- `iso7730`：ISO 7730:2005《Ergonomics of the Thermal Environment---Analytical Determination and Interpretation of Thermal Comfort Using Calculation of the PMV and PPD Indices and Local Thermal Comfort Criteria》。
  - 进入Q2的位置：服装表面对流换热系数采用自然对流与强制对流两支中的较大者：`h_c=max{2.38|T_cl-T_a|^0.25, 12.1 sqrt(v)}`。
  - 使用边界：该关系来自热舒适/人体热平衡体系；本题南极低温环境超出典型室内舒适标定环境，因此同时用近年热人模和穿衣CFD文献交叉检查风速效应与数量级。
- `yang2023hc`：Yang J, Zhang S. Three-dimensional simulation of the convective heat transfer coefficient of the human body under various air velocities and human body angles. International Journal of Thermal Sciences, 2023, 187: 108171, DOI: 10.1016/j.ijthermalsci.2023.108171。
  - 支持范围：0.2--20 m/s、五种人体迎风角的热人模CFD；全身和局部 `h_c` 随风速按幂函数增加，3 m/s位于研究区间内；用于Q2风速效应和换热系数量级校核。
  - 不直接支持：把裸热人模回归系数直接等同于防护服外表面系数。
- `xu2022clothingwind`：Xu J, Psikuta A, Li J, Lu Y. Numerical investigation of the effect of clothing air gap distribution and environmental air speed on dry heat transfer underneath clothing. International Journal of Heat and Mass Transfer, 2022, 198: 123400, DOI: 10.1016/j.ijheatmasstransfer.2022.123400。
  - 支持范围：穿衣人体CFD显示外部风通过服装开口及衣下空气层改变并增强干热交换，说明有风环境不能沿用静止空气边界。
  - 不直接支持：给出本题 `v=3 m/s` 时服装外表面 `h_e` 的单一经验数值；原文模拟风速为0.2--2.5 m/s。

## TODO
- [ ] 核对正文所有引用键、文献真实性与格式。
- [ ] 若 Q1 最终保留有限差分/有限体积作为独立基准，只在正文实际出现时补充对应数值方法文献。
- [ ] Q3 成本/重量与 Q4 放热增强若使用外部参数，分别补充原始来源。

## NEEDS_REVIEW
- [ ] GB/T 42841--2023 官方公开系统受版权限制不提供标准全文；正文只能把官方页面明确支持的标准状态、范围与采标关系归于国标，`c_h=3470 J/(kg·K)`须同时引用PHS公开文献。
- [ ] 不将 2018/2021 两篇文献用于证明本题 `q_pcm(T)` 冻结近似；正文应明确这是针对附件数据的时间步近似。
- [ ] Q2 的 `12.1 sqrt(v)` 关系虽然与题目附件自然对流支路构成完整经典表达，但南极极低温应用需要在结果阶段做替代风速关系敏感性检查，避免把热舒适经验式的适用范围写得过宽。

## DONE
- [x] 已核对并写入 Q1 主要方法来源的作者、题名、卷期页码/文章号和 DOI。
- [x] 已加入 GB/T 42841--2023，并记录其现行状态及ISO采标关系。
- [x] 已补充可公开核验 `c_h=3470 J/(kg·K)` 的PHS文献，避免误把数值归因于无法公开读取的国标正文。
- [x] 已加入 Q2 的 ISO 7730 服装表面对流关系、Yang 2023 风速回归和 Xu 2022 穿衣风效应文献，并分别限定其可支持的结论。
