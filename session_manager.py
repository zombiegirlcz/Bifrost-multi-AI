"""
Bifrost 2.0 — Správa Playwright sessions pro AI modely
Architektura: Monica Multi-Chat — 1 stránka, 3 mozky paralelně
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
from config import (
    BROWSER_PATH, MONICA_URL, MONICA_COOKIES, MONICA_PANELS,
    MONICA_SELECTORS, RESPONSE_POLL_INTERVAL, RESPONSE_MAX_WAIT,
)


def _sanitize_cookies(cookies: list[dict]) -> list[dict]:
    """Playwright vyžaduje sameSite jako 'Strict'|'Lax'|'None' nebo klíč chybí."""
    for c in list(cookies):
        if "sameSite" in c:
            if c["sameSite"] is None or c["sameSite"] not in ("Strict", "Lax", "None"):
                del c["sameSite"]
    return cookies


class MonicaMultiSession:
    """1 stránka Monica.im, 3 panely = 3 AI mozky paralelně."""

    def __init__(self):
        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.human: HumanBehavior | None = None
        self.is_connected = False
        self.panel_models: dict[str, dict] = {}  # key → panel config
        self._sel = MONICA_SELECTORS

    async def connect(self):
        """Spustí Chromium, otevře Monica, nastaví 3 panely."""
        log_phase("worker_build", "monica", "🚀 Spouštím Chromium...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            executable_path=BROWSER_PATH, headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                  "--disable-extensions", "--disable-background-networking",
                  "--disable-sync", "--disable-translate",
                  "--no-first-run", "--disable-default-apps"])
        log_phase("worker_build", "monica", "✅ Chromium běží")

        # Context + cookies
        cookies = []
        if Path(MONICA_COOKIES).exists():
            with open(MONICA_COOKIES) as f:
                cookies = _sanitize_cookies(json.load(f))

        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")
        if cookies:
            await self.context.add_cookies(cookies)

        self.page = await self.context.new_page()

        log_phase("worker_build", "monica", f"📡 Načítám {MONICA_URL}...")
        await self.page.goto(MONICA_URL, wait_until="domcontentloaded", timeout=240000)
        await asyncio.sleep(12)
        log_phase("worker_build", "monica", "📄 Stránka načtena")

        # Layout → 3 sloupce
        await self._set_layout_3col()

        # Nastav modely v panelech
        await self._configure_panels()

        self.human = HumanBehavior(self.page)
        self.is_connected = True
        models_str = " | ".join(
            f"{v['role']}={v['model_label']}" for v in MONICA_PANELS.values())
        log_phase("worker_build", "monica", f"✅ Monica ready: {models_str}")

    async def _set_layout_3col(self):
        """Přepne layout na 3 sloupce."""
        idx = self._sel["layout_3col_idx"]
        await self.page.locator(self._sel["layout_icons"]).nth(idx).click()
        await asyncio.sleep(3)
        log_phase("worker_build", "monica", "📐 Layout: 3 sloupce")

    async def _configure_panels(self):
        """Nastaví správný model v každém panelu (s fallbackem na free tier)."""
        for key, panel_cfg in MONICA_PANELS.items():
            i = panel_cfg["panel_index"]
            label = panel_cfg["model_label"]

            # Klikni na title panelu → otevře dropdown
            await self.page.locator(
                f"{self._sel['panel']} {self._sel['panel_title']}").nth(i).click()
            await asyncio.sleep(2)

            # Zkus premium model, fallback na free
            item = self.page.locator(
                self._sel["model_dropdown"]).filter(has_text=label).first
            try:
                await item.click(timeout=3000)
                selected = label
            except Exception:
                fallback = panel_cfg.get("fallback_label", label)
                log_phase("worker_build", "monica",
                          f"  ⚠️ {label} nedostupný, zkouším {fallback}")
                await self.page.locator(
                    self._sel["model_dropdown"]).filter(has_text=fallback).first.click()
                selected = fallback
            await asyncio.sleep(1.5)

            self.panel_models[key] = {**panel_cfg, "active_model": selected}
            log_phase("worker_build", "monica",
                      f"  🧠 Panel {i}: {selected} ({panel_cfg['role']})")

    async def send_to_all(self, message: str) -> dict[str, str]:
        """Pošle zprávu globálním inputem → čte odpovědi ze všech 3 panelů."""
        if not self.is_connected:
            raise ConnectionError("Monica není připojena")

        if self.human:
            await self.human.anti_detection_routine()

        # Snapshot panelů PŘED odesláním (pro detekci nových odpovědí)
        before_snapshot = await self._snapshot_panels()

        # Vyplň globální input a odešli
        textarea = self.page.locator(self._sel["global_input"])
        await textarea.fill(message)
        await asyncio.sleep(random.uniform(0.3, 0.8))
        await textarea.press("Enter")

        log_phase("brain_round", "monica", f"📤 Odesláno všem ({len(message)} znaků)")

        # Čekej na odpovědi ze všech panelů
        responses = await self._wait_all_responses(before_snapshot)
        return responses

    async def send_per_panel(self, messages: dict[str, str]) -> dict[str, str]:
        """Pošle RŮZNÉ zprávy do jednotlivých panelů přes per-panel inputy.
        
        messages: dict {key: prompt} kde key = "claude"/"gemini"/"gpt"
        """
        if not self.is_connected:
            raise ConnectionError("Monica není připojena")

        if self.human:
            await self.human.anti_detection_routine()

        before_snapshot = await self._snapshot_panels()
        panel_sel = self._sel["panel"]
        input_sel = self._sel["panel_input"]
        send_sel = self._sel["panel_send"]

        # Pošli zprávu do každého panelu individuálně
        for key, msg in messages.items():
            cfg = MONICA_PANELS.get(key)
            if not cfg:
                continue
            idx = cfg["panel_index"]

            # Per-panel input + send
            panel_input = self.page.locator(
                f"{panel_sel} {input_sel}").nth(idx)
            panel_send = self.page.locator(
                f"{panel_sel} {send_sel}").nth(idx)

            await panel_input.fill(msg)
            await asyncio.sleep(random.uniform(0.2, 0.5))
            await panel_send.click()
            await asyncio.sleep(0.5)

            role = cfg["role"]
            log_phase("brain_round", key,
                      f"📤 [{role}] individuální prompt ({len(msg)} znaků)")

        # Čekej na odpovědi ze všech panelů, kterým jsme poslali
        responses = await self._wait_all_responses(
            before_snapshot, expected_keys=set(messages.keys()))
        return responses

    async def _snapshot_panels(self) -> dict[str, int]:
        """Vrátí délku textu v každém panelu (pro detekci nového obsahu)."""
        return await self.page.evaluate("""() => {
            const snapshot = {};
            const panels = document.querySelectorAll('""" + self._sel["panel"] + """');
            for (let i = 0; i < Math.min(panels.length, 3); i++) {
                snapshot[i] = (panels[i].innerText || '').length;
            }
            return snapshot;
        }""")

    async def _wait_all_responses(self, before: dict,
                                    expected_keys: set | None = None) -> dict[str, str]:
        """Polluje panely, dokud všechny nemají nový obsah."""
        panel_sel = self._sel["panel"]
        target_panels = {k: v for k, v in MONICA_PANELS.items()
                         if expected_keys is None or k in expected_keys}
        responses = {}
        elapsed = 0

        while elapsed < RESPONSE_MAX_WAIT:
            await asyncio.sleep(RESPONSE_POLL_INTERVAL)
            elapsed += RESPONSE_POLL_INTERVAL

            status = await self.page.evaluate("""(panelSel) => {
                const results = {};
                const panels = document.querySelectorAll(panelSel);
                for (let i = 0; i < Math.min(panels.length, 3); i++) {
                    const title = panels[i].querySelector('[class*="title"]')
                                    ?.innerText?.trim() || '';
                    const full = panels[i].innerText || '';
                    const body = full.replace(title, '').trim();
                    results[i] = {bodyLen: body.length, body: body};
                }
                return results;
            }""", panel_sel)

            done_count = 0
            for key, cfg in target_panels.items():
                idx = str(cfg["panel_index"])
                panel_data = status.get(idx, {})
                body_len = panel_data.get("bodyLen", 0)
                before_len = before.get(int(idx), before.get(idx, 0))

                if body_len > before_len + 5:
                    body = panel_data.get("body", "")
                    lines = body.split("\n")
                    clean_lines = []
                    active = self.panel_models.get(key, cfg)
                    active_label = active.get("active_model", cfg["model_label"])
                    for line in lines:
                        stripped = line.strip()
                        if stripped and stripped != active_label:
                            clean_lines.append(stripped)
                    responses[key] = "\n".join(clean_lines)
                    done_count += 1

            if done_count >= len(target_panels):
                log_phase("brain_round", "monica",
                          f"✅ {done_count} mozků odpovědělo ({elapsed}s)")
                return responses

            log_phase("brain_round", "monica",
                      f"  ⏳ {done_count}/{len(target_panels)} panelů ({elapsed}s)")

        # Timeout — vrať co máme
        for key, cfg in target_panels.items():
            if key not in responses:
                responses[key] = f"[TIMEOUT] {cfg['model_label']} neodpověděl"
                log_error("monica", f"⏰ {cfg['model_label']} timeout po {RESPONSE_MAX_WAIT}s")

        return responses

    async def disconnect(self):
        """Uklidí vše."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.is_connected = False
        log_phase("complete", "monica", "Session ukončena")
