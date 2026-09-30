import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from app.config import Settings
from app.provider import GeminiProvider, ProviderError
from app.schemas import Grade


def test_sdk_structured_output_configuration_and_validation():
    provider=GeminiProvider(Settings(api_key='test-only-key'))
    client=Mock();provider._client=client
    client.models.generate_content.return_value=SimpleNamespace(text='{"relevant":true,"reason":"Supported"}')
    assert provider.structured('instructions',{'question':'q'},Grade).relevant
    call=client.models.generate_content.call_args.kwargs
    assert call['model']==provider.settings.model
    assert call['config'].response_schema is Grade
    assert call['config'].response_mime_type=='application/json'


def test_embedding_sdk_uses_distinct_query_and_document_tasks():
    provider=GeminiProvider(Settings(api_key='test-only-key',dimensions=3))
    client=Mock();provider._client=client
    client.models.embed_content.return_value=SimpleNamespace(embeddings=[SimpleNamespace(values=[1,0,0])])
    provider.embed(['document']);provider.embed(['query'],query=True)
    configs=[call.kwargs['config'] for call in client.models.embed_content.call_args_list]
    assert configs[0].task_type=='RETRIEVAL_DOCUMENT'
    assert configs[1].task_type=='RETRIEVAL_QUERY'
    assert all(config.output_dimensionality==3 for config in configs)


def test_sdk_error_never_exposes_secret_or_prompt():
    provider=GeminiProvider(Settings(api_key='private-test-value'))
    client=Mock();provider._client=client
    client.models.generate_content.side_effect=RuntimeError('private-test-value private document')
    with pytest.raises(ProviderError) as result:provider.structured('instruction',{},Grade)
    assert 'private-test-value' not in str(result.value)
    assert 'private document' not in str(result.value)


def test_invalid_sdk_json_is_safe_error():
    provider=GeminiProvider(Settings(api_key='test-only-key'))
    client=Mock();provider._client=client
    client.models.generate_content.return_value=SimpleNamespace(text='not json')
    with pytest.raises(ProviderError,match='structured'):provider.structured('i',{},Grade)


def test_embedding_shape_mismatch_is_rejected():
    provider=GeminiProvider(Settings(api_key='test-only-key',dimensions=3))
    client=Mock();provider._client=client
    client.models.embed_content.return_value=SimpleNamespace(embeddings=[SimpleNamespace(values=[1,0])])
    with pytest.raises(ProviderError):provider.embed(['text'])


@pytest.mark.parametrize('code,message',[(401,'authentication'),(403,'authentication'),(429,'quota'),(404,'unavailable')])
def test_provider_errors_are_actionable(code,message):
    assert message in str(GeminiProvider._error(SimpleNamespace(code=code),'text model'))


spec=importlib.util.spec_from_file_location('launcher',Path(__file__).resolve().parents[1]/'scripts/launch.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)


def test_save_key_preserves_settings_and_does_not_print_key(tmp_path,capsys):
    (tmp_path/'.env.example').write_text('GEMINI_API_KEY=\nGEMINI_MODEL=chosen-model\n')
    launcher.save_key('test-only-value',tmp_path)
    assert launcher.stored_key(tmp_path)=='test-only-value'
    assert 'GEMINI_MODEL=chosen-model' in (tmp_path/'.env').read_text()
    assert 'test-only-value' not in capsys.readouterr().out


@pytest.mark.parametrize('key',['','two keys','bad\nINJECTED=yes','"bad"','bad#comment'])
def test_key_input_cannot_inject_other_settings(tmp_path,key):
    (tmp_path/'.env').write_text('GEMINI_API_KEY=previous-value\n')
    with pytest.raises(ValueError):launcher.save_key(key,tmp_path)
    assert launcher.stored_key(tmp_path)=='previous-value'
