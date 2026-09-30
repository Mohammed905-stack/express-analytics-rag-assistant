import hashlib
import json
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .config import ROOT, Settings
from .provider import GeminiProvider, ProviderError
from .schemas import QueryRequest, QueryResponse, FeedbackRequest
from .store import Store
from .ingestion import MAX_BYTES, ingest
from .workflow import build_graph


def create_app(settings=None, provider=None, store=None):
    settings = settings or Settings.from_env()
    provider = provider or GeminiProvider(settings)
    store = store or Store(settings.data_dir/'assistant.sqlite3',settings.dimensions,settings.embedding_model)
    graph = build_graph(provider,store,settings)

    @asynccontextmanager
    async def lifespan(app):
        yield
        store.close()
        if hasattr(provider,'close'):
            provider.close()

    app = FastAPI(title='Express Analytics Technical Documentation Assistant',version='1.0.0',lifespan=lifespan)
    app.state.store = store
    app.state.graph = graph
    app.mount('/static',StaticFiles(directory=ROOT/'app/static'),name='static')

    @app.exception_handler(ProviderError)
    async def provider_error(request, exc):
        return JSONResponse(status_code=503,content={'detail':str(exc)})

    @app.get('/',include_in_schema=False)
    def home():
        return FileResponse(ROOT/'app/static/index.html')

    @app.get('/health')
    def health():
        return {'status':'ok','key_configured':bool(settings.api_key),'documents':len(store.documents()),
                'model':settings.model,'embedding_model':settings.embedding_model}

    @app.post('/query',response_model=QueryResponse)
    def query(body: QueryRequest):
        state = graph.invoke({'question':body.question,'retries':0,'trace':[]},config={'recursion_limit':40})
        response = QueryResponse(query_id=uuid4().hex,answer=state['answer'],status=state['status'],
            sources=state['sources'],retries=state['retries'],query_type=state['query_type'],trace=state['trace'])
        store.save_query(body.question,response.model_dump())
        return response

    @app.post('/ingest',status_code=201)
    def upload(file: UploadFile=File(...),source: str | None=Form(default=None,max_length=1000)):
        content = file.file.read(MAX_BYTES+1)
        if len(content)>MAX_BYTES:
            raise HTTPException(413,'Document exceeds the 2 MiB upload limit')
        try:
            return ingest(store,provider,file.filename or 'document.txt',content,source)
        except ValueError as exc:
            raise HTTPException(400,str(exc)) from exc

    @app.get('/documents')
    def documents():
        return {'documents':store.documents()}

    @app.post('/feedback',status_code=201)
    def feedback(body: FeedbackRequest):
        try:
            feedback_id=store.feedback(body.query_id,body.rating,body.comment)
        except KeyError as exc:
            raise HTTPException(404,'Unknown query_id; submit a question first') from exc
        return {'feedback_id':feedback_id,'status':'saved'}

    @app.post('/ingest-corpus',status_code=201)
    def corpus():
        try:
            items=json.loads((ROOT/'corpus/manifest.json').read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError) as exc:
            raise HTTPException(409,'Starter corpus is missing or invalid; run scripts/fetch_corpus.py') from exc
        results=[]
        for item in items:
            path=ROOT/'corpus'/Path(item['file']).name
            if not path.is_file():
                raise HTTPException(409,'A starter guide is missing; refresh the corpus')
            content=path.read_bytes()
            if hashlib.sha256(content).hexdigest()!=item['sha256']:
                raise HTTPException(409,'Starter corpus checksum changed; refresh the corpus manifest')
            try:
                result=ingest(store,provider,path.name,content,item['source'])
            except ValueError as exc:
                raise HTTPException(400,str(exc)) from exc
            results.append({'file':path.name,**result})
        return {'documents':results}

    return app


app=create_app()
