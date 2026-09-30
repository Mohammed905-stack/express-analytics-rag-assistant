from dataclasses import replace
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.provider import ProviderError


@pytest.fixture
def client(settings,provider):
    with TestClient(create_app(settings=settings,provider=provider)) as client:yield client


def test_all_required_endpoints_work(client):
    uploaded=client.post('/ingest',files={'file':('guide.md',b'# Guide\nUseful technical information.')},data={'source':'https://example.test/guide'})
    assert uploaded.status_code==201
    docs=client.get('/documents').json()['documents'];assert len(docs)==1
    response=client.post('/query',json={'question':'How does it work?'})
    assert response.status_code==200
    result=response.json();assert result['status']=='answered'
    assert result['sources'][0]['source']=='https://example.test/guide'
    feedback=client.post('/feedback',json={'query_id':result['query_id'],'rating':'up','comment':'Reviewed in test'})
    assert feedback.status_code==201 and feedback.json()['status']=='saved'


@pytest.mark.parametrize('question',['','   ','x'*2001,None])
def test_invalid_queries_are_422(client,question):
    assert client.post('/query',json={'question':question}).status_code==422


def test_feedback_validation_and_unknown_query(client):
    assert client.post('/feedback',json={'query_id':'unknown','rating':'up'}).status_code==404
    assert client.post('/feedback',json={'query_id':'unknown','rating':'invalid'}).status_code==422


def test_empty_corpus_returns_insufficient_context(client,provider):
    result=client.post('/query',json={'question':'Can you answer?'}).json()
    assert result['status']=='insufficient_context' and result['sources']==[]
    assert provider.calls==[]


def test_upload_rejections(client):
    assert client.post('/ingest',files={'file':('a.pdf',b'not supported')}).status_code==400
    assert client.post('/ingest',files={'file':('a.txt',b'x'*(2*1024*1024+1))}).status_code==413
    assert client.post('/ingest',files={'file':('a.txt',b'')}).status_code==400


def test_provider_failure_returns_503_and_no_commit(client,provider):
    provider.fail_documents=True
    response=client.post('/ingest',files={'file':('a.txt',b'some content')})
    assert response.status_code==503 and client.get('/documents').json()['documents']==[]


def test_static_ui_health_and_schema(client):
    assert client.get('/').status_code==200
    assert 'Express Docs' in client.get('/').text
    for path in ('/static/app.js','/static/style.css','/docs'):assert client.get(path).status_code==200
    assert client.get('/health').json()['key_configured'] is False
    paths=client.get('/openapi.json').json()['paths']
    for route,method in [('/query','post'),('/ingest','post'),('/documents','get'),('/feedback','post')]:assert method in paths[route]


def test_packaged_corpus_ingests_and_deduplicates(client):
    first=client.post('/ingest-corpus');assert first.status_code==201
    assert len(client.get('/documents').json()['documents'])==5
    second=client.post('/ingest-corpus');assert second.status_code==201
    assert all(item['duplicate'] for item in second.json()['documents'])


def test_real_provider_without_key_is_actionable(settings):
    with TestClient(create_app(settings=settings)) as client:
        response=client.post('/ingest',files={'file':('a.txt',b'content')})
        assert response.status_code==503
        assert 'SETUP_KEY.cmd' in response.json()['detail']
