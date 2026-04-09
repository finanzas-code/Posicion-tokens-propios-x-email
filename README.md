# Reental Token Monitor

Reporte diario automático de tokens ERC-20 de Reental en Polygon.  
Se ejecuta cada día a las 08:00h (hora España) y envía un email con: dirección del contrato, nombre del token y cantidad en wallet.

## Arquitectura

```
Polygonscan API  →  GitHub Actions (cron 08:00h)  →  SendGrid  →  Email
```

Coste total: **$0/mes** (todos los servicios en capa gratuita).

---

## Configuración paso a paso

### 1. Clonar este repositorio

```bash
git clone https://github.com/TU_USUARIO/reental-monitor.git
cd reental-monitor
```

O crear un repo nuevo en GitHub y subir estos archivos.

---

### 2. Obtener API key de Polygonscan

1. Ir a [polygonscan.com](https://polygonscan.com) → crear cuenta gratuita
2. Menú → **API Keys** → **Add** → copiar la key generada

---

### 3. Crear cuenta SendGrid y verificar remitente

1. Ir a [sendgrid.com](https://sendgrid.com) → crear cuenta gratuita
2. **Settings → Sender Authentication → Single Sender Verification**
3. Verificar el email que usarás como remitente (recibirás un correo de confirmación)
4. **Settings → API Keys → Create API Key** → permisos: "Mail Send" → copiar la key

---

### 4. Configurar Secrets en GitHub

En tu repositorio GitHub:  
**Settings → Secrets and variables → Actions → New repository secret**

Añade estos 5 secrets:

| Secret | Valor |
|--------|-------|
| `POLYGONSCAN_API_KEY` | Tu API key de Polygonscan |
| `SENDGRID_API_KEY` | Tu API key de SendGrid |
| `EMAIL_FROM` | Email verificado en SendGrid (ej: `monitor@tudominio.com`) |
| `EMAIL_TO` | Email(s) destinatario(s), separados por coma |
| `WALLET_ADDRESS_1` | Dirección pública de tu Trezor en Polygon (0x...) |

> **Nota Trezor**: La dirección pública de tu wallet en Polygon es la misma que en Ethereum. En Trezor Suite: **Receive → copiar dirección**. No se expone ninguna clave privada en este proceso.

---

### 5. Ajustar filtro de tokens Reental

En `src/monitor.py`, la función `get_reental_tokens()` filtra tokens por símbolo.  
Los tokens de Reental suelen llamarse `RRT-XXX` o similar.  
Puedes verificar los símbolos exactos en Polygonscan buscando tu wallet → pestaña **Token Transfers**.

Si los símbolos no coinciden, edita esta sección:

```python
reental_tokens = [
    t for t in balances.values()
    if t["balance"] > 0 and (
        "RRT" in t["token_symbol"].upper() or
        "REENTAL" in t["token_name"].upper() or
        "REAL" in t["token_symbol"].upper()
    )
]
```

---

### 6. Probar manualmente

En GitHub → **Actions** → **Reental Token Monitor** → **Run workflow** → **Run workflow**

Recibirás el email en segundos. Si algo falla, los logs aparecen en la misma pantalla.

---

### Horario

El workflow usa `cron: "0 6 * * *"` (06:00 UTC):
- **Verano (CEST, UTC+2)**: llega a las **08:00h** ✓  
- **Invierno (CET, UTC+1)**: llega a las **07:00h**

Para invierno exacto cambia a `cron: "0 7 * * *"`. GitHub Actions no soporta zonas horarias nativas.

---

### Añadir segunda wallet

1. En GitHub Secrets, añade `WALLET_ADDRESS_2` con la segunda dirección
2. En `src/monitor.py`, descomenta:
   ```python
   # "Wallet Secundaria": os.environ["WALLET_ADDRESS_2"],
   ```
3. En `.github/workflows/daily-report.yml`, descomenta:
   ```yaml
   # WALLET_ADDRESS_2: ${{ secrets.WALLET_ADDRESS_2 }}
   ```
