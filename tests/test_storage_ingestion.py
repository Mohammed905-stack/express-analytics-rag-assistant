from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pytest
from app.store import Store, normalized
from app.ingestion import extract, split, ingest
from app.provider import ProviderError


def test_faiss_cosine_order_and_persistent_rebuild(tmp_path):
    path=tmp_path/'index.db'
    store=Store(path,3,'model-a')
    store.add('Guide','url','a',['aligned','perpendicular','opposite'],[[10,0,0],[0,2,0],[-4,0,0]])
    result=store.search([8,0,0],3)
    assert [c['text'] for c in result]==['aligned','perpendicular','opposite']
    assert np.allclose([c['score'] for c in result],[1,0,-1])
    store.close(); reopened=Store(path,3,'model-a')
    assert reopened.search([1,0,0],1)[0]['text']=='aligned'
    assert reopened.documents()[0]['chunks']==3
    reopened.close()


@pytest.mark.parametrize('vectors',[[[0,0,0]],[[1,2]],[[float('nan'),0,0]],[[float('inf'),0,0]]])
def test_invalid_vectors_rejected(vectors):
    with pytest.raises(ValueError):normalized(vectors,3)


def test_incompatible_embedding_configuration_rejected(tmp_path):
    path=tmp_path/'index.db';Store(path,3,'one').close()
    with pytest.raises(ValueError,match='different model'):Store(path,3,'two')
    with pytest.raises(ValueError):Store(path,4,'one')


def test_duplicate_ingestion_skips_embedding(store,provider):
    first=ingest(store,provider,'test.md',b'# Guide\nA useful passage.')
    before=provider.doc_calls
    second=ingest(store,provider,'renamed.md',b'# Guide\nA useful passage.')
    assert second['duplicate'] and second['document_id']==first['document_id']
    assert provider.doc_calls==before and len(store.documents())==1


def test_concurrent_duplicate_commits_remain_unique(store):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:store.add('Guide','url','same',['text'],[[1,0,0]]),range(4)))
    assert len(store.documents())==1
    assert sum(not row['duplicate'] for row in results)==1


def test_failed_embedding_leaves_no_partial_document(store,provider):
    provider.fail_documents=True
    with pytest.raises(ProviderError):ingest(store,provider,'test.md',b'A useful passage')
    assert store.documents()==[]


@pytest.mark.parametrize('filename,content',[
    ('empty.txt',b''),('binary.txt',b'a\x00b'),('bad.txt',b'\xff'),('report.pdf',b'PDF'),
    ('script.html',b'<script>nothing useful</script>'),('huge.txt',b'x'*(2*1024*1024+1)),
])
def test_invalid_documents_rejected(filename,content):
    with pytest.raises(ValueError):extract(filename,content)


def test_html_removes_navigation_and_preserves_code():
    html=b'<nav>Wrong navigation</nav><article><h1>Guide</h1><pre>x = 1\nprint(x)</pre></article><script>bad()</script>'
    text=extract('guide.html',html)
    assert 'navigation' not in text and 'bad()' not in text
    assert 'x = 1\nprint(x)' in text


def test_splitter_size_and_overlap():
    text=''.join(str(i%10) for i in range(5000))
    chunks=split(text)
    assert len(chunks)>1 and max(map(len,chunks))<=1800
    assert chunks[0][-250:]==chunks[1][:250]


def test_too_many_chunks_rejected_before_embedding(store,provider):
    with pytest.raises(ValueError,match='150'):ingest(store,provider,'long.txt',b'x'*300000)
    assert provider.doc_calls==0
