from fastapi import FastAPI
from fastapi.responses import JSONResponse
from utils import get_debt_situation, parse_html_response

app = FastAPI()

@app.get("/get_debt/{cuit:int}")
def get_debt(cuit: int):
    try:
        html_response = get_debt_situation(cuit)
        parsed_data = parse_html_response(html_response)
        parsed_data["CUIT"] = cuit
        return parsed_data
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

# If you want to add more endpoints, add them below this line.
