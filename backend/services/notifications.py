"""
Notification Service
Sends alerts when high-value arbs are detected.

Supports two methods (use either or both):

1. EMAIL (FREE) - Gmail SMTP
   Setup:
   - Enable 2FA on your Google account
   - Go to https://myaccount.google.com/apppasswords
   - Create an app password for "Arb Finder"
   - Add to .env:
     NOTIFY_EMAIL=you@gmail.com
     NOTIFY_EMAIL_PASSWORD=xxxx xxxx xxxx xxxx

2. PUSHOVER ($5 one-time) - iPhone/Android push notifications
   Setup:
   - Sign up at pushover.net, download app
   - Create an Application at pushover.net/apps
   - Add to .env:
     PUSHOVER_USER_KEY=your_user_key
     PUSHOVER_APP_TOKEN=your_app_token
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class NotificationService:
    """Send notifications for high-value arb opportunities via email and/or push."""

    def __init__(
        self,
        # Email (free)
        email_address: str | None = None,
        email_password: str | None = None,
        # Pushover (optional)
        pushover_user_key: str | None = None,
        pushover_app_token: str | None = None,
        # Config
        min_profit_to_notify: float = 25.0,
    ):
        self.email_address = email_address
        self.email_password = email_password
        self.pushover_user_key = pushover_user_key
        self.pushover_app_token = pushover_app_token
        self.min_profit_to_notify = min_profit_to_notify
        self._sent_cache: set[str] = set()

    @property
    def is_configured(self) -> bool:
        return self.email_configured or self.pushover_configured

    @property
    def email_configured(self) -> bool:
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

    def _send_email(self, subject: str, plain: str, html: str) -> bool:
        """Send email via Gmail SMTP. Completely free."""
        if not self.email_configured:
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email_address
            msg["To"] = self.email_address  # Send to yourself

            msg.attach(MIMEText(plain, "plain"))
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.email_address, self.email_password)
                server.send_message(msg)

            logger.info(f"Email sent: {subject}")
            return True

        except Exception as e:
            logger.error(f"Email failed: {e}")
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

        subject, plain, html = self._build_message(arb)
        profit = arb.get("guaranteed_profit", 0)
        sent = False

        # Try email first (free)
        if self.email_configured:
            if self._send_email(subject, plain, html):
                sent = True

        # Also try Pushover if configured
        if self.pushover_configured:
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
        """Send a digest email summarizing all arbs found in a scheduled scan."""
        if not self.email_configured:
            return False

        qualifying = [a for a in arbs if a.get("guaranteed_profit", 0) >= self.min_profit_to_notify]
        if not qualifying:
            return False

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
            "email_configured": self.email_configured,
            "email_address": self.email_address[:3] + "***" if self.email_address else None,
            "pushover_configured": self.pushover_configured,
            "min_profit_to_notify": self.min_profit_to_notify,
            "cached_notifications": len(self._sent_cache),
        }