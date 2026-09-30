import httpx

if __name__=='__main__':
    with httpx.Client(timeout=600,trust_env=False) as client:
        response=client.post('http://127.0.0.1:8000/ingest-corpus')
        response.raise_for_status()
        print(response.json())
