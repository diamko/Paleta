import json
import smtplib
import ssl
import urllib.error
import urllib.request
from email.message import EmailMessage

from flask import current_app


def send_password_reset_code(channel: str, destination: str, code: str) -> bool:
    if channel == "email":
        return _send_email_code(destination, code)
    if channel == "phone":
        return _send_sms_code(destination, code)
    return False


def _send_email_code(email: str, code: str) -> bool:
    cfg = current_app.config
    host = cfg.get("SMTP_HOST", "").strip()
    sender = cfg.get("SMTP_FROM", "").strip()
    if not host or not sender:
        return False

    port = int(cfg.get("SMTP_PORT", 587))
    use_ssl = bool(cfg.get("SMTP_USE_SSL", False))
    use_tls = bool(cfg.get("SMTP_USE_TLS", True))
    username = cfg.get("SMTP_USER", "").strip()
    password = cfg.get("SMTP_PASSWORD", "")

    msg = EmailMessage()
    msg["Subject"] = "Код восстановления пароля Paleta"
    msg["From"] = sender
    msg["To"] = email
    msg.set_content(
        (
            "Вы запросили восстановление пароля в Paleta.\n"
            f"Код подтверждения: {code}\n\n"
            "Код действует ограниченное время. Если запрос сделали не вы, просто проигнорируйте письмо."
        )
    )

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=10, context=ssl.create_default_context()) as client:
                if username:
                    client.login(username, password)
                client.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=10) as client:
                if use_tls:
                    client.starttls(context=ssl.create_default_context())
                if username:
                    client.login(username, password)
                client.send_message(msg)
        return True
    except Exception:
        current_app.logger.exception("Не удалось отправить код восстановления на email: %s", email)
        return False


def _send_sms_code(phone: str, code: str) -> bool:
    cfg = current_app.config
    api_url = cfg.get("SMS_API_URL", "").strip()
    if not api_url:
        return False

    token = cfg.get("SMS_API_TOKEN", "").strip()
    sender = cfg.get("SMS_SENDER_NAME", "Paleta").strip() or "Paleta"
    timeout = int(cfg.get("SMS_API_TIMEOUT", 8))
    payload = {
        "to": phone,
        "message": f"{sender}: код восстановления пароля {code}",
        "sender": sender,
    }

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= getattr(response, "status", 0) < 300
    except urllib.error.URLError:
        current_app.logger.exception("Не удалось отправить SMS-код восстановления на номер: %s", phone)
        return False
