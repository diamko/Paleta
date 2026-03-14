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
    """Служебная функция `_resolve_lang` для внутренней логики модуля."""
    app = current_app
    return resolve_request_language(
        request=request,
        url_lang=None,
        supported_languages=app.config["SUPPORTED_LANGUAGES"],
        cookie_name=app.config["LANG_COOKIE_NAME"],
        default_language=app.config["DEFAULT_LANGUAGE"],
        ru_country_codes=app.config["RU_COUNTRY_CODES"],
    )


def _absolute_public_url(endpoint: str, lang: str) -> str:
    """Формирует канонический абсолютный URL публичной страницы для sitemap."""
    if endpoint == "index":
        return request.url_root.rstrip("/") + f"/{lang}/"
    return url_for(endpoint, lang=lang, _external=True)


def register_routes(app):
    """Выполняет операцию `register_routes` в рамках сценария модуля."""
    yandex_verification_file = "yandex_a19b89f07e18fcfd.html"

    @app.get("/")
    def language_root():
        """Выполняет операцию `language_root` в рамках сценария модуля."""
        return redirect(url_for("index", lang=_resolve_lang()), code=302)

    @app.get("/index")
    def index_legacy():
        """Выполняет операцию `index_legacy` в рамках сценария модуля."""
        return redirect(url_for("index", lang="ru"), code=301)

    @app.route("/<lang>/index")
    @app.route("/<lang>/")
    def index(lang):
        """Выполняет операцию `index` в рамках сценария модуля."""
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
        """Выполняет операцию `generatePalet_legacy` в рамках сценария модуля."""
        return redirect(url_for("generatePalet", lang="ru"), code=301)

    @app.route("/<lang>/generatePalet")
    def generatePalet(lang):
        """Выполняет операцию `generatePalet` в рамках сценария модуля."""
        return render_template("generatePalet.html")

    @app.get("/myPalet")
    def myPalet_legacy():
        """Выполняет операцию `myPalet_legacy` в рамках сценария модуля."""
        return redirect(url_for("myPalet", lang="ru"), code=301)

    @app.route("/<lang>/myPalet")
    @login_required
    def myPalet(lang):
        """Выполняет операцию `myPalet` в рамках сценария модуля."""
        palettes = (
            Palette.query.filter_by(user_id=current_user.id)
            .order_by(Palette.created_at.desc())
            .all()
        )
        return render_template("myPalet.html", palettes=palettes)

    @app.get("/faq")
    def faq_legacy():
        """Выполняет операцию `faq_legacy` в рамках сценария модуля."""
        return redirect(url_for("faq", lang="ru"), code=301)

    @app.route("/<lang>/faq")
    def faq(lang):
        """Выполняет операцию `faq` в рамках сценария модуля."""
        return render_template("faq.html")

    @app.route("/<lang>/download")
    def download_app(lang):
        """Страница скачивания мобильного приложения."""
        return render_template("download.html")

    @app.get("/download/paleta.apk")
    def download_apk():
        """Отдаёт APK-файл мобильного приложения."""
        return send_from_directory(
            app.static_folder, "apk/paleta.apk",
            as_attachment=True,
            download_name="Paleta.apk",
        )

    @app.route(f"/{yandex_verification_file}")
    def yandex_verification():
        """Выполняет операцию `yandex_verification` в рамках сценария модуля."""
        return send_from_directory(app.root_path, yandex_verification_file)

    @app.get("/sitemap.xml")
    def sitemap_xml():
        """Выполняет операцию `sitemap_xml` в рамках сценария модуля."""
        public_endpoints = (
            "index",
            "generatePalet",
            "faq",
            "download_app",
        )
        supported_languages = app.config["SUPPORTED_LANGUAGES"]
        default_language = app.config["DEFAULT_LANGUAGE"]
        if default_language not in supported_languages:
            default_language = supported_languages[0]

        url_entries = []
        lastmod = datetime.utcnow().date().isoformat()
        for endpoint in public_endpoints:
            localized_urls = {lang: _absolute_public_url(endpoint, lang) for lang in supported_languages}
            x_default_url = localized_urls[default_language]

            for lang, location in localized_urls.items():
                alternate_links = [
                    f'    <xhtml:link rel="alternate" hreflang="{alt_lang}" href="{alt_url}" />'
                    for alt_lang, alt_url in localized_urls.items()
                ]
                alternate_links.append(
                    f'    <xhtml:link rel="alternate" hreflang="x-default" href="{x_default_url}" />'
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
        """Выполняет операцию `robots_txt` в рамках сценария модуля."""
        sitemap_url = request.url_root.rstrip("/") + url_for("sitemap_xml")
        disallow_paths = [
            "/api/",
            "/myPalet",
            "/profile",
            "/profile/",
            "/profile/update",
            "/profile/password/send-code",
            "/profile/password/change",
            "/logout",
            "/register",
            "/login",
            "/forgot-password",
            "/reset-password",
        ]

        for lang in app.config["SUPPORTED_LANGUAGES"]:
            disallow_paths.extend(
                (
                    f"/{lang}/myPalet",
                    f"/{lang}/profile",
                    f"/{lang}/profile/",
                    f"/{lang}/profile/update",
                    f"/{lang}/profile/password/send-code",
                    f"/{lang}/profile/password/change",
                    f"/{lang}/logout",
                    f"/{lang}/register",
                    f"/{lang}/login",
                    f"/{lang}/forgot-password",
                    f"/{lang}/reset-password",
                )
            )

        unique_disallow_lines = []
        seen_paths = set()
        for path in disallow_paths:
            if path in seen_paths:
                continue
            seen_paths.add(path)
            unique_disallow_lines.append(f"Disallow: {path}")

        body = "\n".join(
            (
                "User-agent: *",
                "Allow: /",
                "Allow: /favicon.ico",
                "Allow: /static/favicon.ico",
                *unique_disallow_lines,
                f"Sitemap: {sitemap_url}",
                "",
            )
        )
        return Response(body, mimetype="text/plain")
