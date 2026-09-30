"""Controlled provider fixtures are test doubles, not live-model evidence."""
from dataclasses import replace
import pytest
from app.config import Settings
from app.schemas import Analysis, Grade, Draft, Grounding
from app.provider import ProviderError
from app.store import Store


class FakeProvider:
    def __init__(self, grades=(True,), draft=None, supported=True):
        self.grades=grades; self.draft=draft; self.supported=supported
        self.query_calls=0; self.doc_calls=0; self.calls=[]; self.fail_documents=False

    def embed(self,texts,*,query=False):
        if query:self.query_calls+=1
        else:
            self.doc_calls+=1
            if self.fail_documents:raise ProviderError('Controlled embedding failure')
        return [[1.,0.,0.] for _ in texts]

    def structured(self,instructions,payload,schema):
        self.calls.append((schema.__name__,payload))
        if schema is Analysis:return Analysis(search_query=f'search {len(self.calls)}',query_type='how-to')
        if schema is Grade:
            relevant=self.grades[min(max(self.query_calls-1,0),len(self.grades)-1)]
            if callable(relevant):relevant=relevant(payload['passage'])
            return Grade(relevant=relevant,reason='Controlled relevance decision')
        if schema is Draft:return self.draft or Draft(answer='Controlled answer [[S1]]',citation_ids=['S1'],sufficient_context=True)
        if schema is Grounding:return Grounding(supported=self.supported,reason='Controlled support decision')
        raise AssertionError(schema)


@pytest.fixture
def settings(tmp_path):return Settings(dimensions=3,data_dir=tmp_path)


@pytest.fixture
def store(settings):
    instance=Store(settings.data_dir/'test.sqlite3',settings.dimensions,settings.embedding_model)
    yield instance
    instance.close()


@pytest.fixture
def provider():return FakeProvider()


@pytest.fixture
def populated(store):
    store.add('Test guide','https://example.test/guide','digest-one',['A useful technical passage.'],[[1.,0.,0.]])
    return store
