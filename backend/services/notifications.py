"""
Notification Service
Sends alerts when high-value arbs are detected.

Supports multiple methods:

1. NTFY.SH (FREE, easiest, recommended) - Push notifications to phone
   Setup:
   - Download "ntfy" app on iPhone/Android
   - Pick any secret topic name (e.g., "my-arb-finder-xyz123")
   - Subscribe to that topic in the app
   - Add to .env: NTFY_TOPIC=my-arb-finder-xyz123
   That's it. No signup, no API key, no domain verification.

2. RESEND (FREE, 100 emails/day) - HTML email alerts
   Setup:
   - Sign up at https://resend.com, create API key
   - Add to .env: RESEND_API_KEY=re_xxx  NOTIFY_EMAIL=you@gmail.com

3. GMAIL SMTP (FREE, local dev only) - Blocked on most cloud hosts
   Setup:
   - Add to .env: NOTIFY_EMAIL=you@gmail.com  NOTIFY_EMAIL_PASSWORD=xxxx

4. PUSHOVER ($5 one-time) - iPhone/Android push notifications
"""

import json
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)


class NotificationService:
    """Send notifications for high-value arb opportunities."""

    def __init__(
        self,
        # ntfy.sh (free, easiest)
        ntfy_topic: str | None = None,
        # Resend (free, email)
        resend_api_key: str | None = None,
        # Email
        email_address: str | None = None,
        email_password: str | None = None,
        # Pushover
        pushover_user_key: str | None = None,
        pushover_app_token: str | None = None,
        # Config
        min_profit_to_notify: float = 25.0,
    ):
        self.ntfy_topic = ntfy_topic
        self.resend_api_key = resend_api_key
        self.email_address = email_address
        self.email_password = email_password
        self.pushover_user_key = pushover_user_key
        self.pushover_app_token = pushover_app_token
        self.min_profit_to_notify = min_profit_to_notify
        self._sent_cache: set[str] = set()

    @property
    def is_configured(self) -> bool:
        return self.ntfy_configured or self.resend_configured or self.smtp_configured or self.pushover_configured

    @property
    def ntfy_configured(self) -> bool:
        return bool(self.ntfy_topic)

    @property
    def resend_configured(self) -> bool:
        return bool(self.resend_api_key and self.email_address)

    @property
    def smtp_configured(self) -> bool:
        return bool(self.email_address and self.email_password)

    @property
    def pushover_configured(self) -> bool:
        return bool(self.pushover_user_key and self.pushover_app_token)

    def should_notify(self, arb: dict) -> bool:
        profit = arb.get("guaranteed_profit", 0)
        if profit < self.min_profit_to_notify:
            return False
        key = f"{arb.get('event_name')}|{arb.get('book_a')}|{arb.get('book_b')}"
        if key in self._sent_cache:
            return False
        return True

    def _build_message(self, arb: dict) -> tuple[str, str, str]:
        """Build subject, plain text, and HTML message from arb data."""
        profit = arb.get("guaranteed_profit", 0)
        pct = arb.get("profit_percentage", 0)
        event = arb.get("event_name", "Unknown")
        book_a = arb.get("book_a", "?")
        book_b = arb.get("book_b", "?")
        outcome_a = arb.get("outcome_a", "?")
        outcome_b = arb.get("outcome_b", "?")
        stake_a = arb.get("stake_a", 0)
        stake_b = arb.get("stake_b", 0)
        total = arb.get("total_stake", 0)
        ret = arb.get("guaranteed_return", 0)

        subject = f"ARB ALERT: ${profit:.2f} profit ({pct:+.1f}%) - {event}"

        plain = (
            f"ARBITRAGE OPPORTUNITY FOUND\n"
            f"{'=' * 40}\n\n"
            f"Event: {event}\n"
            f"Guaranteed Profit: ${profit:.2f} ({pct:+.1f}% ROI)\n\n"
            f"BET 1: {outcome_a} on {book_a}\n"
            f"  Stake: ${stake_a:.2f}\n\n"
            f"BET 2: {outcome_b} on {book_b}\n"
            f"  Stake: ${stake_b:.2f}\n\n"
            f"Total Investment: ${total:.2f}\n"
            f"Guaranteed Return: ${ret:.2f}\n"
            f"Guaranteed Profit: ${profit:.2f}\n\n"
            f"ACT FAST - Arb windows close quickly!\n"
        )

        html = f"""
        <div style="font-family: -apple-system, Arial, sans-serif; max-width: 500px; margin: 0 auto; background: #0a0a0f; color: #e8e8ed; padding: 24px; border-radius: 12px;">
            <h2 style="color: #00e87b; margin: 0 0 4px 0; font-size: 18px;">Arbitrage Found</h2>
            <p style="color: #8888a0; margin: 0 0 16px 0; font-size: 13px;">{event}</p>

            <div style="background: #12121a; border: 1px solid #252536; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #8888a0; font-size: 11px; text-transform: uppercase;">{book_a}</span>
                </div>
                <div style="font-weight: 600;">{outcome_a}</div>
                <div style="color: #ffbe0b; font-family: monospace; font-size: 20px; font-weight: 700; margin-top: 4px;">${stake_a:.2f}</div>
            </div>

            <div style="background: #12121a; border: 1px solid #252536; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #8888a0; font-size: 11px; text-transform: uppercase;">{book_b}</span>
                </div>
                <div style="font-weight: 600;">{outcome_b}</div>
                <div style="color: #ffbe0b; font-family: monospace; font-size: 20px; font-weight: 700; margin-top: 4px;">${stake_b:.2f}</div>
            </div>

            <div style="display: flex; justify-content: space-between; padding: 12px 0; border-top: 1px solid #252536;">
                <div>
                    <div style="color: #8888a0; font-size: 10px; text-transform: uppercase;">Total Stake</div>
                    <div style="font-family: monospace; font-weight: 700;">${total:.2f}</div>
                </div>
                <div>
                    <div style="color: #8888a0; font-size: 10px; text-transform: uppercase;">Return</div>
                    <div style="font-family: monospace; font-weight: 700; color: #00e87b;">${ret:.2f}</div>
                </div>
                <div>
                    <div style="color: #8888a0; font-size: 10px; text-transform: uppercase;">Profit</div>
                    <div style="font-family: monospace; font-weight: 700; font-size: 18px; color: #00e87b;">${profit:.2f}</div>
                </div>
            </div>

            <p style="color: #ff4757; font-size: 12px; margin-top: 12px; text-align: center;">Act fast, arb windows close quickly</p>
        </div>
        """

        return subject, plain, html

    def _send_ntfy(self, arb: dict) -> bool:
        """Send push notification via ntfy.sh. Clean, actionable format."""
        if not self.ntfy_configured:
            return False

        profit = arb.get("guaranteed_profit", 0)
        pct = arb.get("profit_percentage", 0)
        event = arb.get("event_name", "Unknown")
        book_a = arb.get("book_a_display", arb.get("book_a", "?"))
        book_b = arb.get("book_b_display", arb.get("book_b", "?"))
        outcome_a = arb.get("outcome_a", "?")
        outcome_b = arb.get("outcome_b", "?")
        stake_a = arb.get("stake_a", 0)
        stake_b = arb.get("stake_b", 0)
        dashboard_url = os.environ.get("DASHBOARD_URL", "")

        message = (
            f"BET 1: {book_a}\n"
            f"  {outcome_a} -> ${stake_a:.2f}\n\n"
            f"BET 2: {book_b}\n"
            f"  {outcome_b} -> ${stake_b:.2f}\n\n"
            f"Profit: ${profit:.2f} ({pct:+.1f}% ROI)"
        )

        try:
            data = message.encode("utf-8")
            headers = {
                "Title": f"${profit:.2f} arb: {event}",
                "Priority": "5" if profit >= 50 else "4",
                "Tags": "moneybag",
            }
            if dashboard_url:
                headers["Click"] = dashboard_url
                headers["Actions"] = f"view, Open Dashboard, {dashboard_url}"

            req = Request(f"https://ntfy.sh/{self.ntfy_topic}", data=data, headers=headers, method="POST")
            with urlopen(req, timeout=10):
                logger.info(f"ntfy sent: ${profit:.2f} - {event}")
                return True
        except Exception as e:
            logger.error(f"ntfy failed: {e}")
            return False

    def _send_ntfy_digest(self, arbs: list[dict], scan_label: str) -> bool:
        """Send a clean digest notification via ntfy.sh."""
        if not self.ntfy_configured or not arbs:
            return False

        total_profit = sum(a.get("guaranteed_profit", 0) for a in arbs)
        count = len(arbs)
        dashboard_url = os.environ.get("DASHBOARD_URL", "")

        lines = []
        for i, a in enumerate(arbs, 1):
            book_a = a.get("book_a_display", a.get("book_a", "?"))
            book_b = a.get("book_b_display", a.get("book_b", "?"))
            profit = a.get("guaranteed_profit", 0)
            pct = a.get("profit_percentage", 0)
            lines.append(
                f"#{i} ${profit:.2f} ({pct:+.1f}%)\n"
                f"  {a.get('outcome_a', '?')} on {book_a}: ${a.get('stake_a', 0):.2f}\n"
                f"  {a.get('outcome_b', '?')} on {book_b}: ${a.get('stake_b', 0):.2f}"
            )

        message = "\n\n".join(lines)

        try:
            data = message.encode("utf-8")
            headers = {
                "Title": f"{count} arb(s) - ${total_profit:.2f} total ({scan_label})",
                "Priority": "5" if total_profit >= 50 else "4",
                "Tags": "moneybag",
            }
            if dashboard_url:
                headers["Click"] = dashboard_url
                headers["Actions"] = f"view, Open Dashboard, {dashboard_url}"

            req = Request(f"https://ntfy.sh/{self.ntfy_topic}", data=data, headers=headers, method="POST")
            with urlopen(req, timeout=10):
                logger.info(f"ntfy digest sent: {count} arbs, ${total_profit:.2f}")
                return True
        except Exception as e:
            logger.error(f"ntfy digest failed: {e}")
            return False

    def _send_email(self, subject: str, plain: str, html: str) -> bool:
        """Send email. Tries Resend (HTTP) first, falls back to Gmail SMTP."""
        if self.resend_configured:
            if self._send_via_resend(subject, html):
                return True
            logger.warning("Resend failed, trying SMTP fallback...")

        if self.smtp_configured:
            return self._send_via_smtp(subject, plain, html)

        return False

    def _send_via_resend(self, subject: str, html: str) -> bool:
        """Send email via Resend HTTP API. Works on any cloud host. Free 100 emails/day."""
        try:
            data = json.dumps({
                "from": "Arb Finder <onboarding@resend.dev>",
                "to": [self.email_address],
                "subject": subject,
                "html": html,
            }).encode("utf-8")

            req = Request(
                "https://api.resend.com/emails",
                data=data,
                headers={
                    "Authorization": f"Bearer {self.resend_api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            with urlopen(req, timeout=15) as response:
                result = json.loads(response.read())
                logger.info(f"Resend email sent: {subject} (id: {result.get('id', '?')})")
                return True

        except URLError as e:
            logger.error(f"Resend failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Resend error: {e}")
            return False

    def _send_via_smtp(self, subject: str, plain: str, html: str) -> bool:
        """Send email via Gmail SMTP. Works locally, blocked on most cloud hosts."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email_address
            msg["To"] = self.email_address

            msg.attach(MIMEText(plain, "plain"))
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.email_address, self.email_password)
                server.send_message(msg)

            logger.info(f"SMTP email sent: {subject}")
            return True
        except Exception as e:
            logger.error(f"SMTP failed: {e}")
            return False

    async def _send_pushover(self, title: str, message: str, profit: float) -> bool:
        """Send push notification via Pushover ($5 one-time)."""
        if not self.pushover_configured:
            return False

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.pushover.net/1/messages.json",
                    data={
                        "token": self.pushover_app_token,
                        "user": self.pushover_user_key,
                        "title": title,
                        "message": message,
                        "priority": 1 if profit >= 50 else 0,
                        "sound": "cashregister",
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
            logger.info(f"Pushover sent: {title}")
            return True
        except ImportError:
            logger.warning("httpx not installed, cannot send Pushover")
            return False
        except Exception as e:
            logger.error(f"Pushover failed: {e}")
            return False

    async def notify_arb(self, arb: dict) -> bool:
        """Send notification for a high-value arb via all configured channels."""
        if not self.is_configured:
            return False

        if not self.should_notify(arb):
            return False

        sent = False

        # Try ntfy first (simplest, most reliable on cloud)
        if self.ntfy_configured:
            if self._send_ntfy(arb):
                sent = True

        # Try email (Resend first, then SMTP)
        if self.resend_configured or self.smtp_configured:
            subject, plain, html = self._build_message(arb)
            if self._send_email(subject, plain, html):
                sent = True

        # Also try Pushover if configured
        if self.pushover_configured:
            subject, plain, _ = self._build_message(arb)
            profit = arb.get("guaranteed_profit", 0)
            if await self._send_pushover(subject, plain, profit):
                sent = True

        if sent:
            key = f"{arb.get('event_name')}|{arb.get('book_a')}|{arb.get('book_b')}"
            self._sent_cache.add(key)

        return sent

    async def notify_batch(self, arbs: list[dict]) -> int:
        """Send notifications for multiple arbs. Returns count sent."""
        sent = 0
        for arb in arbs:
            if await self.notify_arb(arb):
                sent += 1
        return sent

    def send_digest(self, arbs: list[dict], scan_label: str) -> bool:
        """Send a digest summarizing ALL arbs found in a scheduled scan."""
        if not self.is_configured:
            return False

        # Send ALL arbs found, not just high-profit ones
        # User wants to see everything and decide themselves
        if not arbs:
            return False

        sent = False

        # ntfy digest
        if self.ntfy_configured:
            if self._send_ntfy_digest(arbs, scan_label):
                sent = True

        # Email digest (Resend or SMTP)
        if self.resend_configured or self.smtp_configured:
            sent = self._send_email_digest(arbs, scan_label) or sent

        return sent

    def _send_email_digest(self, qualifying: list[dict], scan_label: str) -> bool:
        """Send HTML email digest."""
        total_profit = sum(a.get("guaranteed_profit", 0) for a in qualifying)
        count = len(qualifying)

        subject = f"Arb Alert: {count} opportunit{'y' if count == 1 else 'ies'} found - ${total_profit:.2f} potential ({scan_label})"

        # Build rows for each arb
        arb_rows_plain = ""
        arb_rows_html = ""
        for i, a in enumerate(qualifying, 1):
            profit = a.get("guaranteed_profit", 0)
            pct = a.get("profit_percentage", 0)
            event = a.get("event_name", "?")
            book_a = a.get("book_a", "?")
            book_b = a.get("book_b", "?")
            outcome_a = a.get("outcome_a", "?")
            outcome_b = a.get("outcome_b", "?")
            stake_a = a.get("stake_a", 0)
            stake_b = a.get("stake_b", 0)

            arb_rows_plain += (
                f"\n#{i}: {event}\n"
                f"  Profit: ${profit:.2f} ({pct:+.1f}% ROI)\n"
                f"  {outcome_a} on {book_a}: ${stake_a:.2f}\n"
                f"  {outcome_b} on {book_b}: ${stake_b:.2f}\n"
            )

            arb_rows_html += f"""
            <div style="background: #12121a; border: 1px solid #252536; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-weight: 600; font-size: 14px;">{event}</span>
                    <span style="color: #00e87b; font-family: monospace; font-weight: 700; font-size: 16px;">${profit:.2f}</span>
                </div>
                <div style="display: flex; gap: 8px;">
                    <div style="flex: 1; background: #1c1c28; border-radius: 6px; padding: 10px;">
                        <div style="color: #8888a0; font-size: 10px; text-transform: uppercase;">{book_a}</div>
                        <div style="font-size: 13px; margin: 4px 0;">{outcome_a}</div>
                        <div style="color: #ffbe0b; font-family: monospace; font-weight: 700;">${stake_a:.2f}</div>
                    </div>
                    <div style="flex: 1; background: #1c1c28; border-radius: 6px; padding: 10px;">
                        <div style="color: #8888a0; font-size: 10px; text-transform: uppercase;">{book_b}</div>
                        <div style="font-size: 13px; margin: 4px 0;">{outcome_b}</div>
                        <div style="color: #ffbe0b; font-family: monospace; font-weight: 700;">${stake_b:.2f}</div>
                    </div>
                </div>
            </div>
            """

        plain = (
            f"ARB FINDER - {scan_label.upper()}\n"
            f"{'=' * 40}\n"
            f"Found {count} arb(s) with ${total_profit:.2f} total potential profit\n"
            f"{arb_rows_plain}\n"
            f"Open your dashboard to view details and place bets.\n"
        )

        html = f"""
        <div style="font-family: -apple-system, Arial, sans-serif; max-width: 540px; margin: 0 auto; background: #0a0a0f; color: #e8e8ed; padding: 24px; border-radius: 12px;">
            <h2 style="color: #00e87b; margin: 0; font-size: 18px;">Arb Opportunities Found</h2>
            <p style="color: #8888a0; margin: 4px 0 16px 0; font-size: 13px;">{scan_label} scan - {datetime.now(timezone.utc).strftime('%b %d, %I:%M %p')} UTC</p>

            <div style="background: #12121a; border: 1px solid #252536; border-radius: 8px; padding: 16px; margin-bottom: 16px; text-align: center;">
                <div style="color: #8888a0; font-size: 10px; text-transform: uppercase;">Total Potential Profit</div>
                <div style="color: #00e87b; font-family: monospace; font-weight: 700; font-size: 28px; margin-top: 4px;">${total_profit:.2f}</div>
                <div style="color: #8888a0; font-size: 12px; margin-top: 4px;">across {count} opportunit{'y' if count == 1 else 'ies'}</div>
            </div>

            {arb_rows_html}

            <p style="color: #ff4757; font-size: 12px; text-align: center; margin-top: 16px;">Act fast, arb windows close quickly. Open your dashboard to place bets.</p>
        </div>
        """

        return self._send_email(subject, plain, html)

    def clear_cache(self):
        self._sent_cache.clear()

    def get_config(self) -> dict:
        return {
            "configured": self.is_configured,
            "ntfy_configured": self.ntfy_configured,
            "ntfy_topic": self.ntfy_topic[:8] + "..." if self.ntfy_topic and len(self.ntfy_topic) > 8 else self.ntfy_topic,
            "resend_configured": self.resend_configured,
            "smtp_configured": self.smtp_configured,
            "email_address": self.email_address[:3] + "***" if self.email_address else None,
            "pushover_configured": self.pushover_configured,
            "min_profit_to_notify": self.min_profit_to_notify,
            "cached_notifications": len(self._sent_cache),
        }