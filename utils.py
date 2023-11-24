from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import datetime, timedelta

import os
import pandas as pd
import urllib.parse
import json
import requests
import os
import pickle

ESTADOS = {
    1: "En situacion normal",
    2: "Con seguimiento especial",
    3: "Con problemas",
    4: "Con alto riesgo de insolvencia",
    5: "Irrecuperable",
    6: "Irrecuperable por disposicion técnica",
}

RIESGOS = {
    1: "Situacion normal",
    2: "Riesgo bajo",
    3: "Riesgo medio",
    4: "Riesgo alto",
    5: "Irrecuperable",
    6: "Irrecuperable por disposicion tecnica",
}


def get_engine():
    load_dotenv()

    db_user = os.environ.get("DB_USER")
    db_pass = os.environ.get("DB_PASS")
    db_host = os.environ.get("DB_HOST")
    db_port = os.environ.get("DB_PORT")
    db_name = os.environ.get("DB_NAME")

    new_pass = urllib.parse.quote_plus(db_pass)
    url = f"postgresql+pg8000://{db_user}:{new_pass}@{db_host}:{db_port}/{db_name}"
    return create_engine(url, pool_size=20, max_overflow=0)


ENGINE = get_engine()


def search_cuit_cache(cuit: int):
    query = (
        "SELECT response FROM cache.api_response "
        f"WHERE cuit = {cuit} "
        "ORDER BY id DESC "
        "LIMIT 1"
    )
    df = pd.read_sql_query(query, ENGINE)

    if not df.empty:
        return df.iloc[0]["response"]
    return None


def get_api_token():
    url = "http://checkone.worldsys.com.ar/api/login"
    payload = {"email": "abergoglio@frba.utn.edu.ar", "password": "F!pzn8jHJj|5V@91"}
    response = requests.request("POST", url, data=payload)
    return response.json()["success"]["token"]


def external_api_request(cuit, token):

    url = "http://checkone.worldsys.com.ar/api/v2/checkone"

    payload = json.dumps(
        {"idtributaria": cuit, "plan": "deudores", "informePdf": False}
    )

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

    response = requests.request("POST", url, headers=headers, data=payload)

    return response.json()


def save_token(token):
    query = text("INSERT INTO cache.api_key (key) VALUES (:token)").bindparams(
        token=token
    )

    with ENGINE.connect() as connection:
        connection.execute(query)
        connection.commit()


def save_response(cuit, response):

    query = text(
        """
        INSERT INTO cache.api_response (cuit,response) VALUES (:cuit ::bigint, :response ::jsonb)
    """
    ).bindparams(cuit=cuit, response=json.dumps(response))

    with ENGINE.connect() as connection:
        connection.execute(query)
        connection.commit()


def get_cached_token():
    now = datetime.now()
    twenty_four_hours_ago = now - timedelta(hours=24)

    query = text(
        f"""
        SELECT key FROM cache.api_key
        WHERE created_date >= '{twenty_four_hours_ago}'
        ORDER BY created_date DESC
        LIMIT 1
    """
    )

    df = pd.read_sql_query(query, ENGINE)

    if not df.empty:
        return df.iloc[0]["key"]
    return None


def get_unpaid_installments(cuit):
    query = text(
        f"""
        select cuotas_impagas 
        from etl.dim_cliente dc 
        inner join etl.fact_plan fp 
        on dc.cliente_id  = fp.cliente_id
        inner join etl.dim_tiempo dt
        on dt.tiempo_id = fp.tiempo_id
        where dc.cuit_cuil={cuit}
        order by anio DESC, mes DESC, dia DESC
        LIMIT 1
    """
    )

    df = pd.read_sql_query(query, ENGINE)

    if not df.empty:
        return df.iloc[0]["cuotas_impagas"]
    return None


def analyze_json(data, cuit):
    print(data)

    dfs = {}

    # Create a DataFrame only if 'info' key exists for the given block
    if "info" in data["res"]["bloques"]["LDISASD24_MNT"]:
        dfs["LDISASD24_MNT"] = pd.DataFrame(
            data["res"]["bloques"]["LDISASD24_MNT"]["info"]
        )

    if "info" in data["res"]["bloques"]["LDISASDEU_MNT"]:
        dfs["LDISASDEU_MNT"] = pd.DataFrame(
            data["res"]["bloques"]["LDISASDEU_MNT"]["info"]
        )

    if "info" in data["res"]["bloques"]["LDISASDEX_MNT"]:
        dfs["LDISASDEX_MNT"] = pd.DataFrame(
            data["res"]["bloques"]["LDISASDEX_MNT"]["info"]
        )

    # Now concatenate only the DataFrames that have been created
    combined_df = pd.concat(dfs.values(), ignore_index=True) if dfs else pd.DataFrame()

    if not combined_df.empty:

        combined_df = combined_df[combined_df["monto"] != 0]
        combined_df = combined_df.rename(
            {"sit": "situacion", "nomEnt": "entidad", "diasAtraso": "dias_atraso"},
            axis=1,
        )
        combined_df = combined_df.drop(["codEnt", "sitDes"], axis=1)
        combined_df = combined_df.replace({"N/A": 0})
        combined_df["periodo"] = combined_df["periodo"].apply(
            lambda x: x[:4] + "-" + x[4:]
        )
        combined_df = combined_df.sort_values("periodo")
        combined_df = combined_df.fillna(value=0)
        combined_df["dias_atraso"] = combined_df["dias_atraso"].astype(int)
        combined_df["monto"] = combined_df["monto"] / 1000

        combined_df = combined_df[
            ["situacion", "monto", "entidad", "periodo", "dias_atraso"]
        ]

        nombre = data["res"]["nombre"]

        data = combined_df.to_dict(orient="records")
        situacion = int(max(combined_df["situacion"]))

    else:
        data = "El usuario no posee deudas registradas"
        situacion=1

    estado = ESTADOS[situacion]
    riesgo = RIESGOS[situacion]

    cuotas_impagas = get_unpaid_installments(cuit)

    usuario_registrado = 0 if cuotas_impagas is None else 1

    cuotas_impagas = int(cuotas_impagas) if cuotas_impagas is not None else 0

    with open('prediction_model.pkl', 'rb') as file:
        modelo_predictivo = pickle.load(file)
   
    contactar = modelo_predictivo.predict(combined_df)

    response = {
        "data": data,
        "contactar": contactar,
        "estado": estado,
        "riesgo": riesgo,
        "cuotas_impagas": cuotas_impagas,
        "usuario_registrado": usuario_registrado,
        "nombre": nombre,
        "cuit": cuit
        
    }
    return json.dumps(response)
