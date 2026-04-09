# Anatel Monitor — 部署指南

## 一、项目概述

GitHub Actions 每周一自动下载 Anatel 产品认证开放数据，过滤为竞品品牌子集，commit 到仓库形成版本历史。本地通过分析脚本或 Claude Skill 触发对比，找出新认证产品并发送邮件。

**核心价值：** 竞品新机型入网 = 上市前 2-6 个月的信号。

---

## 二、数据源（Phase 0 验证结果）

| 属性 | 详情 |
|------|------|
| **来源** | Anatel 开放数据 |
| **下载 URL** | `https://www.anatel.gov.br/dadosabertos/paineis_de_dados/certificacao_de_produtos/produtos_certificados.zip` |
| **5G 手机 URL** | `https://www.anatel.gov.br/dadosabertos/paineis_de_dados/certificacao_de_produtos/celulares_5g_homologados.zip` |
| **格式** | ZIP → CSV (分号分隔, UTF-8 BOM) |
| **全量大小** | ZIP 7MB → CSV 47MB, 178,416 行 |
| **过滤后** | 4,130 行, 609KB (7 个品牌) |
| **更新频率** | Anatel 每日更新，我们每周一抓取 |
| **需要登录** | ❌ 公开数据，无需 API key |

### CSV 字段映射

| 字段名 | 含义 | 用途 |
|--------|------|------|
| `Data da Homologação` | 认证日期 (DD/MM/YYYY) | 判断新增 |
| `Número de Homologação` | 认证编号 | 唯一标识 |
| `Nome do Fabricante` | 制造商名称 | 品牌过滤 |
| `Modelo` | 型号 | 识别产品 |
| `Nome Comercial` | 商业名称 | 如 "JOVI V50 Lite 5G" |
| `Tipo do Produto` | 产品类型 | 如 "Telefone Móvel Celular" |
| `Situação do Requerimento` | 认证状态 | 如 "Homologação Emitida" |
| `País do Fabricante` | 制造商国家 | 供参考 |

### 品牌 → 制造商名称映射

| 品牌 | Anatel 中的制造商名称 |
|------|----------------------|
| SAMSUNG | Samsung Electronics Co Ltd. / SAMSUNG ELECTRONICS CO., LTD |
| APPLE | Apple Inc. |
| XIAOMI | Xiaomi Communications Co., Ltd. |
| HONOR | Honor Device Co., Ltd |
| OPPO | Guangdong OPPO Mobile  Telecommunications Co., Ltd |
| VIVO/JOVI | Vivo Mobile Communication Co., Ltd (商业名称用 JOVI) |
| JBL | Harman International Industries Inc. |

---

## 三、部署步骤

### Step 1: 创建 GitHub 仓库

1. 打开 https://github.com/new
2. 仓库名: `anatel-monitor`
3. 可选 Private
4. 不勾选 "Initialize with README"（我们已有代码）

### Step 2: 推送代码

```bash
cd ~/Desktop/anatel-monitor
git init
git add .
git commit -m "init: anatel certification monitor"
git branch -M main
git remote add origin https://github.com/你的用户名/anatel-monitor.git
git push -u origin main
```

### Step 3: 手动触发测试

1. 进入仓库 → Actions 页面
2. 左侧选 "Fetch Anatel Data"
3. 点击 "Run workflow" → "Run workflow"
4. 等待完成（约 30 秒），检查 `data/` 目录是否有文件

### Step 4: 配置邮件通知（可选）

在仓库 Settings → Secrets and variables → Actions 中添加：

| Secret | 值 |
|--------|---|
| `RESEND_API_KEY` | 你的 Resend API Key |
| `REPORT_EMAIL` | 接收邮件的地址 |

### Step 5: 本地分析

```bash
# 克隆仓库
git clone https://github.com/你的用户名/anatel-monitor.git
cd anatel-monitor

# 等至少两次 Action 运行后，对比新增
python scripts/analyze.py
python scripts/analyze.py --brand SAMSUNG
python scripts/analyze.py --brand XIAOMI --output markdown
```

---

## 四、运行频率

- GitHub Action: **每周一 BRT 09:00** (UTC 12:00)
- 手动触发: 随时可在 Actions 页面点击 "Run workflow"

---

## 五、后续扩展

- [ ] Claude Skill `/anatel` 一键触发分析 + 邮件
- [ ] 添加更多品牌（编辑 `config/brands.json`）
- [ ] Motorola, Realme, Nothing, Google 等品牌
- [ ] 价格趋势与认证时间线关联分析
