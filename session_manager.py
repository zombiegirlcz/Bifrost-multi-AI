"""
Bifrost 2.0 — Správa Playwright sessions pro AI modely
Architektura: 1 sdílený browser, každý model = vlastní context + page (šetří RAM)
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
from config import MODELS, BROWSER_PATH, BROWSER_STARTUP_DELAY


class AISession:
    def __init__(self, model_key: str, rate_limiter: RateLimiter):
        self.model_key = model_key
        self.config = MODELS[model_key]
        self.name = self.config["name"]
        self.role = self.config["role"]
        self.rate_limiter = rate_limiter
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.is_connected = False
        self.human: HumanBehavior | None = None

    async def connect(self, browser: Browser):
        """Inicializuje context + page ve sdíleném browseru."""
        try:
            # Načti cookies
            cookies = []
            cookies_path = self.config["cookies"]
            if Path(cookies_path).exists():
                with open(cookies_path, "r") as f:
                    cookies = json.load(f)
                # Runtime sanitizace — Playwright vyžaduje sameSite jako "Strict"|"Lax"|"None"
                for c in list(cookies):
                    if "sameSite" in c:
                        if c["sameSite"] is None:
                            del c["sameSite"]
                        elif c["sameSite"] not in ("Strict", "Lax", "None"):
                            del c["sameSite"]

            self.context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Linux; Android 13) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Mobile Safari/537.36"
                )
            )

            if cookies:
                await self.context.add_cookies(cookies)

            self.page = await self.context.new_page()
            log_phase("worker_build", self.model_key,
                     f"📡 Načítám {self.config['url']} (timeout 4min)...")
            await self.page.goto(self.config["url"], wait_until="domcontentloaded", timeout=240000)
            log_phase("worker_build", self.model_key, "📄 Stránka načtena")

            # Post-connect akce (dismiss popup, výběr modelu)
            post = self.config.get("post_connect", {})
            if post:
                await self._post_connect(post)

            # Inicializuj HumanBehavior
            self.human = HumanBehavior(self.page)
            await self.human.anti_detection_routine()

            self.is_connected = True
            log_phase("worker_build", self.model_key, f"Session připojena: {self.name}")

        except Exception as e:
            log_error(self.model_key, f"Nepodařilo se připojit: {e}")
            self.is_connected = False
            raise

    async def _post_connect(self, post: dict):
        """Post-connect akce: zavři popup, vyber model."""
        # 1) Zavři payment/upgrade popup (X tlačítko v rohu)
        if post.get("dismiss_popup"):
            await asyncio.sleep(3)  # počkej až se popup zobrazí
            for selector in [
                "button.close", "button.modal-close", "[aria-label='Close']",
                ".modal button:has-text('×')", ".modal button:has-text('✕')",
                "button:has-text('×')", "button:has-text('✕')", "button:has-text('X')",
                ".popup-close", "[data-dismiss]", ".dialog-close",
                "svg.close-icon", "button >> svg[class*='close']",
            ]:
                try:
                    close_btn = await self.page.wait_for_selector(selector, timeout=3000)
                    if close_btn:
                        await close_btn.click()
                        log_phase("worker_build", self.model_key, "✕ Popup zavřen")
                        await asyncio.sleep(1)
                        break
                except:
                    continue

        # 2) Vyber model (klikni na dropdown, pak vyber konkrétní model)
        model_name = post.get("select_model")
        if model_name:
            await asyncio.sleep(2)
            # Klikni na model selector / dropdown
            for dropdown_sel in [
                "button.model-selector", "[class*='model-select']",
                "button:has-text('Model')", "[class*='dropdown'] button",
                "select.model", ".model-picker", "[data-testid*='model']",
            ]:
                try:
                    dropdown = await self.page.wait_for_selector(dropdown_sel, timeout=3000)
                    if dropdown:
                        await dropdown.click()
                        await asyncio.sleep(1)
                        break
                except:
                    continue

            # Klikni na požadovaný model v seznamu
            try:
                model_option = await self.page.wait_for_selector(
                    f"text='{model_name}'", timeout=5000
                )
                if model_option:
                    await model_option.click()
                    log_phase("worker_build", self.model_key,
                             f"🤖 Model vybrán: {model_name}")
                    await asyncio.sleep(1)
            except:
                log_error(self.model_key,
                         f"Model '{model_name}' nenalezen, používám default")

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
        """Uklidí context (browser zůstává — sdílený)."""
        if self.context:
            await self.context.close()
        self.is_connected = False
        log_phase("complete", self.model_key, f"Session ukončena: {self.name}")


class SessionManager:
    """Spravuje všechny AI sessions. 1 browser, N contextů."""

    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.sessions: dict[str, AISession] = {}
        self.playwright = None
        self.browser: Browser | None = None

    async def initialize(self):
        """Spustí 1 Chromium a postupně připojí modely."""
        pw = await async_playwright().start()
        self.playwright = pw

        log_phase("worker_build", "session_manager", "🚀 Spouštím sdílený Chromium...")
        self.browser = await pw.chromium.launch(
            executable_path=BROWSER_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                  "--disable-extensions", "--disable-background-networking",
                  "--disable-sync", "--disable-translate",
                  "--no-first-run", "--disable-default-apps"]
        )
        log_phase("worker_build", "session_manager", "✅ Chromium běží")

        model_keys = list(MODELS.keys())
        for i, model_key in enumerate(model_keys):
            model_config = MODELS[model_key]

            # Přeskoč modely bez cookies nebo s prázdnými cookies
            cookies_path = Path(model_config["cookies"])
            if not cookies_path.exists():
                log_error("session_manager",
                         f"Cookies nenalezeny pro {model_key}, přeskakuji")
                continue
            try:
                with open(cookies_path) as f:
                    cookie_data = json.load(f)
                if not cookie_data:
                    log_phase("worker_build", "session_manager",
                             f"⏭️  {model_key}: prázdné cookies, přeskakuji")
                    continue
            except Exception:
                continue

            log_phase("worker_build", "session_manager",
                     f"🔌 Připojuji {model_config['name']} ({model_config['url']})...")

            session = AISession(model_key, self.rate_limiter)
            try:
                await session.connect(self.browser)
                self.sessions[model_key] = session
            except Exception as e:
                log_error("session_manager",
                         f"Nelze připojit {model_key}: {e}")

            # Pauza mezi contexty — šetříme RAM na Termuxu
            if i < len(model_keys) - 1:
                log_phase("worker_build", "session_manager",
                         f"⏳ Čekám {BROWSER_STARTUP_DELAY}s před dalším modelem...")
                await asyncio.sleep(BROWSER_STARTUP_DELAY)

    def get_brains(self) -> list[AISession]:
        return [s for s in self.sessions.values() if s.role == "brain"]

    def get_worker(self) -> AISession | None:
        workers = [s for s in self.sessions.values() if s.role == "worker"]
        return workers[0] if workers else None

    async def shutdown(self):
        for session in self.sessions.values():
            await session.disconnect()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
