import smtplib
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

from .network_utils import open_tcp_socket


def _emit_debug_log(client: smtplib.SMTP, *args: object) -> None:
    debug_printer = getattr(client, "_print_debug", None)
    if client.debuglevel > 0 and callable(debug_printer):
        debug_printer(*args)


class _SMTPPreferredIPv4(smtplib.SMTP):
    def _get_socket(self, host, port, timeout):
        if timeout is not None and not timeout:
            raise ValueError("Non-blocking socket (timeout=0) is not supported")
        _emit_debug_log(self, "connect: to", (host, port), self.source_address)
        return open_tcp_socket(
            host, port, timeout=timeout, source_address=self.source_address
        )


class _SMTPSSLPreferredIPv4(smtplib.SMTP_SSL):
    def _get_socket(self, host, port, timeout):
        _emit_debug_log(self, "connect:", (host, port))
        new_socket = open_tcp_socket(
            host, port, timeout=timeout, source_address=self.source_address
        )
        return self.context.wrap_socket(new_socket, server_hostname=host)


def _resolve_smtp_auth(account: dict) -> tuple[str, str]:
    email_addr = (account.get("email") or "").strip()
    password = (account.get("smtp_password") or account.get("password") or "").strip()
    if not email_addr:
        raise ValueError("未配置发件邮箱地址(email)。")
    if not password:
        raise ValueError("未配置 SMTP 密码（smtp_password 或 password）。")
    return email_addr, password


def _build_message(
    from_addr: str, from_name: str, to_addr: str, subject: str, body: str
):
    msg = EmailMessage()
    msg["From"] = formataddr((from_name, from_addr)) if from_name else from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def smtp_send_mail(account: dict, to_addr: str, subject: str, body: str):
    smtp_server = (account.get("smtp_server") or "").strip()
    smtp_port = int(account.get("smtp_port") or 0)
    smtp_use_ssl = bool(account.get("smtp_use_ssl", True))

    if not smtp_server:
        raise ValueError("未配置 SMTP 服务器地址(smtp_server)。")
    if smtp_port <= 0:
        raise ValueError("SMTP 端口(smtp_port)配置错误。")

    real_name, real_addr = parseaddr(to_addr)
    if not real_addr or "@" not in real_addr:
        raise ValueError("收件人邮箱格式错误。")

    from_addr, password = _resolve_smtp_auth(account)
    from_name = (account.get("name") or from_addr).strip()
    msg = _build_message(from_addr, from_name, real_addr, subject.strip(), body.strip())

    try:
        if smtp_use_ssl:
            with _SMTPSSLPreferredIPv4(smtp_server, smtp_port, timeout=20) as server:
                server.login(from_addr, password)
                server.send_message(msg)
        else:
            with _SMTPPreferredIPv4(smtp_server, smtp_port, timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(from_addr, password)
                server.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        raise ValueError("SMTP 认证失败，请检查账号或授权码。")
    except smtplib.SMTPException as e:
        raise RuntimeError(f"SMTP 发送失败: {e}")