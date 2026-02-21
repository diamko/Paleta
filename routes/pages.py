"""
Программа: «Paleta» – веб-приложение для генерации и управления цветовыми палитрами.
Модуль: routes/pages.py – маршруты пользовательских страниц.
"""

from datetime import datetime, timedelta

from flask import Response, current_app, redirect, render_template, request, send_from_directory, url_for
from flask_login import login_required, current_user

from models.palette import Palette
from models.upload import Upload
from utils.i18n import resolve_request_language


def _resolve_lang() -> str:
    app = current_app
    return resolve_request_language(
        request=request,
        url_lang=None,
        supported_languages=app.config["SUPPORTED_LANGUAGES"],
        cookie_name=app.config["LANG_COOKIE_NAME"],
        default_language=app.config["DEFAULT_LANGUAGE"],
        ru_country_codes=app.config["RU_COUNTRY_CODES"],
    )


def register_routes(app):
    yandex_verification_file = "yandex_a19b89f07e18fcfd.html"

    @app.get("/")
    def language_root():
        return redirect(url_for("index", lang=_resolve_lang()), code=302)

    @app.get("/index")
    def index_legacy():
        return redirect(url_for("index", lang="ru"), code=301)

    @app.route("/<lang>/index")
    @app.route("/<lang>/")
    def index(lang):
        recent_uploads = []
        if current_user.is_authenticated:
            cutoff = datetime.utcnow() - timedelta(days=7)
            recent_uploads = (
                Upload.query.filter_by(user_id=current_user.id)
                .filter(Upload.created_at >= cutoff)
                .order_by(Upload.created_at.desc())
                .all()
            )

        return render_template("index.html", recent_uploads=recent_uploads)

    @app.get("/generatePalet")
    def generatePalet_legacy():
        return redirect(url_for("generatePalet", lang="ru"), code=301)

    @app.route("/<lang>/generatePalet")
    def generatePalet(lang):
        return render_template("generatePalet.html")

    @app.get("/myPalet")
    def myPalet_legacy():
        return redirect(url_for("myPalet", lang="ru"), code=301)

    @app.route("/<lang>/myPalet")
    @login_required
    def myPalet(lang):
        palettes = (
            Palette.query.filter_by(user_id=current_user.id)
            .order_by(Palette.created_at.desc())
            .all()
        )
        return render_template("myPalet.html", palettes=palettes)

    @app.get("/faq")
    def faq_legacy():
        return redirect(url_for("faq", lang="ru"), code=301)

    @app.route("/<lang>/faq")
    def faq(lang):
        return render_template("faq.html")

    @app.route(f"/{yandex_verification_file}")
    def yandex_verification():
        return send_from_directory(app.root_path, yandex_verification_file)

    @app.get("/sitemap.xml")
    def sitemap_xml():
        public_endpoints = (
            "index",
            "generatePalet",
            "faq",
            "register",
            "login",
            "forgot_password",
            "reset_password",
        )
        supported_languages = app.config["SUPPORTED_LANGUAGES"]
        lastmod = datetime.utcnow().date().isoformat()

        url_entries = []
        for endpoint in public_endpoints:
            localized_urls = {
                lang: url_for(endpoint, lang=lang, _external=True)
                for lang in supported_languages
            }

            for lang, location in localized_urls.items():
                alternate_links = [
                    f'    <xhtml:link rel="alternate" hreflang="{alt_lang}" href="{alt_url}" />'
                    for alt_lang, alt_url in localized_urls.items()
                ]
                alternate_links.append(
                    f'    <xhtml:link rel="alternate" hreflang="x-default" href="{localized_urls[app.config["DEFAULT_LANGUAGE"]]}" />'
                )

                url_entries.append(
                    "\n".join(
                        (
                            "  <url>",
                            f"    <loc>{location}</loc>",
                            f"    <lastmod>{lastmod}</lastmod>",
                            *alternate_links,
                            "  </url>",
                        )
                    )
                )

        xml = "\n".join(
            (
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                'xmlns:xhtml="http://www.w3.org/1999/xhtml">',
                *url_entries,
                "</urlset>",
                "",
            )
        )
        return Response(xml, mimetype="application/xml")

    @app.get("/robots.txt")
    def robots_txt():
        sitemap_url = request.url_root.rstrip("/") + url_for("sitemap_xml")
        disallow_lang_specific = []
        for lang in app.config["SUPPORTED_LANGUAGES"]:
            disallow_lang_specific.extend(
                (
                    f"Disallow: /{lang}/myPalet",
                    f"Disallow: /{lang}/profile",
                    f"Disallow: /{lang}/profile/",
                    f"Disallow: /{lang}/logout",
                )
            )

        body = "\n".join(
            (
                "User-agent: *",
                "Allow: /",
                "Disallow: /api/",
                *disallow_lang_specific,
                f"Sitemap: {sitemap_url}",
                "",
            )
        )
        return Response(body, mimetype="text/plain")
