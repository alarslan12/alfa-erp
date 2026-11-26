"""Offline regression tests for the real mobile HTML script.

No Firebase calls, no browser credentials, no production data.
Node is used only for the JavaScript runtime and WebCrypto UUID contract.
"""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")

HARNESS = r"""
const assert=require('node:assert/strict'),fs=require('node:fs');
const webcrypto=require('node:crypto').webcrypto;
const html=fs.readFileSync(process.argv[1],'utf8');
const js=html.split('<script type="module">')[1].split('</script>')[0].replace(/^import .*;\s*$/gm,'');
new Function(js);
const part=(start,end)=>{const a=js.indexOf(start),b=js.indexOf(end,a+start.length);assert(a>=0&&b>a,start);return js.slice(a,b);};
const pure=part('function addressOrText',"$('#shipping').addEventListener")+
 part('function normalizeTr','function canBulk')+
 part('function checkoutLines','async function checkoutOrderId');
const h=new Function(pure+'return {formatShipping,shippingKey,catalogMatches,sameCheckout,checkoutLines};')();
const workspaceId='e2fc57b1-ef52-47b2-a6c9-ecd2e3832756';
const uuid=new Function('crypto','workspaceId',part('async function checkoutOrderId','async function hydrateHistoryRow')+'return checkoutOrderId;')(webcrypto,workspaceId);
const source={uid:'phone',request_id:'id',platform:'Dolap',shipping_reference:'2624140909632909',order_type:'',gross_amount:40,order_note:'Ayrı kolile',items:{0:{code:'33',print_type:'SB',quantity:1},1:{code:'34',print_type:'RNK',quantity:2}}};
assert.equal(h.formatShipping('2624140909632909'),'262 414 090 963 2909');
assert.equal(h.formatShipping('123456789'),'123 456 789');
assert.equal(h.shippingKey('262 414 090 963 2909'),'2624140909632909');
assert.equal(h.formatShipping('Örnek Sokak 14/2'),'Örnek Sokak 14/2');
assert.equal(h.catalogMatches({code:'133',name:'DUSDATA 133'},'Dusdata 33'),false);
assert.equal(h.catalogMatches({code:'133',name:'DUSDATA33'},'Dusdata 33'),true);
assert.equal(h.catalogMatches({code:'33',name:'Kitap'},'33'),true);
assert.equal(h.catalogMatches({code:'133',name:'Kitap'},'33'),false);
assert.equal(h.sameCheckout({...source,shipping_reference:'262 414 090 963 2909',items:[source.items[1],source.items[0]]},source),true);
for(const changes of [{order_note:''},{gross_amount:41},{request_id:'other'},{items:[{code:'33',print_type:'SB',quantity:2},source.items[1]]}])
 assert.equal(h.sameCheckout({...source,...changes},source),false);

// Use the full actual handler, not a reimplementation.
const submit=js.slice(js.indexOf("$('#order-form').addEventListener('submit'"));
function makeScenario(){
 const fields={'#amount':{value:'40'},'#shipping':{value:'2624140909632909'},'#order-type':{value:''}},note={value:'Ayrı kolile'};
 let handler=null,server=null,pending={},writes=0,ids=0,failReadback=true,message='',history=[],draftClears=0;
 const form={addEventListener:(event,fn)=>{handler=fn;},classList:{add(){},remove(){}},querySelectorAll:()=>[]};
 fields['#order-form']=form;
 const env={
  $:s=>fields[s],noteField:note,books:[{}],cart:new Map([['33:SB',{book:{code:'33',name:'DUSDATA 33'},kind:'SB',qty:1}]]),
  withDeviceLock:fn=>fn(),recordedOrder:()=>history.length?history[0]:null,mobileUser:async()=>({uid:'phone'}),
  readPending:()=>JSON.parse(JSON.stringify(pending)),persistPending:p=>{pending=JSON.parse(JSON.stringify(p));},
  ref:(db,path)=>path,realtime:{},workspaceId,crypto:{randomUUID:()=>{ids++;return 'generated-'+ids;}},
  get:async()=>{if(server&&failReadback){failReadback=false;throw Error('offline');}return {exists:()=>!!server,val:()=>server};},
  set:async(_,body)=>{writes++;server=JSON.parse(JSON.stringify(body));},
  historyAdd:r=>{history.push(r);return true;},localStorage:{removeItem(){draftClears++;}},ORDER_NOTE_DRAFT_KEY:'draft',
  msg:v=>{message=v;},renderCart:()=>{}
 };
 new Function('env',pure+"let busy=false;const {$,noteField,books,cart,withDeviceLock,recordedOrder,mobileUser,readPending,persistPending,ref,realtime,workspaceId,crypto,get,set,historyAdd,localStorage,ORDER_NOTE_DRAFT_KEY,msg,renderCart}=env;\n"+submit)(env);
 return {submit:()=>handler({preventDefault(){}}),env,note,inspect:()=>({server,pending,writes,ids,history,draftClears,message})};
}

(async()=>{
 assert.equal(await uuid('ci-mobile','11111111-2222-4333-8444-555555555555'),'2e7673b7-5762-5b5b-9f7c-0b0cea7a7c06');
 const s=makeScenario();
 await s.submit();let state=s.inspect();
 assert.equal(state.writes,1);assert.equal(state.ids,1);assert.equal(state.history.length,0);
 assert.equal(s.note.value,'Ayrı kolile');assert.equal(s.env.cart.size,1);assert.equal(state.draftClears,0);
 assert.equal(state.server.order_note,'Ayrı kolile');
 assert.equal(Object.values(state.pending)[0].requestId,'generated-1');
 s.note.value='Farklı not';
 await s.submit();state=s.inspect();
 assert.equal(state.writes,1);assert.equal(state.ids,1);assert.equal(state.history.length,0);assert.equal(s.note.value,'Farklı not');
 s.note.value='Ayrı kolile';
 await s.submit();state=s.inspect();
 assert.equal(state.writes,1);assert.equal(state.ids,1);assert.equal(state.history.length,1);assert.equal(state.history[0].orderNote,'Ayrı kolile');
 assert.equal(state.history[0].books[0].name,'DUSDATA 33');assert.equal(s.env.cart.size,0);assert.equal(s.note.value,'');assert.equal(state.draftClears,1);
 assert.equal(Object.keys(state.pending).length,0);
 console.log('Mobile formatting, search, UUID, checkout retry and note tests passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
"""

class MobilePanelRuntimeTests(unittest.TestCase):
    @unittest.skipUnless(NODE, "Node.js is required for mobile JavaScript tests")
    def test_runtime_contract(self):
        result = subprocess.run(
            [NODE, "-e", HARNESS, str(ROOT / "mobil_panel" / "index.html")],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("tests passed", result.stdout)

    def test_history_and_bulk_markup(self):
        html = (ROOT / "mobil_panel" / "index.html").read_text(encoding="utf-8")
        self.assertLess(html.index('id="tracking-screen"'), html.index('id="order-history"'))
        self.assertLess(html.index('id="order-history"'), html.index('id="main-screen"'))
        self.assertEqual(html.count('id="history-list"'), 1)
        self.assertNotIn('class="bulk-help muted"', html)
        self.assertIn('grid-template-columns:repeat(4,minmax(0,1fr)) minmax(0,1.3fr)', html)


if __name__ == "__main__":
    unittest.main()
