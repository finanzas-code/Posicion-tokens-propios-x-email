import os
import smtplib
import requests
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

ETHERSCAN_API_KEY = os.environ["POLYGONSCAN_API_KEY"]
MORALIS_API_KEY   = os.environ["MORALIS_API_KEY"]
SMTP_PASSWORD     = os.environ["BREVO_SMTP_KEY"]
EMAIL_FROM        = os.environ["EMAIL_FROM"]
EMAIL_TO          = os.environ["EMAIL_TO"]

WALLETS = {
    "Wallet Principal":  os.environ["WALLET_ADDRESS_1"],
    "Wallet Secundaria": os.environ["WALLET_ADDRESS_2"],
}

SHEET_ID  = "1E5h0h8bFfLNX-I-XNvm3-NIoYc7S6fnndSn2uv3uwq0"
SHEET_GID = "1247043615"


def get_reserved_tokens():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={SHEET_GID}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    reserved = {}
    lines = resp.text.strip().split("\n")
    for line in lines[1:]:
        cols = line.split(",")
        if len(cols) >= 3:
            symbol  = cols[0].strip().strip('"').upper()
            raw_val = cols[2].strip().strip('"').replace(",", ".")
            try:
                amount = float(raw_val) if raw_val else 0.0
            except ValueError:
                amount = 0.0
            if symbol:
                reserved[symbol] = amount
    print(f"  Sheet leido: {len(reserved)} entradas")
    return reserved


def symbol_to_key(full_symbol):
    parts = full_symbol.split("-", 1)
    return parts[1].upper() if len(parts) > 1 else full_symbol.upper()


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
                "token_address": t.get("token_address", ""),
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
    subtotal = sum(t["balance"] for t in tokens)

    if not tokens:
        rows = "<tr><td colspan='5' style='color:#888;padding:12px 0;'>Sin tokens Reental detectados</td></tr>"
    else:
        rows = ""
        for t in tokens:
            key        = symbol_to_key(t["token_symbol"])
            res        = reserved.get(key, 0.0)
            disp       = t["balance"] - res
            res_str    = f"{res:.4f}"  if res  > 0 else "—"
            disp_str   = f"{disp:.4f}" if disp > 0 else "—"
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
        rows += (
            "<tr style='background:#fff8ee;'>"
            "<td colspan='2' style='padding:11px 10px;font-weight:600;color:#b47300;font-size:12px;'>SUBTOTAL WALLET</td>"
            f"<td style='padding:11px 10px;text-align:right;font-weight:700;color:#FCA311;font-size:15px;'>{subtotal:.4f}</td>"
            "<td></td><td></td>"
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
    return section, subtotal


def build_email_html(report):
    fecha    = report["fecha"]
    reserved = report.get("reserved", {})
    secciones_html = ""
    gran_total = 0.0

    for wallet_name, tokens in report["wallets"].items():
        wallet_addr = report["addresses"][wallet_name]
        seccion, subtotal = build_wallet_section(wallet_name, tokens, wallet_addr, reserved)
        secciones_html += seccion
        gran_total += subtotal

    header = (
        "<div style='background:#1F2937;padding:24px 28px;'>"
        "<table width='100%' cellpadding='0' cellspacing='0'><tr>"
        "<td style='vertical-align:middle;'>"
        "<div style='color:#FCA311;font-size:11px;font-weight:600;letter-spacing:1px;margin-bottom:2px;'>REENTAL MONITOR</div>"
        "<div style='color:#fff;font-size:18px;font-weight:700;margin-bottom:2px;'>Reporte diario de tokens</div>"
        f"<div style='color:#9ca3af;font-size:12px;'>{fecha} &nbsp;·&nbsp; Red Polygon</div>"
        "</td>"
        "<td style='text-align:right;vertical-align:middle;'>"
        "<div style='color:#9ca3af;font-size:10px;font-weight:600;letter-spacing:0.5px;margin-bottom:4px;'>TOTAL COMBINADO</div>"
        f"<div style='color:#FCA311;font-size:28px;font-weight:800;letter-spacing:-1px;line-height:1;'>{gran_total:.4f}</div>"
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
        f"<div style='padding:24px 28px;'>{secciones_html}</div>"
        "<div style='padding:16px 28px;border-top:1px solid #f0f0f0;background:#fafafa;'>"
        "<p style='margin:0;font-size:10px;color:#bbb;'>Reporte automatico diario 08:00h (hora Espana) &nbsp;·&nbsp; Red Polygon PoS</p>"
        "</div></div></body></html>"
    )


def build_email_text(report):
    reserved = report.get("reserved", {})
    lines = [f"REENTAL MONITOR — {report['fecha']}", "=" * 70]
    gran_total = 0.0
    for wallet_name, tokens in report["wallets"].items():
        lines.append(f"\n{wallet_name}")
        lines.append(report["addresses"][wallet_name])
        lines.append("-" * 70)
        if not tokens:
            lines.append("Sin tokens Reental detectados.")
        else:
            lines.append(f"  {'Nombre':<32} {'Cantidad':>10} {'Reservados':>12} {'Disponibles':>12}")
            lines.append("  " + "-" * 68)
            for t in tokens:
                key  = symbol_to_key(t["token_symbol"])
                res  = reserved.get(key, 0.0)
                disp = t["balance"] - res
                lines.append(f"  {t['token_name']:<32} {t['balance']:>10.4f} {res:>12.4f} {disp:>12.4f}")
            subtotal = sum(t["balance"] for t in tokens)
            gran_total += subtotal
            lines.append("  " + "-" * 68)
            lines.append(f"  {'SUBTOTAL':<32} {subtotal:>10.4f}")
    lines.append("\n" + "=" * 70)
    lines.append(f"  {'TOTAL COMBINADO':<32} {gran_total:>10.4f}")
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
