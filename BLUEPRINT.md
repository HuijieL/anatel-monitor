# Anatel 竞品认证监控系统 — 工程蓝图

> 基于 GitHub Actions + Anatel Open Data + Claude Skill 的全自动竞品入网监控方案
> 每周自动抓取 → git 版本化 → Claude 分析 → 邮件推送

---

## 一、系统架构

```
┌─────────────────────────────────────────────────────────┐
│                   GitHub Actions (免费)                   │
│              每周一 UTC 12:00 自动运行 (BRT 09:00)        │
│                                                         │
│  ┌──────────────────┐    ┌──────────────┐    ┌────────┐ │
│  │ 1. 下载 Anatel    │───▶│ 2. 过滤品牌   │───▶│ 3. 存储 │ │
│  │ 全量 ZIP (47MB)   │    │ 7 品牌 4130 行 │    │ CSV    │ │
│  └──────────────────┘    └──────────────┘    └────────┘ │
│                                                    │     │
│                              git commit + push ◄───┘     │
└─────────────────────────────────────────────────────────┘
                              │
                    版本化 CSV 文件（GitHub 仓库）
                    git history = 时间序列
                              │
┌─────────────────────────────────────────────────────────┐
│               你的电脑 (Claude Code + Skill)              │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │ git pull      │───▶│ analyze.py   │───▶│ send_     │  │
│  │ 拉取最新数据   │    │ diff 新增型号  │    │ report.py │  │
│  └──────────────┘    └──────────────┘    └───────────┘  │
│                              │                    │      │
│                        终端报告展示          Resend 邮件   │
└─────────────────────────────────────────────────────────┘
```

**核心价值：** 竞品新机型入网认证 = 上市前 2-6 个月的信号，用于 GTM 竞争情报。

---

## 二、前置准备

### 2.1 需要的账号

| 账号 | 用途 | 费用 | 状态 |
|------|------|------|------|
| GitHub | 托管代码 + Actions 自动抓取 | 免费 | ✅ 已有 (HuijieL/anatel-monitor) |
| Resend | 发送邮件报告 | 免费 (100封/天) | ✅ 已有 |

### 2.2 无需注册的部分

- **Anatel 数据源**：公开数据，无需 API key，无需登录
- **OAuth**：不需要，Anatel 是公开 ZIP 下载

---

## 三、数据源

| 属性 | 详情 |
|------|------|
| **来源** | Anatel 开放数据 (巴西国家电信管理局) |
| **全量产品 URL** | `https://www.anatel.gov.br/dadosabertos/paineis_de_dados/certificacao_de_produtos/produtos_certificados.zip` |
| **5G 手机 URL** | `https://www.anatel.gov.br/dadosabertos/paineis_de_dados/certificacao_de_produtos/celulares_5g_homologados.zip` |
| **格式** | ZIP → CSV (分号分隔, UTF-8 BOM) |
| **全量大小** | ZIP 7MB → CSV 47MB, 178,416+ 行 |
| **过滤后** | ~4,130 行, ~600KB (7 个品牌) |
| **更新频率** | Anatel 每日更新，我们每周一抓取 |
| **需要登录** | ❌ 公开数据 |

### CSV 字段映射

| 原始字段名 | 过滤后字段名 | 含义 | 用途 |
|-----------|-------------|------|------|
| `Data da Homologação` | `data_homologacao` | 认证日期 (DD/MM/YYYY) | 判断新增时间 |
| `Número de Homologação` | `numero_homologacao` | 认证编号 | 唯一标识 |
| `Nome do Fabricante` | `fabricante` | 制造商名称 | 品牌匹配 |
| — | `brand` | 标准品牌名 (脚本生成) | 分组/过滤 |
| `Modelo` | `modelo` | 型号 | 识别产品 |
| `Nome Comercial` | `nome_comercial` | 商业名称 | 如 "JOVI V50 Lite 5G" |
| `Tipo do Produto` | `tipo_produto` | 产品类型 | 如 "Telefone Móvel Celular" |
| `Situação do Requerimento` | `situacao` | 认证状态 | 如 "Homologação Emitida" |
| `País do Fabricante` | `pais` | 制造商国家 | 供参考 |

### 品牌 → 制造商名称映射 (config/brands.json)

| 品牌 | Anatel 中的制造商名称 | 当前数据量 |
|------|----------------------|-----------|
| SAMSUNG | Samsung Electronics Co Ltd. / SAMSUNG ELECTRONICS CO., LTD / SAMSUNG ELECTRONICS CO., LTD. | 2,000 |
| APPLE | Apple Inc. | 910 |
| JBL | Harman International Industries Inc. / Harman International Industries, Inc. / HARMAN INTERNATIONAL INDUSTRIES, INC | 587 |
| XIAOMI | Xiaomi Communications Co., Ltd. / Xiaomi Communication Technology Co., Ltd. | 462 |
| OPPO | Guangdong OPPO Mobile Telecommunications Co., Ltd | 92 |
| HONOR | Honor Device Co., Ltd | 49 |
| VIVO | Vivo Mobile Communication Co., Ltd (商业名称用 JOVI) | 30 |

### 排除的产品类型

- Bateria de Lítio utilizada em Telefone Celular (锂电池)
- Carregador para Telefone Celular (充电器)
- Acessório p/ Telefone Móvel Celular do tipo Bateria Auxiliar (充电宝)

---

## 四、仓库结构

```
anatel-monitor/
├── .github/
│   └── workflows/
│       └── fetch_data.yml             # GitHub Actions 定时抓取
├── config/
│   └── brands.json                    # 品牌 → 制造商名称映射 + 排除类型
├── scripts/
│   ├── fetch_anatel.py                # 云端：下载 ZIP → 过滤 → 保存 CSV
│   ├── analyze.py                     # 本地：git diff 找新增型号
│   └── send_report.py                 # 本地：Resend API 发送 HTML 邮件
├── data/
│   ├── watched_brands.csv             # 过滤后的竞品数据 (git 版本化)
│   ├── celulares_5g.csv               # 5G 手机数据
│   └── meta.json                      # 抓取元数据 (时间/品牌统计)
├── BLUEPRINT.md                       # ← 本文档
├── DEPLOY_GUIDE.md                    # 部署指南
└── README.md
```

---

## 五、核心文件详细设计

### 5.1 `scripts/fetch_anatel.py` — 云端抓取脚本

**运行环境：** GitHub Actions (ubuntu-latest, Python 3.11)
**触发频率：** 每周一 UTC 12:00 + 手动触发

流程：
1. 从 Anatel 下载全量 ZIP (~7MB)
2. 解压 CSV (~47MB, 178k+ 行, 分号分隔, UTF-8 BOM)
3. 读取 `config/brands.json` 构建制造商名称 → 品牌映射
4. 逐行过滤：匹配品牌 + 排除电池/充电器类型
5. 输出精简 CSV 到 `data/watched_brands.csv` (~600KB, ~4130 行)
6. 下载 5G 手机专项数据，保存到 `data/celulares_5g.csv`
7. 写入 `data/meta.json` (抓取时间、各品牌行数统计)

**已实现 ✅** — 见 `scripts/fetch_anatel.py`

### 5.2 `scripts/analyze.py` — 本地分析脚本

**运行环境：** 用户本机 / Claude Skill
**依赖：** 需要 git 历史（至少 2 次 commit）

流程：
1. `git pull --ff-only` 拉取最新数据
2. 读取当前 `data/watched_brands.csv`
3. 通过 `git show {ref}:data/watched_brands.csv` 读取历史版本
4. 对比 `(brand, modelo)` 键值，找出新增项
5. 去重（同一型号多条记录取有商业名称的）
6. 支持输出格式：`table` / `json` / `markdown`
7. 支持过滤：`--brand SAMSUNG` / `--days 7`

**已实现 ✅** — 见 `scripts/analyze.py`

### 5.3 `scripts/send_report.py` — 邮件发送脚本

**运行环境：** 用户本机 / Claude Skill
**依赖：** `RESEND_API_KEY` + `REPORT_EMAIL` 环境变量

流程：
1. 读取 JSON 报告文件 (参数传入路径)
2. 解析 `new_items` 数组和 `date` 字段
3. 生成 HTML 邮件：按品牌分组的表格 + 统计摘要
4. 通过 Resend API 发送到 `REPORT_EMAIL`
5. 支持 `--dry-run` 模式（只打印不发送）

**已实现 ✅** — 见 `scripts/send_report.py`

**输入 JSON 格式：**
```json
{
  "date": "2026-04-10",
  "new_items": [
    {
      "brand": "SAMSUNG",
      "modelo": "SM-S936B/DS",
      "nome_comercial": "Galaxy S25 Ultra",
      "data_homologacao": "15/03/2026",
      "tipo_produto": "Telefone Móvel Celular",
      "fabricante": "Samsung Electronics Co Ltd.",
      "situacao": "Homologação Emitida",
      "pais": "Coréia"
    }
  ]
}
```

### 5.4 `.github/workflows/fetch_data.yml` — 自动化配置

**已实现 ✅**

```yaml
name: Fetch Anatel Data
on:
  schedule:
    - cron: '0 12 * * 1'     # 每周一 UTC 12:00 = BRT 09:00
  workflow_dispatch:          # 手动触发
jobs:
  fetch:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Fetch and filter Anatel data
        run: python scripts/fetch_anatel.py
      - name: Commit if changed
        run: |
          git config user.name 'github-actions[bot]'
          git config user.email 'github-actions[bot]@users.noreply.github.com'
          git add data/
          git diff --staged --quiet || git commit -m "data: update $(date -u +%Y-%m-%d)"
          git push
```

### 5.5 Claude Skill 定义

**已实现 ✅** — 见 `~/.claude/skills/anatel-monitor/SKILL.md`

触发词：Anatel、巴西认证、入网、homologação、竞品新机型
流程：git pull → analyze.py → 终端报告 → send_report.py 邮件

---

## 六、环境变量配置

### 本地环境

在 `~/.zshrc` 或 `.env` 中配置：

| 变量 | 值 | 说明 |
|------|---|------|
| `RESEND_API_KEY` | `re_xxxxxxxx` | Resend API 密钥 |
| `REPORT_EMAIL` | 你的邮箱地址 | 接收报告的邮箱 |

### GitHub Secrets

本项目 GitHub Actions **不需要 Secrets** — Anatel 数据是公开的，Actions 只负责下载数据和 commit，不发邮件。

---

## 七、实施状态

### 阶段一：数据采集 ✅ 已完成

```
✅ Step 1: 创建 GitHub 仓库 (HuijieL/anatel-monitor)
✅ Step 2: 编写 fetch_anatel.py（下载 + 过滤）
✅ Step 3: 配置 brands.json（7 品牌映射）
✅ Step 4: 配置 GitHub Actions（每周一自动抓取）
✅ Step 5: 首次抓取成功 (4,130 行, 7 品牌)
✅ Step 6: 推送到 GitHub
```

### 阶段二：分析脚本 ✅ 已完成

```
✅ Step 7: 编写 analyze.py（git diff 对比）
✅ Step 8: 支持 table/json/markdown 输出
✅ Step 9: 支持 --brand 和 --days 过滤
```

### 阶段三：邮件投递 ✅ 已完成

```
✅ Step 10: 编写 send_report.py（Resend API）
✅ Step 11: HTML 邮件模板（品牌分组表格）
```

### 阶段四：Claude Skill ✅ 已完成

```
✅ Step 12: 创建 SKILL.md (anatel-monitor)
✅ Step 13: 注册为可用 skill
```

### 阶段五：端到端验证 ⬜ 待完成

```
⬜ Step 14: 配置 RESEND_API_KEY + REPORT_EMAIL 环境变量
⬜ Step 15: 等待至少第 2 次 Actions 运行（有 git diff）
⬜ Step 16: 运行 /anatel-monitor 端到端测试
⬜ Step 17: 确认邮件收到
```

---

## 八、analyze.py 输出格式适配

当前 `analyze.py --output json` 输出的是纯数组 `[{...}, {...}]`，而 `send_report.py` 期望的输入是 `{"new_items": [...], "date": "..."}` 格式。

**需要的适配方案（二选一）：**

**方案 A：修改 analyze.py** — 增加 `--output report-json` 模式，直接输出 send_report.py 期望的格式。

**方案 B：Skill 中间层处理** — Claude Skill 读取 analyze.py 的 JSON 数组输出，包装为 `{"new_items": [...], "date": "YYYY-MM-DD"}` 后写入 `/tmp/anatel-report.json`，再交给 send_report.py。

**推荐方案 A**，减少 Skill 中的逻辑。

---

## 九、常见问题

### Q: Anatel 数据源挂了怎么办？

fetch_anatel.py 会报错并 `sys.exit(1)`，GitHub Actions 该次运行失败，不会 commit 空数据。历史数据不受影响。

### Q: 某个品牌的制造商名称变了怎么办？

编辑 `config/brands.json`，在对应品牌的数组中添加新的名称变体。无需改代码。

### Q: 如何添加新的监控品牌？

在 `config/brands.json` 的 `watch_brands` 中添加条目。例如添加 Motorola：
```json
"MOTOROLA": [
  "Motorola Mobility LLC"
]
```
然后手动触发一次 Actions 或等下周一自动抓取。

### Q: 如何排除更多产品类型？

在 `config/brands.json` 的 `exclude_types` 数组中添加要排除的 `Tipo do Produto` 值。

### Q: 我想看更长时间范围的变化？

```bash
python scripts/analyze.py --days 30          # 对比 30 天前
python scripts/analyze.py --ref HEAD~4       # 对比 4 周前
```

### Q: GitHub Actions 免费额度够用吗？

每次运行约 30 秒，每周一次。GitHub 免费额度 2000 分钟/月，本项目月耗约 2 分钟，完全足够。

---

## 十、后续增强方向

| 方向 | 说明 | 优先级 | 难度 |
|------|------|--------|------|
| 格式适配 | analyze.py 增加 report-json 输出模式 | 高 | 低 |
| 定时 Skill | 通过 Claude schedule 每周一自动触发 /anatel-monitor | 高 | 低 |
| 添加品牌 | Motorola, Realme, Nothing, Google, Tecno | 中 | 低 |
| 5G 交叉分析 | 结合 celulares_5g.csv，标注新认证产品是否支持 5G | 中 | 中 |
| 产品类型统计 | 按品类（手机/穿戴/音频/IoT）分类统计趋势 | 中 | 低 |
| 认证时间线 | 分析各品牌认证到上市的平均时间差 | 低 | 中 |
| 多国扩展 | 添加 FCC (美国)、NBTC (泰国) 等其他认证机构 | 低 | 高 |

---

*文档版本: v1.0 | 创建日期: 2026-04-10 | 基于 Meli Price Tracker 蓝图框架设计*
