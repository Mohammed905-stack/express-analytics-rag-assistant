"""Save actual local API responses; this script does not manufacture successes."""
import json
from datetime import datetime,timezone
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parent.parent
QUESTIONS=[
    'How do I declare a JSON request body using a Pydantic model in FastAPI?',
    'How do I make a query parameter optional?',
    'How can I return a 404 error using HTTPException?',
    'What is the difference between bytes and UploadFile?',
    'What is the current weather in Mumbai?',
]


def main():
    record={'mode':'live_api','captured_at':datetime.now(timezone.utc).isoformat(),'queries':[]}
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=600,trust_env=False) as client:
        for endpoint in ('health','documents'):
            response=client.get('/'+endpoint);response.raise_for_status();record[endpoint]=response.json()
        if not record['health']['key_configured'] or not record['documents']['documents']:
            raise SystemExit('Start the app with a valid key and index the guides first.')
        for question in QUESTIONS:
            response=client.post('/query',json={'question':question})
            record['queries'].append({'question':question,'http_status':response.status_code,'response':response.json()})
            print(response.status_code,question)
    folder=ROOT/'evidence';folder.mkdir(exist_ok=True)
    filename=folder/('live-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'.json')
    filename.write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('Saved actual responses to',filename)


if __name__=='__main__':main()
