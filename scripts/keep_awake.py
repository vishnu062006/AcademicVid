"""
Keep the Streamlit Community Cloud app awake.

Streamlit Cloud puts an app to sleep after a period with no visitors (about 12 hours at
the time of writing). A plain HTTP ping does not count: the sleeping page answers 200 OK
and only wakes the app when someone clicks "Yes, get this app back up!". So this script
opens the app in a real (headless) browser, clicks that button if it is there, and waits
for the app to load. It is run by .github/workflows/keep-awake.yml every few hours.

Run it yourself:   pip install playwright && playwright install chromium
                   APP_URL=https://<your-app>.streamlit.app python scripts/keep_awake.py
"""
import os
import sys
import time

from playwright.sync_api import sync_playwright

WAKE_TEXT = "get this app back up"     # part of the button label on the sleep page
LOAD_TIMEOUT_MS = 60_000
WAKE_WAIT_SECONDS = 180                 # waking can take a couple of minutes ("in the oven")


def main() -> int:
    url = (os.environ.get("APP_URL") or "").strip()
    if not url.startswith("https://"):
        print("APP_URL is not set. Add it under GitHub repo Settings -> Secrets and variables "
              "-> Actions -> Variables, e.g. https://<your-app>.streamlit.app")
        return 1

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=LOAD_TIMEOUT_MS)
        page.wait_for_timeout(8_000)    # let the sleep page or the app render

        wake = page.get_by_role("button", name=WAKE_TEXT)
        if wake.count() == 0:
            print("App is awake. Visit recorded.")
            browser.close()
            return 0

        print("App was asleep. Clicking the wake-up button...")
        wake.first.click()
        deadline = time.time() + WAKE_WAIT_SECONDS
        while time.time() < deadline:
            page.wait_for_timeout(10_000)
            if page.get_by_role("button", name=WAKE_TEXT).count() == 0:
                print("Wake-up started; the app is coming back up.")
                page.wait_for_timeout(30_000)   # stay a little so the app fully boots
                browser.close()
                return 0
        print("The app is still showing the sleep page after %ds." % WAKE_WAIT_SECONDS)
        browser.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())
