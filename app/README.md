# config-viewer

App Flask que lê as configurações do host/container onde roda e exibe em uma página web.
Serve como **template padrão** para as próximas apps (Dockerfile + compose + health check).

## Endpoints
- `/` página web
- `/api/config` JSON
- `/health` health check

## Rodar local
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py        # http://localhost:8080
```

## Docker
```bash
cp .env.example .env
docker compose up -d --build
```

## Deploy no Portainer (Stack via Git)
1. Stacks → Add stack → **Repository**
2. Repository URL: URL do repo no GitHub (se privado, ative Authentication e use um PAT)
3. Compose path: `docker-compose.yml`
4. Environment variables: `APP_PORT`, `APP_NAME`, `APP_VERSION`
5. Deploy the stack → acesse `http://IP-DO-HOST:APP_PORT`

## Padrão para novas apps
Copie a pasta e altere: nome do serviço/container no compose, `APP_NAME`, porta e código em `app.py`.
Mantenha `/health`, usuário não-root e variáveis via ambiente (nunca commitar `.env`).

## Rede e host (Ubuntu)
O compose usa `network_mode: host`: hostname e IPs mostrados são os do servidor, e a porta vem de `APP_PORT`
(confira se está livre). `/etc/os-release` é montado em modo leitura para exibir o SO real.
Se preferir isolar, remova `network_mode` e use `ports: ["${APP_PORT:-8080}:8080"]` com `PORT=8080`.

## Nota
Dentro do container, os dados são do container (hostname, IP, CPU/RAM visíveis a ele).
Variáveis com KEY, SECRET, TOKEN, PASS, PWD ou CREDENTIAL no nome são mascaradas.
