import os
import csv
import io
import smtplib
import requests
import json
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

ETHERSCAN_API_KEY = os.environ["POLYGONSCAN_API_KEY"]
MORALIS_API_KEY   = os.environ["MORALIS_API_KEY"]
SMTP_PASSWORD     = os.environ["BREVO_SMTP_KEY"]
EMAIL_FROM        = os.environ["EMAIL_FROM"]
EMAIL_TO          = os.environ["EMAIL_TO"]
GOOGLE_API_KEY    = os.environ["GOOGLE_API_KEY"]

WALLETS = {
    "Wallet Principal": os.environ["WALLET_ADDRESS_1"],
}

OTC_SHEET_ID  = "13Q0n7egbAIJSU9UvwwDucd3MUQ48Q44eoMwsPT-PmGs"
OTC_SHEET_TAB = "Reservas"


def get_reserved_tokens():
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{OTC_SHEET_ID}"
        f"/values/{OTC_SHEET_TAB}!A1?key={GOOGLE_API_KEY}"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    values = data.get("values", [])
    if not values or not values[0]:
        print("  ! Sheet vacio o sin datos en A1")
        return {}

    raw = values[0][0]

    try:
        reservas = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ! No se pudo parsear JSON de reservas: {e}")
        print(f"  RAW (primeros 200 chars): {raw[:200]}")
        return {}

    reserved = {}
    for r in reservas:
        if r.get("estado") in ("completada", "cancelada"):
            continue
        addr   = r.get("token_address", "").lower()
        tokens = float(r.get("n_tokens", 0))
        if addr:
            reserved[addr] = reserved.get(addr, 0.0) + tokens

    print(f"  Reservas activas leidas: {len(reserved)} tokens con reserva")
    for addr, n in reserved.items():
        print(f"    · {addr[:20]}... — {n:.4f} reservados")
    return reserved


def get_reental_tokens(wallet_address):
    url = f"https://deep-index.moralis.io/api/v2.2/{wallet_address}/erc20"
    headers = {"X-API-Key": MORALIS_API_KEY}
    params = {"chain": "polygon"}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    tokens = resp.json()

    reental_tokens = []
    for t in tokens:
        symbol = t.get("symbol", "")
        if "reental" not in symbol.lower():
            continue
        decimals = int(t.get("decimals", 18))
        balance  = int(t.get("balance", 0)) / (10 ** decimals)
        if balance > 0:
            reental_tokens.append({
                "token_address": t.get("token_address", "").lower(),
                "token_name":    t.get("name", symbol),
                "token_symbol":  symbol,
                "balance":       balance,
            })

    print(f"  Tokens Reental encontrados: {len(reental_tokens)}")
    for t in reental_tokens:
        print(f"    · {t['token_name']} ({t['token_symbol']}) — {t['balance']:.4f}")
    return sorted(reental_tokens, key=lambda x: x["balance"], reverse=True)


def build_wallet_section(wallet_name, tokens, wallet_addr, reserved):
    polygonscan_url = f"https://polygonscan.com/address/{wallet_addr}#tokentxns"

    total_cantidad   = sum(t["balance"] for t in tokens)
    total_reservados = sum(reserved.get(t["token_address"], 0.0) for t in tokens)
    total_disponible = total_cantidad - total_reservados

    if not tokens:
        rows = "<tr><td colspan='5' style='color:#888;padding:12px 0;'>Sin tokens Reental detectados</td></tr>"
    else:
        rows = ""
        for t in tokens:
            res        = reserved.get(t["token_address"], 0.0)
            disp       = t["balance"] - res
            res_str    = f"{res:.4f}" if res > 0 else "—"
            disp_str   = f"{disp:.4f}"
            disp_color = "#16a34a" if disp > 0 else "#dc2626"
            rows += (
                "<tr>"
                f"<td style='padding:9px 10px;border-bottom:1px solid #f0f0f0;font-family:monospace;font-size:10px;color:#999;'>{t['token_address']}</td>"
                f"<td style='padding:9px 10px;border-bottom:1px solid #f0f0f0;font-weight:500;color:#1F2937;'>{t['token_name']}</td>"
                f"<td style='padding:9px 10px;border-bottom:1px solid #f0f0f0;text-align:right;font-weight:600;color:#1F2937;'>{t['balance']:.4f}</td>"
                f"<td style='padding:9px 10px;border-bottom:1px solid #f0f0f0;text-align:right;color:#FCA311;font-weight:500;'>{res_str}</td>"
                f"<td style='padding:9px 10px;border-bottom:1px solid #f0f0f0;text-align:right;font-weight:600;color:{disp_color};'>{disp_str}</td>"
                "</tr>"
            )
        disp_total_color = "#a3e635" if total_disponible > 0 else "#f87171"
        rows += (
            "<tr style='background:#1F2937;'>"
            "<td colspan='2' style='padding:11px 10px;font-weight:700;color:#fff;font-size:12px;'>TOTAL</td>"
            f"<td style='padding:11px 10px;text-align:right;font-weight:700;color:#fff;font-size:13px;'>{total_cantidad:.4f}</td>"
            f"<td style='padding:11px 10px;text-align:right;font-weight:700;color:#FCA311;font-size:13px;'>{total_reservados:.4f}</td>"
            f"<td style='padding:11px 10px;text-align:right;font-weight:700;color:{disp_total_color};font-size:13px;'>{total_disponible:.4f}</td>"
            "</tr>"
        )

    section = (
        "<div style='margin-bottom:28px;'>"
        "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>"
        f"<span style='font-size:14px;font-weight:600;color:#1F2937;'>{wallet_name}</span>"
        f"<a href='{polygonscan_url}' style='font-size:11px;color:#FCA311;text-decoration:none;'>Ver en Polygonscan &#8594;</a>"
        "</div>"
        f"<div style='font-size:10px;color:#aaa;margin-bottom:10px;font-family:monospace;'>{wallet_addr}</div>"
        "<table width='100%' cellpadding='0' cellspacing='0' style='border-collapse:collapse;font-size:12px;'>"
        "<thead><tr style='background:#f5f5f5;'>"
        "<th style='padding:7px 10px;text-align:left;font-weight:500;color:#888;font-size:11px;'>Token Address</th>"
        "<th style='padding:7px 10px;text-align:left;font-weight:500;color:#888;font-size:11px;'>Nombre</th>"
        "<th style='padding:7px 10px;text-align:right;font-weight:500;color:#888;font-size:11px;'>Cantidad</th>"
        "<th style='padding:7px 10px;text-align:right;font-weight:500;color:#FCA311;font-size:11px;'>Reservados</th>"
        "<th style='padding:7px 10px;text-align:right;font-weight:500;color:#16a34a;font-size:11px;'>Disponibles</th>"
        "</tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
        f"<div style='font-size:11px;color:#aaa;margin-top:6px;text-align:right;'>{len(tokens)} propiedades</div>"
        "</div>"
    )
    return section, total_cantidad, total_reservados, total_disponible


def build_email_html(report):
    fecha    = report["fecha"]
    reserved = report.get("reserved", {})
    secciones_html = ""
    gran_cantidad   = 0.0
    gran_reservados = 0.0
    gran_disponible = 0.0

    for wallet_name, tokens in report["wallets"].items():
        wallet_addr = report["addresses"][wallet_name]
        seccion, tc, tr, td = build_wallet_section(wallet_name, tokens, wallet_addr, reserved)
        secciones_html += seccion
        gran_cantidad   += tc
        gran_reservados += tr
        gran_disponible += td

    disp_color = "#16a34a" if gran_disponible >= 0 else "#dc2626"
    resumen_html = (
        "<div style='background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;"
        "padding:16px 20px;margin-bottom:24px;'>"
        "<div style='font-size:11px;font-weight:600;color:#64748b;letter-spacing:0.5px;"
        "text-transform:uppercase;margin-bottom:12px;'>Resumen de posición</div>"
        "<table width='100%' cellpadding='0' cellspacing='0'><tr>"
        "<td style='text-align:center;padding:0 8px;'>"
        "<div style='font-size:10px;color:#888;margin-bottom:4px;'>Tokens en custodia</div>"
        f"<div style='font-size:22px;font-weight:800;color:#1F2937;'>{gran_cantidad:.2f}</div>"
        "</td>"
        "<td style='text-align:center;color:#94a3b8;font-size:20px;font-weight:300;'>−</td>"
        "<td style='text-align:center;padding:0 8px;'>"
        "<div style='font-size:10px;color:#888;margin-bottom:4px;'>Reservados</div>"
        f"<div style='font-size:22px;font-weight:800;color:#FCA311;'>{gran_reservados:.2f}</div>"
        "</td>"
        "<td style='text-align:center;color:#94a3b8;font-size:20px;font-weight:300;'>=</td>"
        "<td style='text-align:center;padding:0 8px;'>"
        "<div style='font-size:10px;color:#888;margin-bottom:4px;'>Disponibles</div>"
        f"<div style='font-size:22px;font-weight:800;color:{disp_color};'>{gran_disponible:.2f}</div>"
        "</td>"
        "</tr></table>"
        "</div>"
    )

    header = (
        "<div style='background:#1F2937;padding:24px 28px;'>"
        "<table width='100%' cellpadding='0' cellspacing='0'><tr>"
        "<td style='vertical-align:middle;'>"
        "<div style='color:#FCA311;font-size:11px;font-weight:600;letter-spacing:1px;margin-bottom:2px;'>REENTAL MONITOR</div>"
        "<div style='color:#fff;font-size:18px;font-weight:700;margin-bottom:2px;'>Reporte diario de tokens</div>"
        f"<div style='color:#9ca3af;font-size:12px;'>{fecha} &nbsp;·&nbsp; Red Polygon</div>"
        "</td>"
        "<td style='text-align:right;vertical-align:middle;'>"
        "<div style='color:#9ca3af;font-size:10px;font-weight:600;letter-spacing:0.5px;margin-bottom:4px;'>TOTAL EN CUSTODIA</div>"
        f"<div style='color:#FCA311;font-size:28px;font-weight:800;letter-spacing:-1px;line-height:1;'>{gran_cantidad:.2f}</div>"
        "<div style='color:#6b7280;font-size:10px;margin-top:3px;'>tokens Reental</div>"
        "</td>"
        "</tr></table>"
        "</div>"
    )

    return (
        "<!DOCTYPE html><html><body style='margin:0;padding:0;background:#f3f4f6;"
        "font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;'>"
        "<div style='max-width:680px;margin:32px auto;background:#fff;border-radius:12px;"
        "overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);'>"
        f"{header}"
        f"<div style='padding:24px 28px;'>{resumen_html}{secciones_html}</div>"
        "<div style='padding:16px 28px;border-top:1px solid #f0f0f0;background:#fafafa;'>"
        "<p style='margin:0;font-size:10px;color:#bbb;'>Reporte automatico diario 08:00h (hora Espana) &nbsp;·&nbsp; Red Polygon PoS</p>"
        "</div></div></body></html>"
    )


def build_email_text(report):
    reserved = report.get("reserved", {})
    lines = [f"REENTAL MONITOR — {report['fecha']}", "=" * 70]
    gran_cantidad = gran_reservados = gran_disponible = 0.0

    for wallet_name, tokens in report["wallets"].items():
        lines.append(f"\n{wallet_name}")
        lines.append(report["addresses"][wallet_name])
        lines.append("-" * 70)
        if not tokens:
            lines.append("Sin tokens Reental detectados.")
        else:
            lines.append(f"  {'Nombre':<32} {'Cantidad':>10} {'Reservados':>12} {'Disponibles':>12}")
            lines.append("  " + "-" * 68)
            tc = tr = 0.0
            for t in tokens:
                res  = reserved.get(t["token_address"], 0.0)
                disp = t["balance"] - res
                tc  += t["balance"]
                tr  += res
                lines.append(f"  {t['token_name']:<32} {t['balance']:>10.4f} {res:>12.4f} {disp:>12.4f}")
            td = tc - tr
            gran_cantidad   += tc
            gran_reservados += tr
            gran_disponible += td
            lines.append("  " + "-" * 68)
            lines.append(f"  {'TOTAL':<32} {tc:>10.4f} {tr:>12.4f} {td:>12.4f}")

    lines.append("\n" + "=" * 70)
    lines.append(f"  Tokens en custodia : {gran_cantidad:.4f}")
    lines.append(f"  Reservados         : {gran_reservados:.4f}")
    lines.append(f"  Disponibles        : {gran_disponible:.4f}")
    lines.append("=" * 70)
    lines.append("\nDatos: Moralis · Red Polygon PoS")
    return "\n".join(lines)


def send_email(subject, html_content, text_content):
    recipients = [r.strip() for r in EMAIL_TO.split(",")]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_FROM, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, recipients, msg.as_string())
    print("  Email enviado correctamente.")


def main():
    fecha = datetime.now(timezone.utc).strftime("%d %b %Y")
    print(f"[{datetime.now().isoformat()}] Iniciando consulta de wallets...")

    reserved = get_reserved_tokens()
    report = {"fecha": fecha, "wallets": {}, "addresses": {}, "reserved": reserved}

    for wallet_name, wallet_address in WALLETS.items():
        print(f"  -> Consultando {wallet_name} ({wallet_address[:10]}...)")
        tokens = get_reental_tokens(wallet_address)
        report["wallets"][wallet_name]   = tokens
        report["addresses"][wallet_name] = wallet_address

    subject = f"Reental · Reporte diario {fecha}"
    send_email(subject, build_email_html(report), build_email_text(report))
    print("Proceso completado.")


if __name__ == "__main__":
    main()
