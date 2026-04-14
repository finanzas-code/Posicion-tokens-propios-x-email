import os
import smtplib
import requests
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

ETHERSCAN_API_KEY = os.environ["POLYGONSCAN_API_KEY"]
SMTP_PASSWORD     = os.environ["BREVO_SMTP_KEY"]
EMAIL_FROM        = os.environ["EMAIL_FROM"]
EMAIL_TO          = os.environ["EMAIL_TO"]

WALLETS = {
    "Wallet Principal":  os.environ["WALLET_ADDRESS_1"],
    "Wallet Secundaria": os.environ["WALLET_ADDRESS_2"],
}

API_BASE = "https://api.etherscan.io/v2/api"

LOGO_SVG = '<svg width="52" height="52" viewBox="0 0 275 275" fill="none" xmlns="http://www.w3.org/2000/svg">\n<g clip-path="url(#clip0_2183_764)">\n<circle cx="137.328" cy="137.521" r="121.713" fill="#1F2937"/>\n<path d="M137.316 0.0223541C61.4826 0.0223541 0.0078125 61.4971 0.0078125 137.331C0.0078125 213.164 61.4826 274.638 137.316 274.638C213.149 274.638 274.624 213.164 274.624 137.331C274.624 61.4971 213.149 0.0223541 137.316 0.0223541ZM137.316 258.392C113.372 258.392 89.9663 251.292 70.0577 237.989C50.1492 224.687 34.6326 205.78 25.4698 183.659C16.3069 161.537 13.9095 137.196 18.5807 113.713C23.2519 90.2289 34.7819 68.658 51.7124 51.7269C68.6434 34.7965 90.2143 23.2664 113.698 18.5953C137.182 13.9241 161.523 16.3215 183.644 25.4843C205.765 34.6472 224.672 50.1637 237.975 70.0723C251.277 89.9809 258.377 113.387 258.377 137.331C258.377 169.438 245.623 200.231 222.919 222.934C200.216 245.637 169.424 258.392 137.316 258.392Z" fill="#FCA311"/>\n<g clip-path="url(#clip1_2183_764)">\n<path fill-rule="evenodd" clip-rule="evenodd" d="M78.0898 63.0552C78.0898 61.7639 79.1367 60.7171 80.428 60.7171H143.179C146.789 60.7171 151.357 60.8806 156.064 62.0789C166.634 64.7698 180.871 71.6706 189.289 84.0299C200.746 102.591 201.508 125.33 186.773 145.937C185.971 147.06 184.366 147.188 183.359 146.244L169.837 133.565C169.038 132.815 168.872 131.611 169.401 130.652C177.818 115.38 173.82 106.43 170.2 99.1409C166.43 91.5507 158.285 86.2884 151.41 84.0299C144.161 80.777 130.817 81.3191 127.851 81.3191H105.121C103.83 81.3191 102.783 82.3659 102.783 83.6572V175.922C102.783 176.702 102.394 177.431 101.745 177.865L81.7282 191.258C80.1746 192.297 78.0898 191.184 78.0898 189.315V63.0552Z" fill="white"/>\n<path fill-rule="evenodd" clip-rule="evenodd" d="M145.871 151.23C146.425 150.843 147.175 150.9 147.664 151.366L211.191 211.909C212.119 212.793 211.493 214.357 210.211 214.357H181.028C179.548 214.357 178.126 213.78 177.065 212.747L144.577 181.114L134.244 170.781L128.705 165.242C128.08 164.616 128.171 163.578 128.896 163.072L145.871 151.23Z" fill="white"/>\n</g>\n</g>\n<defs>\n<clipPath id="clip0_2183_764">\n<rect width="274.658" height="274.658" fill="white"/>\n</clipPath>\n<clipPath id="clip1_2183_764">\n<rect width="133.568" height="153.62" fill="white" transform="translate(78.0898 60.6648)"/>\n</clipPath>\n</defs>\n</svg>'


def get_reental_tokens(wallet_address):
    params = {
        "chainid":    "137",
        "module":     "account",
        "action":     "tokentx",
        "address":    wallet_address,
        "startblock": 0,
        "endblock":   99999999,
        "sort":       "asc",
        "apikey":     ETHERSCAN_API_KEY,
    }
    resp = requests.get(API_BASE, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data["status"] != "1":
        print(f"  ! Sin transacciones: {data.get('message')}")
        return []
    balances = {}
    wallet_lower = wallet_address.lower()
    for tx in data["result"]:
        contract = tx["contractAddress"].lower()
        decimals = int(tx["tokenDecimal"]) if tx["tokenDecimal"] else 18
        value = int(tx["value"]) / (10 ** decimals)
        if contract not in balances:
            balances[contract] = {
                "token_address": tx["contractAddress"],
                "token_name":    tx["tokenName"],
                "token_symbol":  tx["tokenSymbol"],
                "balance":       0.0,
            }
        if tx["to"].lower() == wallet_lower:
            balances[contract]["balance"] += value
        elif tx["from"].lower() == wallet_lower:
            balances[contract]["balance"] -= value
    reental_tokens = [
        t for t in balances.values()
        if t["balance"] > 0 and "reental" in t["token_symbol"].lower()
    ]
    print(f"  Tokens Reental encontrados: {len(reental_tokens)}")
    for t in reental_tokens:
        print(f"    · {t['token_name']} ({t['token_symbol']}) — {t['balance']:.4f}")
    return sorted(reental_tokens, key=lambda x: x["balance"], reverse=True)


def build_wallet_section(wallet_name, tokens, wallet_addr):
    polygonscan_url = f"https://polygonscan.com/address/{wallet_addr}#tokentxns"
    subtotal = sum(t["balance"] for t in tokens)
    if not tokens:
        rows = "<tr><td colspan='3' style='color:#888;padding:12px 0;'>Sin tokens Reental detectados</td></tr>"
    else:
        rows = ""
        for t in tokens:
            rows += (
                "<tr>"
                f"<td style='padding:9px 12px;border-bottom:1px solid #f0f0f0;font-family:monospace;font-size:11px;color:#777;'>{t['token_address']}</td>"
                f"<td style='padding:9px 12px;border-bottom:1px solid #f0f0f0;font-weight:500;color:#1F2937;'>{t['token_name']}</td>"
                f"<td style='padding:9px 12px;border-bottom:1px solid #f0f0f0;text-align:right;font-weight:600;color:#1F2937;'>{t['balance']:.4f}</td>"
                "</tr>"
            )
        rows += (
            "<tr style='background:#fff8ee;'>"
            "<td colspan='2' style='padding:11px 12px;font-weight:600;color:#b47300;font-size:12px;'>SUBTOTAL WALLET</td>"
            f"<td style='padding:11px 12px;text-align:right;font-weight:700;color:#FCA311;font-size:15px;'>{subtotal:.4f}</td>"
            "</tr>"
        )
    section = (
        "<div style='margin-bottom:28px;'>"
        "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>"
        f"<span style='font-size:14px;font-weight:600;color:#1F2937;'>{wallet_name}</span>"
        f"<a href='{polygonscan_url}' style='font-size:11px;color:#FCA311;text-decoration:none;'>Ver en Polygonscan &#8594;</a>"
        "</div>"
        f"<div style='font-size:10px;color:#aaa;margin-bottom:10px;font-family:monospace;'>{wallet_addr}</div>"
        "<table width='100%' cellpadding='0' cellspacing='0' style='border-collapse:collapse;font-size:13px;'>"
        "<thead><tr style='background:#f5f5f5;'>"
        "<th style='padding:7px 12px;text-align:left;font-weight:500;color:#888;font-size:11px;'>Token Address</th>"
        "<th style='padding:7px 12px;text-align:left;font-weight:500;color:#888;font-size:11px;'>Nombre</th>"
        "<th style='padding:7px 12px;text-align:right;font-weight:500;color:#888;font-size:11px;'>Cantidad</th>"
        "</tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
        f"<div style='font-size:11px;color:#aaa;margin-top:6px;text-align:right;'>{len(tokens)} propiedades</div>"
        "</div>"
    )
    return section, subtotal


def build_email_html(report):
    fecha = report["fecha"]
    secciones_html = ""
    gran_total = 0.0
    for wallet_name, tokens in report["wallets"].items():
        wallet_addr = report["addresses"][wallet_name]
        seccion, subtotal = build_wallet_section(wallet_name, tokens, wallet_addr)
        secciones_html += seccion
        gran_total += subtotal
    header = (
        "<div style='background:#1F2937;padding:24px 28px;'>"
        "<table width='100%' cellpadding='0' cellspacing='0'><tr>"
        f"<td style='width:60px;vertical-align:middle;'>{LOGO_SVG}</td>"
        "<td style='vertical-align:middle;padding-left:16px;'>"
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
        "<div style='max-width:640px;margin:32px auto;background:#fff;border-radius:12px;"
        "overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);'>"
        f"{header}"
        f"<div style='padding:24px 28px;'>{secciones_html}</div>"
        "<div style='padding:16px 28px;border-top:1px solid #f0f0f0;background:#fafafa;'>"
        "<p style='margin:0;font-size:10px;color:#bbb;'>Reporte automatico diario 08:00h (hora Espana) &nbsp;·&nbsp; Etherscan API V2 &nbsp;·&nbsp; Red Polygon PoS</p>"
        "</div></div></body></html>"
    )


def build_email_text(report):
    lines = [f"REENTAL MONITOR — {report['fecha']}", "=" * 50]
    gran_total = 0.0
    for wallet_name, tokens in report["wallets"].items():
        lines.append(f"\n{wallet_name}")
        lines.append(report["addresses"][wallet_name])
        lines.append("-" * 40)
        if not tokens:
            lines.append("Sin tokens Reental detectados.")
        else:
            for t in tokens:
                lines.append(f"  {t['token_name']:<35} {t['balance']:.4f}")
                lines.append(f"  {t['token_address']}")
            subtotal = sum(t["balance"] for t in tokens)
            gran_total += subtotal
            lines.append("-" * 40)
            lines.append(f"  {'SUBTOTAL':<35} {subtotal:.4f}")
    lines.append("\n" + "=" * 50)
    lines.append(f"  {'TOTAL COMBINADO':<35} {gran_total:.4f}")
    lines.append("=" * 50)
    lines.append("\nDatos: Etherscan API V2 · Red Polygon PoS")
    return "\n".join(lines)


def send_email(subject, html_content, text_content):
    recipients = [r.strip() for r in EMAIL_TO.split(",")]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(recipients)
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
    report = {"fecha": fecha, "wallets": {}, "addresses": {}}
    for wallet_name, wallet_address in WALLETS.items():
        print(f"  -> Consultando {wallet_name} ({wallet_address[:10]}...)")
        tokens = get_reental_tokens(wallet_address)
        report["wallets"][wallet_name] = tokens
        report["addresses"][wallet_name] = wallet_address
    subject = f"Reental · Reporte diario {fecha}"
    send_email(subject, build_email_html(report), build_email_text(report))
    print("Proceso completado.")


if __name__ == "__main__":
    main()
