#!/usr/bin/env python3
"""
Send Anatel certification report via Resend API.

Requires:
  RESEND_API_KEY env var
  REPORT_EMAIL env var (recipient)
"""

import json
import os
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

# Product type: Portuguese → (English, Chinese)
PRODUCT_TYPES = {
    "Telefone Móvel Celular": ("Mobile Phone", "手机"),
    "Transceptor de Radiação Restrita": ("Short-Range Transceiver", "短距离收发器（蓝牙/WiFi设备）"),
    "Transceptor de Radiação Restrita - Espalhamento Espectral": ("Spread Spectrum Transceiver", "扩频收发器"),
    "Transceptor de Radiação Restrita - Híbrido": ("Hybrid Short-Range Transceiver", "混合短距离收发器"),
    "Equipamento de Radiocomunicação de Radiação Restrita": ("Short-Range Radio Equipment", "短距离无线电设备"),
    "Estação Terminal de Acesso": ("Access Terminal", "接入终端（路由器/CPE）"),
    "Sistemas de Identificação por Radiofrequências": ("RFID System", "射频识别系统（NFC/RFID）"),
    "Sistemas Operando nas Faixas de RF Ultra Larga": ("Ultra-Wideband System", "超宽带系统（UWB）"),
    "Sistemas Operando Na Faixa de 57 a 64 GHz": ("60GHz Band System", "60GHz频段系统"),
    "Carregador Indutivo para Telefone Celular": ("Wireless Charger", "无线充电器"),
    "Transceptor Móvel por Satélite": ("Satellite Transceiver", "卫星收发器"),
    "Tela interativa para uso educacional": ("Interactive Display", "交互式显示屏"),
    "Microfone sem Fio": ("Wireless Microphone", "无线麦克风"),
    "Modem Analógico": ("Analog Modem", "模拟调制解调器"),
    "Sistema de Acesso sem Fio em Banda Larga - Redes Locais": ("Wireless Broadband Access", "无线宽带接入"),
    "Equipamento de Fac-Símile": ("Fax Equipment", "传真设备"),
}

# Certification status: Portuguese → (English, Chinese)
STATUS_MAP = {
    "Homologação Emitida": ("Certified", "已认证，可上市销售"),
    "Em Análise - RE": ("Under Review", "审核中，尚未获批"),
    "Homologação Suspensa": ("Suspended", "认证已暂停"),
    "Homologação Cancelada": ("Cancelled", "认证已取消"),
}

# Country: Portuguese → (English, Chinese)
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


def tr_type(tipo):
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

            display = nome if nome else modelo
            lines.append(f"    Product / 产品:  {display}")
            if nome and nome != modelo:
                lines.append(f"    Model / 型号:    {modelo}")
            lines.append(f"    Type / 类型:     {tr_type(tipo)}")
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
