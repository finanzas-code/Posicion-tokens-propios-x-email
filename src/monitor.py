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
    "Wallet Principal": os.environ["WALLET_ADDRESS_1"],
    "Wallet Secundaria": os.environ["WALLET_ADDRESS_2"],
}

API_BASE = "https://api.etherscan.io/v2/api"


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


def build_email_html(report):
    fecha = report["fecha"]
    secciones_html = ""

    for wallet_name, tokens in report["wallets"].items():
        wallet_addr = report["addresses"][wallet_name]
        polygonscan_url = f"https://polygonscan.com/address/{wallet_addr}#tokentxns"
        total_tokens = sum(t["balance"] for t in tokens)

        if not tokens:
            rows = "<tr><td colspan='3' style='color:#888;padding:12px 0;'>Sin tokens Reental detectados</td></tr>"
        else:
            rows = ""
            for t in tokens:
                rows += (
                    "<tr>"
                    f"<td style='padding:10px 12px;border-bottom:1px solid #f0f0f0;font-family:monospace;font-size:11px;color:#777;'>{t['token_address']}</td>"
                    f"<td style='padding:10px 12px;border-bottom:1px solid #f0f0f0;font-weight:500;'>{t['token_name']}</td>"
                    f"<td style='padding:10px 12px;border-bottom:1px solid #f0f0f0;text-align:right;font-weight:600;color:#1a1a2e;'>{t['balance']:.4f}</td>"
                    "</tr>"
                )
            rows += (
                "<tr style='background:#f5f3ff;'>"
                "<td colspan='2' style='padding:12px;font-weight:600;color:#4f35b3;font-size:13px;'>TOTAL TOKENS</td>"
                f"<td style='padding:12px;text-align:right;font-weight:700;color:#4f35b3;font-size:16px;'>{total_tokens:.4f}</td>"
                "</tr>"
            )

        secciones_html += (
            "<div style='margin-bottom:32px;'>"
            "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>"
            f"<span style='font-size:15px;font-weight:600;color:#1a1a2e;'>{wallet_name}</span>"
            f"<a href='{polygonscan_url}' style='font-size:12px;color:#6c4de6;text-decoration:none;'>Ver en Polygonscan</a>"
            "</div>"
            f"<div style='font-size:11px;color:#999;margin-bottom:12px;font-family:monospace;'>{wallet_addr}</div>"
            "<table width='100%' cellpadding='0' cellspacing='0' style='border-collapse:collapse;font-size:13px;'>"
            "<thead><tr style='background:#f5f3ff;'>"
            "<th style='padding:8px 12px;text-align:left;font-weight:500;color:#555;font-size:12px;'>Token Address</th>"
            "<th style='padding:8px 12px;text-align:left;font-weight:500;color:#555;font-size:12px;'>Nombre</th>"
            "<th style='padding:8px 12px;text-align:right;font-weight:500;color:#555;font-size:12px;'>Cantidad</th>"
            "</tr></thead>"
            f"<tbody>{rows}</tbody>"
            "</table>"
            f"<div style='font-size:12px;color:#888;margin-top:8px;text-align:right;'>{len(tokens)} propiedades</div>"
            "</div>"
        )

    return (
        "<!DOCTYPE html><html><body style='margin:0;padding:0;background:#f8f8fb;"
        "font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;'>"
        "<div style='max-width:640px;margin:32px auto;background:#fff;border-radius:12px;"
        "overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.06);'>"
        "<div style='background:linear-gradient(135deg,#6c4de6 0%,#4f35b3 100%);padding:28px 32px;'>"
        "<div style='color:#e8e0ff;font-size:12px;margin-bottom:4px;'>REENTAL MONITOR</div>"
        "<div style='color:#fff;font-size:22px;font-weight:600;'>Reporte diario de tokens</div>"
        f"<div style='color:#c4b5fd;font-size:13px;margin-top:6px;'>{fecha} · Red Polygon</div>"
        "</div>"
        f"<div style='padding:28px 32px;'>{secciones_html}</div>"
        "<div style='padding:20px 32px;border-top:1px solid #f0f0f0;background:#fafafa;'>"
        "<p style='margin:0;font-size:11px;color:#aaa;'>Reporte automatico diario 08:00h (hora Espana) · Red Polygon PoS</p>"
        "</div></div></body></html>"
    )


def build_email_text(report):
    lines = [f"REENTAL MONITOR — {report['fecha']}", "=" * 50]
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
            total = sum(t["balance"] for t in tokens)
            lines.append("-" * 40)
            lines.append(f"  {'TOTAL':<35} {total:.4f}")
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
