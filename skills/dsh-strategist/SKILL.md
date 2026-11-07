---
name: dsh-strategist
description: 中文博弈军师。当用户要处理人际、职场、谈判、冲突、协作、家庭等“人对人”的博弈（如“怎么谈”“怎么赢”“怎么防”“对方怎么想”“要不要撕破脸”“帮我分析这个局面”），用本技能走 SOP：目的澄清→局势拆解→检索计策→推演→决策卡→法律/心性检查→本地报告。
whenToUse: 用户需要针对另一个人或一群人做策略判断、谈判准备、冲突应对、关系取舍，或明确要求“军师/计策/博弈分析”时。
user-invocable: true
disable-model-invocation: false
---

# 军师（dsh-strategist）

一套本地运行的“人对人博弈”工作台：知识库（8 部原典 + 102 西方卡 + 36 计 + 47 变体 + 20 原则）+ 11 个工具 + 表单 + HTML 报告。

## 项目位置

按以下顺序找「项目根」（含 `tools/`、`kb/`、`prompts/` 的目录）：

1. 本技能目录下的 `project-root.txt` 第一行（安装器会写入本地路径）；
2. 本技能目录向上两级（适用于 `<项目根>/skills/dsh-strategist` 布局）；
3. 都没有：问用户，不要猜。

确认以下文件存在（用一次只看不写）：

- `tools/run_pipeline.py`
- `kb/index/unified-variants.json`
- `docs/SOP-谋划流程-v0.1.md`

若不存在，按上面的顺序重找；仍找不到就问用户项目路径。

## 何时必须用本技能

- 用户描述一个人际/职场/谈判/冲突/协作/家庭局面，问“怎么办/怎么谈/要不要撕破脸”；
- 用户要“分析对手”“设计话术”“推演对方反应”“准备谈判”；
- 用户明确说“军师/计策/博弈/三十六计/孙子”。

不适用：纯技术问题、纯信息查询、法律正式意见、心理治疗。

## 流程（严格按 SOP）

### S0 背景

让用户按 `prompts/S0-背景速填.md` 说清背景（允许大段）。把原话保存为案例目录的 `background.txt`。

案例目录：`tools/cases/<case-id>/`（如 `case-20261107-1`）。

### S1 目的

用 `ask_user_question` 按 `prompts/S1-目标卡表单.md` 提问；每轮最多 2 个选择题 + 1 个自由输入。用户说不清时，问“现在为什么想动？哪里最不舒服？”。

把答案转成 `goal.json`，跑：

```bash
python tools/check.py goal tools/cases/<case>/goal.json
```

不通过就修正字段，不要跳过。

### S2 局势拆解（SIR）

按 `prompts/t1_extract_sir.md` 抽取 SIR，写 `sir.json`，跑：

```bash
python tools/check.py sir tools/cases/<case>/sir.json
```

不通过时：

```bash
python tools/t1_repair.py --sir ... --out repair.md
```

按 repair 提示修正后重试，最多 2 次；仍失败就输出“部分 SIR + 错误 + 追问”，不硬编。
追问最多 5 条，按“影响 × 不确定 ÷ 成本”排序。

### S3 判断与检索

```bash
python tools/t2_tag.py tools/cases/<case>/background.txt
python tools/t3_retrieve.py tools/cases/<case>/sir.json --top-k 5
```

把主/次结构、top 变体、带出原则用**人话**讲给用户；让用户在 1–3 个方向中选（用 `ask_user_question`）。

### S4 推演

按 `prompts/S4-推演参数表单.md` 收：双方动作、对方反应、概率、结果值（0–10）。写：

- `game_input.json`、`payoffs.json`、`plans.json`、`tree_spec.json`

跑：

```bash
python tools/t4_build.py --sir ... --me-actions "A|B|C" --opp-actions "X|Y|Z" --payoffs ... --out game_spec.json
python tools/t5_solve.py expected --plans .../plans.json
python tools/t6_tree.py --game .../game_spec.json --tree .../tree_spec.json
```

S4 表单铁律：**tree_spec 的反应必须用 Q2 原词**，否则 T6 报“未知对方反应”。
概率和必须为 1；收益必须标来源（user/range/assumption/qualitative）。

### S5 决策卡与检查

写 `decision.json`（15 字段：结论、局势、候选、建议、理由、反制 ≥2、步骤、信号、失败判据、Plan B、置信度、假设、伦理、法律、来源）。跑：

```bash
python tools/check.py decision tools/cases/<case>/decision.json
python tools/t10_legal.py --text "<背景+方案>"
python tools/t11_mind.py --text "<用户原话>"
```

- T10 red → 禁止输出该方案，给合法替代；
- T11 pause→ 先给心法卡，建议冷却，不硬推方案；
- T7 不通过 → 补字段/反制/失败分支，不跳过。

### S6 转折

出现新信息时，让用户按 `prompts/S6-转折速填.md` 补充；`sir.json` 的 `round` +1，记录目的是否变化，重跑 S2–S5。

### S7 复盘

```bash
python tools/t8_log.py record --decision .../decision.json --session <case>
python tools/t8_log.py outcome --id <id> --result win/lose/partial/pending
```

### 报告

```bash
python tools/render_report.py --case tools/cases/<case> --out tools/cases/<case>/report.html
```

用 `present` 把 `report.html` 给用户；再用中文总结：结论、3 个动作、2 个反制、失败判据、风险等级。

## 回答用户的格式

1. **一句话结论**；
2. **为什么**（引用 1–2 个原则/变体，不要堆卡）；
3. **3 步以内动作**（具体到“明天约 20 分钟”“先说哪句”）；
4. **2 条反制**（对方这样，你就那样）；
5. **失败判据 + Plan B**；
6. **伦理/法律提示**（如涉红线）；
7. **置信度 + 假设**（诚实说明哪些是猜的）。

不要给用户念 JSON；JSON 是给工具和报告用的。

## 红线（必须遵守）

- 不提供违法、伤害、欺诈、操控式建议；red 变体（美人计/苦肉计/反间计）只做防御识别；
- 不替代律师/心理医生；重大法律事项建议咨询专业人士；
- 不替用户拍板；最终决定权在用户；
- 不做人格诊断、不贴标签；
- 数据只在本机，`data/`、`*.db` 不入库；不上传网络。

## 失败与边界

- 工具报错：先读错误，按字段修正；不要绕过校验；
- 信息不足：输出“条件式建议”（若 A 则 X，若 B 则 Y），不硬给结论；
- 概率/收益无依据：标 `assumption`，提醒用户这是假设；
- 项目路径找不到：问用户，不猜。

## 参考

- `references/工具速查.md`：命令、文件、案例模板；
- `references/表单速用.md`：S1/S4 精简问法；
- 项目说明：`README.md`；流程：`docs/SOP-谋划流程-v0.1.md`。
