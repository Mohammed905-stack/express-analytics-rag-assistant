from dataclasses import replace
import pytest
from app.workflow import build_graph
from app.schemas import Draft
from conftest import FakeProvider


def run(store,provider,settings,question='Original question'):
    return build_graph(provider,store,settings).invoke({'question':question,'retries':0,'trace':[]},config={'recursion_limit':40})


def nodes(result):return [event['node'] for event in result['trace']]


def test_grounded_answer_uses_real_source_metadata(populated,provider,settings):
    result=run(populated,provider,settings)
    assert result['status']=='answered'
    assert result['answer']=='Controlled answer [1]'
    assert result['sources'][0]['source']=='https://example.test/guide'
    assert result['sources'][0]['chunk_id'].startswith(result['sources'][0]['document_id'])
    assert nodes(result)==['query_analysis','retrieval','document_grading','generation','grounding_check']


def test_query_rewrite_recovers_and_keeps_original_question(populated,settings):
    provider=FakeProvider(grades=(False,True))
    result=run(populated,provider,settings)
    assert result['status']=='answered' and result['retries']==1
    assert nodes(result).count('retrieval')==2
    assert 'query_rewrite' in nodes(result)
    assert all(payload['question']=='Original question' for name,payload in provider.calls)


@pytest.mark.parametrize('limit',[0,1,3])
def test_irrelevant_passages_stop_at_retry_limit(populated,settings,limit):
    provider=FakeProvider(grades=(False,))
    result=run(populated,provider,replace(settings,max_retries=limit))
    assert result['status']=='insufficient_context' and result['sources']==[]
    assert result['retries']==limit and provider.query_calls==limit+1
    assert 'generation' not in nodes(result)


def test_irrelevant_passages_are_removed_before_generation(populated,settings):
    populated.add('Other','other','digest-two',['Unhelpful passage'],[[1.,0.,0.]])
    provider=FakeProvider(grades=(lambda passage:'useful' in passage,))
    result=run(populated,provider,settings)
    draft_payload=next(payload for name,payload in provider.calls if name=='Draft')
    assert len(draft_payload['passages'])==1
    assert 'Unhelpful' not in draft_payload['passages'][0]['text']
    assert result['status']=='answered'


def test_empty_corpus_skips_all_paid_calls(store,provider,settings):
    result=run(store,provider,settings)
    assert result['status']=='insufficient_context' and result['retries']==0
    assert provider.calls==[] and provider.query_calls==0


@pytest.mark.parametrize('draft',[
    Draft(answer='Unknown [[S999]]',citation_ids=['S999'],sufficient_context=True),
    Draft(answer='Missing marker',citation_ids=['S1'],sufficient_context=True),
    Draft(answer='Mismatch [[S1]]',citation_ids=[],sufficient_context=True),
    Draft(answer='Not sufficient [[S1]]',citation_ids=['S1'],sufficient_context=False),
    Draft(answer='Extra [[S1]] [[bad]]',citation_ids=['S1'],sufficient_context=True),
    Draft(answer='Extra [[S1]] and unsupported [99]',citation_ids=['S1'],sufficient_context=True),
])
def test_invalid_citations_never_escape_to_answer(populated,settings,draft):
    result=run(populated,FakeProvider(draft=draft),settings)
    assert result['status']=='insufficient_context' and result['sources']==[]
    assert nodes(result)[-1]=='fallback'


def test_grounding_failure_withholds_answer_and_sources(populated,settings):
    result=run(populated,FakeProvider(supported=False),settings)
    assert result['status']=='insufficient_context' and result['sources']==[]
    assert 'Controlled answer' not in result['answer']


def test_optional_grounding_can_be_disabled(populated,provider,settings):
    result=run(populated,provider,replace(settings,check_grounding=False))
    assert result['status']=='answered' and 'grounding_check' not in nodes(result)


def test_each_question_gets_fresh_state(populated,provider,settings):
    graph=build_graph(provider,populated,settings)
    one=graph.invoke({'question':'one','retries':0,'trace':[]})
    two=graph.invoke({'question':'two','retries':0,'trace':[]})
    assert len(one['trace'])==len(two['trace'])==5
    assert one['question']=='one' and two['question']=='two'


def test_code_index_syntax_is_preserved(populated,settings):
    draft=Draft(answer='Read items[0]. [[S1]]',citation_ids=['S1'],sufficient_context=True)
    assert run(populated,FakeProvider(draft=draft),settings)['answer']=='Read items[0]. [1]'


def test_explicit_single_bracket_source_ids_are_normalized(populated,settings):
    draft=Draft(answer='Explanation [S1]',citation_ids=['S1'],sufficient_context=True)
    result=run(populated,FakeProvider(draft=draft),settings)
    assert result['answer']=='Explanation [1]' and result['status']=='answered'
    assert 'citation_repair' not in nodes(result)


def test_citation_format_repair_recovers_without_retrieving_again(populated,settings):
    class RepairProvider(FakeProvider):
        attempts=0
        def structured(self,instructions,payload,schema):
            if schema is Draft:
                self.attempts+=1
                if self.attempts==1:
                    return Draft(answer='Explanation [1]',citation_ids=['S1'],sufficient_context=True)
                assert payload['question']=='Original question'
                assert payload['format_correction']['previous_failure']==['inline_labels_do_not_match_citation_ids','unmapped_numeric_citations']
            return super().structured(instructions,payload,schema)
    provider=RepairProvider();result=run(populated,provider,settings)
    assert result['status']=='answered' and provider.attempts==2
    assert provider.query_calls==1 and result['retries']==0
    assert nodes(result).count('citation_repair')==1 and 'grounding_check' in nodes(result)


def test_citation_repair_stops_after_one_attempt_and_reports_real_failure(populated,settings):
    draft=Draft(answer='Explanation [1]',citation_ids=['S1'],sufficient_context=True)
    result=run(populated,FakeProvider(draft=draft),settings)
    assert result['status']=='insufficient_context' and result['sources']==[]
    assert nodes(result).count('generation')==2 and nodes(result).count('citation_repair')==1
    assert 'citation validation' in result['answer']
    assert result['trace'][-1]['reason']=='missing_or_invalid_citations'


def test_model_reported_insufficient_evidence_does_not_retry_citation_format(populated,settings):
    draft=Draft(answer='No evidence',citation_ids=[],sufficient_context=False)
    result=run(populated,FakeProvider(draft=draft),settings)
    assert 'citation_repair' not in nodes(result) and result['status']=='insufficient_context'


def test_unknown_single_bracket_source_is_not_inferred(populated,settings):
    draft=Draft(answer='Explanation [S999]',citation_ids=['S999'],sufficient_context=True)
    result=run(populated,FakeProvider(draft=draft),settings)
    assert result['status']=='insufficient_context' and result['sources']==[]


def test_known_but_unused_metadata_sources_are_not_attached(populated,settings):
    populated.add('Second guide','https://example.test/two','two',['Second useful passage'],[[1.,0.,0.]])
    populated.add('Third guide','https://example.test/three','three',['Third useful passage'],[[1.,0.,0.]])
    draft=Draft(answer='Explanation [[S2]]',citation_ids=['S1','S2','S3'],sufficient_context=True)
    result=run(populated,FakeProvider(draft=draft),settings)
    assert result['status']=='answered' and result['answer']=='Explanation [1]'
    assert len(result['sources'])==1 and result['sources'][0]['title']=='Second guide'
    event=next(e for e in result['trace'] if e['node']=='generation')
    assert event['discarded_unused_ids']==['S1','S3']
    assert 'grounding_check' in nodes(result) and 'citation_repair' not in nodes(result)


def test_unknown_unused_metadata_source_still_fails(populated,settings):
    draft=Draft(answer='Explanation [[S1]]',citation_ids=['S1','S999'],sufficient_context=True)
    result=run(populated,FakeProvider(draft=draft),settings)
    assert result['status']=='insufficient_context' and not result['sources']
    assert 'unknown_citation_ids' in next(e for e in result['trace'] if e['node']=='generation')['citation_failures']


def test_unlisted_inline_source_still_fails(populated,settings):
    populated.add('Second guide','second','second',['Second useful passage'],[[1.,0.,0.]])
    draft=Draft(answer='Explanation [[S2]]',citation_ids=['S1'],sufficient_context=True)
    assert run(populated,FakeProvider(draft=draft),settings)['status']=='insufficient_context'
