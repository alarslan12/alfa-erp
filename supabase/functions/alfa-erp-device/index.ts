// ALFA ERP paired-device gateway: server-side service key NEVER leaves Supabase.
import { createClient } from 'npm:@supabase/supabase-js@2';

const url = Deno.env.get('SUPABASE_URL') ?? '';
const secret = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '';
if (!url || !secret) throw new Error('Supabase function missing server settings');
const db = createClient(url, secret, { auth: {persistSession:false, autoRefreshToken:false} });
const encoder = new TextEncoder();
const respond = (payload:unknown, status=200) => new Response(JSON.stringify(payload), {
  status, headers:{'content-type':'application/json; charset=utf-8','access-control-allow-origin':'*','cache-control':'no-store'}
});
const errorResponse = (message:string, status=400) => respond({error:message},status);
// Transient upstream overload/timeouts are retryable, NEVER permanently reject
// a queued order operation. Clients deduplicate retries by the existing op_id.
const databaseErrorStatus = (e:{message?:string,code?:string}) =>
  /timeout|timed out|connection|temporarily|overload|too many|rate limit|upstream|gateway|503|504/i
    .test(String(e.message||'')+' '+String(e.code||'')) ? 503 : 409;

async function digest(raw:string) {
  const hash = await crypto.subtle.digest('SHA-256',encoder.encode(raw));
  return Array.from(new Uint8Array(hash)).map(x=>x.toString(16).padStart(2,'0')).join('');
}
function secureCode(bytes=24) {
  return Array.from(crypto.getRandomValues(new Uint8Array(bytes)))
    .map(n=>n.toString(16).padStart(2,'0')).join('').toUpperCase();
}
let cachedWorkspace: {id:string,name:string}|null = null;
let cachedWorkspaceAt = 0;
async function workspace() {
  if(cachedWorkspace && Date.now()-cachedWorkspaceAt<300000) return cachedWorkspace;
  const {data,error} = await db.from('workspaces').select('id,name')
    .eq('slug','alfa-erp').single();
  if (error || !data) throw new Error('ALFA ERP workspace not found');
  cachedWorkspace=data;cachedWorkspaceAt=Date.now();
  return data;
}
async function adminAccess(req:Request, wsid:string) {
  const bearer = (req.headers.get('authorization')||'').match(/^Bearer\s+(.+)$/i)?.[1];
  if (!bearer) return false;
  const {data,error}=await db.auth.getUser(bearer);
  if (error || !data?.user?.id) return false;
  const {data:member} = await db.from('workspace_members')
    .select('role').eq('workspace_id',wsid)
    .eq('user_id',data.user.id).eq('active',true).maybeSingle();
  return member?.role==='admin';
}
async function deviceAccess(body:Record<string,unknown>, wsid:string) {
  const token=typeof body.device_token==='string'?body.device_token:'';
  if (!/^[0-9A-Fa-f]{64}$/.test(token)) return null;
  const {data} = await db.from('erp_device_keys').select('id,device_name')
     .eq('workspace_id',wsid).eq('token_hash',await digest(token)).eq('active',true).maybeSingle();
  return data;
}
async function pageAll(table:'orders'|'order_items'|'books'|'erp_inventory_products',wsid:string, select:string) {
  const list:unknown[]=[];
  for(let offset=0;offset<5000;offset+=500) {
    const {data,error}=await db.from(table).select(select).eq('workspace_id',wsid)
      .order('id',{ascending:true}).range(offset,offset+499);
    if(error) throw new Error(table+': '+error.message);
    list.push(...(data||[]));
    if((data||[]).length<500) return list;
  }
  throw new Error(table+' exceeds safe pagination bound');
}
Deno.serve(async(req:Request)=> {
  if(req.method==='OPTIONS') return new Response(null,{status:204,headers:{
    'access-control-allow-origin':'*','access-control-allow-methods':'POST, OPTIONS',
    'access-control-allow-headers':'content-type, apikey, authorization'
  }});
  if(req.method!=='POST') return errorResponse('POST required',405);
  const bodyMax = req.headers.get('authorization') ? 4000000 : 1500000;
  if(Number(req.headers.get('content-length')||0)>bodyMax) return errorResponse('Too large',413);
  try {
    const body=await req.json();
    if(!body || typeof body!=='object' || Array.isArray(body)) return errorResponse('Invalid JSON');
    const action=String(body.action||'');
    const ws=await workspace();
    if(action==='pair') {
      const code=String(body.code||'').trim().toUpperCase();
      const deviceName=String(body.device_name||'').trim().slice(0,120);
      if(!/^[0-9A-F]{48}$/.test(code)||!deviceName) return errorResponse('Geçersiz cihaz eşleştirme kodu',401);
      const codeHash=await digest(code);
      const {data:claimed,error:claimError}=await db.from('erp_pairing_codes')
        .update({claimed_at:new Date().toISOString()})
        .eq('workspace_id',ws.id).eq('code_hash',codeHash).is('claimed_at',null)
        .or('expires_at.is.null,expires_at.gt.'+new Date().toISOString()).select('workspace_id').maybeSingle();
      if(claimError||!claimed) return errorResponse('Kod geçersiz, süresi dolmuş veya önceden kullanılmış',401);
      const token=secureCode(32);
      const {error}=await db.from('erp_device_keys').insert({
        workspace_id:ws.id,device_name:deviceName,token_hash:await digest(token)
      });
      if(error) return errorResponse('Cihaz eklenemedi',500);
      return respond({device_token:token,device_name:deviceName,workspace_id:ws.id});
    }
    if(action.startsWith('admin_')) {
      if(!await adminAccess(req,ws.id)) return errorResponse('Yönetici oturumu gerekli',403);
      if(action==='admin_status') return respond({access:true,role:'admin'});
      if(action==='admin_setup_code') {
        // Tek cihaz için tek kullanımlık dağıtım bileti (14 gün).
        const code=secureCode(24);
        const {error}=await db.from('erp_pairing_codes').insert({
          workspace_id:ws.id,code_hash:await digest(code),
          expires_at:null
        });
        if(error) return errorResponse('Kurulum kodu oluşturulamadı',500);
        return respond({code,one_time:true});
      }
      if(action==='admin_payment') {
        const days=body.days;
        if(!Array.isArray(days)||days.length>45||typeof body.paid!=='boolean')
          return errorResponse('Geçersiz muhasebe günleri',400);
        const fp=(body.fingerprints||{}) as Record<string,string>;
        for(const day of days) {
          if(typeof day!=='string'||!/^\d{4}-\d\d-\d\d$/.test(day)||
            (body.paid && !/^[0-9a-f]{64}$/i.test(String(fp[day]||''))))
            return errorResponse('Geçersiz gün veya doğrulama imzası',400);
        }
        for(const day of days) {
          const {error}=await db.from('accounting_days').upsert({
            workspace_id:ws.id,accounting_day:day,paid:body.paid,
            completion_fingerprint:body.paid?fp[day]:null,
            paid_at:body.paid?new Date().toISOString():null
          },{onConflict:'workspace_id,accounting_day'});
          if(error) return errorResponse('Muhasebe günleri güncellenemedi',500);
        }
        const {data,error}=await db.from('accounting_days')
          .select('accounting_day,paid,completion_fingerprint,updated_at')
          .eq('workspace_id',ws.id).order('accounting_day');
        if(error)return errorResponse('Muhasebe günleri yüklenemedi',500);
        return respond({accounting_days:data||[]});
      }
      if(action==='admin_audit') {
        const [{data:events,error:e1},{data:devices,error:e2}]=await Promise.all([
          db.from('audit_events')
             .select('id,entity_name,entity_id,action,changed_fields,created_at,actor_id')
             .eq('workspace_id',ws.id).order('created_at',{ascending:false}).limit(1000),
          db.from('erp_device_activity')
             .select('id,device_name,action,order_ids,details,created_at')
             .eq('workspace_id',ws.id).order('created_at',{ascending:false}).limit(500)
        ]);
        if(e1||e2)return errorResponse('İşlem günlüğü okunamadı',500);
        return respond({audit_events:events||[],device_activity:devices||[]});
      }
      if(action==='admin_inventory_image') {
        const raw=String(body.image_base64||'');
        const mime=String(body.mime||'image/jpeg');
        if(!['image/jpeg','image/png','image/webp'].includes(mime)||
            raw.length<100||raw.length>3900000||!/^[A-Za-z0-9+/=]+$/.test(raw))
            return errorResponse('Görsel JPG/PNG/WebP ve en fazla 2.9MB olmalı',400);
        let bytes:Uint8Array;
        try {bytes=Uint8Array.from(atob(raw),c=>c.charCodeAt(0));}
        catch {return errorResponse('Görsel kodlaması geçersiz',400);}
        if(bytes.length>2900000) return errorResponse('Görsel boyutu aşılmış',413);
        if(mime==='image/jpeg'&&!(bytes[0]===255&&bytes[1]===216)||
           mime==='image/png'&&!(bytes[0]===137&&bytes[1]===80)||
           mime==='image/webp'&&new TextDecoder().decode(bytes.slice(8,12))!=='WEBP')
            return errorResponse('Görsel biçimi yanlış',400);
        const path=ws.id+'/'+crypto.randomUUID()+'.'+(mime==='image/png'?'png':mime==='image/webp'?'webp':'jpg');
        const {error}=await db.storage.from('alfa-inventory-images').upload(path,bytes,
          {contentType:mime,upsert:false,cacheControl:'31536000'});
        if(error)return errorResponse('Görsel yükleme başarısız',500);
        return respond({url:db.storage.from('alfa-inventory-images').getPublicUrl(path).data.publicUrl});
      }
      if(action==='admin_inventory_upsert') {
        const p=(body.product||{}) as Record<string,any>;
        const title=String(p.title||'').trim(), sku=String(p.sku||'').trim();
        const category=String(p.category||'Genel').trim();
        const tags=Array.isArray(p.tags)?p.tags.map((x:any)=>String(x).trim()).filter(Boolean).slice(0,15):[];
        const attributes=p.attributes||{};
        const qty=Number(p.quantity),price=Number(p.sale_price),cost=Number(p.cost_price);
        if(!title||title.length>200||!sku||sku.length>90||category.length>100||
          !Number.isInteger(qty)||qty<0||qty>10000000||
          !Number.isFinite(price)||price<0||price>999999999||
          !Number.isFinite(cost)||cost<0||cost>999999999||
          String(p.description||'').length>4000||JSON.stringify(attributes).length>6000||
          tags.some((t:string)=>t.length>45)||JSON.stringify(p.image_url||'').length>1200)
          return errorResponse('Ürün alanları geçersiz veya çok uzun',400);
        if(p.image_url && !String(p.image_url).startsWith(url+'/storage/v1/object/public/alfa-inventory-images/'))
          return errorResponse('Görsel yalnızca ALFA deposundan seçilebilir',400);
        const payload:any={workspace_id:ws.id,sku,title,category,
          tags,description:String(p.description||''),
          attributes,quantity:qty,sale_price:price,cost_price:cost,
          image_url:String(p.image_url||''),active:p.active!==false,
          updated_at:new Date().toISOString()};
        if(typeof p.in_inventory==='boolean')payload.in_inventory=p.in_inventory;
        if(p.id && /^[0-9a-f-]{36}$/i.test(String(p.id))) {
          const {data,error}=await db.from('erp_inventory_products').update(payload)
            .eq('id',String(p.id)).eq('workspace_id',ws.id).select('id').single();
          if(error)return errorResponse(error.message,409);
          await db.from('erp_device_activity').insert({workspace_id:ws.id,device_name:'Yönetici',action:'inventory_product_update'});
          return respond({id:data.id});
        }
        const {data,error}=await db.from('erp_inventory_products').insert(payload).select('id').single();
        if(error)return errorResponse(error.message,409);
        await db.from('erp_device_activity').insert({workspace_id:ws.id,device_name:'Yönetici',action:'inventory_product_create'});
        return respond({id:data.id});
      }
      if(action==='admin_inventory_archive') {
        const id=String(body.id||'');
        if(!/^[0-9a-f-]{36}$/i.test(id)) return errorResponse('Geçersiz ürün',400);
        const {error}=await db.from('erp_inventory_products').update({active:false,updated_at:new Date().toISOString()})
          .eq('id',id).eq('workspace_id',ws.id);
        if(error)return errorResponse('Ürün arşivlenemedi',500);
        return respond({ok:true});
      }
      if(action==='admin_catalog') {
        const input=body.books;
        if(!Array.isArray(input)||input.length<1||input.length>2000)
          return errorResponse('Excel 1-2000 geçerli kitap içermeli',400);
        const {data,error}=await db.rpc('erp_catalog_replace',{
          p_workspace_id:ws.id,p_books:input
        });
        if(error)return errorResponse(error.message,409);
        await db.from('erp_device_activity').insert({
          workspace_id:ws.id,device_name:'Yönetici',
          action:'excel_catalog_update'
        });
        return respond(data);
      }
      if(action==='admin_code') {
        const code=secureCode(24);
        const {error}=await db.from('erp_pairing_codes').insert({
          workspace_id:ws.id,code_hash:await digest(code),
          expires_at:new Date(Date.now()+15*60*1000).toISOString()
        });
        if(error) return errorResponse('Kod üretilemedi',500);
        return respond({code,valid_minutes:15});
      }
      if(action==='admin_devices') {
        const {data,error}=await db.from('erp_device_keys')
          .select('id,device_name,active,last_seen_at,created_at')
          .eq('workspace_id',ws.id).order('created_at',{ascending:false});
        if(error) return errorResponse('Cihazlar okunamadı',500);
        return respond({devices:data||[]});
      }
      if(action==='admin_revoke') {
        if(!/^[0-9a-f-]{36}$/i.test(String(body.id||''))) return errorResponse('Invalid ID');
        const {error}=await db.from('erp_device_keys').update({active:false})
          .eq('workspace_id',ws.id).eq('id',body.id);
        if(error) return errorResponse('Cihaz iptal edilemedi',500);
        return respond({ok:true});
      }
      if(action==='admin_import') {
        if(!Array.isArray(body.edits)||body.edits.length>100) return errorResponse('Too many orders');
        const {data,error}=await db.rpc('erp_device_commit',{
          p_workspace_id:ws.id,p_edits:body.edits,p_admin:true
        });
        if(error) return errorResponse(error.message,409);
        return respond({results:data});
      }
      return errorResponse('Unknown admin action');
    }
    if(action==='public_catalog') {
      const {data:books,error}=await db.from('books')
       .select('code,name,group_name,page_count,supports_color')
       .eq('workspace_id',ws.id).eq('is_active',true).order('code').limit(2000);
      if(error)return errorResponse('Katalog okunamadı',500);
      const {data:rev}=await db.from('erp_sync_state')
        .select('catalog_revision').eq('workspace_id',ws.id).single();
      return respond({books:books||[],catalog_revision:rev?.catalog_revision||1});
    }
    if(action==='public_submit') {
      const order=body.order as Record<string,unknown>;
      const items=order?.items as Record<string,unknown>[];
      const request_id=String(order?.request_id||'');
      const shipping=String(order?.shipping_reference||'').trim();
      const type=String(order?.order_type||'');
      const amount=Number(order?.gross_amount);
      if(!/^[0-9a-f-]{36}$/i.test(request_id)||shipping.length<1||shipping.length>500||
          type.length>100||!Number.isFinite(amount)||amount<0||amount>999999999||
          !Array.isArray(items)||items.length<1||items.length>100)
        return errorResponse('Geçersiz sipariş',400);
      const ip=String(req.headers.get('x-forwarded-for')||req.headers.get('cf-connecting-ip')||'unknown')
       .split(',')[0].trim().slice(0,200);
      const quota=await db.rpc('erp_take_public_quota',{p_workspace_id:ws.id,
        p_source_hash:await digest(ip)});
      if(quota.error||!quota.data)return errorResponse('Sipariş sınırına ulaşıldı, daha sonra tekrar deneyin',429);
      const lines=[];
      for(const line of items){
        const code=String(line?.code||'').trim(),kind=String(line?.print_type||'').toUpperCase();
        const qty=Number(line?.quantity);
        if(!code||code.length>80||!['SB','RNK'].includes(kind)||!Number.isInteger(qty)||qty<1||qty>100000)
          return errorResponse('Geçersiz kitap satırı',400);
        lines.push({kod:code,tur:kind,adet:qty,hazir:0,koli:0});
      }
      const order_payload={platform:String(order.platform||'Mobil').slice(0,100),
        kod:shipping,siparis_turu:type,ciro:amount,kitaplar:lines,durum:'havuz'};
      const {data,error}=await db.rpc('erp_device_commit',{p_workspace_id:ws.id,
        p_edits:[{local_id:'mobile',request_id,order:order_payload}],p_admin:true});
      if(error)return errorResponse(error.message,409);
      const created=(data||[])[0]||{};
      return respond({order_number:created.order_number,reused:false});
    }
    if(action==='sync') {
      const token=typeof body.device_token==='string'?body.device_token:'';
      if(!/^[0-9a-fA-F]{64}$/.test(token)) return errorResponse('Cihaz eşleştirmesi gerekli',401);
      // One DB request validates device access and reads all revision counters.
      const {data:state,error:syncError}=await db.rpc('erp_authorized_sync',{
        p_workspace_id:ws.id,p_token_hash:await digest(token)
      });
      if(syncError)return errorResponse('Senkronizasyon durumu okunamadı',500);
      if(!state)return errorResponse('Cihaz erişimi iptal edilmiş',401);
      const known=(body.known&&typeof body.known==='object'&&!Array.isArray(body.known)
        ?body.known:{} ) as Record<string,unknown>;
      const sameEpoch=String(known.epoch||'')===String(state.epoch);
      const changedOrders=!sameEpoch||String(known.orders_revision)!==String(state.orders_revision);
      const changedCatalog=!sameEpoch||String(known.catalog_revision)!==String(state.catalog_revision);
      const changedInventory=!sameEpoch||String(known.inventory_revision)!==String(state.inventory_revision);
      const result:Record<string,unknown>={
        epoch:state.epoch,orders_revision:state.orders_revision,
        catalog_revision:state.catalog_revision,inventory_revision:state.inventory_revision,
        workspace_id:ws.id
      };
      if(body.mode==='notifications'){
        if(changedOrders){
          const last=Math.max(0,Number.isSafeInteger(Number(body.last_order_number))
            ?Number(body.last_order_number):0);
          const {data,error}=await db.from('orders')
            .select('id,order_number')
            .eq('workspace_id',ws.id).is('deleted_at',null)
            .gt('order_number',sameEpoch?last:0)
            .order('order_number',{ascending:true}).limit(1000);
          if(error)return errorResponse('Bildirim sipariş listesi okunamadı',500);
          result.orders_brief=data||[];
        }
        return respond(result);
      }
      // Never fetch the book catalog or full inventory for a counter click.
      const requests:Promise<void>[]=[];
      if(changedOrders){
        requests.push((async()=>{
          const [orders,items,accounting_days]=await Promise.all([
            pageAll('orders',ws.id,'id,order_number,status,platform,shipping_reference,order_type,gross_amount,shipping_fee,version,client_request_id,created_at,started_at,completed_at,deleted_at'),
            pageAll('order_items',ws.id,'id,order_id,book_code,book_name_snapshot,page_count_snapshot,print_type,quantity,prepared_count,boxed_count'),
            (async()=>{const {data,error}=await db.from('accounting_days')
              .select('accounting_day,paid,completion_fingerprint,updated_at')
              .eq('workspace_id',ws.id).order('accounting_day');
              if(error)throw new Error('Account data unavailable');return data||[];})()
          ]);
          result.orders=orders;result.items=items;result.accounting_days=accounting_days;
        })());
      }
      if(changedCatalog)requests.push((async()=>{
        result.books=await pageAll('books',ws.id,'code,name,group_name,page_count,supports_color,is_active');
      })());
      if(changedInventory)requests.push((async()=>{
        const [products,sales]=await Promise.all([
          pageAll('erp_inventory_products',ws.id,
            'id,sku,title,category,tags,description,attributes,image_url,quantity,sale_price,cost_price,active,in_inventory,updated_at'),
          (async()=>{const {data,error}=await db.from('erp_inventory_sales')
            .select('id,product_id,quantity,sale_price,cost_price,created_at')
            .eq('workspace_id',ws.id).order('created_at',{ascending:false}).limit(3000);
            if(error)throw new Error('Inventory sales unavailable');return data||[];})()
        ]);
        result.inventory_products=products;result.inventory_sales=sales;
      })());
      await Promise.all(requests);
      return respond(result);
    }
    const device=await deviceAccess(body,ws.id);
    if(!device) return errorResponse('Cihaz eşleştirmesi gerekli veya erişim iptal edilmiş',401);
    if(action==='pulse') {
      const {data,error}=await db.from('erp_sync_state')
       .select('epoch,catalog_revision,orders_revision,inventory_revision')
       .eq('workspace_id',ws.id).single();
      if(error)return errorResponse('Senkronizasyon durumu okunamadı',500);
      return respond(data);
    }
    if(action==='transition') {
      if(!Array.isArray(body.events)||body.events.length<1||body.events.length>40)
        return errorResponse('Geçersiz sipariş durum işlemleri',400);
      const {data,error}=await db.rpc('erp_apply_status_batch',{
        p_workspace_id:ws.id,p_device_id:device.id,p_actions:body.events
      });
      if(error){console.error('ALFA_TRANSITION_REJECT',String(error.code||''),String(error.message||'').slice(0,300));return errorResponse(error.message,databaseErrorStatus(error));}
      await db.from('erp_device_activity').insert({
        workspace_id:ws.id,device_id:device.id,device_name:device.device_name,
        action:'transition',order_ids:[...new Set((body.events as any[])
         .map((x:any)=>String(x.order_id||'')))].filter(x=>/^[0-9a-f-]{36}$/i.test(x)),
        details:{events:(body.events as any[]).slice(0,30).map((ev:any)=>({
          order_id:String(ev.order_id||''),from_status:String(ev.from_status||''),
          to_status:String(ev.to_status||'')}))}
      });
      return respond({results:data||[]});
    }
    if(action==='progress') {
      if(!Array.isArray(body.events)||body.events.length<1||body.events.length>80)
        return errorResponse('Invalid progress batch',400);
      const {data,error}=await db.rpc('erp_apply_progress_batch',{
        p_workspace_id:ws.id,p_device_id:device.id,p_actions:body.events
      });
      if(error){console.error('ALFA_PROGRESS_REJECT',String(error.code||''),String(error.message||'').slice(0,300));return errorResponse(error.message,databaseErrorStatus(error));}
      // Log the actor once for each batch, with order IDs for supervisor auditing.
      const ids=[...new Set((body.events as any[]).map((e:any)=>String(e.order_id||'')))];
      await db.from('erp_device_activity').insert({
        workspace_id:ws.id,device_id:device.id,device_name:device.device_name,
        action:'progress',order_ids:ids.filter(x=>/^[0-9a-f-]{36}$/i.test(x)),
        details:{events:(body.events as any[]).slice(0,80).map((ev:any)=>({
          order_id:String(ev.order_id||''),book_code:String(ev.book_code||'').slice(0,40),
          print_type:String(ev.print_type||'').slice(0,5),
          delta_ready:Number(ev.delta_ready||0),delta_boxed:Number(ev.delta_boxed||0),
          target_ready:ev.target_ready===undefined?null:Number(ev.target_ready),
          target_boxed:ev.target_boxed===undefined?null:Number(ev.target_boxed)}))}
      });
      return respond({results:data||[]});
    }
    if(action==='inventory_sale') {
      const product_id=String(body.product_id||''),quantity=Number(body.quantity);
      const price=Number(body.sale_price);
      if(!/^[0-9a-f-]{36}$/i.test(product_id)||!Number.isInteger(quantity)||quantity<1||quantity>100000||
        !Number.isFinite(price)||price<0||price>999999999)
        return errorResponse('Geçersiz satış bilgileri',400);
      const {data,error}=await db.rpc('erp_inventory_record_sale',{
        p_workspace_id:ws.id,p_product_id:product_id,p_quantity:quantity,p_price:price,p_device_id:device.id
      });
      if(error)return errorResponse(error.message,409);
      await db.from('erp_device_activity').insert({
        workspace_id:ws.id,device_id:device.id,device_name:device.device_name,
        action:'inventory_sale',order_ids:[]
      });
      return respond(data);
    }
    if(action==='snapshot') {
      const [orders,items,accounting_days,books,state,inventory_products,inventory_sales]=await Promise.all([
        pageAll('orders',ws.id,'id,order_number,status,platform,shipping_reference,order_type,gross_amount,shipping_fee,version,client_request_id,created_at,started_at,completed_at,deleted_at'),
        pageAll('order_items',ws.id,'id,order_id,book_code,book_name_snapshot,page_count_snapshot,print_type,quantity,prepared_count,boxed_count'),
        (async()=> {
          const {data,error}=await db.from('accounting_days')
            .select('accounting_day,paid,completion_fingerprint,updated_at')
            .eq('workspace_id',ws.id).order('accounting_day');
          if(error) throw new Error('Account data unavailable');
          return data||[];
        })(),
        pageAll('books',ws.id,'code,name,group_name,page_count,supports_color,is_active'),
        (async()=>{
          const {data,error}=await db.from('erp_sync_state')
            .select('epoch,catalog_revision,orders_revision,inventory_revision').eq('workspace_id',ws.id).single();
          if(error)throw new Error('Cloud generation unavailable');
          return data;
        })(),
        pageAll('erp_inventory_products' as any,ws.id,
          'id,sku,title,category,tags,description,attributes,image_url,quantity,sale_price,cost_price,active,updated_at'),
        (async()=>{
          const {data,error}=await db.from('erp_inventory_sales')
            .select('id,product_id,quantity,sale_price,cost_price,created_at')
            .eq('workspace_id',ws.id).order('created_at',{ascending:false}).limit(3000);
          if(error)throw new Error('Inventory sales unavailable');
          return data||[];
        })()
      ]);
      const stale=new Date(Date.now()-180000).toISOString();
      await db.from('erp_device_keys').update({last_seen_at:new Date().toISOString()})
        .eq('id',device.id).or('last_seen_at.is.null,last_seen_at.lt.'+stale);
      return respond({orders,items,accounting_days,books,inventory_products,
        inventory_sales,epoch:state.epoch,catalog_revision:state.catalog_revision,
        orders_revision:state.orders_revision,inventory_revision:state.inventory_revision,
        workspace_id:ws.id});
    }
    if(action==='commit') {
      if(!Array.isArray(body.edits)||body.edits.length>100) return errorResponse('Invalid update batch');
      const {data,error}=await db.rpc('erp_device_commit',{
        p_workspace_id:ws.id,p_edits:body.edits,p_admin:false
      });
      if(error){console.error('ALFA_COMMIT_REJECT',String(error.code||''),String(error.message||'').slice(0,300));return errorResponse(error.message,databaseErrorStatus(error));}
      try {
        await db.from('erp_device_activity').insert({
          workspace_id:ws.id,device_id:device.id,device_name:device.device_name,
          action:'commit',order_ids:(data||[]).map((x:any)=>x.uuid).filter(Boolean)
        });
      } catch (_ignored) { /* Business write already succeeded; log is best effort. */ }
      return respond({results:data});
    }
    return errorResponse('Unknown device action');
  } catch(e) {
    return errorResponse(e instanceof SyntaxError ? 'Invalid JSON' : 'Cloud connection error', 500);
  }
});