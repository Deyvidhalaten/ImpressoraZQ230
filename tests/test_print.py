import requests
import json
import sys

base_url = "http://127.0.0.1:8000/api"

def search_product():
    try:
        # Search for "ma" (common prefix)
        resp = requests.get(f"{base_url}/search", params={"q": "ma", "type": "descricao", "modo": "flv"})
        if resp.status_code == 200:
            data = resp.json()
            products = data.get("products", [])
            if products:
                print(f"Encontrado produto: {products[0]['descricao']} (Code: {products[0]['codprod']})")
                return products[0]['codprod']
    except Exception as e:
        print(f"Erro na busca: {e}")
    return None

def print_product(code):
    url = f"{base_url}/print"
    payload = {
        "codigo": code,
        "copies": 1,
        "printer_ip": "127.0.0.1",
        "modo": "flv"
    }
    try:
        print(f"Enviando POST para {url} com code={code}...")
        response = requests.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Erro no print: {e}")

code = search_product()
if code:
    print_product(code)
else:
    print("Nenhum produto encontrado para testes via API.")
    # Fallback to a hardcoded guess if search fails logic
    print("Tentando codigo hardcoded '1'...")
    print_product("1")
