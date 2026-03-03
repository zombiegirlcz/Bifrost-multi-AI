"""
Bifrost 2.0 — Human Behavior Simulator: anti-detection pro Playwright

Simuluje lidské chování:
- Náhodné scrollování
- Náhodné hovery
- Zpoždění mezi akcemi
- Klikání na náhodná místa
- Otevírání/zavírání panelů
- Čekání v neočekávaných chvílích
"""
import asyncio
import random
from typing import Optional
from playwright.async_api import Page


class HumanBehavior:
    """Simuluje lidské chování na webových stránkách."""

    def __init__(self, page: Page):
        self.page = page
        self.min_delay = 0.5
        self.max_delay = 3.0

    async def random_delay(self, min_sec: float = None, max_sec: float = None):
        """Čekej náhodnou dobu (aby to nevypadalo na bot)."""
        min_sec = min_sec or self.min_delay
        max_sec = max_sec or self.max_delay
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def scroll_around(self, times: int = 1):
        """Scrolluj náhodně nahoru/dolů."""
        for _ in range(times):
            direction = random.choice([-1, 1])  # Nahoru nebo dolů
            distance = random.randint(100, 400)
            await self.page.evaluate(f"window.scrollBy(0, {direction * distance})")
            await self.random_delay(0.3, 1.0)

    async def random_hover(self):
        """Najeď myší na náhodný element."""
        try:
            # Najdi random element na stránce
            elements = await self.page.query_selector_all("button, a, div[role='button']")
            if elements:
                elem = random.choice(elements[:5])  # Z prvních 5 elementů
                await elem.hover()
                await self.random_delay(0.2, 0.8)
        except:
            pass

    async def random_click_empty(self):
        """Klikni na prázdné místo (třeba background)."""
        try:
            x = random.randint(100, 1000)
            y = random.randint(100, 500)
            await self.page.click(f"body")  # Klikni někam do stránky
            await self.random_delay(0.3, 1.0)
        except:
            pass

    async def type_slowly(self, selector: str, text: str, typo_chance: float = 0.05):
        """Piš text pomalu, někdy udělej překlep (jako člověk)."""
        await self.page.click(selector)
        await self.random_delay(0.3, 0.8)

        for char in text:
            # Občas udělej překlep a oprav ho
            if random.random() < typo_chance:
                typo_char = random.choice("abcdefghijklmnopqrstuvwxyz")
                await self.page.type(selector, typo_char)
                await self.random_delay(0.1, 0.3)
                await self.page.press(selector, "Backspace")
                await self.random_delay(0.1, 0.2)

            await self.page.type(selector, char, delay=random.randint(50, 200))

        await self.random_delay(0.3, 0.8)

    async def open_close_panel(self):
        """Otevři a zavři boční panel (pokud existuje)."""
        try:
            # Hledej tlačítko na otevření panelu
            panel_button = await self.page.query_selector(
                "button[aria-label*='panel'], button[aria-label*='sidebar'], button[aria-label*='menu']"
            )

            if panel_button:
                await panel_button.click()
                await self.random_delay(1.0, 2.0)

                # Zavři ho znovu
                await panel_button.click()
                await self.random_delay(0.5, 1.5)
        except:
            pass

    async def random_model_switch(self):
        """Klikni na výběr modelu (ChatGPT 4, etc)."""
        try:
            model_selector = await self.page.query_selector(
                "button[aria-label*='model'], div[role='combobox']"
            )
            if model_selector:
                await model_selector.click()
                await self.random_delay(0.5, 1.5)

                # Vyber random model z seznamu
                options = await self.page.query_selector_all("div[role='option']")
                if options:
                    chosen = random.choice(options[:3])
                    await chosen.click()
                    await self.random_delay(0.3, 1.0)
        except:
            pass

    async def idle_like_human(self, seconds: float = 2.0):
        """Čekej jako by jsi čti odpověď (ne jako bot co vzorkovacího)."""
        # Občas scrolluj, hoveri, čekej
        actions = [
            self.scroll_around(1),
            self.random_hover(),
            self.random_delay(seconds - 1, seconds + 1),
        ]

        for _ in range(random.randint(1, 3)):
            action = random.choice(actions)
            try:
                await action
            except:
                pass

    async def anti_detection_routine(self):
        """Celá rutina anti-detection před odesláním zprávy."""
        # 50% šance že něco uděláš
        if random.random() > 0.5:
            actions = [
                lambda: self.scroll_around(1),
                lambda: self.random_hover(),
                lambda: self.open_close_panel(),
                lambda: self.random_click_empty(),
            ]
            action_func = random.choice(actions)
            try:
                await action_func()
            except:
                pass

        await self.random_delay(0.3, 0.8)

    async def think_like_human(self):
        """Čekej jako by sis dumal nad odpovědí."""
        # 40% šance že budeš delší dobu nečinný
        if random.random() > 0.6:
            await self.random_delay(1.5, 4.0)
