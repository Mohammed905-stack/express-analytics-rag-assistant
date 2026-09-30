"""Fetch five official guides, preserving code examples and recording provenance."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import httpx
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent.parent
GUIDES=['body','query-params','response-model','handling-errors','request-files']


def main():
    folder=ROOT/'corpus'; folder.mkdir(exist_ok=True)
    records=[]
    with httpx.Client(timeout=30,follow_redirects=True) as client:
        for name in GUIDES:
            url=f'https://fastapi.tiangolo.com/tutorial/{name}/'
            response=client.get(url); response.raise_for_status()
            soup=BeautifulSoup(response.text,'html.parser')
            article=soup.find('article') or soup.find('main')
            if article is None:
                raise RuntimeError(f'No main content at {url}')
            for tag in article.select('script,style,nav,footer,a.headerlink'):
                tag.decompose()
            heading=article.find('h1')
            title=heading.get_text(' ',strip=True) if heading else name.replace('-',' ').title()
            if heading:heading.decompose()
            for pre in article.find_all('pre'):
                pre.replace_with('\n```python\n'+pre.get_text()+'\n```\n')
            text=f'# {title}\n\nSource: {url}\n\n'+article.get_text('\n',strip=True)+'\n'
            content=text.encode('utf-8'); (folder/f'{name}.md').write_bytes(content)
            records.append({'file':f'{name}.md','source':url,'sha256':hashlib.sha256(content).hexdigest(),
                            'fetched_at':datetime.now(timezone.utc).isoformat()})
            print(f'{name}: {len(content)} bytes')
        license_response=client.get('https://raw.githubusercontent.com/fastapi/fastapi/master/LICENSE')
        license_response.raise_for_status()
    (folder/'manifest.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    (ROOT/'THIRD_PARTY_NOTICES.md').write_text(
        '# Third-party notices\n\nThe corpus contains extracted text and code from official FastAPI documentation. '
        'Navigation was removed and formatting adapted. Source URLs, timestamps and hashes are in corpus/manifest.json.\n\n'
        'Project: https://github.com/fastapi/fastapi\n\nLicense: https://github.com/fastapi/fastapi/blob/master/LICENSE\n\n'
        'The upstream notice is reproduced below. Dependency packages retain their own licenses.\n\n'+license_response.text,
        encoding='utf-8')


if __name__=='__main__':main()
