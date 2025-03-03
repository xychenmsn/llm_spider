import asyncio
import os
import json
from PySide6.QtCore import QObject, Signal, QThread
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

class PlaywrightController(QObject):
    coordinateAndHtmlSignal = Signal(str)
    debugSignal = Signal(str)
    errorSignal = Signal(str)
    htmlSignal = Signal(str)
    browserStartedSignal = Signal(object)
    completeHtmlSignal = Signal(str)

    def __init__(self):
        super().__init__()
        self.base_wait_time = 5000
        self.page = None
        self.browser = None
        self.context = None
        self.loop = None
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self.run)

    def start(self):
        self.thread.start()

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        # Start the browser when the thread starts
        future = asyncio.run_coroutine_threadsafe(self.start_browser(), self.loop)
        # Store the future to prevent it from being garbage collected
        self._browser_future = future
        self.loop.run_forever()

    async def start_browser(self):
        print("PlaywrightController.start_browser")
        self.debugSignal.emit("...in start_browser...")
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                device_scale_factor=1,
            )
            self.page = await self.context.new_page()
            await self.page.expose_function("sendCoordinatesAndHtml", self.send_coordinates_and_html)
            await self.page.expose_function("debugLog", lambda msg: self.debugSignal.emit(f"Browser: {msg}"))
            self.debugSignal.emit("Browser started")
            self.browserStartedSignal.emit(self.page)
            # Don't wait indefinitely - this will allow the coroutine to complete
            # await asyncio.Event().wait()
        except Exception as e:
            self.errorSignal.emit(f"Failed to start browser: {str(e)}")

    def navigate_to_url(self, url):
        if self.loop is None:
            self.errorSignal.emit("Error: Event loop not initialized")
            return
        # Emit a signal immediately to indicate navigation has started
        self.debugSignal.emit(f"Starting navigation to {url}")
        # Run the navigation in the background thread
        asyncio.run_coroutine_threadsafe(self._navigate_to_url(url), self.loop)
        # Return immediately, don't block the UI thread
        return

    async def _navigate_to_url(self, url):
        # Wait for the browser to be ready
        retry_count = 0
        max_retries = 5
        while not self.page and retry_count < max_retries:
            self.debugSignal.emit(f"Waiting for browser to be ready... (attempt {retry_count + 1}/{max_retries})")
            await asyncio.sleep(1)
            retry_count += 1
            
        if not self.page:
            self.errorSignal.emit("Error: Page not available after waiting")
            return
        
        self.debugSignal.emit(f"Navigating to {url}")
        try:
            await self.page.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Referer': url
            })
            response = await self.page.goto(url, wait_until="domcontentloaded", timeout=self.base_wait_time * 3)
            if response:
                self.debugSignal.emit(f"Response status: {response.status}")
            else:
                self.debugSignal.emit("No response received")
            await self.page.wait_for_timeout(self.base_wait_time // 5)
            await self.page.evaluate("window.scrollTo(0, 0)")
            await self.page.wait_for_timeout(self.base_wait_time // 5)
            self.debugSignal.emit("Page loaded and scrolled")
            complete_html = await self.page.content()
            self.completeHtmlSignal.emit(complete_html)
        except PlaywrightTimeoutError:
            self.errorSignal.emit(f"Timeout while loading {url}")
            self.debugSignal.emit("Continuing with partially loaded page")
        except Exception as e:
            self.errorSignal.emit(f"Error while loading {url}: {str(e)}")
            self.debugSignal.emit("Continuing with partially loaded page")

    def send_coordinates_and_html(self, data):
        print(f"send_coordinates_and_html called with: {data}")
        self.coordinateAndHtmlSignal.emit(data)

    def inject_marking_script(self):
        asyncio.run_coroutine_threadsafe(self._inject_marking_script(), self.loop)

    async def _inject_marking_script(self):
        print("PlaywrightController._inject_marking_script")
        if not self.page:
            self.debugSignal.emit("Error: Page not available")
            return
        script_path = os.path.join(os.path.dirname(__file__), 'marking_script.js')
        with open(script_path, 'r') as file:
            js_code = file.read()
        await self.page.evaluate(js_code)
        await self.page.evaluate("toggleMarkArea()")
        self.debugSignal.emit("Marking script injected and activated")

    def show_dev_tools(self):
        asyncio.run_coroutine_threadsafe(self._show_dev_tools(), self.loop)

    async def _show_dev_tools(self):
        print("PlaywrightController._show_dev_tools")
        if self.page:
            await self.page.evaluate("() => { debugger; }")
            self.debugSignal.emit("Developer tools opened")
        else:
            self.debugSignal.emit("Error: Page not available")

    def close_browser(self):
        asyncio.run_coroutine_threadsafe(self._close_browser(), self.loop)

    async def _close_browser(self):
        print("PlaywrightController._close_browser")
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        self.page = None
        self.debugSignal.emit("Browser closed")
        self.thread.quit()

    def get_marked_html(self, data_json):
        asyncio.run_coroutine_threadsafe(self._get_marked_html(data_json), self.loop)

    async def _get_marked_html(self, data_json):
        if not self.page:
            self.debugSignal.emit("Error: Page not available")
            return

        try:
            data = json.loads(data_json)
            coords = data['coordinates']
            html_fragment = data['htmlFragment']

            if html_fragment:
                self.html_frag = html_fragment
                self.htmlSignal.emit(html_fragment)
                self.debugSignal.emit("Retrieved HTML for marked area")
            else:
                self.html_frag = None
                self.debugSignal.emit("No suitable element found for the marked area")

            # Emit both coordinates and HTML fragment
            self.coordinateAndHtmlSignal.emit(json.dumps({
                'coordinates': coords,
                'htmlFragment': html_fragment
            }))
        except json.JSONDecodeError:
            self.errorSignal.emit(f"Error decoding JSON: {data_json}")
        except KeyError as e:
            self.errorSignal.emit(f"Missing key in JSON: {str(e)}")
        except Exception as e:
            self.errorSignal.emit(f"Error retrieving HTML: {str(e)}") 