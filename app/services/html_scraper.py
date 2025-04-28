from selenium.webdriver import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from utils.logger import setup_logger
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from fake_useragent import UserAgent

SELENIUM_REMOTE_URL = os.getenv("SELENIUM_REMOTE_URL")
STATE = os.getenv("STATE")
logger = setup_logger("scraper")

async def fetch_company_details(url: str) -> dict:
    driver = None
    try:
        ua = UserAgent()
        user_agent = ua.random
        options = webdriver.ChromeOptions()
        options.add_argument(f'--user-agent={user_agent}')
        options.add_argument('--lang=en-US')
        options.add_argument("--headless=new")
        options.add_argument("--start-maximized")
        options.page_load_strategy = 'eager'
        options.add_argument("--disable-webrtc")
        options.add_argument("--disable-features=WebRtcHideLocalIpsWithMdns")
        options.add_argument("--force-webrtc-ip-handling-policy=default_public_interface_only")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-features=DnsOverHttps")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        driver = webdriver.Remote(
            command_executor=SELENIUM_REMOTE_URL,
            options=options
        )
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                                const getContext = HTMLCanvasElement.prototype.getContext;
                                HTMLCanvasElement.prototype.getContext = function(type, attrs) {
                                    const ctx = getContext.apply(this, arguments);
                                    if (type === '2d') {
                                        const originalToDataURL = this.toDataURL;
                                        this.toDataURL = function() {
                                            return "data:image/png;base64,fake_canvas_fingerprint";
                                        };
                                    }
                                    return ctx;
                                };
                                """
        })
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                            Object.defineProperty(navigator, 'webdriver', {
                              get: () => undefined
                            })
                          '''
        })
        driver.get(url)
        wait = WebDriverWait(driver, 15)
        wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "#Form1 > div:nth-child(7) > table")))
        table = driver.find_element(By.CSS_SELECTOR, "#Form1 > div:nth-child(7) > table")
        html = table.get_attribute('outerHTML')
        return await parse_html_details(html)
    except Exception as e:
        logger.error(f"Error fetching data for query '{url}': {e}")
        return []
    finally:
        if driver:
            driver.quit()
async def fetch_company_data(query: str) -> list[dict]:
    driver = None
    url = "https://corp.sec.state.ma.us/CorpWeb/CorpSearch/CorpSearch.aspx"
    try:
        ua = UserAgent()
        user_agent = ua.random
        options = webdriver.ChromeOptions()
        options.add_argument(f'--user-agent={user_agent}')
        options.add_argument('--lang=en-US')
        options.add_argument("--headless=new")
        options.add_argument("--start-maximized")
        options.page_load_strategy = 'eager'
        options.add_argument("--disable-webrtc")
        options.add_argument("--disable-features=WebRtcHideLocalIpsWithMdns")
        options.add_argument("--force-webrtc-ip-handling-policy=default_public_interface_only")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-features=DnsOverHttps")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        driver = webdriver.Remote(
            command_executor=SELENIUM_REMOTE_URL,
            options=options
        )
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                                const getContext = HTMLCanvasElement.prototype.getContext;
                                HTMLCanvasElement.prototype.getContext = function(type, attrs) {
                                    const ctx = getContext.apply(this, arguments);
                                    if (type === '2d') {
                                        const originalToDataURL = this.toDataURL;
                                        this.toDataURL = function() {
                                            return "data:image/png;base64,fake_canvas_fingerprint";
                                        };
                                    }
                                    return ctx;
                                };
                                """
        })
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                            Object.defineProperty(navigator, 'webdriver', {
                              get: () => undefined
                            })
                          '''
        })
        driver.get(url)
        input_field = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#MainContent_txtEntityName")))
        input_field.send_keys(query)
        input_field.send_keys(Keys.RETURN)
        wait = WebDriverWait(driver, 15)
        wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "#MainContent_SearchControl_grdSearchResultsEntity")))
        table = driver.find_element(By.CSS_SELECTOR, "#MainContent_SearchControl_grdSearchResultsEntity")
        html = table.get_attribute('outerHTML')
        return await parse_html_search(html)
    except Exception as e:
        logger.error(f"Error fetching data for query '{query}': {e}")
        return []
    finally:
        if driver:
            driver.quit()

async def parse_html_search(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    rows = soup.select("tbody tr")[1:-2]
    for row in rows:
        link_tag = row.find("th").find("a")
        cols = row.find_all("td")
        if len(cols) >= 2:
            if link_tag and link_tag.get("href"):
                results.append({
                    "state": STATE,
                    "id": cols[0].get_text(strip=True),
                    "name": link_tag.get_text(strip=True),
                    "url": "https://corp.sec.state.ma.us/CorpWeb/CorpSearch/" + link_tag["href"],
                })
    return results

async def parse_html_details(html: str) -> dict:
    soup = BeautifulSoup(html, 'html.parser')

    async def get_text(selector):
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None
    async def get_text_for_address(selector):
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else ""

    async def get_address(prefix):
        street = await get_text_for_address(f"#{prefix}Street")
        city = await get_text_for_address(f"#{prefix}City")
        state = await get_text_for_address(f"#{prefix}State")
        zip_code = await get_text_for_address(f"#{prefix}Zip")
        country = await get_text_for_address(f"#{prefix}Country")
        parts = [street, city, state, zip_code, country]
        return ", ".join(p.strip() for p in parts if p)

    async def get_other_managers():
        table = soup.select_one("#MainContent_tblOtherManagers")
        if not table:
            return []
        rows = table.select("tr")[3:]
        officers = []
        for row in rows:
            cols = row.find_all("td")
            th_cols = row.find("th")
            if len(cols) >= 2 and th_cols:
                if not th_cols.get_text(strip=True) or th_cols.get_text(strip=True) == "":
                    continue
                officers.append({
                    "title": th_cols.get_text(strip=True),
                    "name": cols[0].get_text(strip=True),
                    "address": cols[1].get_text(strip=True)
                })
        return officers
    async def get_managers():
        table = soup.select_one("#MainContent_tblManagers")
        if not table:
            return []
        rows = table.select("tr")[3:]  # skip header
        managers = []
        for row in rows:
            cols = row.find_all("td")
            th_cols = row.find("th")
            if len(cols) >= 2 and th_cols:
                if not th_cols.get_text(strip=True) or th_cols.get_text(strip=True) == "":
                    continue
                managers.append({
                    "title": th_cols.get_text(strip=True),
                    "name": cols[0].get_text(strip=True),
                    "address": cols[1].get_text(strip=True)
                })
        return managers

    async def get_officers():
        table = soup.select_one("#MainContent_grdOfficers")
        if not table:
            return []
        rows = table.select("tr")[1:]
        officers = []
        for row in rows:
            cols = row.find_all("td")
            th_cols = row.find("th")
            if len(cols) >= 2 and th_cols:
                if not th_cols.get_text(strip=True) or th_cols.get_text(strip=True) == "":
                    continue
                officers.append({
                    "title": th_cols.get_text(strip=True),
                    "name": cols[0].get_text(strip=True),
                    "address": cols[1].get_text(strip=True)
                })
        return officers
    return {
        "state": STATE,
        "name": await get_text("#MainContent_lblEntityName"),
        "status": "Revoked" if await get_text("#MainContent_tdInactiveDate") else "Active",
        "registration_number": (await get_text("#MainContent_lblIDNumber")).replace("Identification Number:",""),
        "date_registered": await get_text("#MainContent_lblOrganisationDate"),
        "entity_type": await get_text("#MainContent_lblEntityType"),
        "agent_name": await get_text("#MainContent_lblResidentAgentName"),
        "agent_address": await get_address("MainContent_lblResident"),
        "principal_address": await get_address("MainContent_lblPrinciple"),
        "mailing_address": await get_address("MainContent_lblOffice"),
        "officers": await get_officers(),
        "other_managers": await get_other_managers(),
        "managers": await get_managers(),
        "document_images": []
    }