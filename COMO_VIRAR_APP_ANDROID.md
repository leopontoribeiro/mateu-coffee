# 📱 Mateu Coffee → App Android

## PASSO 1 — Deploy na nuvem (Streamlit Cloud — GRÁTIS)

### 1.1 Acesse
👉 https://share.streamlit.io/

### 1.2 Conecte o repositório
- Clique em **"New app"**
- Escolha o repositório `leopontoribeiro/mateu-coffee`
- Branch: `main`
- Main file: `streamlit_app_final.py`

### 1.3 Configure os Secrets
Clique em **"Advanced settings"** antes de publicar e cole:

```toml
[connections.postgresql]
dialect = "postgresql"
driver = "psycopg2"
host = "ep-bitter-firefly-aqw6p7rq.c-8.us-east-1.aws.neon.tech"
port = 5432
database = "neondb"
username = "neondb_owner"
password = "npg_OpGHYl9dCF1I"

ANTHROPIC_API_KEY = "sua-chave-anthropic-aqui"
```

### 1.4 Clique em **"Deploy"**
Aguarde ~2 minutos. Você terá uma URL tipo:
```
https://leopontoribeiro-mateu-coffee.streamlit.app
```

---

## PASSO 2 — Instalar como app no Android (PWA — sem APK)

No celular Android, abra a URL no **Chrome**:
1. Toque nos 3 pontinhos (menu)
2. Toque em **"Adicionar à tela inicial"**
3. Confirme → ícone aparece como app

✅ Funciona como app, abre sem barra de URL, tela cheia.

---

## PASSO 3 — Gerar APK real (opcional)

### Opção A — Android Studio (APK local)

1. Abra a pasta `android/` no **Android Studio**
2. Edite o arquivo `android/app/src/main/java/com/mateucoffee/app/MainActivity.kt`
3. Substitua a linha:
   ```kotlin
   private val APP_URL = "https://SEU-APP.streamlit.app"
   ```
   pela URL que você obteve no Passo 1.

4. Clique em **Build → Build Bundle(s) / APK(s) → Build APK(s)**
5. O APK estará em `android/app/build/outputs/apk/debug/app-debug.apk`
6. Envie por WhatsApp para o celular e instale

### Opção B — PWABuilder (sem precisar de Android Studio)

1. Acesse https://www.pwabuilder.com
2. Cole a URL do app deployado
3. Clique em **"Start"** → **"Android"** → **"Download"**
4. Instale o APK no celular

---

## Requisitos mínimos do celular
- Android 8.0 ou superior
- Conexão com internet (o app se conecta ao banco Neon)
