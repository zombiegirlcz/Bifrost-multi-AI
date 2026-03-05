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
from .utils.logger import log_phase, log_error
from .utils.rate_limiter import RateLimiter
from .utils.human_behavior import HumanBehavior
from .config import (
    BROWSER_PATH, MONICA_URL, MONICA_COOKIES, MONICA_PANELS,
    MONICA_SELECTORS, RESPONSE_POLL_INTERVAL, RESPONSE_MAX_WAIT,
    RESPONSE_STABLE_POLLS,
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
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
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

        # Finální dismiss — zavři cokoliv co zbylo
        await self._dismiss_overlays()

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

    async def _dismiss_overlays(self):
        """Zavře premium upsell overlay / drawer, pokud je viditelný."""
        overlay_selectors = [
            ".drawer-mask--od0gH",
            ".feature-title-box--E_N7v",
            ".ant-modal-close",
            "[class*='close'][class*='icon']",
        ]
        for sel in overlay_selectors:
            try:
                el = self.page.locator(sel).first
                if await el.is_visible(timeout=500):
                    await el.click(force=True, timeout=2000)
                    await asyncio.sleep(0.5)
                    log_phase("worker_build", "monica",
                              f"  🔒 Zavřen overlay: {sel}")
            except Exception:
                pass
        # Zkus Escape jako univerzální dismiss
        try:
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.3)
        except Exception:
            pass

    async def _configure_panels(self):
        """Nastaví správný model v každém panelu (s fallbackem na free tier).

        Nový (PC) layout Monica má někdy jiné CSS. Proto:
        - otevřeme panel klikem na title
        - hledáme položku v několika menu scopech a fallbackneme na textové vyhledání
        """
        for key, panel_cfg in MONICA_PANELS.items():
            i = panel_cfg["panel_index"]
            label = panel_cfg["model_label"]
            fallback = panel_cfg.get("fallback_label", label)
            variants = [label] + panel_cfg.get("label_variants", []) + [fallback]
            # deduplikace při zachování pořadí
            seen = set()
            variants = [v for v in variants if not (v in seen or seen.add(v))]

            # Klikni na title panelu → otevře dropdown
            panel_title = self.page.locator(
                f"{self._sel['panel']} {self._sel['panel_title']}").nth(i)
            await panel_title.click()
            await asyncio.sleep(1.5)

            async def _click_option(name: str) -> bool:
                """Pokuste se kliknout na položku dropdownu podle textu."""
                # Primární selektor (legacy mobilní CSS)
                try:
                    item = self.page.locator(self._sel["model_dropdown"]).filter(has_text=name).first
                    await item.click(timeout=2500)
                    return True
                except Exception:
                    pass

                # Generické menu položky (PC layout)
                generic_scopes = ["[role='menuitem']", "[role='option']", ".ant-dropdown-menu div", ".dropdown-menu-item", "li"]
                for scope in generic_scopes:
                    try:
                        cand = self.page.locator(scope).filter(has_text=name).first
                        await cand.click(timeout=2000)
                        return True
                    except Exception:
                        continue

                # Poslední pokus: libovolný text na stránce (může být rizikové, ale zachrání fallback model)
                try:
                    await self.page.get_by_text(name, exact=False).first.click(timeout=2000)
                    return True
                except Exception:
                    return False

            # Zkus všechny varianty postupně, první úspěšná vítězí
            selected = variants[0] if variants else label
            for name in variants:
                if await _click_option(name):
                    selected = name
                    break
                log_phase("worker_build", "monica",
                          f"  ⚠️ {name} nedostupný, zkouším další variantu")
                await self._dismiss_overlays()
                try:
                    await panel_title.click()
                    await asyncio.sleep(1.0)
                except Exception:
                    pass
            else:
                log_phase("worker_build", "monica",
                          f"  ⚠️ Nepodařilo se přepnout model pro panel {i}, nechávám výchozí")

            await asyncio.sleep(1.2)
            await self._dismiss_overlays()

            self.panel_models[key] = {**panel_cfg, "active_model": selected}
            log_phase("worker_build", "monica",
                      f"  🧠 Panel {i}: {selected} ({panel_cfg['role']})")

    async def send_to_all(self, message: str) -> dict[str, str]:
        """Pošle zprávu globálním inputem → čte odpovědi ze všech 3 panelů."""
        if not self.is_connected:
            raise ConnectionError("Monica není připojena")

        if self.human:
            await self.human.anti_detection_routine()

        # Zavři případné overlays
        await self._dismiss_overlays()

        # Snapshot panelů PŘED odesláním (pro detekci nových odpovědí)
        before_snapshot = await self._snapshot_panels()

        # Vyplň globální input a odešli (truncate if too long for textarea)
        MAX_TEXTAREA = 30000
        if len(message) > MAX_TEXTAREA:
            message = message[:MAX_TEXTAREA] + "\n...[zkráceno]"
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

        # Zavři případné premium overlays PŘED interakcí
        await self._dismiss_overlays()

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

            # Dismiss overlay před každým panelem
            await self._dismiss_overlays()

            # Per-panel input — scope to specific panel element
            panel_el = self.page.locator(panel_sel).nth(idx)
            panel_input = panel_el.locator(input_sel)

            try:
                await panel_input.scroll_into_view_if_needed(timeout=5000)
            except Exception:
                pass  # element may already be visible

            await panel_input.fill(msg)
            await asyncio.sleep(random.uniform(0.3, 0.8))
            # Submit via Enter on input (more reliable than clicking SVG)
            await panel_input.press("Enter")
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
        """Polluje panely dokud všechny nevrátí stabilní (dokončenou) odpověď.

        Dvě podmínky pro 'hotovo' na panelu:
        1. body_len vzrostl o >5 znaků oproti snímku před odesláním
        2. body_len se nezměnil po RESPONSE_STABLE_POLLS po sobě jdoucích pollech
           (= AI přestala generovat)

        Per-panel early timeout: pokud panel zůstane na 0ch 90s+ zatímco
        alespoň jeden jiný panel je hotový, označí se jako timeout.
        """
        PER_PANEL_DEAD_TIMEOUT = 90  # sekundy — 0ch panel se vzdá po tomto čase

        panel_sel = self._sel["panel"]
        target_panels = {k: v for k, v in MONICA_PANELS.items()
                         if expected_keys is None or k in expected_keys}
        responses = {}
        elapsed = 0

        # Stabilizační stav per panel
        last_lengths: dict[str, int] = {}   # klíč → délka při posledním pollu
        stable_counts: dict[str, int] = {}  # klíč → počet pollů se stejnou délkou
        zero_since: dict[str, float] = {}   # klíč → kdy začal být na 0ch

        while elapsed < RESPONSE_MAX_WAIT:
            await asyncio.sleep(RESPONSE_POLL_INTERVAL)
            elapsed += RESPONSE_POLL_INTERVAL

            # Každých 30s zkontroluj a zavři premium overlays
            if int(elapsed) % 30 == 0:
                await self._dismiss_overlays()

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
            has_any_response = len(responses) > 0

            for key, cfg in target_panels.items():
                if key in responses:
                    done_count += 1
                    continue

                idx = str(cfg["panel_index"])
                panel_data = status.get(idx, {})
                body_len = panel_data.get("bodyLen", 0)
                before_len = before.get(int(idx), before.get(idx, 0))

                # Čekáme na >5 nových znaků (streaming začal)
                if body_len <= before_len + 5:
                    stable_counts[key] = 0
                    last_lengths[key] = body_len

                    # Per-panel early timeout: 0ch příliš dlouho + jiné panely hotové
                    if key not in zero_since:
                        zero_since[key] = elapsed
                    dead_time = elapsed - zero_since[key]
                    if dead_time >= PER_PANEL_DEAD_TIMEOUT and has_any_response:
                        model = cfg.get("model_label", key)
                        responses[key] = f"[TIMEOUT] {model} neodpověděl ({dead_time:.0f}s, overlay?)"
                        done_count += 1
                        log_error("monica",
                                  f"⏰ {model} early timeout — 0ch po {dead_time:.0f}s (overlay blokuje?)")
                    continue

                # Panel začal generovat — reset zero timer
                zero_since.pop(key, None)

                # Zjisti zda délka ustálila (generování skončilo)
                prev_len = last_lengths.get(key, -1)
                if body_len == prev_len:
                    stable_counts[key] = stable_counts.get(key, 0) + 1
                else:
                    stable_counts[key] = 0
                last_lengths[key] = body_len

                if stable_counts.get(key, 0) >= RESPONSE_STABLE_POLLS:
                    body = panel_data.get("body", "")
                    active = self.panel_models.get(key, cfg)
                    active_label = active.get("active_model", cfg["model_label"])
                    clean_lines = [
                        l.strip() for l in body.split("\n")
                        if l.strip() and l.strip() != active_label
                    ]
                    responses[key] = "\n".join(clean_lines)
                    done_count += 1
                    log_phase("brain_round", key,
                              f"  ✅ {active_label}: {body_len} znaků ({elapsed}s)")

            if done_count >= len(target_panels):
                log_phase("brain_round", "monica",
                          f"✅ {done_count} mozků odpovědělo ({elapsed}s)")
                return responses

            # Loguj průběh každých 15s
            if int(elapsed) % 15 == 0:
                still_waiting = [k for k in target_panels if k not in responses]
                lengths_str = " | ".join(
                    f"{k}:{last_lengths.get(k, 0)}ch" for k in still_waiting)
                log_phase("brain_round", "monica",
                          f"  ⏳ {done_count}/{len(target_panels)} hotovo ({elapsed}s) — {lengths_str}")

        # Timeout — vrať co máme (i nekompletní)
        for key, cfg in target_panels.items():
            if key not in responses:
                # Vrať co bylo k dispozici i když není stabilní
                idx = str(cfg["panel_index"])
                panel_data = status.get(idx, {})
                body = panel_data.get("body", "")
                if body and len(body) > before.get(int(idx), 0) + 5:
                    responses[key] = body  # Aspoň co máme
                    log_error("monica",
                              f"⏰ {cfg['model_label']} timeout (nestabilní, {len(body)} znaků)")
                else:
                    responses[key] = f"[TIMEOUT] {cfg['model_label']} neodpověděl"
                    log_error("monica",
                              f"⏰ {cfg['model_label']} timeout po {RESPONSE_MAX_WAIT}s — žádný obsah")

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
