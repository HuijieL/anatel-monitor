#!/usr/bin/env python3
"""
Send Anatel certification report via Resend API.

Requires:
  RESEND_API_KEY env var
  REPORT_EMAIL env var (recipient)
"""

import json
import os
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent

# Load .env file if present
_env_file = ROOT / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
REPORT_EMAIL = os.environ.get("REPORT_EMAIL", "")
SENDER = "Anatel Monitor <onboarding@resend.dev>"

# ── Product type: Portuguese → (English, Chinese) ──
PRODUCT_TYPES = {
    "Telefone Móvel Celular": ("Mobile Phone", "手机"),
    "Transceptor de Radiação Restrita": ("Short-Range Transceiver", "短距离收发器"),
    "Transceptor de Radiação Restrita - Espalhamento Espectral": ("Spread Spectrum Transceiver", "扩频收发器"),
    "Transceptor de Radiação Restrita - Híbrido": ("Hybrid Short-Range Transceiver", "混合短距离收发器"),
    "Equipamento de Radiocomunicação de Radiação Restrita": ("Short-Range Radio Equipment", "短距离无线电设备"),
    "Estação Terminal de Acesso": ("Access Terminal", "接入终端（路由器/CPE）"),
    "Sistemas de Identificação por Radiofrequências": ("RFID/NFC System", "射频识别系统（NFC/RFID）"),
    "Sistemas Operando nas Faixas de RF Ultra Larga": ("Ultra-Wideband (UWB)", "超宽带（UWB）"),
    "Sistemas Operando Na Faixa de 57 a 64 GHz": ("60GHz Band System", "60GHz频段系统"),
    "Carregador Indutivo para Telefone Celular": ("Wireless Charger", "无线充电器"),
    "Transceptor Móvel por Satélite": ("Satellite Transceiver", "卫星收发器"),
    "Tela interativa para uso educacional": ("Interactive Display", "交互式显示屏"),
    "Microfone sem Fio": ("Wireless Microphone", "无线麦克风"),
    "Modem Analógico": ("Analog Modem", "模拟调制解调器"),
    "Sistema de Acesso sem Fio em Banda Larga - Redes Locais": ("Wireless LAN", "无线局域网"),
    "Equipamento de Fac-Símile": ("Fax Equipment", "传真设备"),
    "Equipamento de Rede de Dados": ("Data Network Equipment", "数据网络设备"),
    "Transceptor para Estação Rádio Base": ("Base Station Transceiver", "基站收发器"),
    "Transceptor Digital": ("Digital Transceiver", "数字收发器"),
    "Multiplex Óptico WDM": ("Optical WDM Multiplexer", "光波分复用器"),
    "Multiplex SDH - Equipamento STM-64": ("SDH Multiplexer", "SDH复用设备"),
    "ONT - Terminação de Rede Ótica": ("Optical Network Terminal", "光网络终端（ONT）"),
    "ONU - Unidade de Rede Óptica": ("Optical Network Unit", "光网络单元（ONU）"),
    "Antena Ponto-Área": ("Point-to-Area Antenna", "点对面天线"),
    "Antena Ponto a Ponto": ("Point-to-Point Antenna", "点对点天线"),
    "Antena Direcional": ("Directional Antenna", "定向天线"),
    "Equipamento para Interconexão de Redes": ("Network Interconnect Equipment", "网络互联设备"),
    "ATA - Adaptador para Telefone Analógico (com fio)": ("Analog Telephone Adapter", "模拟电话适配器"),
    "Sistema de Retificadores": ("Rectifier System", "整流系统"),
}

# ── Keyword → inferred product (English, Chinese) ──
# Order matters: first match wins. Checked against modelo + nome_comercial.
PRODUCT_KEYWORDS = [
    # Wearables
    (r"\bwatch\b", "Smartwatch", "智能手表"),
    (r"\btalkband\b", "Smart Band", "智能手环"),
    (r"\bband\s?\d", "Smart Band", "智能手环"),
    (r"\bband\b(?!.*box)", "Smart Band", "智能手环"),
    (r"\bfit\b", "Fitness Tracker", "运动追踪器"),
    # Huawei Watch: XXX-B09/B19/B29 pattern (Watch GT/D/Fit series)
    (r"^[A-Z]{3}-B[012]9", "Smartwatch", "智能手表"),
    # Huawei Phone: XXX-LNN pattern
    (r"^[A-Z]{3}-L\d", "Smartphone", "智能手机"),
    # Audio
    (r"\bbuds\b", "Wireless Earbuds", "无线耳机"),
    (r"\benco\b", "Wireless Earbuds", "无线耳机"),
    (r"\bearphone", "Earphone", "耳机"),
    (r"\bearbud", "Wireless Earbuds", "无线耳机"),
    (r"\bheadphone", "Headphone", "头戴式耳机"),
    (r"\bheadset", "Headset", "耳麦"),
    (r"\bspeaker\b", "Speaker", "音箱"),
    (r"\bsoundbar\b", "Soundbar", "条形音箱"),
    (r"\bsoundstick", "Speaker", "音箱"),
    (r"\bpartybox\b", "Party Speaker", "派对音箱"),
    (r"\bflip\s?\d", "Portable Speaker", "便携音箱"),
    (r"\bcharge\s?\d", "Portable Speaker", "便携音箱"),
    (r"\bpulse\b", "Portable Speaker", "便携音箱"),
    (r"\bxtreme\b", "Portable Speaker", "便携音箱"),
    (r"\bboombox\b", "Portable Speaker", "便携音箱"),
    (r"\bgo\s?\d", "Portable Speaker", "便携音箱"),
    (r"\bclip\s?\d", "Portable Speaker", "便携音箱"),
    (r"\btune\b", "Headphone/Earbuds", "耳机"),
    (r"\blive\s+\d", "Headphone/Earbuds", "耳机"),
    (r"\bvibe\b", "Headphone/Earbuds", "耳机"),
    (r"\bwave\b", "Headphone/Earbuds", "耳机"),
    (r"\breflect\b", "Sport Earbuds", "运动耳机"),
    (r"\bendurance\b", "Sport Earbuds", "运动耳机"),
    (r"\bfreebuds\b", "Wireless Earbuds", "无线耳机"),
    (r"\bfreeclip\b", "Wireless Earbuds", "无线耳机"),
    # Tablets & Laptops
    (r"\bipad\b", "Tablet", "平板电脑"),
    (r"\bmediapad\b", "Tablet", "平板电脑"),
    (r"\bmatepad\b", "Tablet", "平板电脑"),
    (r"\b(redmi\s+)?pad\b", "Tablet", "平板电脑"),
    (r"\btablet\b", "Tablet", "平板电脑"),
    (r"\bmatebook\b", "Laptop", "笔记本电脑"),
    (r"\bnotebook\b", "Laptop", "笔记本电脑"),
    # Phones (by naming pattern)
    (r"\bgalaxy\s+[sazm]\d", "Smartphone", "智能手机"),
    (r"\bgalaxy\s+note", "Smartphone", "智能手机"),
    (r"\bgalaxy\s+fold", "Foldable Phone", "折叠手机"),
    (r"\bgalaxy\s+z\s+f", "Foldable Phone", "折叠手机"),
    (r"\bpoco\b", "Smartphone", "智能手机"),
    (r"\bredmi\s+\d", "Smartphone", "智能手机"),
    (r"\bredmi\s+note", "Smartphone", "智能手机"),
    (r"\bredmi\s+k\d", "Smartphone", "智能手机"),
    (r"\bmi\s+\d+[a-z]?\b", "Smartphone", "智能手机"),
    (r"\bxiaomi\s+\d+", "Smartphone", "智能手机"),
    (r"\breno\s*\d", "Smartphone", "智能手机"),
    (r"\boppo\s+a\d", "Smartphone", "智能手机"),
    (r"\bjovi\b", "Smartphone", "智能手机"),
    (r"\bhonor\s+magic", "Smartphone", "智能手机"),
    (r"\bhonor\s+x\d", "Smartphone", "智能手机"),
    (r"\biphone\b", "Smartphone", "智能手机"),
    (r"\bmate\s+\d", "Smartphone", "智能手机"),
    (r"\bp\d+\s+(pro|lite)", "Smartphone", "智能手机"),
    (r"\bnova\s+\d", "Smartphone", "智能手机"),
    # Smart home & IoT
    (r"\bcamera\b", "Camera", "摄像头"),
    (r"\bdoorbell\b", "Smart Doorbell", "智能门铃"),
    (r"\btv\b", "TV / Display", "电视/显示器"),
    (r"\brouter\b", "Router", "路由器"),
    (r"\bsmartthings\b", "IoT Hub", "智能家居中枢"),
    (r"\bsmart\s?tag\b", "Tracker Tag", "追踪标签"),
    # Samsung wearables by model prefix
    (r"\bSM-R[1-5]\d{2}\b", "Wearable (Buds/Band/Ring)", "穿戴设备（耳机/手环/戒指）"),
    (r"\bSM-R[6-9]\d{2}\b", "Smartwatch", "智能手表"),
    (r"\bEI-T\d+\b", "Tracker Tag", "追踪标签"),
    (r"\bwifi.*extender\b", "WiFi Extender", "WiFi扩展器"),
    (r"\brange\s+extender\b", "WiFi Extender", "WiFi扩展器"),
    (r"\bstick\b", "Streaming Stick", "电视棒"),
    (r"\bprojector\b", "Projector", "投影仪"),
    # Accessories
    (r"\bs.pen\b", "Stylus", "触控笔"),
    (r"\bpen\b", "Stylus", "触控笔"),
    (r"\bcharger\b|charging\s+pad", "Wireless Charger", "无线充电器"),
    # Network equipment (Huawei enterprise)
    (r"\bairengine\b", "Enterprise WiFi AP", "企业级WiFi接入点"),
    (r"\bap\d{3,}", "WiFi Access Point", "WiFi接入点"),
    (r"\b(s|ce)?5[0-9]{3}", "Network Switch", "网络交换机"),
    (r"\b(s|ce)?6[0-9]{3}", "Network Switch", "网络交换机"),
    (r"\b(s|ce)?8[0-9]{3}", "Network Switch", "网络交换机"),
    (r"\b(s|ce)?9[0-9]{3}", "Network Switch", "网络交换机"),
    (r"\bar\d{3,}", "Enterprise Router", "企业路由器"),
    (r"\batn\b", "Transport Router", "传输路由器"),
    (r"\boptix\b", "Optical Transport", "光传输设备"),
    (r"\brru\b", "Remote Radio Unit", "远端射频单元"),
    (r"\bbts\b", "Base Station", "基站"),
    (r"\benode\b", "eNodeB Base Station", "4G基站"),
    (r"\bgnodeb\b", "gNodeB Base Station", "5G基站"),
    (r"\bonte?\b", "Optical Terminal", "光终端"),
    (r"\bonu\b", "Optical Network Unit", "光网络单元"),
    (r"\busg\b", "Firewall/Gateway", "防火墙/网关"),
    (r"\bnetengine\b", "Enterprise Router", "企业路由器"),
    (r"\becolife\b", "Optical Terminal", "光终端"),
]


# ── Certification status ──
STATUS_MAP = {
    "Homologação Emitida": ("Certified", "已认证，可上市销售"),
    "Em Análise - RE": ("Under Review", "审核中，尚未获批"),
    "Homologação Suspensa": ("Suspended", "认证已暂停"),
    "Homologação Cancelada": ("Cancelled", "认证已取消"),
}

CERTIFIED = "Homologação Emitida"

# ── Country ──
COUNTRY_MAP = {
    "Coréia": ("South Korea", "韩国"),
    "Estados Unidos da América": ("United States", "美国"),
    "China": ("China", "中国"),
    "Japão": ("Japan", "日本"),
    "Vietnã": ("Vietnam", "越南"),
    "Índia": ("India", "印度"),
    "Alemanha": ("Germany", "德国"),
    "Finlândia": ("Finland", "芬兰"),
    "Suécia": ("Sweden", "瑞典"),
    "Taiwan, Província da China": ("Taiwan", "中国台湾"),
    "Tailândia": ("Thailand", "泰国"),
    "Indonésia": ("Indonesia", "印度尼西亚"),
    "Malásia": ("Malaysia", "马来西亚"),
    "México": ("Mexico", "墨西哥"),
    "Brasil": ("Brazil", "巴西"),
    "Reino Unido": ("United Kingdom", "英国"),
    "França": ("France", "法国"),
    "Itália": ("Italy", "意大利"),
    "Dinamarca": ("Denmark", "丹麦"),
    "Hungria": ("Hungary", "匈牙利"),
    "Polônia": ("Poland", "波兰"),
    "Irlanda": ("Ireland", "爱尔兰"),
    "Singapura": ("Singapore", "新加坡"),
    "Filipinas": ("Philippines", "菲律宾"),
}


def send_email(subject, html_body):
    if not RESEND_API_KEY:
        print("ERROR: RESEND_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    if not REPORT_EMAIL:
        print("ERROR: REPORT_EMAIL not set", file=sys.stderr)
        sys.exit(1)

    payload = json.dumps({
        "from": SENDER,
        "to": [REPORT_EMAIL],
        "subject": subject,
        "html": html_body,
    }).encode("utf-8")

    req = Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "anatel-monitor/1.0",
        },
    )

    with urlopen(req) as resp:
        result = json.loads(resp.read())
        print(f"Email sent: {result}")


def infer_product(modelo, nome_comercial):
    """Infer actual product type from model number and commercial name."""
    text = f"{nome_comercial} {modelo}".lower()
    for pattern, en, zh in PRODUCT_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            return f"{en} / {zh}"
    return None


def tr_type(tipo, modelo="", nome_comercial=""):
    """Translate product type + infer real product when possible."""
    inferred = infer_product(modelo, nome_comercial)
    if inferred:
        return inferred
    if tipo in PRODUCT_TYPES:
        en, zh = PRODUCT_TYPES[tipo]
        return f"{en} / {zh}"
    return tipo


def tr_status(situacao):
    if situacao in STATUS_MAP:
        en, zh = STATUS_MAP[situacao]
        return f"{en} / {zh}"
    return situacao


def tr_country(pais):
    if pais in COUNTRY_MAP:
        en, zh = COUNTRY_MAP[pais]
        return f"{en} / {zh}"
    return pais


def build_html(report_path):
    """Build email subject and HTML body from report file."""
    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)

    items = report.get("new_items", [])
    date = report.get("date", "")
    total = len(items)

    S = "font-family:monospace,Consolas,'Courier New';font-size:14px;line-height:1.6;color:#222;max-width:720px;margin:0 auto;padding:16px"

    if total == 0:
        subject = f"[Anatel] No new certifications — {date}"
        body = f"""<div style="{S}">
<pre>
══════════════════════════════════════════
  Anatel Certification Monitor
  Anatel 竞品认证监控报告
  Report Date / 报告日期: {date}
══════════════════════════════════════════

本期无新增认证产品。所有监控品牌与上期数据一致。
No new certified products. All watched brands unchanged.

══════════════════════════════════════════
Generated by Anatel Monitor
Design by Ben LI Huijie
</pre></div>"""
        return subject, body

    # Group by brand
    by_brand = {}
    for item in items:
        by_brand.setdefault(item["brand"], []).append(item)

    brand_counts = " | ".join(f"{b}: {len(v)}" for b, v in sorted(by_brand.items()))
    subject = f"[Anatel] {total} new certifications — {date}"

    # Build plain text report
    lines = []
    lines.append("══════════════════════════════════════════")
    lines.append("  Anatel Certification Monitor")
    lines.append("  Anatel 竞品认证监控报告")
    lines.append(f"  Report Date / 报告日期: {date}")
    lines.append("══════════════════════════════════════════")
    lines.append("")
    lines.append("Anatel certification (homologação) is required")
    lines.append("before any telecom product can be sold in Brazil.")
    lines.append("New certification = product launch in 2-6 months.")
    lines.append("Anatel 认证是所有电信产品在巴西销售前的必要步骤。")
    lines.append("新认证通常意味着该产品将在 2-6 个月内在巴西上市。")
    lines.append("")
    lines.append("★ = Certified / 已认证 (ready to sell / 可上市销售)")
    lines.append("")
    lines.append(f"▶ New Certifications / 新增认证: {total} models")
    lines.append(f"  {brand_counts}")
    lines.append("──────────────────────────────────────────")

    for brand, brand_items in sorted(by_brand.items()):
        lines.append("")
        lines.append(f"  {brand} ({len(brand_items)} new)")
        lines.append("")

        for item in brand_items:
            modelo = item.get("modelo", "")
            nome = item.get("nome_comercial", "")
            tipo = item.get("tipo_produto", "")
            situacao = item.get("situacao", "")
            data = item.get("data_homologacao", "")
            pais = item.get("pais", "")

            is_certified = situacao == CERTIFIED
            marker = "  ★" if is_certified else "   "

            display = nome if nome else modelo
            lines.append(f"{marker} Product / 产品:  {display}")
            if nome and nome != modelo:
                lines.append(f"    Model / 型号:    {modelo}")
            lines.append(f"    Type / 类型:     {tr_type(tipo, modelo, nome)}")
            lines.append(f"    Status / 状态:   {tr_status(situacao)}")
            lines.append(f"    Date / 日期:     {data}")
            lines.append(f"    Origin / 产地:   {tr_country(pais)}")
            lines.append("")

    lines.append("══════════════════════════════════════════")
    lines.append("Generated by Anatel Monitor")
    lines.append("Data source: Anatel Open Data (anatel.gov.br)")
    lines.append("Design by Ben LI Huijie")

    pre_content = "\n".join(lines)
    body = f'<div style="{S}"><pre>{pre_content}</pre></div>'
    return subject, body


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_report.py <report.json>")
        sys.exit(1)

    subject, body = build_html(sys.argv[1])
    print(f"Subject: {subject}")

    if "--dry-run" in sys.argv:
        print(body)
    else:
        send_email(subject, body)
