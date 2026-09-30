from pathlib import Path
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter

MAX_BYTES = 2 * 1024 * 1024
MAX_CHUNKS = 150
CHUNK_SIZE = 1800
CHUNK_OVERLAP = 250


def extract(filename, content):
    if not content or len(content) > MAX_BYTES:
        raise ValueError('Upload a nonempty document no larger than 2 MiB')
    suffix = Path(filename).suffix.lower()
    if suffix not in ('.txt','.md','.html','.htm'):
        raise ValueError('Supported uploads: UTF-8 .txt, .md, .html or .htm')
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('Document must be encoded as UTF-8 text') from exc
    if '\x00' in text:
        raise ValueError('Binary content is not supported')
    if suffix in ('.html','.htm'):
        soup = BeautifulSoup(text, 'html.parser')
        for tag in soup(['script','style','nav','footer','header']):
            tag.decompose()
        for pre in soup.find_all('pre'):
            pre.replace_with('\n```\n'+pre.get_text()+'\n```\n')
        text = (soup.find('article') or soup.find('main') or soup).get_text('\n', strip=True)
    text = text.strip()
    if not text:
        raise ValueError('Document contains no usable text')
    return text


def split(text):
    return RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE,chunk_overlap=CHUNK_OVERLAP,
        separators=['\n\n','\n',' ','']).split_text(text)


def ingest(store, provider, filename, content, source=None):
    filename = Path(filename.replace('\\','/')).name
    text = extract(filename,content)
    digest = store.digest(text)
    prior = store.existing(digest)
    if prior:
        return {'document_id':prior,'chunks_added':0,'duplicate':True}
    chunks = split(text)
    if len(chunks) > MAX_CHUNKS:
        raise ValueError(f'Document produces more than {MAX_CHUNKS} passages; upload a shorter document')
    vectors = []
    for start in range(0,len(chunks),16):
        vectors.extend(provider.embed(chunks[start:start+16]))
    title = next((line.lstrip('#').strip() for line in text.splitlines() if line.startswith('# ')),
                 Path(filename).stem.replace('-',' ').title())
    return store.add(title[:250],(source or filename).strip(),digest,chunks,vectors)
