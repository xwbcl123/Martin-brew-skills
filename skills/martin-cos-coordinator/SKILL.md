---
name: martin-cos-coordinator
description: Discover and follow a host project's CoS coordination workflow when asked to arrange workers, coordinate work/personal tasks, or track and accept delegated results. Excludes bounded workers and ordinary direct tasks; does not authorize dispatch or external actions.
---

# CoS 协调入口

先判断角色：安排执行者、跨任务协调或跟踪验收属于 Coordinator；已收到 bounded worker contract 则保持 Worker。普通问答和直接任务在当前上下文完成。协调职责不意味着每次都要委派，也不授予任何新的执行、外发或审批豁免。

## 读取宿主的权威入口

从当前项目 `AGENTS.md` 或用户明确指定的项目入口，解析以下真实契约；路径由宿主管理，不假定某个电脑、vault 或终端布局。项目可以在 AGENTS 中链接本 Skill 作为发现兜底，不假定 Skill catalog 热加载一定生效。

| 宿主契约 | 在哪里继续 |
|---|---|
| CoS continuity 入口 | 实际完成其启动读取，取得必要的稳定偏好和相关 handoff；不是只引用入口 |
| 委派核心 | 授权、业务域、canonical worker、规则/分类工具、执行 fabric 与验收 |
| Session 状态契约 | 恢复当前任务，解析实际 schema、handoff/state/修订及在途 owner |
| 所选 adapter / roster / service contract | 选定 fabric 后，核验身份、工具、账号、模型与 busy/draft/approval 边界 |

若宿主缺少必要契约，或当前指令禁止某项读取，明确缺口及原因，不宣称启动/路线已验。不另造 Memory、roster 或平行状态机；继续不依赖该缺口的已授权本地工作。

## 协调决策

- 当前请求确定任务身份和权限；旧 handoff 只提供相关背景，不触发无关旧项目续跑，也不产生新的外部动作授权。
- 依用户指定、资料归属和宿主规则判定工作/个人等业务域；cwd 不决定资料归属。冲突时只推进独立的已授权部分，不擅自跨域搬运资料。
- 先核对适用的 canonical persistent worker，复用其 contract 与幂等约束；再按角色、权限和收益选择 fabric，最后查实际模型/工具能力。显式模型不得静默替换。
- 明确规则够用时直接用规则；有界分类仍有歧义时，按宿主契约评估 Jev 或其他分类工具的适用性、最小输入及外传授权。记录本次选择理由；未调用就明确未调用。路由结果只是建议。
- 只有选择具体 fabric 后才加载对应 adapter。区分 requested/configured/observed；核对 fresh binding、cwd、账号/工具及空闲条件。只读预览不代替实际接单、空闲或认证，命令副作用以当前实现为准。
- 需要持久 Session 时沿用宿主状态协议；单次只读安排说明不强制建档。派发前界定精确读写范围、禁止项和可回读的成果；共享状态由原 owner 单写。

主控必须读取真实产物，对照来源、scope、状态和所需外部 readback 验收。dispatch、安静的终端、Worker 完成标记或文件 hash 均不能单独证明成果完成。工具/权限/身份缺失时停止依赖步骤，保留已确认结果，不伪报成功。
