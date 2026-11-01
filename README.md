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
- **Filtros** (Top 50, RSI, MA9 x SMA20, SMA20 x EMA50, divergência; o botão "Legenda" do site explica cada um): objeto `PRED` em `docs/index.html`. Janela dos cruzamentos: `CROSS_DAYS` em `scripts/build.py` (padrão 3 pregões).

## Divergência de alta

O script marca uma divergência de alta quando o preço faz um fundo **mais baixo** que o anterior, mas o RSI (ou o MACD)
faz um fundo **mais alto**. Os dois fundos são ligados no gráfico (verde = RSI, azul claro = MACD) e há filtros no site.
Parâmetros no topo de `scripts/build.py` (`DIV_*`): janela do fundo, quão recente, distância entre fundos, margem do RSI.
O 2º fundo só é confirmado depois de `DIV_PIVOT` pregões (padrão 3), então o sinal chega com esse atraso.

## Projeção de volatilidade e Fibonacci

No fim de cada gráfico há uma análise (role a página para baixo), disponível para todos os ativos, qualquer que seja o filtro:

- **Volatilidade:** desvio padrão dos retornos diários (`VOL_WINDOW`, 60 pregões) projetado com a raiz do tempo, sem tendência.
  O gráfico mostra o cone de ±1σ (amarelo tracejado) e ±2σ (roxo pontilhado) por `VOL_HORIZON` pregões; a tabela mostra 5, 10 e 20 pregões.
- **Fibonacci:** retrações (23,6 / 38,2 / 50 / 61,8 / 78,6%) e extensões (127,2 / 161,8%) sobre o último grande movimento
  (maior máxima x menor mínima dos últimos `FIB_LOOKBACK` pregões). A tabela diz quais níveis cabem dentro do cone de ±1σ ou ±2σ.
- As datas futuras do cone são dias úteis; feriados da B3 não são descontados.
- Parâmetros no topo de `scripts/build.py` (`VOL_*`, `FIB_*`). Teoria estatística, não previsão.
