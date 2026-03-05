"""
Bifrost 2.0 — Human Behavior Simulator: anti-detection pro Playwright

Monica-specifické lidské chování:
- Bezier křivky pohybu myši (ne rovné čáry)
- Náhodné scrollování v panelech
- Otevření/zavření model dropdownu bez změny
- Hover nad UI elementy
- Micro-pauzy a překlepy při psaní
- Idle čtení odpovědí
"""
import asyncio
import random
import math
from playwright.async_api import Page
from ..config import MONICA_SELECTORS


class HumanBehavior:
    """Simuluje lidské chování na Monica.im multi-chat."""

    def __init__(self, page: Page):
        self.page = page
        self._sel = MONICA_SELECTORS
        self.min_delay = 0.5
        self.max_delay = 3.0
        self._last_mouse_x = 400
        self._last_mouse_y = 300

    # ── Pohyby myši (Bezier křivky) ──────────────────────────

    async def _bezier_move(self, target_x: int, target_y: int, steps: int = 0):
        """Pohyb myší po Bezier křivce — ne rovná čára."""
        sx, sy = self._last_mouse_x, self._last_mouse_y
        if steps == 0:
            dist = math.hypot(target_x - sx, target_y - sy)
            steps = max(8, int(dist / 15))

        # 2 kontrolní body pro kubickou Bezier
        cp1x = sx + random.randint(-80, 80)
        cp1y = sy + random.randint(-60, 60)
        cp2x = target_x + random.randint(-80, 80)
        cp2y = target_y + random.randint(-60, 60)

        for i in range(1, steps + 1):
            t = i / steps
            inv = 1 - t
            # Kubická Bezier: B(t) = (1-t)³P0 + 3(1-t)²tP1 + 3(1-t)t²P2 + t³P3
            x = inv**3 * sx + 3 * inv**2 * t * cp1x + 3 * inv * t**2 * cp2x + t**3 * target_x
            y = inv**3 * sy + 3 * inv**2 * t * cp1y + 3 * inv * t**2 * cp2y + t**3 * target_y
            await self.page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.005, 0.025))

        self._last_mouse_x = target_x
        self._last_mouse_y = target_y

    async def _mouse_jitter(self):
        """Drobný třes myší — člověk nikdy nedrží kurzor nehybně."""
        for _ in range(random.randint(2, 5)):
            dx = random.randint(-3, 3)
            dy = random.randint(-3, 3)
            nx = max(0, self._last_mouse_x + dx)
            ny = max(0, self._last_mouse_y + dy)
            await self.page.mouse.move(nx, ny)
            self._last_mouse_x, self._last_mouse_y = nx, ny
            await asyncio.sleep(random.uniform(0.05, 0.15))

    async def random_mouse_wander(self):
        """Myš se přesune na náhodné místo na stránce."""
        vp = self.page.viewport_size or {"width": 1280, "height": 720}
        tx = random.randint(50, vp["width"] - 50)
        ty = random.randint(50, vp["height"] - 50)
        await self._bezier_move(tx, ty)
        if random.random() < 0.3:
            await self._mouse_jitter()

    # ── Scrollování ──────────────────────────────────────────

    async def random_delay(self, min_sec: float = None, max_sec: float = None):
        """Čekej náhodnou dobu."""
        min_sec = min_sec or self.min_delay
        max_sec = max_sec or self.max_delay
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    async def scroll_around(self, times: int = 1):
        """Scrolluj náhodně nahoru/dolů."""
        for _ in range(times):
            direction = random.choice([-1, 1])
            distance = random.randint(80, 350)
            await self.page.evaluate(f"window.scrollBy(0, {direction * distance})")
            await self.random_delay(0.3, 1.0)

    async def scroll_panel(self):
        """Scrolluj uvnitř náhodného panelu (čtení odpovědi)."""
        try:
            panels = self.page.locator(self._sel["panel"])
            count = await panels.count()
            if count == 0:
                return
            idx = random.randint(0, min(count, 3) - 1)
            panel = panels.nth(idx)
            box = await panel.bounding_box()
            if not box:
                return
            # Přesuň myš do panelu
            cx = box["x"] + box["width"] / 2 + random.randint(-20, 20)
            cy = box["y"] + box["height"] / 2 + random.randint(-20, 20)
            await self._bezier_move(int(cx), int(cy))
            # Scrolluj kolečkem
            delta = random.choice([-120, -80, 80, 120, 200])
            await self.page.mouse.wheel(0, delta)
            await self.random_delay(0.5, 1.5)
            # Občas zpátky
            if random.random() < 0.4:
                await self.page.mouse.wheel(0, -delta // 2)
                await self.random_delay(0.3, 0.8)
        except Exception:
            pass

    # ── Monica-specifické interakce ──────────────────────────

    async def peek_model_dropdown(self):
        """Otevři dropdown modelů v náhodném panelu, podívej se, zavři."""
        try:
            panels = self.page.locator(
                f"{self._sel['panel']} {self._sel['panel_title']}")
            count = await panels.count()
            if count == 0:
                return
            idx = random.randint(0, min(count, 3) - 1)
            title = panels.nth(idx)
            box = await title.bounding_box()
            if not box:
                return

            # Přesuň myš k titulku a klikni
            await self._bezier_move(
                int(box["x"] + box["width"] / 2),
                int(box["y"] + box["height"] / 2))
            await self.random_delay(0.2, 0.6)
            await title.click()
            await self.random_delay(1.0, 2.5)

            # Hover nad pár modely v dropdownu (bez kliknutí)
            items = self.page.locator(self._sel["model_dropdown"])
            item_count = await items.count()
            if item_count > 0:
                for _ in range(random.randint(1, 3)):
                    hover_idx = random.randint(0, min(item_count, 8) - 1)
                    try:
                        item_box = await items.nth(hover_idx).bounding_box()
                        if item_box:
                            await self._bezier_move(
                                int(item_box["x"] + item_box["width"] / 2),
                                int(item_box["y"] + item_box["height"] / 2))
                            await self.random_delay(0.3, 0.8)
                    except Exception:
                        break

            # Zavři dropdown — Escape nebo klik mimo
            if random.random() < 0.5:
                await self.page.keyboard.press("Escape")
            else:
                await self.page.mouse.click(50, 50)
            await self.random_delay(0.3, 0.8)
        except Exception:
            pass

    async def hover_ui_elements(self):
        """Najeď myší na náhodné UI elementy (tlačítka, ikony)."""
        try:
            selectors = [
                self._sel["layout_icons"],
                f"{self._sel['panel']} {self._sel['panel_title']}",
                "button", "svg[class*='icon']",
            ]
            sel = random.choice(selectors)
            elements = self.page.locator(sel)
            count = await elements.count()
            if count == 0:
                return
            idx = random.randint(0, min(count, 6) - 1)
            box = await elements.nth(idx).bounding_box()
            if box:
                await self._bezier_move(
                    int(box["x"] + box["width"] / 2),
                    int(box["y"] + box["height"] / 2))
                await self.random_delay(0.2, 0.6)
        except Exception:
            pass

    # ── Psaní ────────────────────────────────────────────────

    async def type_slowly(self, selector: str, text: str, typo_chance: float = 0.03):
        """Piš text pomalu s občasnými překlepy."""
        await self.page.click(selector)
        await self.random_delay(0.3, 0.8)

        for char in text:
            if random.random() < typo_chance:
                typo_char = random.choice("abcdefghijklmnopqrstuvwxyz")
                await self.page.type(selector, typo_char)
                await self.random_delay(0.08, 0.25)
                await self.page.press(selector, "Backspace")
                await self.random_delay(0.08, 0.2)

            await self.page.type(selector, char, delay=random.randint(40, 180))

            # Občas pauza uprostřed psaní (přemýšlení)
            if random.random() < 0.02:
                await self.random_delay(0.8, 2.5)

        await self.random_delay(0.3, 0.8)

    # ── Idle & čtení ─────────────────────────────────────────

    async def idle_like_human(self, seconds: float = 2.0):
        """Simuluj čtení odpovědi — scroll v panelu, hover, pauzy."""
        end = asyncio.get_event_loop().time() + seconds + random.uniform(-0.5, 1.0)
        while asyncio.get_event_loop().time() < end:
            action = random.choice([
                self.scroll_panel,
                self.hover_ui_elements,
                self._mouse_jitter,
                lambda: self.random_delay(0.5, 1.5),
            ])
            try:
                await action()
            except Exception:
                pass
            await asyncio.sleep(random.uniform(0.2, 0.6))

    async def think_like_human(self):
        """Pauza jako bys přemýšlel nad odpovědí."""
        if random.random() < 0.4:
            await self.random_mouse_wander()
            await self.random_delay(1.5, 4.0)

    # ── Hlavní anti-detection rutina ─────────────────────────

    async def anti_detection_routine(self):
        """Celá rutina anti-detection před odesláním zprávy."""
        # 60% šance že provedeme nějakou akci
        if random.random() < 0.6:
            actions = [
                (0.25, self.scroll_panel),
                (0.20, self.random_mouse_wander),
                (0.20, self.hover_ui_elements),
                (0.15, self.peek_model_dropdown),
                (0.10, self._mouse_jitter),
                (0.10, lambda: self.scroll_around(1)),
            ]
            # Vyber 1-2 akce podle vah
            weights = [w for w, _ in actions]
            fns = [fn for _, fn in actions]
            chosen = random.choices(fns, weights=weights,
                                     k=random.randint(1, 2))
            for fn in chosen:
                try:
                    await fn()
                except Exception:
                    pass

        await self.random_delay(0.2, 0.6)
