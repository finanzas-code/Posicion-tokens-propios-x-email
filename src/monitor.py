"""
Reental Token Monitor
Consulta tokens ERC-20 de Reental en Polygon y envía reporte diario por email.
"""

import os
import json
import requests
from datetime import datetime, timezone
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# ─── Configuración ────────────────────────────────────────────────────────────

POLYGONSCAN_API_KEY = os.environ["POLYGONSCAN_API_KEY"]
SENDGRID_API_KEY    = os.environ["SENDGRID_API_KEY"]
EMAIL_FROM          = os.environ["EMAIL_FROM"]       # ej: monitor@tudominio.com
EMAIL_TO            = os.environ["EMAIL_TO"]         # ej: equipo@tudominio.com (separados por coma)

# Direcciones de wallet a monitorear (añade o quita según necesites)
WALLETS = {
    "Wallet Principal": os.environ["WALLET_ADDRESS_1"],
    # "Wallet Secundaria": os.environ["WALLET_ADDRESS_2"],  # descomenta si usas 2
}

# Dirección del contrato emisor de Reental (filtramos solo sus tokens)
REENTAL_ISSUER = "0x6D7B3113A1Af7f6f91dC7fB1a6Eda97c31FBf48"  # actualiza si cambia

POLYGONSCAN_BASE = "https://api.etherscan.io/v2/api?chainid=137"

# ─── Lógica de consulta ───────────────────────────────────────────────────────

def get_reental_tokens(wallet_address: str) -> list[dict]:
    """
    Obtiene todos los tokens ERC-20 de una wallet en Polygon.
    Filtra los emitidos por Reental comparando el campo 'contractAddress'
    contra la lista de tokens conocidos de Reental.
    """
    params = {
        "module":  "account",
        "action":  "tokentx",
        "address": wallet_address,
        "startblock": 0,
        "endblock":   99999999,
        "sort":    "asc",
        "apikey":  POLYGONSCAN_API_KEY,
    }
    resp = requests.get(POLYGONSCAN_BASE, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if data["status"] != "1":
        print(f"Sin transacciones para {wallet_address}: {data.get('message')}")
        return []

    # Identificamos contratos únicos de Reental
    # Estrategia: agrupamos por contractAddress y calculamos balance neto
    # (suma de entradas - suma de salidas)
    balances: dict[str, dict] = {}
    wallet_lower = wallet_address.lower()

    for tx in data["result"]:
        contract = tx["contractAddress"].lower()
        decimals = int(tx["tokenDecimal"])
        value    = int(tx["value"]) / (10 ** decimals)
        name     = tx["tokenName"]
        symbol   = tx["tokenSymbol"]

        if contract not in balances:
            balances[contract] = {
                "token_address": tx["contractAddress"],
                "token_name":    name,
                "token_symbol":  symbol,
                "balance":       0.0,
            }

        if tx["to"].lower() == wallet_lower:
            balances[contract]["balance"] += value
        elif tx["from"].lower() == wallet_lower:
            balances[contract]["balance"] -= value

    # Filtramos tokens con balance positivo
    # y que contengan "RRT" o "Reental" en el nombre (ajusta según naming de Reental)
    reental_tokens = [
        t for t in balances.values()
        if t["balance"] > 0 and (
            "RRT" in t["token_symbol"].upper() or
            "REENTAL" in t["token_name"].upper() or
            "REAL" in t["token_symbol"].upper()
        )
    ]

    return sorted(reental_tokens, key=lambda x: x["token_name"])


# ─── Construcción del email ───────────────────────────────────────────────────

def build_email_html(report: dict) -> str:
    fecha = report["fecha"]
    secciones_html = ""

    for wallet_name, tokens in report["wallets"].items():
        wallet_addr = report["addresses"][wallet_name]
        short_addr  = f"{wallet_addr[:6]}...{wallet_addr[-4:]}"
        polygonscan_url = f"https://polygonscan.com/address/{wallet_addr}#tokentxns"

        if not tokens:
            rows = "<tr><td colspan='3' style='color:#888;padding:12px 0;'>Sin tokens Reental detectados</td></tr>"
        else:
            rows = ""
            for t in tokens:
                rows += f"""
                <tr>
                  <td style='padding:10px 12px;border-bottom:1px solid #f0f0f0;font-family:monospace;font-size:12px;color:#555;'>{t['token_address']}</td>
                  <td style='padding:10px 12px;border-bottom:1px solid #f0f0f0;font-weight:500;'>{t['token_name']}</td>
                  <td style='padding:10px 12px;border-bottom:1px solid #f0f0f0;text-align:right;font-weight:600;color:#1a1a2e;'>{t['balance']:.4f}</td>
                </tr>"""

        total = len(tokens)
        secciones_html += f"""
        <div style='margin-bottom:32px;'>
          <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>
            <span style='font-size:15px;font-weight:600;color:#1a1a2e;'>{wallet_name}</span>
            <a href='{polygonscan_url}' style='font-size:12px;color:#6c4de6;text-decoration:none;'>
              Ver en Polygonscan →
            </a>
          </div>
          <div style='font-size:12px;color:#888;margin-bottom:12px;font-family:monospace;'>{wallet_addr}</div>
          <table width='100%' cellpadding='0' cellspacing='0' style='border-collapse:collapse;font-size:13px;'>
            <thead>
              <tr style='background:#f5f3ff;'>
                <th style='padding:8px 12px;text-align:left;font-weight:500;color:#555;font-size:12px;'>Token Address</th>
                <th style='padding:8px 12px;text-align:left;font-weight:500;color:#555;font-size:12px;'>Nombre</th>
                <th style='padding:8px 12px;text-align:right;font-weight:500;color:#555;font-size:12px;'>Cantidad</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
          <div style='font-size:12px;color:#888;margin-top:8px;text-align:right;'>
            {total} token{'s' if total != 1 else ''} Reental encontrado{'s' if total != 1 else ''}
          </div>
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <body style='margin:0;padding:0;background:#f8f8fb;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;'>
      <div style='max-width:640px;margin:32px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.06);'>

        <!-- Header -->
        <div style='background:linear-gradient(135deg,#6c4de6 0%,#4f35b3 100%);padding:28px 32px;'>
          <div style='color:#e8e0ff;font-size:12px;margin-bottom:4px;letter-spacing:0.5px;'>REENTAL MONITOR</div>
          <div style='color:#fff;font-size:22px;font-weight:600;'>Reporte diario de tokens</div>
          <div style='color:#c4b5fd;font-size:13px;margin-top:6px;'>{fecha} · Red Polygon</div>
        </div>

        <!-- Contenido -->
        <div style='padding:28px 32px;'>
          {secciones_html}
        </div>

        <!-- Footer -->
        <div style='padding:20px 32px;border-top:1px solid #f0f0f0;background:#fafafa;'>
          <p style='margin:0;font-size:11px;color:#aaa;'>
            Este reporte se genera automáticamente cada día a las 08:00h (hora España).<br>
            Datos obtenidos de Polygonscan · Red Polygon PoS
          </p>
        </div>

      </div>
    </body>
    </html>
    """


def build_email_text(report: dict) -> str:
    lines = [f"REENTAL MONITOR — {report['fecha']}\n{'='*50}\n"]
    for wallet_name, tokens in report["wallets"].items():
        lines.append(f"\n{wallet_name}")
        lines.append(report["addresses"][wallet_name])
        lines.append("-" * 40)
        if not tokens:
            lines.append("Sin tokens Reental detectados.")
        else:
            for t in tokens:
                lines.append(f"  {t['token_name']:<30} {t['balance']:.4f}")
                lines.append(f"  {t['token_address']}")
        lines.append("")
    lines.append("\nDatos: Polygonscan · Red Polygon PoS")
    return "\n".join(lines)


# ─── Envío de email ───────────────────────────────────────────────────────────

def send_email(subject: str, html_content: str, text_content: str):
    recipients = [r.strip() for r in EMAIL_TO.split(",")]
    message = Mail(
        from_email=EMAIL_FROM,
        to_emails=recipients,
        subject=subject,
        html_content=html_content,
        plain_text_content=text_content,
    )
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    print(f"Email enviado. Status: {response.status_code}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    fecha = datetime.now(timezone.utc).strftime("%d %b %Y")
    print(f"[{datetime.now().isoformat()}] Iniciando consulta de wallets...")

    report = {
        "fecha":     fecha,
        "wallets":   {},
        "addresses": {},
    }

    for wallet_name, wallet_address in WALLETS.items():
        print(f"  → Consultando {wallet_name} ({wallet_address[:10]}...)")
        tokens = get_reental_tokens(wallet_address)
        report["wallets"][wallet_name]   = tokens
        report["addresses"][wallet_name] = wallet_address
        print(f"     {len(tokens)} tokens encontrados")

    subject      = f"Reental · Reporte diario {fecha}"
    html_content = build_email_html(report)
    text_content = build_email_text(report)

    send_email(subject, html_content, text_content)
    print("Proceso completado.")


if __name__ == "__main__":
    main()
