'use strict';
const $ = id => document.getElementById(id);
const qs = s => [...document.querySelectorAll(s)];
let state={settings:{},books:[],catalog:[],palettes:{},styles:[],layouts:[],covers:0};
let renderTimer=null,latestRender=0,selectedCover=null,cropMode=false,customTarget=null;
let draftTimer=null,draftReady=false,selectedArchiveIds=new Set(),libraryEntries=[];
const slogans=['Güncel kaynaklar · Özenli baskı','Kitap koduyla hızlı sipariş','Temel · Klinik · Tam Set','Set seçenekleri için mesaj atın','Sınav hazırlığında pratik seçim','Baskı seçeneklerini birlikte belirleyelim','Güncel katalog · Düzenli kitap setleri'];
const escapeHTML = s => String(s??'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const normalize = s => String(s||'').toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ı/g,'i').replace(/ğ/g,'g').replace(/ş/g,'s').replace(/ç/g,'c').replace(/ö/g,'o').replace(/ü/g,'u');
function toast(message){const n=$('toast');n.textContent=message;n.classList.add('show');clearTimeout(n._timer);n._timer=setTimeout(()=>n.classList.remove('show'),3400)}
function busy(message='',on=true){$('busy').classList.toggle('show',on);if(message)$('busyTitle').textContent=message}
async function api(url,options={}){const resp=await fetch(url,options);const type=resp.headers.get('Content-Type')||'';const val=type.includes('application/json')?await resp.json():await resp.blob();if(!resp.ok)throw new Error(val.error||`İstek başarısız: ${resp.status}`);return val}
function draftPayload(){return JSON.stringify({settings:state.settings,books:state.books})}
async function saveDraft(){
 if(!draftReady)return;
 try{await api('/api/draft/save',{method:'POST',headers:{'Content-Type':'application/json'},body:draftPayload()})}
 catch(e){console.warn('Yerel taslak kaydedilemedi:',e.message)}
}
function saveDraftSoon(){
 if(!draftReady)return;
 clearTimeout(draftTimer);
 draftTimer=setTimeout(()=>void saveDraft(),450);
}
function showCoverStatus(result){
 const info=result?.cover_status||result||{};
 if(info.matched===undefined)return;
 const count=info.covers??state.covers;
 $('dataStatus').textContent=`${state.catalog.length} kitap · ${count} kodlu kapak · ${info.matched}/${info.total} eşleşti`;
 $('dataStatus').title=(info.missing||[]).length?
   'Eşleşmeyen ilk kitaplar: '+info.missing.join(' | '):'Tüm kitapların kapakları eşleşti';
 if(info.total&&info.matched===0){toast('Kapaklar eşleşmedi: kodu veya kitap adı dosya adıyla kontrol et. Eksikler için veri alanının üzerine gel.')}
}
window.addEventListener('pagehide',()=>{
 if(!draftReady)return;
 clearTimeout(draftTimer);
 // Works even if the ephemeral localhost port changes next time.
 navigator.sendBeacon('/api/draft/save',new Blob([draftPayload()],{type:'application/json'}));
});

function updateControls(){
 const s=state.settings;
 qs('[data-setting]').forEach(el=>{
  const key=el.dataset.setting;if(!(key in s))return;
  if(el.type==='checkbox')el.checked=!!s[key];else el.value=s[key]||'';
 });
 qs('[data-offer]').forEach(el=>el.classList.toggle('active',el.dataset.offer===s.offer));
 for(const id of ['colorPriceRow','colorSingleRow']){
  const row=$(id);if(!row)continue;
  row.style.opacity=s.offer==='SB + RENKLİ'?'1':'.42';
  row.querySelector('input').disabled=s.offer!=='SB + RENKLİ';
 }
 $('coverZoom').value=s.cover_zoom||100;$('zoomValue').textContent='%'+(s.cover_zoom||100);
 $('coverSpacing').value=s.cover_spacing??12;$('spacingValue').textContent=(s.cover_spacing??12)+' px';
 qs('.palette-card').forEach(el=>el.classList.toggle('active',el.dataset.theme===s.theme));
 qs('.style-pill').forEach(el=>el.classList.toggle('active',el.dataset.style===s.style));
 $('layoutSelect').value=s.layout||'Akıllı';
 const sliders=[['editionSize','edition_font_size',' pt'],['coverEditionSize','cover_edition_font_size',' pt'],['coverBadgeSize','cover_badge_font_size',' pt']];
 sliders.forEach(([id,key,suffix])=>{const el=$(id);if(!el)return;el.value=s[key]??20;$(id+'Value').textContent=el.value+suffix});
 if($('outputResolution'))$('outputResolution').value=String(s.export_scale||2);
}
function generatePresets(){
 const p=$('paletteGrid');p.innerHTML='';
 Object.entries(state.palettes).forEach(([name,c])=>{
  let el=document.createElement('button');el.className='palette-card';el.dataset.theme=name;
  el.innerHTML=`<div class="palette-demo" style="background:linear-gradient(140deg,${c.base},${c.end});color:${c.ink};border-bottom:5px solid ${c.accent}">Aa</div><span class="palette-title">${escapeHTML(name)}</span>`;
  el.onclick=()=>{state.settings.theme=name;updateControls();scheduleRender()};p.append(el)
 });
 const st=$('styleGrid');st.innerHTML='';state.styles.forEach(name=>{
  let el=document.createElement('button');el.className='style-pill';el.dataset.style=name;el.textContent=name;
  el.onclick=()=>{state.settings.style=name;updateControls();scheduleRender()};st.append(el)
 });
 const sel=$('layoutSelect');sel.innerHTML=state.layouts.map(s=>`<option value="${escapeHTML(s)}">${escapeHTML(s)}</option>`).join('');
}
function normalizeCode(value){
 const raw=String(value??'').trim();
 if(/^\\d+(?:[.,]0+)?$/.test(raw))return String(Number(raw.replace(',','.')));
 return raw.toUpperCase();
}
function reconcileSelectedBooks(){
 const current=new Map(state.catalog.map(b=>[normalizeCode(b.code),b]));
 let refreshed=0,removed=0;
 state.books=state.books.flatMap(old=>{
  if(String(old.id||'').startsWith('EXTRA-')||old.group==='Harici kapak')return [old];
  const book=current.get(normalizeCode(old.code));
  if(!book){removed++;return []}
  const nameChanged=normalize(old.name)!==normalize(book.name);
  if(nameChanged)refreshed++;
  return [{...book,
   cover_override:nameChanged?'':(old.cover_override||''),
   badge_override:old.badge_override||'',
   edition_override:old.edition_override||''}];
 });
 return {refreshed,removed};
}
function renderGroups(){
 // Preserve the workbook's first-appearance order instead of alphabetizing.
 const groups=[...new Set(state.catalog.map(b=>b.group).filter(Boolean))];
 const current=$('groupFilter').value;
 $('groupFilter').innerHTML='<option value="">Tüm gruplar</option>'+groups.map(x=>`<option value="${escapeHTML(x)}">${escapeHTML(x)}</option>`).join('');
 if(groups.includes(current))$('groupFilter').value=current;
 const quick=$('quickGroup'),prior=quick.value;
 quick.innerHTML='<option value="">Bir grup seçiniz</option>'+groups.map(x=>`<option value="${escapeHTML(x)}">${escapeHTML(x)}</option>`).join('');
 if(groups.includes(prior))quick.value=prior;
}
function filteredBooks(){const q=normalize($('bookSearch').value.trim()),g=$('groupFilter').value;return state.catalog.filter(b=>(!g||g===b.group)&&(!q||normalize([b.code,b.name,b.group].join(' ')).includes(q)))}
function renderCatalog(){
 const results=filteredBooks();$('catalogCount').textContent=results.length+' kayıt';
 const panel=$('catalogList');panel.innerHTML='';
 for(const book of results){
  const el=document.createElement('button');el.className='catalog-item';
  el.innerHTML=`<span class="code">${escapeHTML(book.code)}</span><span class="name">${escapeHTML(book.name)}</span><span class="plus">+</span>`;
  el.title=book.group;el.onclick=()=>addBook(book);panel.append(el)
 }

 if(!results.length)panel.innerHTML='<div class="empty">Bu aramaya uygun kitap bulunamadı.</div>';
}
function addBook(book){
 if(state.books.length>=30){toast('Bir afişte en fazla 30 kitap olabilir.');return}
 if(state.books.some(x=>x.id===book.id && x.cover_override===book.cover_override)){
  toast('Bu kitap afişte zaten bulunuyor.');return
 }
 state.books.push({...book});afterBooksChanged()
}
function afterBooksChanged(){selectedCover=null;renderSelected();scheduleRender()}
function renderSelected(){
 const el=$('selectedList');el.innerHTML='';$('selectedCount').textContent=state.books.length+' / 30';
 if(!state.books.length){el.innerHTML='<div class="empty">Sol katalogdan kitap seçin veya + harici JPG ekleyin.</div>';return}
 state.books.forEach((book,i)=>{
  const row=document.createElement('div');row.className='selected-item';row.draggable=true;row.dataset.index=i;
  const coverName=book.cover_override?book.cover_override.split(/[\\/]/).pop():'';
  const fromArchive=/^[a-f0-9]{64}\.(jpe?g|png|webp)$/i.test(coverName);
  let img=book.cover_override?`<img src="${fromArchive?'/api/library/asset':'/api/custom-cover'}?name=${encodeURIComponent(coverName)}" alt="kapak">`:`<img src="/api/cover?code=${encodeURIComponent(book.code)}" alt="kapak">`;
  row.innerHTML=`<span class="grip" title="Sürükleyerek sırala">⠿</span>${img}
   <span class="name">${escapeHTML(book.name||'Özel Kapak')}<small>#${escapeHTML(book.code)} · ${escapeHTML(book.group||'Harici')}</small></span>
   <button class="icon-btn" title="Kapak görselini değiştir" data-action="cover">▧</button>
   <button class="icon-btn" title="Baskı / fiyat düzenle (sağ tık)" data-action="edit">⋯</button>
   <button class="icon-btn" title="Listeden çıkar" data-action="remove">×</button>`;
  row.querySelector('[data-action=remove]').onclick=()=>{state.books.splice(i,1);afterBooksChanged()};
  row.querySelector('[data-action=cover]').onclick=()=>{customTarget=i;$('fileCustom').click()};
  row.querySelector('[data-action=edit]').onclick=e=>showCoverMenu(e.clientX,e.clientY,i);
  row.addEventListener('contextmenu',e=>{e.preventDefault();showCoverMenu(e.clientX,e.clientY,i)});
  row.addEventListener('dragstart',ev=>{row.classList.add('dragging');ev.dataTransfer.setData('text/plain',String(i));ev.dataTransfer.effectAllowed='move'});
  row.addEventListener('dragend',()=>row.classList.remove('dragging'));
  row.addEventListener('dragover',ev=>{ev.preventDefault();ev.dataTransfer.dropEffect='move'});
  row.addEventListener('drop',ev=>{ev.preventDefault();const from=Number(ev.dataTransfer.getData('text/plain'));if(!Number.isInteger(from)||from<0||from>=state.books.length||from===i)return;const [book]=state.books.splice(from,1);state.books.splice(i,0,book);afterBooksChanged()});
  el.append(row)

 })
}
let renderInFlight=false;
function scheduleRender(){saveDraftSoon();clearTimeout(renderTimer);renderTimer=setTimeout(()=>void renderPoster(),310)}
async function renderPoster(){
 const n=++latestRender;
 const request={settings:state.settings,books:state.books,square:cropMode};
 $('previewMeta').textContent=`${state.books.length} kitap · ${state.settings.theme} · ${state.settings.layout} · Dışa aktarma ${1200*(state.settings.export_scale||2)}×${1600*(state.settings.export_scale||2)}`;
 try{
  const data=await api('/api/render',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)});
  if(n!==latestRender)return;
  $('poster').src=data.image;
  renderCoverOverlay(data.positions||[],cropMode);
 }catch(e){if(n===latestRender)toast('Önizleme hatası: '+e.message)}
}
function renderCoverOverlay(pos,isSquare){
 const root=$('coverOverlay');root.innerHTML='';
 const croppedTop=isSquare?200:0;
 const sizeHeight=isSquare?1200:1600;
 pos.forEach(([x1,y1,x2,y2,i])=>{
  if(y2<croppedTop||y1>croppedTop+sizeHeight)return;
  const item=document.createElement('button');item.className='cover-hit';item.title=`${i+1}. kitap · swap için iki kapağa sırayla tıkla`;
  item.style.left=x1/12+'%';item.style.width=(x2-x1)/12+'%';
  item.style.top=(Math.max(y1,croppedTop)-croppedTop)/sizeHeight*100+'%';
  item.style.height=(Math.min(y2,croppedTop+sizeHeight)-Math.max(y1,croppedTop))/sizeHeight*100+'%';
  item.addEventListener('contextmenu',e=>{e.preventDefault();showCoverMenu(e.clientX,e.clientY,i)});
  item.onclick=()=>{
   if(selectedCover===null){selectedCover=i;item.classList.add('marked');toast(`${i+1}. kapak seçildi. Yer değiştirmek için ikinci kapağa tıkla.`);return}
   if(selectedCover===i){selectedCover=null;renderCoverOverlay(pos,isSquare);return}
   [state.books[selectedCover],state.books[i]]=[state.books[i],state.books[selectedCover]];
   selectedCover=null;afterBooksChanged();toast('Kapakların yeri değiştirildi.')
  };
  root.append(item)
 })
}
function hideCoverMenu(){const menu=$('coverContext');if(menu)menu.classList.remove('show')}
function showCoverMenu(clientX,clientY,index){
 hideCoverMenu();
 const book=state.books[index];if(!book)return;
 const menu=$('coverContext');
 menu.innerHTML=`<div class="context-title">${escapeHTML(book.code+' · '+book.name)}</div>
  <button data-act="edition">✎ Kitaba özel baskı numarası</button>
  <button data-act="badge">₺ Kitaba özel ekstra fiyat</button>
  <button data-act="clear">⊘ Özel etiketleri kaldır</button>
  <button data-act="remove">× Kitabı afişten kaldır</button>`;
 menu.querySelector('[data-act=edition]').onclick=()=>{
  const result=prompt('Bu kitabın kapağının alt ortasına gelecek baskı numarası (örn. 37. Baskı). Boş = kaldır:',book.edition_override||'');
  if(result!==null){book.edition_override=result.trim().slice(0,40);afterBooksChanged()}
  hideCoverMenu();
 };
 menu.querySelector('[data-act=badge]').onclick=()=>{
  const result=prompt('Bu kitabın kapağının sağ üstüne gelecek ekstra maliyet (örn. +150 TL). Boş = genel ayara dön:',book.badge_override||'');
  if(result!==null){book.badge_override=result.trim().slice(0,35);afterBooksChanged()}
  hideCoverMenu();
 };
 menu.querySelector('[data-act=clear]').onclick=()=>{delete book.edition_override;delete book.badge_override;hideCoverMenu();afterBooksChanged()};
 menu.querySelector('[data-act=remove]').onclick=()=>{state.books.splice(index,1);hideCoverMenu();afterBooksChanged()};
 menu.style.left='0px';menu.style.top='0px';menu.classList.add('show');
 const width=menu.offsetWidth||275,height=menu.offsetHeight||175;
 menu.style.left=Math.min(clientX,innerWidth-width-8)+'px';
 menu.style.top=Math.min(clientY,innerHeight-height-8)+'px';
}
document.addEventListener('click',e=>{if(!e.target.closest('#coverContext')&&!e.target.closest('.cover-hit'))hideCoverMenu()});
document.addEventListener('keydown',e=>{if(e.key==='Escape')hideCoverMenu()});

function addSelectedGroup(){
 const name=$('quickGroup').value;
 if(!name){toast('Önce grup seçiniz.');return}
 const books=state.catalog.filter(b=>b.group===name);
 if(!books.length){toast('Grup boş.');return}
 let added=0;
 for(const book of books){
  if(state.books.length>=30)break;
  if(state.books.some(b=>b.id===book.id))continue;
  state.books.push({...book});added++;
 }
 // Existing headlines and prices are not changed by group selection.
 afterBooksChanged();
 toast(added+' kitap eklendi'+(books.length>30?' · 30 kapak sınırı geçerli':''));
}
let studioRelease=null;
let studioNonce='';
let studioUpdateInProgress=false;
async function studioCheckUpdate(){
 if(studioUpdateInProgress)return;
 studioUpdateInProgress=true;
 $('studioCheckUpdate').disabled=true;
 $('studioInstallUpdate').disabled=true;
 $('studioUpdateStatus').textContent='GitHub kararlı sürümü kontrol ediliyor…';
 try{
  const result=await api('/api/update/check');
  studioRelease=result.release;
  if(result.release.available){
   $('studioUpdateStatus').textContent='Yeni Suite sürümü: '+result.release.latest+' · Kurulu: '+result.current;
   $('studioReleaseNotes').textContent=result.release.notes||'Sürüm notları belirtilmedi.';
   $('studioInstallUpdate').disabled=false;
  }else{
   $('studioUpdateStatus').textContent='Güncel sürümdesin. Suite '+result.current;
   $('studioReleaseNotes').textContent='Yeni güncelleme bulunmadı.';
  }
 }catch(e){
  studioRelease=null;
  $('studioUpdateStatus').textContent='Sürüm kontrolüne erişilemedi: '+e.message;
  $('studioReleaseNotes').textContent='Ağ bağlantısını ve GitHub erişimini kontrol et.';
 }finally{
  studioUpdateInProgress=false;
  $('studioCheckUpdate').disabled=false;
 }
}
async function studioInstallUpdate(){
 if(studioUpdateInProgress||!studioRelease?.available||!studioNonce)return;
 const approved=confirm(
  'Suite '+studioRelease.latest+' yüklensin mi?\n\n'+
  'Yeni kurulum GitHub’dan indirilecek ve SHA-256 ile doğrulanacak. '+
  'Banner Studio kapanacak, Windows kurulum sihirbazı açılacak ve '+
  'kurulum tamamlandığında yeniden başlatılacak.\n\nDevam edilsin mi?');
 if(!approved)return;
 studioUpdateInProgress=true;
 $('studioInstallUpdate').disabled=true;
 $('studioCheckUpdate').disabled=true;
 try{
  $('studioUpdateStatus').textContent='Suite kurulumu indiriliyor ve SHA-256 ile doğrulanıyor…';
  await api('/api/update/download',{
   method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({nonce:studioNonce})
  });
  $('studioUpdateStatus').textContent='Kurulum doğrulandı. Banner Studio kapatılıp kurulum başlatılıyor…';
  await api('/api/update/install',{
   method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({nonce:studioNonce})
  });
  $('studioUpdateStatus').textContent='Kurulum başlatılıyor. Stüdyo penceresi kapanabilir; Windows kurulum sihirbazını tamamla.';
 }catch(e){
  $('studioUpdateStatus').textContent='Güncelleme başarısız: '+e.message;
  $('studioInstallUpdate').disabled=false;
  $('studioCheckUpdate').disabled=false;
 }finally{studioUpdateInProgress=false}
}
function cleanExportName(parts,ext){
 const stem=parts.map(x=>String(x||'').trim()).filter(Boolean).join(' - ')
  .replace(/[<>:"/\\|?*\x00-\x1f]/g,'_').replace(/\s+/g,' ').trim().slice(0,160);
 return (stem||'ALFA_Tasarim')+'.'+ext;
}
function currentExportName(square,format){
 const s=state.settings;
 const subtitle=(s.show_subtitle&&String(s.subtitle||'').trim())?s.subtitle:state.books.length+' Kitap';
 return cleanExportName([s.title_series,s.title_set,subtitle,square?'Kare':''],format==='JPEG'?'jpg':'png');
}
function archiveExportName(entry){
 return cleanExportName([entry.series,entry.set||entry.title,entry.subtitle||entry.books_count+' Kitap'],'png');
}
async function chooseSaveFile(name,mime){
 if(!window.showSaveFilePicker)return {fallback:true};
 try{
  const ext=mime==='image/png'?'.png':mime==='application/zip'?'.zip':'.jpg';
  return {handle:await showSaveFilePicker({suggestedName:name,
   types:[{description:'ALFA dışa aktarım',accept:{[mime]:[ext]}}]})};
 }catch(e){if(e.name==='AbortError')return {cancelled:true};throw e}
}
async function saveImageBlob(blob,name,chosen){
 if(chosen.cancelled)return false;
 if(chosen.handle){
  const writer=await chosen.handle.createWritable();
  try{await writer.write(blob);await writer.close()}catch(e){await writer.abort().catch(()=>{});throw e}
 }else{
  const url=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),10000);
  toast('Tarayıcı indirme klasörü kullanıldı. Edge/Chrome ile kayıt yeri seçilebilir.');
 }
 return true;
}
async function downloadImage(square,format='PNG'){
 if(!state.books.length){toast('Önce afişe kitap ekle.');return}
 const name=currentExportName(square,format);
 let destination;
 try{destination=await chooseSaveFile(name,format==='JPEG'?'image/jpeg':'image/png')}
 catch(e){toast('Kayıt yeri seçilemedi: '+e.message);return}
 if(destination.cancelled)return;
 busy('Yüksek çözünürlüklü afiş hazırlanıyor…',true);
 try{
  const blob=await api('/api/export',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({settings:state.settings,books:state.books,square,format})});
  if(await saveImageBlob(blob,name,destination))
   toast('Görsel kaydedildi ve Tasarım Arşivi’ne eklendi.');
 }catch(e){toast('Görsel kaydedilemedi: '+e.message)}finally{busy('',false)}
}
async function saveToLibrary(){
 if(!state.books.length){toast('Arşive kaydetmek için kitap ekle.');return}
 const name=prompt('Bu tasarım arşivde hangi adla görünsün?',`${state.settings.title_series} · ${state.settings.title_set}`);
 if(name===null)return;
 busy('Afiş kalıcı arşive kaydediliyor…',true);
 try{
  const result=await api('/api/library/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({settings:state.settings,books:state.books,name,format:'PNG'})});
  toast('Tasarım arşive kaydedildi: '+result.saved.title);
 }catch(e){toast('Arşive kaydedilemedi: '+e.message)}finally{busy('',false)}
}
function closeLibrary(){$('libraryModal').classList.remove('show')}
async function openLibrary(){
 $('libraryModal').classList.add('show');$('libraryList').innerHTML='<div class="empty">Kayıtlar açılıyor…</div>';
 try{
  const result=await api('/api/library/list');
  $('libraryLocation').textContent='Bu bilgisayarda · '+result.folder;
  libraryEntries=result.items||[];
  selectedArchiveIds=new Set([...selectedArchiveIds].filter(id=>libraryEntries.some(x=>x.id===id)));
  updateLibrarySelection();
  const list=$('libraryList');list.innerHTML='';
  if(!result.items.length){list.innerHTML='<div class="empty">Henüz kayıt yok. Tasarımı “Arşive Kaydet” ile kaydet veya PNG/JPG indir; burada görünecek.</div>';return}
  result.items.forEach(entry=>{
   const card=document.createElement('article');card.className='library-card';
   const img='/api/library/preview?id='+encodeURIComponent(entry.id);
   card.innerHTML=`<label class="library-pick" title="Toplu ZIP için seç"><input type="checkbox" data-op="pick" ${selectedArchiveIds.has(entry.id)?'checked':''}><span>Seç</span></label><img src="${img}" alt="${escapeHTML(entry.title)}">
    <div class="library-card-body"><strong>${escapeHTML(entry.title)}</strong>
    <small>${escapeHTML((entry.created_at||'').replace('T',' ').slice(0,16))} · ${entry.books_count} kitap · ${escapeHTML(entry.format.toUpperCase())}</small>
    <div class="library-actions"><button data-op="open" class="btn compact gold" ${entry.reason==='import'?'disabled':''}>Düzenle</button>
    <button data-op="download" class="btn compact">Görseli indir</button>
    <button data-op="rename" class="btn compact ghost">Ad</button>
    <button data-op="delete" class="btn compact danger">Sil</button></div></div>`;
   card.querySelector('[data-op=pick]').onchange=e=>{if(e.target.checked)selectedArchiveIds.add(entry.id);else selectedArchiveIds.delete(entry.id);updateLibrarySelection()};
   card.querySelector('[data-op=open]').onclick=async()=>{
    try{const project=await api('/api/library/open?id='+encodeURIComponent(entry.id));
     if(project.editable===false)throw new Error('Bu kayıt dışarıdan eklenmiş bir JPG/PNG. Görüntülenebilir fakat katmanlı proje değildir.');
     state.books=project.books;state.settings={...state.settings,...project.settings};
     updateControls();renderSelected();scheduleRender();closeLibrary();toast('Eski tasarım düzenlemeye açıldı.');
    }catch(e){toast(e.message)}
   };
   card.querySelector('[data-op=download]').onclick=async()=>{
    const name=archiveExportName(entry);
    let chosen;
    try{chosen=await chooseSaveFile(name,'image/png')}
    catch(e){toast('Kayıt yeri: '+e.message);return}
    if(chosen.cancelled)return;
    busy('PNG arşiv görseli hazırlanıyor…',true);
    try{
     const blob=await api('/api/library/png?id='+encodeURIComponent(entry.id));
     await saveImageBlob(blob,name,chosen);
    }catch(e){toast('PNG indirme: '+e.message)}finally{busy('',false)}
   };
   card.querySelector('[data-op=rename]').onclick=async()=>{
    const title=prompt('Tasarımın yeni adı:',entry.title);if(!title?.trim())return;
    try{await api('/api/library/rename',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:entry.id,title})});await openLibrary()}
    catch(e){toast(e.message)}
   };
   card.querySelector('[data-op=delete]').onclick=async()=>{
    if(!confirm('“'+entry.title+'” arşiv kaydı silinsin mi? Bu işlem geri alınamaz.'))return;
    try{await api('/api/library/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:entry.id})});await openLibrary();toast('Kayıt arşivden silindi.')}
    catch(e){toast(e.message)}
   };
   list.append(card)
  });
 }catch(e){$('libraryList').innerHTML='<div class="empty">Arşiv okunamadı: '+escapeHTML(e.message)+'</div>'}
}

function updateLibrarySelection(){
 if($('archiveSelectedCount'))$('archiveSelectedCount').textContent=`${selectedArchiveIds.size} tasarım seçili`;
}
async function downloadArchiveSelection(){
 if(!selectedArchiveIds.size){toast('Toplu indirmek için tasarım seç.');return}
 const ids=[...selectedArchiveIds];let folder=null,chosen=null;
 try{
  if(window.showDirectoryPicker)folder=await window.showDirectoryPicker({mode:'readwrite'});
  else chosen=await chooseSaveFile('ALFA_Tasarim_Arsivi_PNG.zip','application/zip');
 }catch(e){if(e.name==='AbortError')return;toast('Klasör seçilemedi: '+e.message);return}
 if(chosen&&chosen.cancelled)return;
 busy('PNG dosyaları hazırlanıyor…',true);
 try{
  if(folder){
   const manifest=await api('/api/library/export-names',{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids})
   });
   if(!Array.isArray(manifest.files)||manifest.files.length!==ids.length)
    throw new Error('Seçilen dosya listesi eksik.');
   let done=0;
   for(const item of manifest.files){
    $('busyTitle').textContent='PNG kaydediliyor: '+(++done)+' / '+manifest.files.length;
    const blob=await api('/api/library/png?id='+encodeURIComponent(item.id));
    const handle=await folder.getFileHandle(item.name,{create:true});
    const writer=await handle.createWritable();
    try{await writer.write(blob);await writer.close()}
    catch(e){await writer.abort().catch(()=>{});throw e}
   }
   toast('Seçilen klasöre '+done+' PNG kaydedildi. JSON dosyası yok.');
  }else{
   const name='ALFA_Tasarim_Arsivi_PNG.zip';
   const blob=await api('/api/library/bulk-download',{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids})
   });
   await saveImageBlob(blob,name,chosen);
   toast(ids.length+' PNG dosyası arşivlendi. JSON yok.');
  }
 }catch(e){toast('Toplu PNG indirme: '+e.message)}finally{busy('',false)}
}
async function uploadBinary(url,file){return api(url,{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:file})}
function bindUI(){
 $('bookSearch').addEventListener('input',renderCatalog);$('groupFilter').addEventListener('change',renderCatalog);
 $('addFiltered').onclick=()=>{let n=0;for(const item of filteredBooks()){if(state.books.length>=30)break;if(!state.books.some(x=>x.id===item.id)){state.books.push({...item});n++}}afterBooksChanged();toast(n+' kitap eklendi.')};
 $('addQuickGroup').onclick=addSelectedGroup;
 $('studioCheckUpdate').onclick=studioCheckUpdate;
 $('studioInstallUpdate').onclick=studioInstallUpdate;
 $('clearSelection').onclick=()=>{state.books=[];afterBooksChanged()};
 $('resetSwap').onclick=()=>{selectedCover=null;const marked=qs('.cover-hit.marked');marked.forEach(x=>x.classList.remove('marked'));toast('Kapak seçimi temizlendi.')};
 $('toggleCrop').onclick=()=>{cropMode=!cropMode;$('canvasWrap').classList.toggle('square',cropMode);$('toggleCrop').textContent=cropMode?'▤ Tam afişe dön':'▢ Kare kırpma kontrolü';selectedCover=null;scheduleRender()};
 qs('[data-tab]').forEach(el=>el.onclick=()=>{qs('[data-tab]').forEach(x=>x.classList.toggle('active',x===el));qs('.tabpane').forEach(x=>x.classList.toggle('active',x.id==='tab-'+el.dataset.tab))});
 qs('[data-setting]').forEach(el=>{
  const key=el.dataset.setting;const event=el.tagName==='SELECT'||el.type==='checkbox'?'change':'input';
  el.addEventListener(event,()=>{state.settings[key]=el.type==='checkbox'?el.checked:el.value;scheduleRender()})
 });
 qs('[data-offer]').forEach(el=>el.onclick=()=>{state.settings.offer=el.dataset.offer;updateControls();scheduleRender()});
 $('layoutSelect').onchange=()=>{state.settings.layout=$('layoutSelect').value;scheduleRender()};
 $('coverZoom').oninput=()=>{state.settings.cover_zoom=Number($('coverZoom').value);$('zoomValue').textContent='%'+state.settings.cover_zoom;scheduleRender()};
 $('coverSpacing').oninput=()=>{state.settings.cover_spacing=Number($('coverSpacing').value);$('spacingValue').textContent=state.settings.cover_spacing+' px';scheduleRender()};
 [['editionSize','edition_font_size'],['coverEditionSize','cover_edition_font_size'],['coverBadgeSize','cover_badge_font_size']].forEach(([id,key])=>{
  $(id).oninput=()=>{state.settings[key]=Number($(id).value);$(id+'Value').textContent=$(id).value+' pt';scheduleRender()}
 });
 $('outputResolution').onchange=()=>{state.settings.export_scale=Number($('outputResolution').value);saveDraftSoon();toast('Dışa aktarma: '+(1200*state.settings.export_scale)+' × '+(1600*state.settings.export_scale)+' piksel')};
 $('randomSlogan').onclick=()=>{state.settings.slogan=slogans[Math.floor(Math.random()*slogans.length)];updateControls();scheduleRender()};
 $('restoreNotes').onclick=()=>{state.settings.note1='İlan fiyatı yalnız tek kitap içindir; set için mesaj atınız.';state.settings.note2='Lütfen bu ilanı doğrudan satın almayınız.';state.settings.note3='Kitap kodu, set ve baskı türünü mesajla belirtiniz.';updateControls();scheduleRender()};
 $('downloadPoster').onclick=()=>downloadImage(false,'PNG');
 $('downloadJpg').onclick=()=>downloadImage(false,'JPEG');
 $('downloadSquare').onclick=()=>downloadImage(true,'PNG');
 $('openLibrary').onclick=()=>openLibrary();
 $('archiveSelectAll').onclick=()=>{selectedArchiveIds=new Set(libraryEntries.map(x=>x.id));openLibrary()};
 $('archiveClear').onclick=()=>{selectedArchiveIds.clear();openLibrary()};
 $('archiveDownload').onclick=()=>downloadArchiveSelection();
 $('saveLibrary').onclick=()=>saveToLibrary();
 $('closeLibrary').onclick=()=>closeLibrary();
 $('importLibraryImage').onclick=()=>$('fileImportArtwork').click();
 $('pickExcel').onclick=()=>$('fileExcel').click();$('pickCovers').onclick=()=>$('fileCovers').click();$('pickCoverZip').onclick=()=>$('fileCoverZip').click();
 $('addCustom').onclick=()=>{customTarget=null;$('fileCustom').click()};
 $('fileExcel').onchange=async ev=>{
  const file=ev.target.files[0];if(!file)return;
  busy('Excel kodları ve başlıkları doğrulanıyor…',true);
  try{
   const result=await uploadBinary('/api/upload/excel',file);
   state.catalog=result.catalog;
   const counts=reconcileSelectedBooks();
   renderGroups();renderCatalog();renderSelected();showCoverStatus(result);scheduleRender();
   toast('Excel: '+result.total+' kitap, kodlar doğrulandı.'+
    (counts.refreshed?' '+counts.refreshed+' seçili başlık güncellendi.':'')+
    (counts.removed?' '+counts.removed+' eski/kaldırılmış kod afişten çıkarıldı.':''));
  }catch(e){
   toast('Excel değişmedi: '+e.message);
   alert('Excel içe aktarılamadı; önceki katalog korundu.\\n\\n'+e.message);
  }finally{busy('',false);ev.target.value=''}
 };
 $('fileCoverZip').onchange=async ev=>{
  const file=ev.target.files[0];if(!file)return;
  busy('Kapak ZIP arşivi açılıyor (birkaç dakika sürebilir)…',true);
  try{
   const result=await uploadBinary('/api/upload/cover-zip',file);
   state.covers=result.covers;showCoverStatus(result);renderSelected();scheduleRender();
   toast(`${result.uploaded} kapak eklendi · ${result.matched}/${result.total} Excel kaydı eşleşti`);
  }catch(e){toast('Kapak ZIP yüklenemedi: '+e.message)}
  finally{busy('',false);ev.target.value=''}
 };
 $('fileCovers').onchange=async ev=>{
  const files=[...ev.target.files].filter(f=>/\.(png|jpe?g|webp)$/i.test(f.name));if(!files.length){toast('Seçilen klasörde JPG/PNG bulunamadı.');return}
  busy('Kapaklar aktarılıyor: 0 / '+files.length,true);
  let done=0,failed=0;const concurrency=4;let cursor=0;
  async function worker(){while(cursor<files.length){let f=files[cursor++];try{await uploadBinary('/api/upload/cover?name='+encodeURIComponent(f.name),f)}catch(e){failed++}done++;$('busyTitle').textContent=`Kapaklar aktarılıyor: ${done} / ${files.length}`}}
  try{await Promise.all(Array.from({length:Math.min(concurrency,files.length)},worker));let result=await api('/api/upload/commit',{method:'POST'});state.covers=result.covers;showCoverStatus(result);renderSelected();scheduleRender();toast(done-failed+' kapak yüklendi; '+result.matched+' kitapla eşleşti'+(failed?`, ${failed} dosya atlandı`:''))}catch(e){toast(e.message)}finally{busy('',false);ev.target.value=''}
 };
 $('fileCustom').onchange=async ev=>{const file=ev.target.files[0];if(!file)return;busy('Kapak ekleniyor…',true);try{const result=await uploadBinary('/api/upload/custom?name='+encodeURIComponent(file.name),file);if(customTarget!==null&&state.books[customTarget]){state.books[customTarget].cover_override=result.cover_path}else if(state.books.length<30){state.books.push({id:'EXTRA-'+Date.now(),code:'ÖZEL',name:file.name.replace(/\.[^.]+$/,''),group:'Harici kapak',pages:null,color:false,cover_override:result.cover_path,badge_override:'',edition_override:''})}else{toast('30 kapak sınırı dolu.');return}afterBooksChanged();toast('Harici kapak eklendi')}catch(e){toast(e.message)}finally{busy('',false);ev.target.value=''}};
 $('saveProject').onclick=()=>{const data={schema:3,settings:state.settings,books:state.books};const file=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const url=URL.createObjectURL(file);let a=document.createElement('a');a.href=url;a.download='ALFA_Banner_Proje.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Proje JSON indirildi.')};
 $('loadProject').onclick=()=>$('fileProject').click();
 $('fileProject').onchange=async ev=>{const file=ev.target.files[0];if(!file)return;try{const obj=JSON.parse(await file.text());if(![3,4].includes(obj.schema)||!Array.isArray(obj.books)||obj.books.length>30||!obj.settings)throw new Error('Banner Studio proje dosyası değil.');state.books=obj.books;state.settings={...state.settings,...obj.settings};updateControls();renderSelected();scheduleRender();toast('Proje açıldı.')}catch(e){toast('Proje açılamadı: '+e.message)}ev.target.value=''};
 $('fileImportArtwork').onchange=async e=>{const f=e.target.files[0];if(!f)return;busy('Eski afiş arşive alınıyor…',true);try{await uploadBinary('/api/library/import?name='+encodeURIComponent(f.name),f);await openLibrary();toast('Önceden indirilmiş JPG/PNG arşive eklendi.')}catch(err){toast(err.message)}finally{busy('',false);e.target.value=''}};
 $('libraryModal').addEventListener('click',e=>{if(e.target.id==='libraryModal')closeLibrary()});
}
async function boot(){try{const result=await api('/api/bootstrap');state={...state,...result};
  studioNonce=result.update_nonce||'';
  $('studioVersion').textContent='Banner Studio v3.6 · Suite '+(result.suite_version||'bilinmiyor');
 const previous=await api('/api/draft').catch(()=>({draft:null}));
 if(previous.draft){
  state.books=previous.draft.books||[];
  state.settings={...state.settings,...previous.draft.settings};
  const reconciled=reconcileSelectedBooks();
  if(reconciled.removed||reconciled.refreshed)
   toast('Taslak güncel Excel kodlarıyla eşleştirildi.'+
    (reconciled.removed?' '+reconciled.removed+' eski kayıt ayıklandı.':''));
 }
 generatePresets();renderGroups();bindUI();updateControls();renderCatalog();renderSelected();showCoverStatus(result);
 draftReady=true;scheduleRender();
 if(previous.draft)toast('Son çalışman otomatik geri yüklendi.');
 }catch(e){toast('Uygulama başlatılamadı: '+e.message)}}
window.addEventListener('DOMContentLoaded',boot);
