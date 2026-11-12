"""
pdf-exporter — gera PDF de um dashboard Grafana (OSS) usando Chromium headless.

Uso como serviço (botão "📄 Exportar PDF" do dashboard):  GET /pdf?from=...&to=...&var-unidade=...
Uso em linha de comando:  python app.py --out relatorio.pdf --query "from=now-30d&to=now&var-unidade=X"
"""
import argparse, datetime as dt, io, os, re, threading
from urllib.parse import parse_qsl, urlencode

GRAFANA_URL = os.getenv("GRAFANA_URL", "http://10.200.201.119:3000").rstrip("/")
GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN", "")              # service account (Viewer)
DASH_UID = os.getenv("DASH_UID", "deas2tf4nfl6oe")
DASH_TITLE = os.getenv("DASH_TITLE", "MONITORAMENTO GIGANET")
VIEW_W = int(os.getenv("VIEW_WIDTH", "1600"))
SCALE = float(os.getenv("SCALE", "1.5"))                     # nitidez (1 a 2)
THEME = os.getenv("THEME", "light")
PAGE_RATIO = 210 / 297 if os.getenv("ORIENTATION", "portrait") == "portrait" else 297 / 210
ALLOWED = re.compile(r"^(from|to|orgId|timezone|var-[A-Za-z0-9_\-]+)$")
_lock = threading.Semaphore(int(os.getenv("MAX_PARALLEL", "2")))


def safe_query(raw):
    """Repassa só parâmetros conhecidos (período e variáveis) para o Grafana."""
    return [(k, v) for k, v in raw if ALLOWED.match(k)]


def plan_pages(total_h, page_h, breaks):
    """Define as alturas de corte das páginas, preferindo cortar entre painéis.
    breaks = posições (px) onde termina um painel (bom ponto de corte)."""
    cuts, start = [], 0
    breaks = sorted(set(b for b in breaks if 0 < b < total_h))
    while total_h - start > page_h:
        limit = start + page_h
        ok = [b for b in breaks if start + page_h * 0.55 < b <= limit]
        cut = max(ok) if ok else limit
        cuts.append((start, cut)); start = cut
    cuts.append((start, total_h))
    return cuts


def build_pdf(png_bytes, breaks, title, scale):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    W, H = img.size
    page_h = int(W / PAGE_RATIO) - int(48 * scale)             # reserva rodapé
    cuts = plan_pages(H, page_h, [int(b * scale) for b in breaks])
    try:
        font = ImageFont.load_default(size=int(13 * scale))
    except TypeError:
        font = ImageFont.load_default()
    stamp = dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    pages = []
    for i, (a, b) in enumerate(cuts, 1):
        canvas = Image.new("RGB", (W, int(W / PAGE_RATIO)), "white")
        canvas.paste(img.crop((0, a, W, b)), (0, 0))
        d = ImageDraw.Draw(canvas)
        y = canvas.size[1] - int(30 * scale)
        d.line([(int(16 * scale), y - 6), (W - int(16 * scale), y - 6)], fill="#dee2e6", width=max(1, int(scale)))
        d.text((int(16 * scale), y), f"{title}  ·  gerado em {stamp}", fill="#6c757d", font=font)
        d.text((W - int(110 * scale), y), f"página {i}/{len(cuts)}", fill="#6c757d", font=font)
        pages.append(canvas)
    out = io.BytesIO()
    pages[0].save(out, format="PDF", save_all=True, append_images=pages[1:], resolution=150 * scale / 1.5)
    return out.getvalue()


def render_pdf(query, expand=False):
    from playwright.sync_api import sync_playwright
    qs = urlencode(safe_query(query) + [("kiosk", ""), ("theme", THEME)])
    url = f"{GRAFANA_URL}/d/{DASH_UID}?{qs}"
    headers = {"Authorization": f"Bearer {GRAFANA_TOKEN}"} if GRAFANA_TOKEN else {}
    with _lock, sync_playwright() as p:
        br = p.chromium.launch(args=["--no-sandbox"])
        ctx = br.new_context(viewport={"width": VIEW_W, "height": 1000}, device_scale_factor=SCALE, extra_http_headers=headers)
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=90000)
        page.wait_for_selector('section[data-testid^="data-testid Panel header"]', timeout=60000)
        if expand:   # melhor esforço: expande as linhas recolhidas (detalhe por unidade)
            for _ in range(60):
                rows = page.locator('[data-testid="dashboard-row-title"], button[aria-label*="xpand row"]')
                if rows.count() == 0: break
                try: rows.first.click(timeout=2000)
                except Exception: break
                page.wait_for_timeout(150)
        # rola até o fim para disparar o carregamento "lazy" de todos os painéis
        for _ in range(40):
            page.mouse.wheel(0, 1800); page.wait_for_timeout(250)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2500)
        info = page.evaluate("""() => {
            const secs=[...document.querySelectorAll('section[data-testid^="data-testid Panel header"]')];
            const sc=document.querySelector('[data-testid="data-testid Dashboard Scroll"], .scrollbar-view, main') || document.scrollingElement;
            const top=(sc.getBoundingClientRect?sc.getBoundingClientRect().top:0)-(sc.scrollTop||0);
            const rects=secs.map(s=>{const r=s.getBoundingClientRect();return [r.top-top, r.bottom-top]});
            return {bottoms:rects.map(r=>r[1]), height:Math.max(...rects.map(r=>r[1]))+16};
        }""")
        page.set_viewport_size({"width": VIEW_W, "height": int(info["height"]) + 40})
        page.wait_for_timeout(3000)
        png = page.screenshot(full_page=True, type="png")
        br.close()
    return build_pdf(png, info["bottoms"], DASH_TITLE, SCALE)


def create_app():
    from flask import Flask, Response, request, jsonify
    app = Flask(__name__)

    @app.get("/pdf")
    def pdf():
        try:
            data = render_pdf(request.args.items(multi=True), expand=request.args.get("expandir") == "1")
        except Exception as e:                                   # noqa
            return jsonify(erro=str(e)), 500
        name = "relatorio-%s.pdf" % dt.datetime.now().strftime("%Y%m%d-%H%M")
        return Response(data, mimetype="application/pdf", headers={"Content-Disposition": f'inline; filename="{name}"'})

    @app.get("/health")
    def health(): return "ok"
    return app


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="relatorio.pdf")
    ap.add_argument("--query", default="from=now-30d&to=now")
    ap.add_argument("--expandir", action="store_true")
    a = ap.parse_args()
    open(a.out, "wb").write(render_pdf(parse_qsl(a.query), expand=a.expandir))
    print("PDF gerado:", a.out)
else:
    app = create_app()
