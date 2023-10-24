from playwright.sync_api import sync_playwright
from playwright_recaptcha import recaptchav2
from playwright_stealth import stealth_sync
import requests
import http.cookiejar

import pandas as pd
from lxml import html

ESTADOS = {
    1: "En situación normal",
    2: "Con seguimiento especial",
    3: "Con problemas",
    4: "Con alto riesgo de insolvencia",
    5: "Irrecuperable",
    6: "Irrecuperable por disposición técnica",
}

RIESGOS = {
    1: "Situación normal",
    2: "Riesgo bajo",
    3: "Riesgo medio",
    4: "Riesgo alto",
    5: "Irrecuperable",
    6: "Irrecuperable por disposición técnica",
}


def get_debt_situation(cuit: int):

    try:

        with sync_playwright() as playwright:
            browser = playwright.firefox.launch()
            page = browser.new_page()
            stealth_sync(page)
            page.goto("https://www.bcra.gob.ar/BCRAyVos/Situacion_Crediticia.asp")

            with recaptchav2.SyncSolver(page) as solver:
                token = solver.solve_recaptcha(wait=True)

            print(222222222222)
            
            cookie_jar = http.cookiejar.CookieJar()
            for cookie in page.context.cookies():
                cookie.pop("httpOnly")
                cookie.pop("sameSite")
                cookie["version"] = 0
                cookie["port"] = None
                cookie["port_specified"] = False
                cookie["domain_specified"] = False
                cookie["domain_initial_dot"] = False
                cookie["path_specified"] = True
                cookie["discard"] = False

                cookie["comment"] = None
                cookie["comment_url"] = None
                cookie["rest"] = {}

                cookie_jar.set_cookie(http.cookiejar.Cookie(**cookie))

            s = requests.session()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.3",
                "Referer": "https://www.bcra.gob.ar/BCRAyVos/Situacion_Crediticia.asp",
            }

            # Make an initial GET request
            s.get(
                "https://www.bcra.gob.ar/BCRAyVos/Situacion_Crediticia.asp", headers=headers
            )

            response = s.post(
                url="https://www.bcra.gob.ar/BCRAyVos/Situacion_Crediticia.asp",
                data={"g-recaptcha-response": token, "CUIT": str(cuit), "Action": "Go"},
                headers=headers,
                cookies=cookie_jar,
            )

            page.close()
            playwright.stop()

            return response.text
    except:
        return None

def clean_accented_chars(text):
    """Replace accented characters with unaccented counterparts."""
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "Á": "A",
        "É": "E",
        "Í": "I",
        "Ó": "O",
        "Ú": "U",
        # Add more replacements if needed
    }

    for char, replacement in replacements.items():
        text = text.replace(char, replacement)

    return text


def parse_html_response(response):

    try:
        # Parse the HTML using lxml
        tree = html.fromstring(response)

        # Use XPath to extract data
        rows = tree.xpath("//table//tr")

        data = []
        for row in rows:
            cols = [td.text_content().strip() for td in row.xpath(".//td")]

            # If the first element of a row is empty or contains only whitespace, break
            if not cols or not cols[0]:
                break

            # Check if row has meaningful data (in this case, more than 2 non-empty cells)
            if len(cols) > 2:
                data.append(cols)

        # Ensure all rows match header length
        header_length = len(data[0])
        for i in range(1, len(data)):
            while len(data[i]) < header_length:
                data[i].append(None)

        # Create a Pandas DataFrame
        df = pd.DataFrame(data[1:], columns=data[0])
        df.columns = [x[:-1] for x in df.columns]
        df.columns = [clean_accented_chars(col) for col in df.columns]

        data = df.to_json(orient="records")
        situacion = int(max(df["Situacion"]))
        print(situacion)
    except Exception as e:
        print(e)
        data = "La persona no posee deudas registradas"
        situacion = 1

    contactar = "SI" if situacion > 1 else "NO"
    estado = ESTADOS[situacion]
    riesgo = RIESGOS[situacion]

    return {"data": data, "contactar": contactar, "estado": estado, "riesgo": riesgo}

