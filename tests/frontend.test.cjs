// Tests the actual shipped JS with a minimal DOM and controlled HTTP responses.
// No live model calls or browser layout claims are made by these tests.
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

function element(tag='div') {
  return {tag,textContent:'',value:'',hidden:true,disabled:false,children:[],listeners:{},files:[],
    append(...children){this.children.push(...children)},replaceChildren(...children){this.children=children},
    addEventListener(event,callback){this.listeners[event]=callback},focus(){},scrollIntoView(){},reset(){},click(){}};
}
async function setup({documents=[],key=true}={}) {
  const elements=new Map();
  const document={getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id)},
    createElement:element,querySelectorAll(selector){return selector==='button'?[...elements.values()]:[]}};
  const result={query_id:'test-query',answer:'Controlled answer [1]',status:'answered',retries:0,
    sources:[{citation:1,title:'Guide',source:'https://example.test',excerpt:'<script>untrusted text</script>'}],
    trace:[{node:'retrieval',count:1},{node:'grounding_check',supported:true}]};
  const state={documents,key,result,requests:[],failure:false,exports:[]};
  const context=vm.createContext({document,console,Blob,FormData,setTimeout:callback=>callback(),
    URL:{createObjectURL(blob){state.exports.push(blob);return 'blob:test'},revokeObjectURL(){}},
    fetch:async(url,options={})=>{
      state.requests.push({url,options});
      if(url==='/query'&&state.failure)return{ok:false,json:async()=>({detail:'Controlled provider failure'})};
      const body=url==='/health'?{key_configured:state.key}:url==='/documents'?{documents:state.documents}:
        url==='/ingest-corpus'?{documents:state.documents}:state.result;
      return{ok:true,json:async()=>body};
    }});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../app/static/app.js'),'utf8'),context);
  await new Promise(resolve=>setImmediate(resolve));
  return{state,context,get:id=>document.getElementById(id)};
}
const submit={preventDefault(){}};

test('populated library renders all five guides without shadowing document',async()=>{
  const ui=await setup({documents:Array.from({length:5},(_,i)=>({title:'Guide '+i,chunks:i+1}))});
  assert.equal(String(ui.get('count').textContent),'5');
  assert.equal(ui.get('documents').children.length,5);
  assert.equal(ui.get('documents').children[4].children[0].textContent,'Guide 4');
  assert.equal(ui.get('documents').children[4].children[1].textContent,'5 searchable passages');
  assert(!ui.get('health').textContent.includes('unavailable'));
});
test('successful indexing refreshes the library and releases controls',async()=>{
  const ui=await setup();ui.state.documents=[{title:'New guide',chunks:2}];
  await ui.get('index').listeners.click();
  assert.equal(ui.get('documents').children.length,1);
  assert(ui.get('notice').textContent.includes('Ready:'));
  assert.equal(ui.get('busy').hidden,true);
});
test('missing key produces setup instructions without query requests',async()=>{
  const ui=await setup({key:false});ui.get('question').value='Question';
  await ui.get('query-form').listeners.submit(submit);
  assert(ui.get('notice').textContent.includes('SETUP_KEY.cmd'));
  assert(!ui.state.requests.some(r=>r.url==='/query'));
});
test('empty library requests indexing before a query',async()=>{
  const ui=await setup();ui.get('question').value='Question';
  await ui.get('query-form').listeners.submit(submit);
  assert(ui.get('notice').textContent.includes('Index the five guides'));
  assert(!ui.state.requests.some(r=>r.url==='/query'));
});
test('answer sources and trace are safely rendered as text',async()=>{
  const ui=await setup({documents:[{title:'Guide',chunks:1}]});ui.get('question').value='Question';
  await ui.get('query-form').listeners.submit(submit);
  assert.equal(ui.get('answer').textContent,ui.state.result.answer);
  assert.equal(ui.get('sources').children[0].children[2].textContent,'<script>untrusted text</script>');
  assert.equal(ui.get('trace').children.length,2);
  assert.equal(ui.get('status').textContent,'SUPPORT CHECK PASSED');
});
test('provider error is shown and the busy state ends',async()=>{
  const ui=await setup({documents:[{title:'Guide',chunks:1}]});ui.state.failure=true;ui.get('question').value='Question';
  await ui.get('query-form').listeners.submit(submit);
  assert.equal(ui.get('notice').textContent,'Controlled provider failure');
  assert.equal(ui.get('busy').hidden,true);assert.equal(ui.get('ask').disabled,false);
});
test('feedback includes optional comment and the actual response id',async()=>{
  const ui=await setup({documents:[{title:'Guide',chunks:1}]});ui.get('question').value='Question';
  await ui.get('query-form').listeners.submit(submit);ui.get('comment').value='Needs more detail';
  await ui.get('down').listeners.click();
  const request=ui.state.requests.find(r=>r.url==='/feedback');
  assert.deepEqual(JSON.parse(request.options.body),{query_id:'test-query',rating:'down',comment:'Needs more detail'});
  assert.equal(ui.get('feedback-state').textContent,'Feedback saved.');
});
test('JSON download keeps the original question after the input is edited',async()=>{
  const ui=await setup({documents:[{title:'Guide',chunks:1}]});ui.get('question').value='Original question';
  await ui.get('query-form').listeners.submit(submit);ui.get('question').value='Edited question';ui.get('download').listeners.click();
  const record=JSON.parse(await ui.state.exports[0].text());
  assert.equal(record.question,'Original question');assert.equal(record.response.query_id,'test-query');
});
