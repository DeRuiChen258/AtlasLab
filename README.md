# AtlasLab

AtlasLab 是面向中文数学建模竞赛的多智能体系统：赛题与附件解析、蓝图审查、分阶段建模、代码求解、
图表生成、分节写作、量化评审到 LaTeX 出稿，整条链路由 LangGraph 驱动，并提供本地 Web 工作台
用于配置、启动与监控。

现行实现要点、质量基线与已知边界统一记录在 [`docs/README.md`](docs/README.md)，本文件只做入口说明。

---

## 核心能力

- **端到端多智能体流水线**：ProblemBlueprint → 蓝图审查 → 分阶段建模 → 模型—代码一致性 →
  独立基线 → 敏感性分析 → 图像评审 → 分节写作 → 论文评审 → 量化评价 → 人工审核 → LaTeX 编译 →
  finalizer，全部由 LangGraph 编排，产物落盘可审计。
- **本地 Web 工作台**：首次访问走五步向导（环境检查 → 服务商选择 → 密钥填写 → 模型验证 → 保存配置），
  之后按“导入题目 → 确认题目 → 启动生成”推进，并提供运行日志与产物面板。
- **检查点恢复**：modeler、coder、sensitivity、figure、writer 等昂贵节点可从 SQLite checkpoint 定点恢复；
  运行状态为 `failed` 且存在 `checkpoints.sqlite` 时，Web 与 CLI 都能续跑。确定性配置错误进入 `blocked`，
  修正配置后再恢复。人工审核的批准/拒绝走独立的 `resume` / `supervise-resume`，不与错误恢复混用。
- **硬门禁与证据隔离**：runner 对子进程树执行 120 秒 / 2 GB 的默认硬限制，拒绝未读取附件、硬编码、
  全零、非法数值以及“退出码 0 但正文声明失败”的结果；`primary`、`baseline`、`supporting` 与临时
  attempt 的证据职责相互隔离，正式论文只消费当前批次已验证的证据。
- **文档导入与 RAG 检索**：题目与附件支持 PDF、Word、Excel、CSV、Markdown、TXT，内置 PDF → Markdown
  提取（PyMuPDF / pypdf）；`math-agent ingest` 会把语料切块、嵌入并写入 sqlite-vec，检索时按
  “向量 : BM25 = 0.7 : 0.3” 的默认权重混合排序。

---

## 环境要求

- Python 3.11–3.13（推荐 `uv`）
- Node.js 18+
- 模型后端：Ollama，或任意 OpenAI 兼容端点（DeepSeek 等）

---

## 快速开始

```bash
git clone https://github.com/DeRuiChen258/AtlasLab.git
cd AtlasLab

npm install
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv sync                                              # 或：pip install -e .

cp .env.example .env                                 # 填写 API 密钥与模型
npm start
```

浏览器打开 `http://127.0.0.1:5173`，按首次配置向导完成模型配置；缺少 `.env` 或密钥时页面会自动进入向导。

桌面形态可以直接运行 `python3 AtlasLab.py`：它在本机默认端口 `18080` 启动同一套前端，并在服务端把
上传的 PDF 转成 Markdown 后再交给流水线。

---

## 命令行

```bash
# 完整跑一次：默认输出到 runs/latest，默认在人工审核处暂停
math-agent run --problem problems/huazhong-2026-a-green-logistics.json --out runs/latest

# 无需人工介入，直接跑到底
math-agent run --problem <题目.json> --out runs/<run> --no-interrupt

# 后台受监管运行：崩溃或可恢复故障后自动从 checkpoint 续跑
math-agent start --problem <题目.json> --out runs/<run>

# 恢复、人审与监管到终态
math-agent recover           --out runs/<run> --thread <thread>
math-agent supervise-recover --out runs/<run> --thread <thread>
math-agent resume            --out runs/<run> --thread <thread> --approve
math-agent supervise-resume  --out runs/<run> --thread <thread> --approve

# 状态、报告、语料入库与基准
math-agent status --out runs/<run> --thread <thread>
math-agent report --out runs/<run> --thread <thread>
math-agent ingest --src corpus --db runs/rag.sqlite
math-agent bench  --out runs/bench        # live 回归，需要真实 API key
```

`math-agent --help` 会列出全部命令。`run` 与 `supervise` 还支持 `--template gmcm`，配合
`--school` / `--team-id` / `--members` 可直接产出国赛 `gmcmthesis` 模板稿件。

---

## 配置要点

`.env.example` 是配置真相源，常用项如下：

| 变量 | 说明 |
| --- | --- |
| `MATH_AGENT_DEFAULT_MODEL` / `MATH_AGENT_STRONG_MODEL` / `MATH_AGENT_CODER_MODEL` / `MATH_AGENT_FIGURE_MODEL` | 各角色使用的模型 |
| `MATH_AGENT_COMMAND` | Web 服务调用后端的命令，默认 `uv run math-agent` |
| `MATH_AGENT_LLM_*` | 单次尝试超时、总预算与降级模型预留 |
| `MATH_AGENT_CODE_TIMEOUT` / `MATH_AGENT_CODE_MEMORY_LIMIT_MB` | 代码节点硬限制，默认 120 秒 / 2048 MB |
| `MATH_AGENT_MIN_*` | 篇幅与质量分门禁（正文页数、字数、各类评审分数下限） |
| `MATH_AGENT_RAG_*` / `MATH_AGENT_HYBRID_*` | RAG 开关、嵌入模型、维度、top-k 与混合检索权重 |
| `OPENAI_API_BASE` / `OPENAI_API_KEY` | OpenAI 兼容端点与密钥 |
| `MINERU_*` | 可选的 MinerU 文档解析服务 |

OpenAI 兼容路由的模型名必须是 `openai/<model>` 形式（例如 `openai/deepseek-chat`）；只配置
`OPENAI_API_BASE` 不能让 LiteLLM 从裸模型名推断 provider。保存到 `.env` 时保留 `provider/`，
连接测试则临时剥离该前缀直连端点，两套协议不能混为一谈。

---

## 目录结构

```
AtlasLab
├── AtlasLab.py              # 桌面/后台启动器（默认端口 18080，内置 PDF → Markdown）
├── frontend/                # 本地 Web 工作台与 Node.js API 服务
├── src/math_agent/          # 流水线核心：graph、nodes、knowledge、rag、tools、supervisor
├── scripts/                 # E2E 与运维脚本
├── corpus/                  # 数学建模语料（教材笔记与算法资料）
├── problems/                # 竞赛题目定义（JSON）
├── docs/                    # 设计与诊断文档，入口 docs/README.md
├── tests/                   # pytest 测试套件
└── runs/                    # 运行产物（已 gitignore）
```

---

## 技术栈

- **编排**：LangGraph + SQLite checkpoint
- **LLM 网关**：LiteLLM 1.91.0（多服务商；固定版本以保证 Windows 可直接安装 wheel）
- **后端**：Python 3.11+（PyMuPDF、pypdf、pydantic、Jinja2、matplotlib、pandas）
- **前端**：Node.js 18+，原生 HTML/CSS/JS
- **检索**：sqlite-vec 向量库 + BM25 混合排序
- **出稿**：LaTeX（内置 `default` 与国赛 `gmcmthesis` 模板）

---

## 验证

```bash
uv run --extra dev pytest -q                                  # Python 全量回归
npm test                                                      # 前端服务端测试
uv run math-agent status --out runs/<run> --thread <thread>    # 运行状态与终态标记
```

论文类运行还要检查 `completion.json` 哈希、正式证据角色与 LaTeX 两遍编译日志，并把 PDF 逐页渲染后做
视觉检查。“流程跑到结尾”或“生成了文件”本身不算验收完成。

---

## 已知边界

- 城市绿色物流真题的主方案仍是启发式可行上界，没有全规模精确下界或全局最优性间隙；时间窗满足率
  93.33%，低于部分获奖论文报告的水平。
- 五类动态事件试验是从同一静态解出发的单事件检查；30 次任务移动压力试验成功率 70%，尚未验证
  连续事件序列与滚动时域长期表现。
- 离线应急评审（`MATH_AGENT_OFFLINE_REVIEW=1`）只为城市绿色物流确定性事实稿提供完整覆盖，
  其他题目不得把它当作通用评审替代品。

完整数值、获奖论文对照与剩余差距见 [`docs/huazhong-2026-a-quality-gap.md`](docs/huazhong-2026-a-quality-gap.md)。

---

## 许可

MIT，见 [`LICENSE`](LICENSE)。
