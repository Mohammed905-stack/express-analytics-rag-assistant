"""Optional developer QA. Requires Playwright and a running local app.

No Gemini key is needed. Interaction scenarios intercept HTTP responses with
explicit fixtures; they verify UI behaviour, not live-model answers.
"""
import json
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent.parent


def main():
    records=[];folder=ROOT/'evidence';folder.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://127.0.0.1:8000',wait_until='networkidle')
        assert 'Express Docs' in page.title()
        assert 'key needed' in page.locator('#health').inner_text()
        assert page.locator('#notice').is_visible()
        page.screenshot(path=str(folder/'interface-before-key.png'),full_page=True)
        records.append('Real local page: loads, shows missing-key instructions, and serves the interface.')
        page.get_by_role('button',name='Request bodies',exact=True).click()
        assert 'Pydantic' in page.locator('#question').input_value()
        page.locator('#ask').click()
        assert 'SETUP_KEY.cmd' in page.locator('#notice').inner_text()
        assert not page.locator('#result').is_visible()
        records.append('Missing-key submission shows instructions without fabricated answers.')
        for width in (390,768):
            page.set_viewport_size({'width':width,'height':900})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'),width
        records.append('390px, 768px and 1440px layouts: no horizontal overflow.')

        # Explicit HTTP fixtures for populated-library and answer scenarios.
        docs=[]
        guides=[{'document_id':str(i),'title':name,'chunks':i+1} for i,name in enumerate(
            ['Request Body','Query Parameters','Response Model','Handling Errors','Request Files'])]
        response={'query_id':'browser-test-fixture','answer':'CONTROLLED UI TEST: use a model. [1]',
            'status':'answered','query_type':'how-to','retries':1,
            'sources':[{'citation':1,'chunk_id':'fixture-1','document_id':'fixture',
                        'title':'Request Body','source':'https://example.test/fixture',
                        'excerpt':'<script>window.fixtureExecuted=true</script>'}],
            'trace':[{'node':'retrieval','count':1},{'node':'query_rewrite','retries':1},
                     {'node':'grounding_check','supported':True,'reason':'Controlled fixture'}]}
        def fulfill(route,value):route.fulfill(status=200,content_type='application/json',body=json.dumps(value))
        page.route('**/health',lambda route:fulfill(route,{'key_configured':True,'documents':len(docs)}))
        page.route('**/documents',lambda route:fulfill(route,{'documents':docs}))
        def index(route):docs.extend(guides);fulfill(route,{'documents':guides})
        page.route('**/ingest-corpus',index)
        page.route('**/query',lambda route:fulfill(route,response))
        feedback=[]
        def save_feedback(route):feedback.append(route.request.post_data_json);fulfill(route,{'status':'saved'})
        page.route('**/feedback',save_feedback)
        page.set_viewport_size({'width':1440,'height':1000})
        page.reload(wait_until='networkidle')
        page.locator('#index').click()
        page.wait_for_function("document.querySelectorAll('#documents li').length === 5")
        assert page.locator('#count').inner_text()=='5'
        assert 'Ready:' in page.locator('#notice').inner_text()
        records.append('Controlled HTTP fixtures: indexing renders all five guides without document shadowing errors.')
        page.get_by_role('button',name='Request bodies',exact=True).click()
        original=page.locator('#question').input_value()
        page.locator('#ask').click()
        page.locator('#result').wait_for(state='visible')
        assert 'CONTROLLED UI TEST' in page.locator('#answer').inner_text()
        page.locator('#sources summary').click()
        assert '<script>' in page.locator('.excerpt').inner_text()
        assert not page.evaluate('Boolean(window.fixtureExecuted)')
        page.locator('.workflow summary').click()
        assert page.locator('.trace-step').count()==3
        page.locator('#comment').fill('Browser fixture feedback')
        page.locator('#down').click()
        page.wait_for_function("document.getElementById('feedback-state').textContent === 'Feedback saved.'")
        assert feedback[0]['rating']=='down' and feedback[0]['comment']=='Browser fixture feedback'
        page.locator('#question').fill('Edited input')
        with page.expect_download() as download_info:page.locator('#download').click()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'response.json';download_info.value.save_as(path)
            record=json.loads(path.read_text());assert record['question']==original
            assert record['response']['query_id']=='browser-test-fixture'
        records.append('Controlled fixtures: answer, citations, safe text excerpts, retry trace, feedback and original-question JSON download work.')
        # Inject a failed API request and check the UI recovers.
        page.unroute('**/query')
        page.route('**/query',lambda route:route.fulfill(status=503,content_type='application/json',body='{"detail":"Controlled provider failure"}'))
        page.locator('#ask').click()
        page.wait_for_function("document.getElementById('notice').textContent === 'Controlled provider failure'")
        assert page.locator('#ask').is_enabled()
        records.append('Controlled HTTP 503: error is shown and the submit button is re-enabled.')
        assert errors==[],errors
        records.append('No browser JavaScript exceptions occurred.')
        browser.close()
    (folder/'browser-checks.txt').write_text('Browser QA: actual Chromium UI; model/network success scenarios use explicit HTTP fixtures.\n'+
        '\n'.join(records)+'\ninterface-before-key.png is an actual unconfigured interface screenshot, not live model evidence.\n',encoding='utf-8')
    print('\n'.join(records))


if __name__=='__main__':main()
