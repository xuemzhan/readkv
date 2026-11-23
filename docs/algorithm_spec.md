# CF-RCT 算法规格书（V2.0 · 反事实功能保真）

> 状态：**设计产出 / 待 PI 批复**。本文定义算法、损失函数与机制诊断的可实现规格；文中所有阈值、效应量与数字均为**待验证的设计目标**，不是实验结论。Mock 后端数字一律不构成证据（见 `docs/protocol.md` 首段、`docs/decisions/p0_direction.md §4`）。
> 依据：`docs/protocol.md §1–§6/§9/§10`、`docs/decisions/p0_direction.md §1–§5`、`docs/architecture.md §3–§6`、`docs/gpu_handoff.md §2/§5`、`configs/protocol.yaml`、`configs/eval.yaml`、`configs/prereg/*`。
> 边界：本文只写设计，不写代码、不改 `configs/prereg/**` 既有冻结文件、不改运行产物、不改主终点定义。

---

## 0. 硬约束（贯穿全部设计）

1. **严格 zero re-prefill**：可部署迁移臂只有 **Joint**（K、V 都来自映射教师缓存）。K-only / V-only / Self / Oracle 均为离线诊断或训练期工具，不得宣传为可部署方法；Joint 推理图禁止学生处理文档 token，禁止在线读取 `C_S(d)`；每次运行写 `zero_re_prefill=true` 并由 `verify_zero_re_prefill` 断言。
2. **主终点不可改**：封存测试上新方法与 `primary_baseline=kd_only` 的**成对 `E_CF` 差异**，模板 / 来源簇级 paired bootstrap（10000 resamples），95% CI **上界 < 0** 才算稳健改善；`E_CF` 必须与 `dual_correct` / `flip_consistency` / `coverage` / `info_gap` 联合报告。
3. **判据先写后跑**：`τ=1.0`、`self_threshold=0.1` 已冻结（仅引用）；Huber 阈值 δ、标签平衡、机制单元选择规则须在封存测试前用**验证集**确定并经 PI 以**新增版本判据文件**冻结（见 §5）。不得按测试结果调任何阈值 / 权重 / 种子。
4. **双文档独立**：`d_A`、`d_B` 由教师各自独立 Prefill，禁止篡改缓存字节伪造另一文档；GQA、QK-Norm、位置 / RoPE、dtype / kernel 在全部对照中一致。
5. **Oracle 隔离**：`L_local` 与层 / 头 / Token 诊断依赖学生原生状态，只允许在训练期 / 离线诊断期使用，不得进入 Joint 推理图；推理期预算分配只能用教师缓存、映射状态、学生当前 Query 等可观测量。
6. **反事实分别诊断**：须在 `d_A` 与 `d_B` 上分别诊断映射误差，再比较差值；不可用单文档注意力误差替代反事实误差。
7. **不把“加一个 loss / 多做一套评测”当贡献**（见 §7 与 `protocol.md §10`）。

---

## 1. 记号与对象

| 记号 | 含义 | 备注 |
|---|---|---|
| `T` / `S` | 教师 / 接收学生；`S` 全部主权重冻结 | `Ĉ_S(d)=gθ(C_T(d))` |
| `C_T(d)` / `C_S(d)` | 教师缓存 / 学生原生缓存 | `C_S(d)` 是离线 Oracle，不进 Joint |
| `gθ` | K/V Mapper，待训练的唯一可训练对象 | 详见 §2 |
| `u=(q,d_A,d_B,a,b,m)` | 反事实评测最小单元 | 候选 A/B 在每对内一致，顺序随机交换 |
| `g(C,q) = log P(A|C,q) − log P(B|C,q)` | 单候选对的响应强度差 | 单 token 同一生成位置取 logits |
| `D_self = g(C_S(d_A),q) − g(C_S(d_B),q)` | 原生反事实差 | 离线锚点，不参与梯度 |
| `D_trans = g(Ĉ_S(d_A),q) − g(Ĉ_S(d_B),q)` | 迁移反事实差 | Joint 路径产出 |
| `E_CF = |D_trans − D_self|` | 主终点原值 | 封存测试上比对成对差异 |
| `normalized_E_CF = |D_trans − D_self| / (|D_self| + τ)` | 跨模型归一 | `τ=1.0`，仅验证集固定 |
| Self 有效子集 | `|D_self| ≥ self_threshold = 0.1` | `flip_consistency` 在此子集计算；`E_CF` 全量 + 子集同报 |
| `Q_S`, `A_S`, `V_S` | 固定接收端局部 Query / 学生注意力 / 学生 Value | `L_local` 与诊断的固定条件 |

---

## 2. Mapper 参数化（容量逐级控制）

按 `protocol.md §6.1` 的“低风险起步、逐级放量”原则，默认只用 ① + ②，③ 仅在显著必要时开启并单列参数量：

1. **① per-(layer, channel, head) affine + 层映射**：对每个 `(层, 通道∈{K,V}, 头)` 一个 `d×d` 线性矩阵 `W_{ℓ,ch,h}`；非等深对（4B→1.7B，36→28 层）由 `models/layer_map.py` 给出教师层→学生层对应，不强行同层对齐。以训练校准集上的闭式 ridge（`K_T→K_S`、`V_T→V_S`）作初始化，降低训练起步风险。
2. **② 低秩残差修正**：`W = W_0 + A Bᵀ`（`r≪d`），`L_reg` 约束其范数；`rank=0` 时退化为纯 affine（便于消融“容量是否解释增益”）。
3. **③ 小型跨层 Mixer（不默认启用）**：仅当 ①+② 明显停滞且消融证明需要跨层信息时加入；必须与 lite 版本单列可训练参数量，否则不能排除“更多参数解释全部增益”。

实现约束：de-RoPE 后在内容空间回归，注入前按学生位置 / RoPE 元数据 re-RoPE；GQA 下多个 Query Head 共享 KV Head，按 KV head 聚合；dtype/kernel 与基线完全一致（`configs/eval.yaml`：bf16 + sdpa）。

---

## 3. 三版本算法定义与伪代码

`CF-RCT`（Counterfactual Response-Constrained Translation）为**算法族工作名**；两个可运行实例为 `CF-RCT-lite` 与 `CF-RCT-mech`。三者共享同一训练骨架，仅损失开关与机制单元来源不同。**先 lite 后 mech**；只有 mech 对 lite 和最强公共基线均有增益，才允许把“机制引导”写成核心方法创新（`protocol.md §6.4`）。

### 3.1 CF-RCT 训练骨架（umbrella）

```
Algorithm 1  CF_RCT_TRAIN                      # 唯一可训练对象为 gθ，S 冻结
Input : 校准反事实对 {u_i}; 离线教师缓存 C_T(d_A), C_T(d_B);
        学生原生锚点 C_S(d_A), C_S(d_B) (离线);
        λ_KD, λ_CF, λ_local, λ_reg; τ=1.0, δ (验证集冻结), δ 见 §5;
        self_threshold=0.1; epochs E; lr; seed
Output: gθ

  torch.manual_seed(seed)
  gθ ← RidgeInit(C_T, C_S, 校准对)             # per-(layer,ch,head) 闭式解
  opt ← Adam(gθ.parameters(), lr)
  for epoch = 1 .. E:
      shuffle(校准对, seed=seed+epoch)
      for each u_i = (q, d_A, d_B, ...):
          Ĉ_A ← gθ(C_T(d_A));  Ĉ_B ← gθ(C_T(d_B))     # 两次映射，共享参数
          # ——离线锚点，no_grad，梯度不触及 C_S——
          with no_grad:
              p_A^S ← S_forward(C_S(d_A), q);  p_B^S ← S_forward(C_S(d_B), q)
              D_self ← g(p_A^S) − g(p_B^S)
          # ——Joint 路径，梯度经映射缓存回传至 gθ，学生权重冻结——
          p_A^t ← S_forward(Ĉ_A, q);  p_B^t ← S_forward(Ĉ_B, q)
          D_trans ← g(p_A^t) − g(p_B^t)

          L_KD    ← KL(p_A^t ‖ p_A^S) + KL(p_B^t ‖ p_B^S)     # 逐文档分布一致
          m       ← 1[ |D_self| ≥ self_threshold ]           # Self 有效掩码
          L_CF    ← mean_i[ m_i · Huber_δ(D_trans^i − D_self^i) ]
          L_local ← (mech only) 见 §3.3 / §6.2；lite 时为 0
          L_reg   ← ‖低秩残差‖² (rank=0 时为 0)

          L ← λ_KD·L_KD + λ_CF·L_CF + λ_local·L_local + λ_reg·L_reg
          zero_grad(); L.backward(); clip_grad_norm(gθ, 1.0); opt.step()
  return gθ
```

要点：

- `L_CF` 只在 **Self 有效子集**上求均值：`|D_self|<0.1` 处 Self 本就无可辨识信息，强行要求 Mapper 更敏感会诱发目标退化（`protocol.md §6.3`）；该子集仍进入 `L_KD` 与全量指标报告。
- 两次学生 Query Forward 是**唯一**的接收端 Forward 预算来源；`C_S` 的 Forward 为离线预计算、不计入可部署成本，但需在超参配平时如实记录。
- 标签平衡：每对 `d_A/d_B` 1:1、候选 A/B 顺序 50/50 交换，F5 非翻转负控按固定比例纳入；策略与 δ 一同冻结（§5）。
- 退化防护：联合监控 `dual_correct`、`flip_consistency`、`coverage`、`info_gap`；若出现“`D_trans→0` 换取低 `E_CF`”，按 `protocol.md §6.3 / §8` 处理，不把它写成改善。

### 3.2 CF-RCT-lite（L_KD + L_CF）

`Algorithm 1` 中置 `λ_local=0`、`λ_CF>0`。用途：检验“在逐样本 KD 之上叠加成对反事实约束是否带来**独立**增益”，并作为 mech 的直接消融对象。若 lite 相对 `kd_only` 无增益，则 `λ_CF` 不得作为方法贡献（协议 §6.2）。

### 3.3 CF-RCT-mech（加机制约束）

`Algorithm 1` 中 `λ_local>0`，且机制单元 `(层, 头[, Token])` 由**训练 / 验证集**的局部干预排序选出（§6.3 的 `rank_units_by_repair`），不使用封存测试标签。`L_local` 在固定的接收端局部 `Q_S` 下约束：

```
L_local = Σ_{(ℓ,h)∈U} [ ‖(Â−A_S) V_S W_O‖₂ + ‖Â (V̂−V_S) W_O‖₂ ]
          (+ 可选 attention score KL 项，见 §6.2)
```

`U` 为选出的机制单元集合。**`Q_S`、`C_S(d)`、`A_S` 均为 Oracle 训练信号，只存在于训练图；推理 Joint 臂不计算 `L_local`。**

### 3.4 严格零重 Prefill 推理（唯一可部署路径）

```
Algorithm 2  JOINT_INFER                        # 主报告路径
Input : q, 教师离线缓存 C_T(d), 训练好的 gθ, 冻结学生 S
  Ĉ ← gθ(C_T(d))
  断言 verify_zero_re_prefill(): q 之外无文档 token 进入 S；未读取 C_S(d)
  logits ← S_decode(Ĉ, q)                        # 首 token 取自 prefill logits
  return logits, zero_re_prefill=true
```

K-only / V-only / Oracle 移植只在 `Algorithm 3`（§6.1）中调用，输出带 `deployable=false` 标记。

---

## 4. 损失函数：理论动机与超参数选择原则

| 损失 | 形式 | 理论动机 | 选择原则 / 固定位置 |
|---|---|---|---|
| `L_KD` | `KL(p_trans‖p_self)` 逐文档求和 | 逐样本分布匹配，是 KV-Lingo 类行为的直接强基线；保证映射缓存仍保留单文档预测语义，抑制 `D_trans→0` 塌缩 | 候选 logits 统一在同一位置取；`λ_KD` 固定为 1.0 作锚点，与基线同预算；验证集确认不过拟合后不再调 |
| `L_CF` | `mean_{Self有效} Huber_δ(D_trans − D_self)` | 直接约束**反事实响应差**的幅度与方向；对离群对稳健（Huber 二次→线性过渡），避免少数难例主导 | `δ` **只在验证集固定**（§5）；两份文档共享 `gθ`、成对更新；`λ_CF` 用验证集网格，且与所有基线同调参次数 |
| `L_local` | routing 项 + consumption 项（§5.1 分解的监督版），可选 score KL | 由 `V̂` 的消费输出与 routing 分布一致，间接约束 K/V 分工；仅在被局部诊断选中的层/头施加，容量可控 | Oracle 信号**仅训练期**；`λ_local` 验证集固定；仅 mech 启用；只在 mech>lite 且>最强基线时才可写成创新 |
| `L_reg` | `‖低秩残差‖²`（rank=0 时为 0） | 小型合成域上抑制过拟合；使“容量解释增益”可被消融 | `λ_reg=1e-4` 起步，验证集固定；不用于掩盖 seed 方差 |

总损失 `L = λ_KD·L_KD + λ_CF·L_CF + λ_local·L_local + λ_reg·L_reg`（与 `protocol.md §6.2` 一致）。所有 `λ` 用**同一验证集、同一网格、同一调参预算**选择；选择过程记录网格与搜索成本；封存测试运行后不得改动（prereg `forbidden_after_run`）。`L_total` 本身不构成理论新颖性证据。

**与基线的公平配平**：KD-only、CE-only、Consumer-space、错文档对比、强行为 Mapper 使用同校准对、同 Self Forward 次数、同可训练参数量、同训练步数与学习率调参次数；普通 QA 与反事实 QA 同报（`protocol.md §7`、`p0_direction.md §5.1`）。

---

## 5. Huber 阈值缺口：建议值与冻结流程

**缺口事实**：`configs/protocol.yaml` 与全部 prereg 文件均无 Huber 阈值数值；`docs/protocol.md §6.2` 只要求“在验证集固定”。`experiments/P3_method.py` 中的 `huber_delta: 1.0` 仅为 mock 接线占位，**不是冻结值、也不是证据**（`p0_direction.md §2.3 / §4`）。

**建议值（供 PI 冻结参考，科学家不写入 prereg）**：

- `L_CF` 的残差 `r = D_trans − D_self` 是 logit 差尺度上的量，与 `τ=1.0` 的归一化尺度同量纲。建议 **δ 标称值 = 1.0**（logit 单位），理由：①与已冻结 `τ=1.0` 同尺度，避免 `δ≪|r|` 退化为 L1-型弱梯度或 `δ≫|r|` 退化为 L2 被离群对主导；②与现有 mock 占位一致，便于判据接线回归。
- 确定流程（验证集，不碰封存测试）：在验证集 Self 有效子集上取 `q70 = quantile(|D_self|, 0.7)`，在网格 `δ ∈ {0.5, 1.0, 2.0}`（必要时以 `clip(q70, 0.5, 2.0)` 补充候选）上训练候选 Mapper，按“验证集 `E_CF` 最小，且 `dual_correct`、`flip_consistency` 不劣于 `kd_only`，普通 QA 不退化”的固定优先级选择；若网格最优偏离 1.0，以网格结果为准。
- 标签平衡同步冻结：每对 A/B 1:1、候选顺序 50/50 交换、F5 负控固定配比、`L_CF` 仅在 Self 有效子集求均值。

**冻结流程请求（PI 权限）**：请 PI 在封存测试运行前，**新增**版本判据文件（建议 `configs/prereg/phase3_loss_config_v2.1.yaml`，注明 `frozen_at: protocol-v2.1`），写入：δ 数值、选择网格与验证集 split id、`λ_KD/λ_CF/λ_local/λ_reg`、标签平衡策略、机制单元选择规则、选择理由与 `forbidden_after_run`；**不得回写**已冻结的 `configs/protocol.yaml` 或既有 `phase1_*` / `phase3_*` / `stage*_decision` 文件。**未冻结前 P3 封存测试为 No-Go**；审稿人须专项复核（见 `p0_direction.md §2.3 / §5.3`）。

---

## 6. 机制诊断设计

### 6.1 K/V 四臂（Self / K-only / V-only / Joint）

| 臂 | Key | Value | `deployable` | 用途 |
|---|---|---|---|---|
| Self | 学生自身 `K_S` | 学生自身 `V_S` | false | 原生锚点；训练 / 诊断参考 |
| K-only | 映射教师 `K̂_S` | 学生自身 `V_S` | false | 分离寻址 / 路由扰动 |
| V-only | 学生自身 `K_S` | 映射教师 `V̂_S` | false | 分离读取 / 消费扰动 |
| Joint | 映射教师 `K̂_S` | 映射教师 `V̂_S` | **true** | 唯一严格零重 Prefill 可部署路径 |

四臂须在**同一 `q`、同一位置、同一 dtype/kernel**下打分；比较 `(D_trans^arm − D_self)` 而非单文档 logits。**两类效应必须分开**：在 `d_A`、`d_B` 上分别诊断，再比较差值（`protocol.md §5.3`）。K-only / V-only 的另一半缓存来自学生自身 Prefill，**不得宣传为零重 Prefill 方法**。

### 6.2 局部 Routing / Consumption 分解

固定接收端 Query `Q_S`、固定位置与当前层，记 `A_S = softmax(Q_S K_Sᵀ/√d)`、`Â = softmax(Q_S K̂_Sᵀ/√d)`，则代数恒等式：

```
Ô − O_S = (Â − A_S) V_S W_O^S  +  Â (V̂ − V_S) W_O^S
          └─── Routing ───┘     └──── Consumption ────┘
```

- 第一项：**Routing**（Key 改变导致注意力分布变化，读取学生 Value）；第二项：**Consumption**（在映射注意力分布下读取 Value 的变化）。
- 数值校验：`‖routing + consumption − total‖` 应≈0，写入逐单元记录（`diagnostics/route_value.py::AttentionDecomposition.residual_norm`）。
- **解释边界**：这是固定 Q / 固定位置的**局部代数恒等式**，不能直接解释为全模型任务损失的加性因果分解；前层注入会改变后层 Q 与非线性状态。不得把热图直接称为因果分解。

三层推进（A/B 只是关联，C 才具因果识别力）：

- **A 缓存层**：K/V `R²`、score 差、attention top-k / TV、`W_O` 输出误差；
- **B 模型层**：候选答案响应差、token-level KL；
- **C 因果层**：层 / 头 / Token Oracle 状态移植，观察 `E_CF` 改变，并用独立文档验证。

### 6.3 层 / 头 / Token Oracle 移植

```
Algorithm 3  ORACLE_RANK_AND_VERIFY                 # 仅训练/验证集 + 离线诊断
Input : (C_S(d_A), C_S(d_B)), (Ĉ(d_A), Ĉ(d_B)), 基线 E_CF, 训练/验证 split
  对每层 ℓ、头 h、通道 ch∈{K,V,both}、Token t（含 t=None 表示整头）:
      把学生原生状态移植回映射缓存 → 修复后 cache
      Δ(ℓ,h,ch,t) = E_CF_before − E_CF_after
  按 Δ 降序取候选单元集 U                            # 只用训练/验证集
  在独立验证文档上检验 U 的 repair 命中率 / E_CF 改善       # 预测价值检验
  return U, 稳定性统计
```

- Oracle 依赖学生原生 Prefill，**只在离线诊断 / 训练期出现**；推理期预算分配预测器只能用可观测量（教师缓存、映射状态、学生当前 Query），不得在线读 `C_S(d)`。
- **预测价值判据（运行前冻结）**：候选单元在独立验证文档上的 repair 效果需显著优于随机单元 / 全层平均（具体阈值由 PI 在新增版本判据冻结，建议先以“top-k 命中率显著高于随机基线、且 held-out `E_CF` 改善方向一致”为原则）；仅事后相关 → 机制层降级为现象报告（`protocol.md §8`）。

### 6.4 对称 Key 四目标（前置机制实验）

比较（V 侧暂固定 consumer-space Mapper）：

| 目标 | 定义 | 说明 |
|---|---|---|
| A | per-head ridge `K_T → K_S` | 缓存层基线，非任务因果 |
| B | student attention-mass 加权回归 | 以注意力质量加权 |
| C | 对学生 pre-softmax score 的回归 | 含 C-score / C-score-weighted |
| D | attention KL / ranking 目标 | 可微学生 attention，SGD |

GQA 下按多个 Query Head 对应同一 KV Head 聚合；对 RoPE 前 / 后回归分别测试并报告位置扰动。**阳性判据（跑前冻结于 `configs/prereg/stage1_decision.yaml`，V1 遗留机制基线）**：C 显著优于 A/B 且 D 不优于 C；routing 改善而 `E_CF`/EM 不动 → 阴性，指向 query–key 交互或需重算。两种结果都写入论文。Key 侧无论正负都只是机制基线（第二篇对称性补全 + 第三篇机制前置），**只有发现新型可迁移规律才可提升为方法主贡献**。

---

## 7. 三个贡献层次：独立证据与 §10 门槛对应

| 层次 | 研究问题 / 假设 | 独立证据（不可互借） | 主实验 | 成立后才可用的措辞（`protocol.md §10`） |
|---|---|---|---|---|
| **①评价层** | RQ1 / H1：常规分数不保证反事实保真 | 在 Self 可答对文档对上，强基线（`kd_only`/consumer/affine/score/ridge）的 `E_CF` 相对 Self 仍有稳定差距；七类控制组差距齐全；`coverage`/`dual_correct`/`flip_consistency` 同报 | E0 + E1（+ P1 `phase1_benchmark_decision`：distortion_present ∧ quality_pass） | (1) "We identify a reproducible gap between standard transfer utility and counterfactual response fidelity…" |
| **②机制层** | RQ2 / H2：失真可归因于 Key 路由与 Value 消费 | K/V 四臂分离 + Routing/Consumption 分解残差≈0 + Oracle 修复在**独立文档**上有预测价值（非事后热图）；Key 四目标阳性/阴性如实报告 | E2（+ P2 机制报告） | (2) "We localize the gap to receiver-side routing and consumption effects…" |
| **③方法层** | RQ3 / H3：同预算下机制感知 Mapper 定向恢复 | 封存测试上 CF-RCT 相对 `kd_only` 的成对 `E_CF` 差异 CI 上界<0、`flip_consistency≥0.7`、`dual_correct≥0.7`、≥3 seed、Holm；mech 对 lite 与最强公共基线均有额外增益；普通 QA 不退化；成本已核算 | E3 + E4 + E5 + E6（+ P3 `phase3_method_decision`） | (3) "We present a mechanism-constrained mapper that reduces this gap… without target-side re-prefill at inference." |

**降级规则**：仅 ① 成立 → 改写为边界 / 实证研究论文，**不得保留 (2)(3) 措辞**；H2 只有事后相关 → 机制主张降级；H3 只有 `E_CF` 下降而常规任务退化 → 如实报告权衡（`tradeoff`）；mech 不优于 lite → 方法贡献降级，不挑种子掩盖无效。评价层新增或单纯“加一个 `λ_CF`”**不自动成立为贡献**。

---

## 8. Novelty 与研究范畴核查（文献边界）

- 四个范畴必须区分，不得混淆：①**跨模型传输**（本工作主线）；②**同模型增量编辑缓存修复**（明确不研究）；③**无信息消息适应**（作为控制组 / 信息归因，非本贡献）；④**内容依赖审计**（沿用公开因果审计原则，不主张原创指标）。
- 强基线可复现性：优先复现 **KV-Lingo** 的同模型对、同协议行为蒸馏；**CacheLink** 若无可运行官方实现，按公开文档实现并明确报告偏差，不假定原作者结果可在当前任务直接复现（`protocol.md §7`）。
- 不主张的创新：表示误差 / `R²` 等于任务质量、单文档注意力误差等于反事实原因、Oracle 诊断可部署、identity 审计本身。论文 novelty 须落在“反事实功能保真评价 + 可外推机制诊断 + 配平预算下经检验的方法增益”三者的**独立证据**上。
- 同期工作引用须核查正式版本、日期与实验口径（`protocol.md §9`）。

---

## 9. 交接事项

**给工程师**：按 §2–§4 实现 / 对齐 `models/cf_rct.py`、`train/cf_rct.py`、`diagnostics/route_value.py`；`L_CF` 加 Self 有效掩码；`L_local` 仅在 mech 且仅训练期；Joint 推理写 `zero_re_prefill=true`；四臂带 `deployable` 标记；逐对记录按 `protocol.md` 附录 A schema 落盘。**不得**把 placeholder `huber_delta=1.0` 当作冻结值写进正式 run 配置。

**给 PI（需裁决 / 冻结）**：
1. 批复本规格书后触发工程师实现；
2. 用验证集确定 δ 与标签平衡策略，**新增** `phase3_loss_config_v2.1.yaml`（`frozen_at: protocol-v2.1`）冻结；科学家不写 prereg；
3. 冻结机制诊断的“独立文档预测价值”阈值（§6.3）；
4. P3 封存测试在上述冻结完成前维持 No-Go。

**给写作者 / 审稿人**：方法章节素材来自 §2–§6；贡献措辞严格按 §7 门槛；审稿复核 δ 冻结、Oracle 不泄漏、`E_CF` 联合报告三处。
