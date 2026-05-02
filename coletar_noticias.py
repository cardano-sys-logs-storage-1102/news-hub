"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              NEWS HUB — Coletor de Notícias Diário                         ║
║   RSS (NYT, Guardian, BBC, Reuters...) + YouTube Data API v3               ║
║   Saída: noticias.json  →  GitHub Pages dashboard                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Instalação:
    pip install requests feedparser

Uso:
    YOUTUBE_API_KEY=AIzaSy... python coletar_noticias.py
    (a chave é lida do ambiente — nunca coloque no código)
"""

import os, json, datetime, time, hashlib
import requests, feedparser
from pathlib import Path

# ── Configuração ───────────────────────────────────────────────────────────────

JSON_PATH       = Path(__file__).parent / "noticias.json"
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
MAX_ARTIGOS_RSS = 6    # por feed
MAX_VIDEOS_YT   = 3    # por canal
DIAS_HISTORICO  = 7    # quantos dias guardar no JSON

# ── Fontes RSS por categoria ───────────────────────────────────────────────────

RSS_FEEDS = {
    "science_tech": [
        ("Nature",           "https://www.nature.com/nature.rss"),
        ("MIT Tech Review",  "https://www.technologyreview.com/feed/"),
        ("Ars Technica",     "https://feeds.arstechnica.com/arstechnica/index"),
        ("The Verge",        "https://www.theverge.com/rss/index.xml"),
        ("Science Daily",    "https://www.sciencedaily.com/rss/top/science.xml"),
        ("Phys.org",         "https://phys.org/rss-feed/"),
        ("NASA",             "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
        ("New Scientist",    "https://www.newscientist.com/feed/home/"),
    ],
    "economy": [
        ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
        ("Financial Times",  "https://www.ft.com/rss/home/uk"),
        ("The Economist",    "https://www.economist.com/finance-and-economics/rss.xml"),
        ("Bloomberg",        "https://feeds.bloomberg.com/markets/news.rss"),
        ("AP Business",      "https://rsshub.app/apnews/topics/business"),
        ("WSJ Markets",      "https://feeds.content.dowjones.io/public/rss/mw_marketpulse"),
    ],
    "brazil_politics": [
        ("Reuters Brazil",   "https://feeds.reuters.com/reuters/companyNews?topic=BRAZIL"),
        ("BBC Brasil",       "https://www.bbc.com/portuguese/brasil/index.xml"),
        ("AP Latin America", "https://rsshub.app/apnews/topics/hub_Latin-America"),
        ("DW Brasil",        "https://rss.dw.com/rdf/rss-br-bra"),
        ("Al Jazeera Brazil","https://www.aljazeera.com/xml/rss/all.xml"),
    ],
    "world_politics": [
        ("NYT World",        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
        ("The Guardian",     "https://www.theguardian.com/world/rss"),
        ("BBC World",        "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("AP Top News",      "https://rsshub.app/apnews/topics/apf-topnews"),
        ("France 24",        "https://www.france24.com/en/rss"),
        ("Foreign Affairs",  "https://www.foreignaffairs.com/rss.xml"),
        ("DW World",         "https://rss.dw.com/rdf/rss-en-all"),
    ],
}

# ── Canais YouTube por categoria ───────────────────────────────────────────────

YOUTUBE_CHANNELS = {
    "science_tech": [
        ("Kurzgesagt",        "UCsXVk37bltHxD1rDPwtNM8Q"),
        ("Veritasium",        "UCHnyfMqiRRG1u-2MsSQLbXA"),
        ("MIT OpenCourseWare","UCEBb1b_L6zDS3xTUrIALZOw"),
        ("TED",               "UCAuUUnT6oDeKwE6v1NGQxug"),
        ("Two Minute Papers", "UCbfYPyITQ-7l4upoX8nvctg"),
        ("NASA",              "UCLA_DiR1FfKNvjuUpBHmylQ"),
        ("Ars Technica",      "UCUU3jROBO4mrcmFNJnObLug"),
    ],
    "economy": [
        ("Bloomberg Quicktake","UCIALMKvObZNtJ6Rg1HnhQXA"),
        ("CNBC",               "UCvJJ_dzjViJCoLf5uKUTwoA"),
        ("The Economist",      "UC0p5jTq6Xx_DosDFxVXnWaQ"),
        ("Financial Times",    "UCHtcRlPOPU9lG2F-7ZKp1ZA"),
        ("ColdFusion",         "UC4QZ_LsYcvcq7qOsOhpAX4A"),
        ("Wendover Productions","UCsooa4yRKGN_zEE8iknghZA"),
    ],
    "brazil_politics": [
        ("BBC News Brasil",  "UCer0OBDHBiTLxfUCPNkEjYA"),
        ("DW Brasil",        "UCGCNibhWuCEAnlJJHQQgAag"),
        ("Al Jazeera Eng",   "UCNye-wNBqNL5ZzHSJdqvbow"),
        ("VICE News",        "UCZaT_X_mc0BI-djXOlfhqWQ"),
        ("Reuters",          "UCAhmMjrhKMI1vQKFqDeIqvw"),
    ],
    "world_politics": [
        ("DW News",          "UCknLrEdhRCp1aegoMqRaCZg"),
        ("PBS NewsHour",     "UC6ZFN9Tx6xh-skXCuRHCDpQ"),
        ("Al Jazeera Eng",   "UCNye-wNBqNL5ZzHSJdqvbow"),
        ("BBC News",         "UC16niRr50-MSBwiO3He68cA"),
        ("France 24 Eng",    "UCQfwfsi5VrQ8yKZ-UWmAEFg"),
        ("Stratfor",         "UCowJ_eq9by7znKxdJuKLAKQ"),
    ],
}

CATEGORY_META = {
    "science_tech":    {"label": "Science & Technology", "color": "#378ADD", "icon": "🔬"},
    "economy":         {"label": "Economy & Markets",    "color": "#1D9E75", "icon": "📈"},
    "brazil_politics": {"label": "Brazil Politics",      "color": "#7F77DD", "icon": "🇧🇷"},
    "world_politics":  {"label": "World Politics",       "color": "#EF9F27", "icon": "🌍"},
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NewsHub/1.0; +https://github.com/news-hub)"
}

# ── Utilidades ─────────────────────────────────────────────────────────────────

def uid(titulo, fonte):
    return hashlib.md5(f"{titulo}{fonte}".encode()).hexdigest()[:12]

def parse_data(entry):
    for campo in ["published_parsed", "updated_parsed"]:
        val = getattr(entry, campo, None)
        if val:
            try:
                return datetime.datetime(*val[:6]).isoformat(timespec="seconds")
            except Exception:
                pass
    return datetime.datetime.utcnow().isoformat(timespec="seconds")

def resumo(entry, max_chars=280):
    for campo in ["summary", "description", "content"]:
        txt = getattr(entry, campo, None)
        if isinstance(txt, list):
            txt = txt[0].get("value", "") if txt else ""
        if txt:
            import re
            txt = re.sub(r"<[^>]+>", " ", txt)
            txt = re.sub(r"\s+", " ", txt).strip()
            return txt[:max_chars] + ("…" if len(txt) > max_chars else "")
    return ""

def eh_recente(iso_str, dias=2):
    try:
        dt = datetime.datetime.fromisoformat(iso_str)
        return (datetime.datetime.utcnow() - dt).days <= dias
    except Exception:
        return True

# ── RSS ────────────────────────────────────────────────────────────────────────

def coletar_rss(categoria):
    artigos = []
    feeds = RSS_FEEDS.get(categoria, [])
    for nome, url in feeds:
        print(f"    RSS  {nome}...", end=" ", flush=True)
        try:
            feed = feedparser.parse(url, request_headers=HEADERS)
            count = 0
            for entry in feed.entries[:MAX_ARTIGOS_RSS]:
                titulo = getattr(entry, "title", "").strip()
                link   = getattr(entry, "link",  "").strip()
                if not titulo or not link:
                    continue
                data = parse_data(entry)
                artigos.append({
                    "id":       uid(titulo, nome),
                    "tipo":     "artigo",
                    "titulo":   titulo,
                    "resumo":   resumo(entry),
                    "link":     link,
                    "fonte":    nome,
                    "data":     data,
                    "destaque": False,
                })
                count += 1
            print(f"{count}")
        except Exception as e:
            print(f"erro: {e}")
        time.sleep(1)
    return artigos

# ── YouTube ────────────────────────────────────────────────────────────────────

def coletar_youtube(categoria):
    videos = []
    if not YOUTUBE_API_KEY:
        print("    ⚠  YOUTUBE_API_KEY não definida — pulando vídeos")
        return videos

    canais = YOUTUBE_CHANNELS.get(categoria, [])
    for nome, channel_id in canais:
        print(f"    YT   {nome}...", end=" ", flush=True)
        try:
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "key":        YOUTUBE_API_KEY,
                "channelId":  channel_id,
                "part":       "snippet",
                "order":      "date",
                "type":       "video",
                "maxResults": MAX_VIDEOS_YT,
                "publishedAfter": (
                    datetime.datetime.utcnow() - datetime.timedelta(days=3)
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            items = r.json().get("items", [])
            count = 0
            for item in items:
                s = item.get("snippet", {})
                vid_id = item.get("id", {}).get("videoId", "")
                titulo = s.get("title", "").strip()
                if not titulo or not vid_id:
                    continue
                thumb = (s.get("thumbnails", {})
                          .get("medium", {})
                          .get("url", ""))
                videos.append({
                    "id":        uid(titulo, nome),
                    "tipo":      "video",
                    "titulo":    titulo,
                    "resumo":    s.get("description", "")[:280],
                    "link":      f"https://www.youtube.com/watch?v={vid_id}",
                    "fonte":     nome,
                    "thumbnail": thumb,
                    "data":      s.get("publishedAt", "")[:19],
                    "destaque":  False,
                })
                count += 1
            print(f"{count}")
        except Exception as e:
            print(f"erro: {e}")
        time.sleep(0.5)
    return videos

# ── Destaque do dia ────────────────────────────────────────────────────────────

def marcar_destaque(itens):
    """Marca o item mais recente como destaque da categoria."""
    if not itens:
        return itens
    itens_sorted = sorted(itens, key=lambda x: x.get("data",""), reverse=True)
    itens_sorted[0]["destaque"] = True
    return itens_sorted

# ── JSON ───────────────────────────────────────────────────────────────────────

def carregar_historico():
    if JSON_PATH.exists():
        with open(JSON_PATH, encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                pass
    return {"categorias": {}, "ultima_atualizacao": "", "dias_historico": DIAS_HISTORICO}

def salvar_json(dados_novos):
    historico = carregar_historico()
    limite = datetime.datetime.utcnow() - datetime.timedelta(days=DIAS_HISTORICO)
    total_novos = 0

    for cat, itens_novos in dados_novos.items():
        existentes = historico["categorias"].get(cat, [])
        ids_existentes = {i["id"] for i in existentes}

        # Remove itens muito antigos
        existentes = [
            i for i in existentes
            if i.get("data", "") >= limite.isoformat(timespec="seconds")
        ]

        # Adiciona apenas novos
        for item in itens_novos:
            if item["id"] not in ids_existentes:
                existentes.append(item)
                total_novos += 1

        # Ordena por data desc, limita a 60 por categoria
        existentes.sort(key=lambda x: x.get("data",""), reverse=True)
        existentes = existentes[:60]

        # Re-marca destaque
        if existentes:
            for i in existentes:
                i["destaque"] = False
            existentes[0]["destaque"] = True

        historico["categorias"][cat] = existentes

    historico["ultima_atualizacao"] = datetime.datetime.utcnow().isoformat(timespec="seconds")
    historico["meta"] = CATEGORY_META

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)

    print(f"\n  ✔  {total_novos} itens novos adicionados")
    total = sum(len(v) for v in historico["categorias"].values())
    print(f"  ✔  Total no arquivo: {total} itens")
    return total_novos

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    import time as _t; t0 = _t.time()
    print(f"\n{'═'*60}")
    print(f"  NEWS HUB — {datetime.date.today()}")
    print(f"  YouTube API: {'✔ configurada' if YOUTUBE_API_KEY else '✗ não definida'}")
    print(f"{'═'*60}\n")

    dados = {}
    for cat in RSS_FEEDS:
        label = CATEGORY_META[cat]["label"]
        print(f"▶  {label}")
        artigos = coletar_rss(cat)
        videos  = coletar_youtube(cat)
        dados[cat] = artigos + videos
        print(f"   Subtotal: {len(artigos)} artigos + {len(videos)} vídeos\n")

    salvar_json(dados)
    print(f"  Concluído em {round(_t.time()-t0)}s\n")

if __name__ == "__main__":
    main()
