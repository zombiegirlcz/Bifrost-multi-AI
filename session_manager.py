"""
Bifrost 2.0 — Správa Playwright sessions pro AI modely
"""
import json
import asyncio
import random
from pathlib import Path
try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
except ImportError:
    async_playwright = None
    Browser = Page = BrowserContext = None
from utils.logger import log_phase, log_error
from utils.rate_limiter import RateLimiter
from utils.human_behavior import HumanBehavior
from config import MODELS, CHROMIUM_PATH


class AISession:
    def __init__(self, model_key: str, rate_limiter: RateLimiter):
        self.model_key = model_key
        self.config = MODELS[model_key]
        self.name = self.config["name"]
        self.role = self.config["role"]
        self.rate_limiter = rate_limiter
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.is_connected = False
        self.human: HumanBehavior | None = None

    async def connect(self, playwright):
        """Inicializuje browser session s cookies."""
        try:
            self.browser = await playwright.chromium.launch(
                executable_path=CHROMIUM_PATH,
                headless=True,
                args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
            )

            # Načti cookies
            cookies = []
            cookies_path = self.config["cookies"]
            if Path(cookies_path).exists():
                with open(cookies_path, "r") as f:
                    cookies = json.load(f)
                # Runtime sanitizace — Playwright vyžaduje sameSite jako "Strict"|"Lax"|"None"
                for c in cookies:
                    if "sameSite" in c:
                        if c["sameSite"] is None:
                            del c["sameSite"]
                        elif c["sameSite"] not in ("Strict", "Lax", "None"):
                            del c["sameSite"]

            self.context = await self.browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Linux; Android 13) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Mobile Safari/537.36"
                )
            )

            if cookies:
                await self.context.add_cookies(cookies)

            self.page = await self.context.new_page()
            await self.page.goto(self.config["url"], wait_until="networkidle")
            
            # Inicializuj HumanBehavior
            self.human = HumanBehavior(self.page)
            
            # Urči si lidi s anti-detection routinou
            await self.human.anti_detection_routine()
            
            self.is_connected = True
            log_phase("worker_build", self.model_key, f"Session připojena: {self.name}")

        except Exception as e:
            log_error(self.model_key, f"Nepodařilo se připojit: {e}")
            self.is_connected = False
            raise

    async def send_message(self, message: str) -> str:
        """Pošle zprávu AI modelu a vrátí odpověď."""
        if not self.is_connected:
            raise ConnectionError(f"{self.name} není připojen")

        await self.rate_limiter.wait(self.model_key)

        try:
            # Simuluj lidské chování PŘED komunikací
            await self.human.anti_detection_routine()
            
            # Počet odpovědí PŘED odesláním
            existing_responses = await self.page.query_selector_all(
                self.config["response_selector"]
            )
            count_before = len(existing_responses)

            # Vyplň input
            input_el = await self.page.wait_for_selector(
                self.config["input_selector"], timeout=30000
            )
            
            # Klikni (někdy vicej krát, jak by dělal člověk)
            for _ in range(random.randint(1, 2)):
                await input_el.click()
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            await input_el.fill("")
            
            # Piš pomalu s lidským chováním
            if self.human:
                await self.human.type_slowly(self.config["input_selector"], message)
            else:
                # Fallback - postupné psaní
                chunks = [message[i:i+500] for i in range(0, len(message), 500)]
                for chunk in chunks:
                    await input_el.type(chunk, delay=5)
                    await asyncio.sleep(0.1)

            # Čekej jako by sis dumal nad zprávou
            await self.human.think_like_human()

            # Odešli
            submit_btn = await self.page.wait_for_selector(
                self.config["submit_selector"], timeout=10000
            )
            await submit_btn.click()

            # Čekej na odpověď (se simulací čtení)
            response_text = await self._wait_for_response(count_before)
            
            log_phase("brain_round", self.model_key, 
                     f"Odpověď přijata ({len(response_text)} znaků)")
            return response_text

        except Exception as e:
            log_error(self.model_key, f"Chyba při komunikaci: {e}")
            raise

    async def _wait_for_response(self, count_before: int) -> str:
        """Čeká na novou odpověď od modelu."""
        timeout = self.config["timeout"]
        poll_interval = 2000  # ms

        # Čekej na nový element odpovědi
        for _ in range(timeout // poll_interval):
            await asyncio.sleep(poll_interval / 1000)

            responses = await self.page.query_selector_all(
                self.config["response_selector"]
            )

            if len(responses) > count_before:
                # Čekej až model dopíše (button se stane opět klikatelným)
                try:
                    await self.page.wait_for_selector(
                        self.config["wait_selector"],
                        timeout=timeout
                    )
                except:
                    await asyncio.sleep(5)  # Fallback čekání

                # Získej poslední odpověď
                responses = await self.page.query_selector_all(
                    self.config["response_selector"]
                )
                last_response = responses[-1]
                return await last_response.inner_text()

        raise TimeoutError(f"{self.name} neodpověděl v časovém limitu")

    async def disconnect(self):
        """Uklidí session."""
        if self.browser:
            await self.browser.close()
        self.is_connected = False
        log_phase("complete", self.model_key, f"Session ukončena: {self.name}")


class SessionManager:
    """Spravuje všechny AI sessions."""

    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.sessions: dict[str, AISession] = {}
        self.playwright = None

    async def initialize(self):
        """Spustí Playwright a připojí všechny modely."""
        pw = await async_playwright().start()
        self.playwright = pw

        for model_key, model_config in MODELS.items():
            if not Path(model_config["cookies"]).exists():
                log_error("session_manager",
                         f"Cookies nenalezeny pro {model_key}, přeskakuji")
                continue

            session = AISession(model_key, self.rate_limiter)
            try:
                await session.connect(pw)
                self.sessions[model_key] = session
            except Exception as e:
                log_error("session_manager",
                         f"Nelze připojit {model_key}: {e}")

    def get_brains(self) -> list[AISession]:
        return [s for s in self.sessions.values() if s.role == "brain"]

    def get_worker(self) -> AISession | None:
        workers = [s for s in self.sessions.values() if s.role == "worker"]
        return workers[0] if workers else None

    async def shutdown(self):
        for session in self.sessions.values():
            await session.disconnect()
        if self.playwright:
            await self.playwright.stop()
