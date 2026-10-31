# Gráficos de Ações B3 (GitHub Pages)

Site estático para ver no celular os gráficos técnicos (candles, MA9, SMA20, Bollinger, EMA50/200,
Volume, MACD, RSI, Estocástico lento e ATR) de ~450 tickers da B3, ordenados por liquidez.

- Um workflow do GitHub Actions baixa os dados do Yahoo Finance e recalcula tudo de segunda a sexta às 18:30 (Brasília).
- O site (`docs/index.html`) lê os JSONs gerados e desenha gráficos interativos (zoom, arrastar, toque).
- Não há servidor, token nem custo.

## Publicar (uma vez)

1. Crie um repositório no GitHub (ex.: `acoes-graficos`) e envie estes arquivos:
   ```bash
   git init && git add . && git commit -m "primeiro commit"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/acoes-graficos.git
   git push -u origin main
   ```
2. No GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Vá em **Actions → Atualizar gráficos → Run workflow** (primeira execução manual).
4. Em alguns minutos o site abre em `https://SEU_USUARIO.github.io/acoes-graficos/`.
   No celular, use "Adicionar à tela inicial" para virar um atalho.

> Repositório privado só publica Pages em planos pagos. No plano gratuito o repositório precisa ser público
> (o site mostra apenas dados públicos de mercado).

## Rodar localmente

```bash
pip install -r requirements.txt
python scripts/build.py            # gera docs/data/*.json
python -m http.server -d docs 8000 # abra http://localhost:8000
```

## Personalizar

- **Tickers**: edite `tickers.txt` (sem `.SA`; duplicatas são ignoradas).
- **Janela de liquidez / candles exibidos**: constantes no topo de `scripts/build.py`.
- **Horário da atualização**: `cron` em `.github/workflows/update.yml` (em UTC).
- **Filtros** (RSI, EMA200, MA9 x SMA20, SMA20 x EMA50): objeto `PRED` em `docs/index.html`. Janela dos cruzamentos: `CROSS_DAYS` em `scripts/build.py` (padrão 3 pregões).
