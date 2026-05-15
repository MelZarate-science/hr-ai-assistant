import requests
import json

def test_query():
    url = "http://localhost:8000/ask"
    payload = {
        "query": "¿Qué antigüedad necesito para el programa de Mentoría y qué rango debo tener?",
        "history": []
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=4, ensure_ascii=False))
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    url = "http://localhost:8000/ask"
    payload = {
        "query": "¿Qué actividades de RSE hace la empresa?",
        "history": []
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=4, ensure_ascii=False))
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Connection error: {e}")
