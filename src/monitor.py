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

LOGO_B64 = "PHN2ZyB3aWR0aD0iMjc1IiBoZWlnaHQ9IjI3NSIgdmlld0JveD0iMCAwIDI3NSAyNzUiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxnIGNsaXAtcGF0aD0idXJsKCNjbGlwMF8yMTgzXzc2NCkiPgo8Y2lyY2xlIGN4PSIxMzcuMzI4IiBjeT0iMTM3LjUyMSIgcj0iMTIxLjcxMyIgZmlsbD0iIzFGMjkzNyIvPgo8cGF0aCBkPSJNMTM3LjMxNiAwLjAyMjM1NDFDNjEuNDgyNiAwLjAyMjM1NDEgMC4wMDc4MTI1IDYxLjQ5NzEgMC4wMDc4MTI1IDEzNy4zMzFDMC4wMDc4MTI1IDIxMy4xNjQgNjEuNDgyNiAyNzQuNjM4IDEzNy4zMTYgMjc0LjYzOEMyMTMuMTQ5IDI3NC42MzggMjc0LjYyNCAyMTMuMTY0IDI3NC42MjQgMTM3LjMzMUMyNzQuNjI0IDYxLjQ5NzEgMjEzLjE0OSAwLjAyMjM1NDEgMTM3LjMxNiAwLjAyMjM1NDFaTTEzNy4zMTYgMjU4LjM5MkMxMTMuMzcyIDI1OC4zOTIgODkuOTY2MyAyNTEuMjkyIDcwLjA1NzcgMjM3Ljk4OUM1MC4xNDkyIDIyNC42ODcgMzQuNjMyNiAyMDUuNzggMjUuNDY5OCAxODMuNjU5QzE2LjMwNjkgMTYxLjUzNyAxMy45MDk1IDEzNy4xOTYgMTguNTgwNyAxMTMuNzEzQzIzLjI1MTkgOTAuMjI4OSAzNC43ODE5IDY4LjY1OCA1MS43MTI0IDUxLjcyNjlDNjguNjQzNCAzNC43OTY1IDkwLjIxNDMgMjMuMjY2NCAxMTMuNjk4IDE4LjU5NTNDMTM3LjE4MiAxMy45MjQxIDE2MS41MjMgMTYuMzIxNSAxODMuNjQ0IDI1LjQ4NDNDMjA1Ljc2NSAzNC42NDcyIDIyNC42NzIgNTAuMTYzNyAyMzcuOTc1IDcwLjA3MjNDMjUxLjI3NyA4OS45ODA5IDI1OC4zNzcgMTEzLjM4NyAyNTguMzc3IDEzNy4zMzFDMjU4LjM3NyAxNjkuNDM4IDI0NS42MjMgMjAwLjIzMSAyMjIuOTE5IDIyMi45MzRDMjAwLjIxNiAyNDUuNjM3IDE2OS40MjQgMjU4LjM5MiAxMzcuMzE2IDI1OC4zOTJaIiBmaWxsPSIjRkNBMzExIi8+CjxnIGNsaXAtcGF0aD0idXJsKCNjbGlwMV8yMTgzXzc2NCkiPgo8cGF0aCBmaWxsLXJ1bGU9ImV2ZW5vZGQiIGNsaXAtcnVsZT0iZXZlbm9kZCIgZD0iTTc4LjA4OTggNjMuMDU1MkM3OC4wODk4IDYxLjc2MzkgNzkuMTM2NyA2MC43MTcxIDgwLjQyOCA2MC43MTcxSDE0My4xNzlDMTQ2Ljc4OSA2MC43MTcxIDE1MS4zNTcgNjAuODgwNiAxNTYuMDY0IDYyLjA3ODlDMTY2LjYzNCA2NC43Njk4IDE4MC44NzEgNzEuNjcwNiAxODkuMjg5IDg0LjAyOTlDMjAwLjc0NiAxMDIuNTkxIDIwMS41MDggMTI1LjMzIDE4Ni43NzMgMTQ1LjkzN0MxODUuOTcxIDE0Ny4wNiAxODQuMzY2IDE0Ny4xODggMTgzLjM1OSAxNDYuMjQ0TDE2OS44MzcgMTMzLjU2NUMxNjkuMDM4IDEzMi44MTUgMTY4Ljg3MiAxMzEuNjExIDE2OS40MDEgMTMwLjY1MkMxNzcuODE4IDExNS4zOCAxNzMuODIgMTA2LjQzIDE3MC4yIDk5LjE0MDlDMTY2LjQzIDkxLjU1MDcgMTU4LjI4NSA4Ni4yODg0IDE1MS40MSA4NC4wMjk5QzE0NC4xNjEgODAuNzc3IDEzMC44MTcgODEuMzE5MSAxMjcuODUxIDgxLjMxOTFIMTA1LjEyMUMxMDMuODMgODEuMzE5MSAxMDIuNzgzIDgyLjM2NTkgMTAyLjc4MyA4My42NTcyVjE3NS45MjJDMTAyLjc4MyAxNzYuNzAyIDEwMi4zOTQgMTc3LjQzMSAxMDEuNzQ1IDE3Ny44NjVMODEuNzI4MiAxOTEuMjU4QzgwLjE3NDYgMTkyLjI5NyA3OC4wODk4IDE5MS4xODQgNzguMDg5OCAxODkuMzE1VjYzLjA1NTJaIiBmaWxsPSJ3aGl0ZSIvPgo8cGF0aCBmaWxsLXJ1bGU9ImV2ZW5vZGQiIGNsaXAtcnVsZT0iZXZlbm9kZCIgZD0iTTE0NS44NzEgMTUxLjIzQzE0Ni40MjUgMTUwLjg0MyAxNDcuMTc1IDE1MC45IDE0Ny42NjQgMTUxLjM2NkwyMTEuMTkxIDIxMS45MDlDMjEyLjExOSAyMTIuNzkzIDIxMS40OTMgMjE0LjM1NyAyMTAuMjExIDIxNC4zNTdIMTgxLjAyOEMxNzkuNTQ4IDIxNC4zNTcgMTc4LjEyNiAyMTMuNzggMTc3LjA2NSAyMTIuNzQ3TDE0NC41NzcgMTgxLjExNEwxMzQuMjQ0IDE3MC43ODFMMTI4LjcwNSAxNjUuMjQyQzEyOC4wOCAxNjQuNjE2IDEyOC4xNzEgMTYzLjU3OCAxMjguODk2IDE2My4wNzJMMTQ1Ljg3MSAxNTEuMjNaIiBmaWxsPSJ3aGl0ZSIvPgo8L2c+CjwvZz4KPGRlZnM+CjxjbGlwUGF0aCBpZD0iY2xpcDBfMjE4M183NjQiPgo8cmVjdCB3aWR0aD0iMjc0LjY1OCIgaGVpZ2h0PSIyNzQuNjU4IiBmaWxsPSJ3aGl0ZSIvPgo8L2NsaXBQYXRoPgo8Y2xpcFBhdGggaWQ9ImNsaXAxXzIxODNfNzY0Ij4KPHJlY3Qgd2lkdGg9IjEzMy41NjgiIGhlaWdodD0iMTUzLjYyIiBmaWxsPSJ3aGl0ZSIgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoNzguMDg5OCA2MC42NjQ4KSIvPgo8L2NsaXBQYXRoPgo8L2RlZnM+Cjwvc3ZnPgo="


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

    logo_img = f"<img src='data:image/svg+xml;base64,{LOGO_B64}' width='52' height='52' style='display:block;' alt='Reental' />"

    header = (
        "<div style='background:#1F2937;padding:24px 28px;'>"
        "<table width='100%' cellpadding='0' cellspacing='0'><tr>"
        f"<td style='width:60px;vertical-align:middle;'>{logo_img}</td>"
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
