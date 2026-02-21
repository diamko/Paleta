"""
Программа: «Paleta» – веб-приложение для работы с цветовыми палитрами.
Модуль: routes/auth.py – маршруты аутентификации и управления сессиями.

Назначение модуля:
- Регистрация новых пользователей с проверкой сложности пароля.
- Вход и выход из системы с использованием Flask-Login.
- Восстановление пароля через email или телефон.
- Загрузка пользователя по идентификатору для управления сессией.
"""

from datetime import datetime, timedelta
import secrets

from flask import current_app, render_template, request, flash, redirect, url_for, session
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import login_manager, db
from models.user import User
from models.user_contact import UserContact
from models.password_reset_token import PasswordResetToken
from utils.contact_normalizer import normalize_email, normalize_phone
from utils.rate_limit import get_client_identifier
from utils.reset_delivery import send_password_reset_code


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def _validate_password_strength(password: str, username: str | None = None) -> str | None:
    if not (10 <= len(password) <= 128):
        return "Пароль должен содержать от 10 до 128 символов."
    if any(ch.isspace() for ch in password):
        return "Пароль не должен содержать пробелы."
    if not any(ch.isupper() for ch in password):
        return "Пароль должен содержать хотя бы одну заглавную букву."
    if not any(ch.islower() for ch in password):
        return "Пароль должен содержать хотя бы одну строчную букву."
    if not any(ch.isdigit() for ch in password):
        return "Пароль должен содержать хотя бы одну цифру."
    if not any(not ch.isalnum() for ch in password):
        return "Пароль должен содержать хотя бы один спецсимвол."
    if username and username.lower() in password.lower():
        return "Пароль не должен содержать имя пользователя."
    return None


def _normalize_contact(channel: str, raw_value: str) -> str:
    if channel == "email":
        return normalize_email(raw_value)
    if channel == "phone":
        return normalize_phone(raw_value)
    return ""


def _find_user_contact(channel: str, destination: str) -> UserContact | None:
    if channel == "email":
        return UserContact.query.filter_by(email=destination).first()
    if channel == "phone":
        return UserContact.query.filter_by(phone=destination).first()
    return None


def register_routes(app):
    def _is_rate_limited(bucket: str, limit: int, window_seconds: int, identity: str | None = None) -> bool:
        limiter = current_app.extensions.get("rate_limiter")
        if limiter is None:
            return False

        rate_identity = identity or get_client_identifier()
        rate_key = f"{bucket}:{rate_identity}"
        return not limiter.is_allowed(rate_key, limit, window_seconds)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            if _is_rate_limited("register", limit=10, window_seconds=15 * 60):
                flash("Слишком много попыток регистрации. Попробуйте через несколько минут.", "error")
                return redirect(url_for("register"))

            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            raw_email = request.form.get("email") or ""
            raw_phone = request.form.get("phone") or ""
            email = normalize_email(raw_email)
            phone = normalize_phone(raw_phone)

            if not username or not password:
                flash("Пожалуйста, заполните все поля", "error")
                return redirect(url_for("register"))

            if not raw_email.strip() and not raw_phone.strip():
                flash("Укажите email или номер телефона для восстановления пароля.", "error")
                return redirect(url_for("register"))

            if raw_email.strip() and not email:
                flash("Введите корректный email.", "error")
                return redirect(url_for("register"))

            if raw_phone.strip() and not phone:
                flash("Введите корректный номер телефона (от 10 до 15 цифр).", "error")
                return redirect(url_for("register"))

            password_error = _validate_password_strength(password, username=username)
            if password_error:
                flash(password_error, "error")
                return redirect(url_for("register"))

            if User.query.filter_by(username=username).first():
                flash("Пользователь с таким именем уже существует", "error")
                return redirect(url_for("register"))

            if email and UserContact.query.filter_by(email=email).first():
                flash("Этот email уже используется другим аккаунтом.", "error")
                return redirect(url_for("register"))

            if phone and UserContact.query.filter_by(phone=phone).first():
                flash("Этот номер телефона уже используется другим аккаунтом.", "error")
                return redirect(url_for("register"))

            hashed_password = generate_password_hash(password, method="scrypt")
            new_user = User(username=username, password_hash=hashed_password)
            new_user.contact = UserContact(email=email or None, phone=phone or None)
            db.session.add(new_user)
            db.session.commit()

            flash("Регистрация успешна! Теперь войдите в систему", "success")
            return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")

            if _is_rate_limited("login_ip", limit=20, window_seconds=10 * 60):
                flash("Слишком много попыток входа. Попробуйте позже.", "error")
                return redirect(url_for("login"))

            username_key = (username or "").strip().lower() or "anonymous"
            if _is_rate_limited(
                "login_user",
                limit=10,
                window_seconds=10 * 60,
                identity=username_key,
            ):
                flash("Слишком много попыток входа для этого пользователя. Попробуйте позже.", "error")
                return redirect(url_for("login"))

            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                flash("Вход выполнен успешно", "success")
                return redirect(url_for("index"))
            else:
                flash("Неверное имя пользователя или пароль", "error")

        return render_template("login.html")

    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        if request.method == "POST":
            if _is_rate_limited("forgot_password_ip", limit=8, window_seconds=15 * 60):
                flash("Слишком много запросов. Попробуйте позже.", "error")
                return redirect(url_for("forgot_password"))

            channel = (request.form.get("channel") or "email").strip().lower()
            raw_contact = (request.form.get("contact") or "").strip()

            if channel not in {"email", "phone"}:
                flash("Выберите способ восстановления: email или телефон.", "error")
                return redirect(url_for("forgot_password"))

            destination = _normalize_contact(channel, raw_contact)
            if not destination:
                if channel == "email":
                    flash("Введите корректный email.", "error")
                else:
                    flash("Введите корректный номер телефона (от 10 до 15 цифр).", "error")
                return redirect(url_for("forgot_password"))

            if _is_rate_limited(
                f"forgot_password_{channel}",
                limit=5,
                window_seconds=15 * 60,
                identity=destination,
            ):
                flash("Слишком много запросов для этого контакта. Попробуйте позже.", "error")
                return redirect(url_for("forgot_password"))

            user_contact = _find_user_contact(channel, destination)
            if user_contact and user_contact.user:
                now = datetime.utcnow()
                expires_at = now + timedelta(
                    minutes=max(5, int(current_app.config.get("PASSWORD_RESET_CODE_TTL_MINUTES", 15)))
                )
                code = f"{secrets.randbelow(1_000_000):06d}"

                PasswordResetToken.query.filter(
                    PasswordResetToken.user_id == user_contact.user_id,
                    PasswordResetToken.used_at.is_(None),
                    PasswordResetToken.expires_at > now,
                ).update({PasswordResetToken.used_at: now}, synchronize_session=False)

                reset_token = PasswordResetToken(
                    user_id=user_contact.user_id,
                    channel=channel,
                    destination=destination,
                    code_hash=generate_password_hash(code, method="scrypt"),
                    expires_at=expires_at,
                )
                db.session.add(reset_token)
                db.session.commit()

                sent = send_password_reset_code(channel, destination, code)
                if not sent:
                    current_app.logger.warning(
                        "Код восстановления (%s) для %s: %s",
                        channel,
                        destination,
                        code,
                    )
                    if current_app.debug:
                        flash(f"Dev-код восстановления: {code}", "info")

            # Не раскрываем, существует ли аккаунт для указанного контакта.
            flash("Если контакт найден, код восстановления отправлен.", "success")
            return redirect(url_for("reset_password", channel=channel, contact=destination))

        return render_template("forgot_password.html")

    @app.route("/reset-password", methods=["GET", "POST"])
    def reset_password():
        if request.method == "POST":
            if _is_rate_limited("reset_password_ip", limit=20, window_seconds=15 * 60):
                flash("Слишком много попыток сброса пароля. Попробуйте позже.", "error")
                return redirect(url_for("reset_password"))

            channel = (request.form.get("channel") or "email").strip().lower()
            raw_contact = (request.form.get("contact") or "").strip()
            code = (request.form.get("code") or "").strip()
            new_password = request.form.get("new_password") or ""
            confirm_password = request.form.get("confirm_password") or ""

            if channel not in {"email", "phone"}:
                flash("Выберите корректный способ восстановления.", "error")
                return redirect(url_for("reset_password"))

            destination = _normalize_contact(channel, raw_contact)
            if not destination:
                if channel == "email":
                    flash("Введите корректный email.", "error")
                else:
                    flash("Введите корректный номер телефона (от 10 до 15 цифр).", "error")
                return redirect(url_for("reset_password"))

            if not (code.isdigit() and len(code) == 6):
                flash("Код восстановления должен состоять из 6 цифр.", "error")
                return redirect(url_for("reset_password", channel=channel, contact=destination))

            if new_password != confirm_password:
                flash("Пароли не совпадают.", "error")
                return redirect(url_for("reset_password", channel=channel, contact=destination))

            user_contact = _find_user_contact(channel, destination)
            if not user_contact or not user_contact.user:
                flash("Неверный код или контакт. Проверьте данные.", "error")
                return redirect(url_for("reset_password", channel=channel, contact=destination))

            if _is_rate_limited(
                f"reset_password_{channel}",
                limit=12,
                window_seconds=15 * 60,
                identity=destination,
            ):
                flash("Слишком много попыток для этого контакта. Попробуйте позже.", "error")
                return redirect(url_for("reset_password", channel=channel, contact=destination))

            now = datetime.utcnow()
            token = (
                PasswordResetToken.query.filter_by(
                    user_id=user_contact.user_id,
                    channel=channel,
                    destination=destination,
                    used_at=None,
                )
                .filter(PasswordResetToken.expires_at > now)
                .order_by(PasswordResetToken.created_at.desc())
                .first()
            )

            if not token:
                flash("Код не найден или истек. Запросите новый код.", "error")
                return redirect(url_for("forgot_password"))

            max_attempts = max(3, int(current_app.config.get("PASSWORD_RESET_MAX_ATTEMPTS", 5)))
            if token.attempts >= max_attempts:
                flash("Превышено число попыток. Запросите новый код.", "error")
                return redirect(url_for("forgot_password"))

            if not check_password_hash(token.code_hash, code):
                token.attempts += 1
                db.session.commit()
                flash("Неверный код восстановления.", "error")
                return redirect(url_for("reset_password", channel=channel, contact=destination))

            password_error = _validate_password_strength(new_password, username=user_contact.user.username)
            if password_error:
                flash(password_error, "error")
                return redirect(url_for("reset_password", channel=channel, contact=destination))

            if check_password_hash(user_contact.user.password_hash, new_password):
                flash("Новый пароль должен отличаться от текущего.", "error")
                return redirect(url_for("reset_password", channel=channel, contact=destination))

            user_contact.user.password_hash = generate_password_hash(new_password, method="scrypt")
            token.used_at = now
            PasswordResetToken.query.filter(
                PasswordResetToken.user_id == user_contact.user_id,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
                PasswordResetToken.id != token.id,
            ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
            db.session.commit()

            flash("Пароль обновлен. Теперь вы можете войти с новым паролем.", "success")
            return redirect(url_for("login"))

        prefill_channel = (request.args.get("channel") or "email").strip().lower()
        if prefill_channel not in {"email", "phone"}:
            prefill_channel = "email"
        prefill_contact = (request.args.get("contact") or "").strip()
        return render_template(
            "reset_password.html",
            prefill_channel=prefill_channel,
            prefill_contact=prefill_contact,
        )

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        # Очищаем данные о последней загрузке при выходе из аккаунта
        session.pop("last_upload", None)
        logout_user()
        flash("Вы вышли из системы", "info")
        return redirect(url_for("index"))
