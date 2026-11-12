# pdf-exporter (Grafana → PDF)

O Grafana livre não exporta PDF sozinho. Este serviço abre o dashboard num Chromium headless,
carrega todos os painéis e devolve um PDF paginado (corta entre painéis, com rodapé e número de página).

## 1. Token
Grafana → Administration → Users and access → **Service accounts** → criar com papel **Viewer** → *Add token*.
Cole em `GRAFANA_TOKEN` no `docker-compose.yml` (ou use um Portainer Stack com as mesmas variáveis).

## 2. Subir
    docker compose up -d --build
    curl "http://localhost:8085/health"

## 3. Botão no dashboard
O dashboard já tem o link **📄 Exportar PDF** apontando para `http://SEU_SERVIDOR:8085/pdf`.
Troque `SEU_SERVIDOR` pelo IP/nome do servidor (Dashboard settings → Links). O link envia o período
e os filtros (unidade e interface) que estiverem selecionados.

## Opções
- `&expandir=1` na URL: tenta expandir as linhas recolhidas (detalhe por unidade). Pode ficar longo.
- Linha de comando: `python app.py --out sla.pdf --query "from=now-30d&to=now&var-unidade=SANTA"`

## Observações
- O serviço não tem login próprio: deixe-o acessível só na rede interna.
- Tabelas com mais linhas que a altura do painel mostram rolagem; aumente a altura do painel se crescer o nº de unidades.
- O PDF é uma captura de imagem de alta resolução (texto não selecionável).

## Problemas comuns
- `Timeout ... wait_for_function` / "Dashboard não carregou": a mensagem de erro traz a URL final, o título e o texto da página.
  Abra `http://SEU_SERVIDOR:8085/ultimo-erro.png` para ver a captura do que o Chromium viu.
  - Tela de login → token inválido ou sem papel Viewer; ou use `GRAFANA_USER`/`GRAFANA_PASSWORD`.
  - "Dashboard not found" → confira `DASH_UID` (é o trecho da URL após `/d/`).
- Depois de trocar arquivos: `docker compose up -d --build`.
