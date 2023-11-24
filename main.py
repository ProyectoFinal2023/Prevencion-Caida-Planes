import pandas as pd

from utils import (
    analyze_json,
    search_cuit_cache,
    external_api_request,
    get_api_token,
    get_cached_token,
    save_response,
    save_token,
)


def lambda_handler(event, context):

    cuit = event["pathParameters"]["cuit"]

    return get_debt(cuit)


def get_debt(cuit: int):

    token = get_cached_token()
    if token is None:
        token = get_api_token()
        save_token(token)

    cached = search_cuit_cache(cuit)

    if cached is None:
        partial_response = external_api_request(cuit, token)
        save_response(cuit, partial_response)
        response = analyze_json(partial_response, cuit)

    else:
        response = analyze_json(cached, cuit)

    return response


print(get_debt(27163225382))
