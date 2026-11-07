# dsh-strategist · 中文博弈军师

一套**本地离线**运行的「人对人博弈」工作台：知识库 + 拆解工具链 + 表单 + 可视化报告，并封装为 DSH 技能。

适用于人际、职场、谈判、冲突、协作、家庭等场景下的策略判断、谈判准备与关系取舍。
不适用于违法手段、伤害他人、正式法律意见、心理治疗。

---

## 快速开始

要求：Python 3.8+，无需安装依赖。

```bash
# 跑一个完整示例（T0–T11）
python tools/run_pipeline.py --case examples/case4 --out /tmp/case4-run

# 生成可视化报告，浏览器打开
python tools/render_report.py --case examples/case4 --out examples/case4/report.html
```

示例案例：晋升竞聘（竞争 + 权威），包含背景、目标卡、SIR、推演参数与决策卡。

---

## 安装为 DSH 技能

```bash
# 预览将写入的文件
python tools/install_skill.py --scope user --dry-run

# 用户级（推荐，任意会话可用）
python tools/install_skill.py --scope user

# 或项目级（仅本项目会话）
python tools/install_skill.py --scope project
```

安装后，在对话里说“军师，帮我分析这个局面”即可触发。

---

## 本包内容

```
skills/dsh-strategist/   技能（SKILL.md + 参考）
tools/               11 个工具 + 主链路 + 渲染 + 安装器
tools/rules/         结构与法律/心性规则库
prompts/             T1 提示词 + S0/S1/S4/S6 表单
kb/                  8 部原典、158 张卡、47 个统一变体、索引
docs/                用户文档（SOP、知识库结构）
examples/case4/      示例案例
README.md  LICENSE  package.json  RELEASE_MANIFEST.json
```

---

## 工具

| 工具 | 作用 |
|---|---|
| `check.py` | 目标卡/局势卡/决策卡校验 |
| `t1_repair.py` | 抽取校验与修复闭环 |
| `t2_tag.py` | 结构与标签规则 |
| `t3_retrieve.py` | 机制/标签 → 变体/原则 |
| `t4_build.py` | 博弈结构 |
| `t5_solve.py` | 期望值 / 最小最大 |
| `t6_tree.py` | 分支树与概率归一 |
| `t8_log.py` | 日志与复盘 |
| `t9_profile.py` | 对手画像 |
| `t10_legal.py` | 法律风险 |
| `t11_mind.py` | 心性评估 |
| `run_pipeline.py` | 主链路 |
| `render_report.py` | HTML 报告 |
| `install_skill.py` | 技能安装 |

---

## 已知限制

- 西方卡为二手提炼，参数是启发式；
- 8 部原典为初采，文本未逐字校勘；
- T1 抽取依赖 LLM 提示词；
- T5/T6 的概率与收益来自用户假设；
- T10/T11 是规则启发式，不构成法律意见/心理诊断；
- 本发布包为运行时版本，不含测试与设计资料。

---

## 伦理与边界

- 不提供违法、伤害、欺诈、操控式建议；
- 高风险计策（美人计/苦肉计/反间计）仅用于防御识别；
- 不替代律师、心理医生；
- 最终决定权在用户；数据默认留本地。

---

## 许可

GPL-3.0。完整条款见 [LICENSE](LICENSE)；衍生作品需同样以 GPL-3.0 开源并保留声明。
