import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'

type Tab = 'ai' | 'studio' | 'store' | 'account'
type Mode = 'general' | 'research' | 'code' | 'plan'
type Model = {
  id:string; name:string; provider:string; provider_label?:string; provider_logo?:string;
  brand_logo?:string; family?:string; developer?:string; capabilities?:string[];
  availability?:string; selectable?:boolean; status_reason?:string; estimated_1k_credits?:number;
  context_length?:number; description?:string; is_froxy?:boolean
}
type Message = { role:'user'|'assistant'; content:string; sources?:{title:string;url:string;snippet?:string}[]; status?:string }
type Product = { id:string; title:string; price_num:number; price:string; image:string; badge?:string; store_category?:string; delivery_label?:string; description?:string; max_qty?:number }
type User = { first_name?:string; wallet_balance?:number; ai_credits?:number; free_text_remaining?:number; free_image_remaining?:number; orders?:Record<string,unknown>[] }
type ImageModel = { id:string; name:string; provider:string; provider_logo?:string; active?:boolean; selectable?:boolean; estimated_credits?:number; status_reason?:string }

declare global { interface Window { Telegram?: { WebApp?: any }; SpeechRecognition?: any; webkitSpeechRecognition?: any } }

const rootPrefix = location.pathname.startsWith('/froxy') ? '/froxy' : ''
const api = (path:string) => `${rootPrefix}${path}`
const initData = () => window.Telegram?.WebApp?.initData || ''
const devId = new URLSearchParams(location.search).get('dev_user_id') || ''
const headers = (json=true):HeadersInit => ({
  ...(json ? {'Content-Type':'application/json'} : {}),
  ...(initData() ? {'X-Telegram-Init-Data':initData()} : {}),
  ...(devId ? {'X-Dev-User-Id':devId} : {})
})
const money = (value=0) => new Intl.NumberFormat('tr-TR',{style:'currency',currency:'TRY'}).format(value)
const uid = () => crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`

function Icon({name,size=20}:{name:string,size?:number}) {
  const paths:Record<string,string> = {
    ai:'M4 6h16v10H7l-3 3V6Zm4 4h8M8 13h5', studio:'M4 5h16v14H4zM4 15l5-5 4 4 2-2 5 5M15 8h.01', store:'M5 8h14l-1 12H6L5 8Zm3 0a4 4 0 0 1 8 0', account:'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0', search:'m21 21-4.3-4.3M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z', plus:'M12 5v14M5 12h14', send:'m22 2-7 20-4-9-9-4 20-7ZM11 13 22 2', close:'M6 6l12 12M18 6 6 18', mic:'M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Zm-7 9a7 7 0 0 0 14 0M12 19v3', cart:'M3 4h2l2 11h10l3-8H6M9 20h.01M17 20h.01', spark:'m12 2 1.8 5.2L19 9l-5.2 1.8L12 16l-1.8-5.2L5 9l5.2-1.8L12 2Z', history:'M3 12a9 9 0 1 0 3-6.7L3 8m0-5v5h5M12 7v5l3 2', chevron:'m8 10 4 4 4-4', copy:'M8 8h11v11H8zM5 16H4V5h11v1', play:'m9 6 9 6-9 6V6Z', trash:'M4 7h16M9 7V4h6v3m3 0-1 13H7L6 7', wallet:'M3 6h18v13H3zM3 10h18', globe:'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm0 0c3 3 3 17 0 20M2 12h20'
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]||paths.spark}/></svg>
}

function Logo({model,size=38}:{model?:Partial<Model>,size?:number}) {
  const src = model?.brand_logo || model?.provider_logo
  return <span className="brand-mark" style={{width:size,height:size}}>{src ? <img src={src} alt="" onError={e=>{e.currentTarget.style.display='none'}}/> : <b>{(model?.family||model?.name||'AI').slice(0,2).toUpperCase()}</b>}</span>
}

function CodeBlock({language,code}:{language:string;code:string}) {
  const [output,setOutput]=useState(''),[running,setRunning]=useState(false)
  const supported=/^(js|javascript|ts|typescript|py|python)$/i.test(language||'')
  const run=()=>{
    if(!supported||running)return;setRunning(true);setOutput('Çalıştırılıyor…')
    const python=/^(py|python)$/i.test(language)
    const source=python
      ? `importScripts('https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js');(async()=>{try{const p=await loadPyodide();self.fetch=()=>{throw Error('Ağ erişimi kapalı')};let r=await p.runPythonAsync(${JSON.stringify(code)});postMessage({ok:true,value:r==null?'':String(r)})}catch(e){postMessage({ok:false,value:String(e)})}})()`
      : `self.fetch=()=>Promise.reject(Error('Ağ erişimi kapalı'));self.XMLHttpRequest=undefined;self.WebSocket=undefined;const logs=[];console.log=(...x)=>logs.push(x.map(String).join(' '));(async()=>{try{let r=await (new Function('return (async()=>{'+${JSON.stringify(code)}+'\n})()'))();postMessage({ok:true,value:[...logs,r==null?'':String(r)].filter(Boolean).join('\n')})}catch(e){postMessage({ok:false,value:String(e)})}})()`
    const worker=new Worker(URL.createObjectURL(new Blob([source],{type:'text/javascript'})))
    const timer=setTimeout(()=>{worker.terminate();setOutput('Çalıştırma 8 saniye sınırını aştı.');setRunning(false)},8000)
    worker.onmessage=e=>{clearTimeout(timer);worker.terminate();setOutput(String(e.data?.value||'(çıktı yok)').slice(0,12000));setRunning(false)}
    worker.onerror=()=>{clearTimeout(timer);worker.terminate();setOutput('Kod güvenli çalışma alanında başlatılamadı.');setRunning(false)}
  }
  return <div className="code-block"><header><span>{language||'code'}</span><div><button onClick={()=>navigator.clipboard.writeText(code)}><Icon name="copy" size={14}/>Kopyala</button>{supported&&<button onClick={run} disabled={running}><Icon name="play" size={14}/>{running?'Çalışıyor':'Çalıştır'}</button>}</div></header><pre><code>{code}</code></pre>{output&&<div className="code-output"><b>Çıktı</b><pre>{output}</pre></div>}</div>
}

function RichText({text}:{text:string}) {
  const parts:any[]=[]; const pattern=/```([\w+-]*)\n([\s\S]*?)```/g; let last=0,match:RegExpExecArray|null,index=0
  while((match=pattern.exec(text))){if(match.index>last)parts.push(<span key={`t${index}`}>{text.slice(last,match.index)}</span>);parts.push(<CodeBlock key={`c${index++}`} language={match[1]} code={match[2].trimEnd()}/>);last=pattern.lastIndex}
  if(last<text.length)parts.push(<span key="tail">{text.slice(last)}</span>)
  return <>{parts}</>
}

function ProductCover({product}:{product:Product}) {
  const title=product.title.toLocaleLowerCase('tr')
  const brand=title.includes('gemini')?['Gemini',`${rootPrefix}/assets/provider_google.svg`]:title.includes('chatgpt')||title.includes('openai')?['OpenAI',`${rootPrefix}/assets/provider_openai.svg`]:title.includes('perplexity')?['Perplexity',`${rootPrefix}/assets/provider_perplexity.svg`]:title.includes('canva')?['Canva','https://cdn.simpleicons.org/canva/FFFFFF']:title.includes('adobe')?['Adobe','https://cdn.simpleicons.org/adobe/FFFFFF']:null
  if(!brand)return <div className="product-art"><img src={product.image} alt={product.title}/><span>{product.badge||'Froxy'}</span></div>
  return <div className={`product-art branded ${brand[0].toLowerCase()}`}><img src={brand[1]} alt={brand[0]}/><span>{brand[0]}</span><b>{product.title}</b></div>
}

function App() {
  const [tab,setTab] = useState<Tab>('ai')
  const [user,setUser] = useState<User>({})
  const [models,setModels] = useState<Model[]>([])
  const [selected,setSelected] = useState<Model|null>(null)
  const [catalogReady,setCatalogReady] = useState(false)
  const [sheet,setSheet] = useState(false)
  const [messages,setMessages] = useState<Message[]>([])
  const [mode,setMode] = useState<Mode>('general')
  const [reasoning,setReasoning] = useState('adaptive')
  const [sending,setSending] = useState(false)
  const [toast,setToast] = useState('')

  const notify=(text:string)=>{setToast(text);setTimeout(()=>setToast(''),2600)}
  const refreshUser=async()=>{try{const r=await fetch(api('/api/me'),{headers:headers(false)});if(r.ok)setUser((await r.json()).user||{})}catch{}}
  useEffect(()=>{
    window.Telegram?.WebApp?.ready?.(); window.Telegram?.WebApp?.expand?.()
    fetch(api('/api/models?scope=recommended&limit=48')).then(r=>r.json()).then(d=>{
      const rows:Model[]=d.models||[]; setModels(rows); setSelected(rows.find(x=>x.id==='froxy-smart')||rows.find(x=>x.selectable||x.availability==='active')||null);setCatalogReady(true)
    }).catch(()=>notify('Model kataloğu yenileniyor'))
    refreshUser()
  },[])

  async function send(text:string) {
    const clean=text.trim(); if(!clean||sending||!selected)return
    const outgoing:Message={role:'user',content:clean}; const assistant:Message={role:'assistant',content:'',status:'Froxy düşünüyor'}
    const history=[...messages,outgoing]; setMessages([...history,assistant]); setSending(true)
    try{
      const response=await fetch(api('/api/chat'),{method:'POST',headers:headers(),body:JSON.stringify({model:selected.id,messages:history.map(({role,content})=>({role,content})),chat_id:uid(),request_id:uid(),mode,reasoning_level:reasoning,web_search:mode==='research',max_tokens:1800})})
      if(!response.ok){const e=await response.json().catch(()=>({}));throw new Error(e.error||'İstek tamamlanamadı')}
      const reader=response.body!.getReader(), decoder=new TextDecoder(); let buffer='',content='',sources:any[]=[]
      while(true){const {done,value}=await reader.read();buffer+=decoder.decode(value||new Uint8Array(),{stream:!done});const blocks=buffer.split('\n\n');buffer=blocks.pop()||''
        for(const block of blocks){let event='message',data='';for(const line of block.split('\n')){if(line.startsWith('event:'))event=line.slice(6).trim();if(line.startsWith('data:'))data+=line.slice(5).trim()}
          if(!data)continue;const payload=JSON.parse(data)
          if(event==='delta')content+=payload.content||''
          if(event==='done')sources=payload.web_sources||[]
          if(event==='error')throw new Error(payload.error||'Model yanıt veremedi')
          setMessages([...history,{role:'assistant',content,status:event==='tool_start'?'Web kaynakları taranıyor':event==='reasoning_status'&&payload.state==='thinking'?'Derin düşünme aktif':'',sources}])
        } if(done)break
      }
      await refreshUser()
    }catch(error:any){setMessages([...history,{role:'assistant',content:`İstek tamamlanamadı: ${error.message}`}])}finally{setSending(false)}
  }

  return <div className="app-shell">
    <header className="app-header">
      <button className="identity" onClick={()=>setTab('ai')}><img src={`${rootPrefix}/assets/froxy_logo.png`} alt="Froxy"/><span><b>Froxy</b><small>{selected?.name||(catalogReady?'Model seç':'Modeller yükleniyor')}</small></span></button>
      <button className="credit-pill" onClick={()=>setTab('account')}><Icon name="wallet" size={16}/><span>{money(user.wallet_balance||0)}</span><i>{(user.ai_credits||0).toLocaleString('tr-TR')} kredi</i></button>
    </header>
    <main className="workspace">
      {tab==='ai'&&<ChatView selected={selected} onModels={()=>setSheet(true)} messages={messages} onSend={send} sending={sending} mode={mode} setMode={setMode} reasoning={reasoning} setReasoning={setReasoning} notify={notify}/>}
      {tab==='studio'&&<Studio user={user} refreshUser={refreshUser} notify={notify}/>}
      {tab==='store'&&<Store user={user} refreshUser={refreshUser} notify={notify}/>}
      {tab==='account'&&<Account user={user} refreshUser={refreshUser} notify={notify}/>}
    </main>
    <nav className="bottom-nav">{([['ai','AI'],['studio','Stüdyo'],['store','Mağaza'],['account','Hesap']] as [Tab,string][]).map(([id,label])=><button key={id} className={tab===id?'active':''} onClick={()=>setTab(id)}><Icon name={id}/><span>{label}</span></button>)}</nav>
    {sheet&&<ModelLibrary current={selected} initial={models} onClose={()=>setSheet(false)} onSelect={m=>{setSelected(m);setSheet(false);notify(`${m.name} seçildi`)}}/>}
    {toast&&<div className="toast">{toast}</div>}
  </div>
}

function ChatView({selected,onModels,messages,onSend,sending,mode,setMode,reasoning,setReasoning,notify}:{selected:Model|null;onModels:()=>void;messages:Message[];onSend:(v:string)=>void;sending:boolean;mode:Mode;setMode:(v:Mode)=>void;reasoning:string;setReasoning:(v:string)=>void;notify:(s:string)=>void}){
  const [value,setValue]=useState(''); const [listening,setListening]=useState(false); const end=useRef<HTMLDivElement>(null)
  useEffect(()=>{end.current?.scrollIntoView({behavior:'smooth'})},[messages,sending])
  const submit=(e?:FormEvent)=>{e?.preventDefault();onSend(value);setValue('')}
  const voice=()=>{const SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR){notify('Bu tarayıcı canlı yazıya çevirmeyi desteklemiyor');return}const r=new SR();r.lang='tr-TR';r.interimResults=true;r.onstart=()=>setListening(true);r.onend=()=>setListening(false);r.onresult=(e:any)=>setValue(Array.from(e.results).map((x:any)=>x[0].transcript).join(''));r.start()}
  const starters=[['Bir konuyu güncel kaynaklarla araştır','research'],['Bu kodu analiz et ve iyileştir','code'],['Fikrim için uygulanabilir plan hazırla','plan'],['Karmaşık bir şeyi sade anlat','general']] as [string,Mode][]
  return <section className="chat-page">
    <div className="chat-toolbar"><button className="model-button" onClick={onModels}><Logo model={selected||undefined}/><span><small>Model</small><b>{selected?.name||'Model seç'}</b></span><Icon name="chevron"/></button><button className="round-button" title="Yeni sohbet" onClick={()=>location.reload()}><Icon name="plus"/></button></div>
    <div className="mode-row">{(['general','research','code','plan'] as Mode[]).map(x=><button key={x} className={mode===x?'active':''} onClick={()=>setMode(x)}>{({general:'Genel',research:'Araştırma',code:'Kod',plan:'Plan'} as any)[x]}</button>)}</div>
    <div className="conversation">
      {!messages.length&&<div className="empty-chat"><div className="orb"><img src={`${rootPrefix}/assets/froxy_logo.png`} alt=""/></div><p className="eyebrow">FROXY AI WORKSPACE</p><h1>Ne üzerinde çalışıyoruz?</h1><p>Model seç, bir çalışma modu belirle ve doğal şekilde anlat.</p><div className="starter-grid">{starters.map(([text,m])=><button key={text} onClick={()=>{setMode(m);setValue(text)}}><Icon name={m==='research'?'globe':m==='code'?'play':'spark'} size={18}/><span>{text}</span></button>)}</div></div>}
      {messages.map((m,i)=><article key={i} className={`message ${m.role}`}><div className="message-label">{m.role==='user'?'Sen':selected?.name||'Froxy'}</div><div className="message-body">{m.content?<RichText text={m.content}/>:<span className="thinking"><i/><i/><i/> {m.status}</span>}</div>{m.sources?.length?<div className="sources"><b>Kaynaklar</b>{m.sources.map((s,j)=><a key={j} href={s.url} target="_blank" rel="noreferrer"><span>{j+1}</span>{s.title}</a>)}</div>:null}{m.role==='assistant'&&m.content&&<div className="message-actions"><button onClick={()=>navigator.clipboard.writeText(m.content)}><Icon name="copy" size={15}/>Kopyala</button><button onClick={()=>speechSynthesis.speak(new SpeechSynthesisUtterance(m.content))}><Icon name="mic" size={15}/>Dinle</button></div>}</article>)}
      <div ref={end}/>
    </div>
    <div className="composer-wrap"><div className="composer-meta"><span>{mode==='research'?'Web araştırması açık':mode==='code'?'Kod araçları hazır':mode==='plan'?'Planlama modu':'Genel asistan'}</span><select value={reasoning} onChange={e=>setReasoning(e.target.value)}><option value="adaptive">Akıllı düşünme</option><option value="fast">Hızlı</option><option value="balanced">Dengeli</option><option value="max">Maksimum</option></select></div><form className="composer" onSubmit={submit}><button type="button" className={listening?'recording':''} onClick={voice}><Icon name="mic"/></button><textarea value={value} onChange={e=>setValue(e.target.value)} placeholder="Froxy'ye mesaj yaz…" rows={1} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();submit()}}}/><button className="send" disabled={!value.trim()||sending}><Icon name="send"/></button></form></div>
  </section>
}

function ModelLibrary({current,initial,onClose,onSelect}:{current:Model|null;initial:Model[];onClose:()=>void;onSelect:(m:Model)=>void}){
  const [rows,setRows]=useState<Model[]>(initial),[query,setQuery]=useState(''),[filter,setFilter]=useState('recommended'),[cursor,setCursor]=useState<string|null>(null),[loading,setLoading]=useState(false)
  const load=async(reset=true)=>{setLoading(true);const params=new URLSearchParams({scope:filter==='recommended'?'recommended':'all',limit:'50'});if(query)params.set('q',query);if(filter==='free')params.set('availability','active');if(!reset&&cursor)params.set('cursor',cursor);const d=await fetch(api(`/api/models?${params}`)).then(r=>r.json());setRows(reset?(d.models||[]):[...rows,...(d.models||[])]);setCursor(d.next_cursor||null);setLoading(false)}
  useEffect(()=>{const t=setTimeout(()=>load(true),250);return()=>clearTimeout(t)},[query,filter])
  return <div className="sheet-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}}><section className="model-sheet"><header><div><p className="eyebrow">MODEL KÜTÜPHANESİ</p><h2>İşin için doğru modeli seç</h2></div><button onClick={onClose}><Icon name="close"/></button></header><div className="library-search"><Icon name="search"/><input autoFocus value={query} onChange={e=>setQuery(e.target.value)} placeholder="Model, aile veya sağlayıcı ara"/></div><div className="library-tabs">{[['recommended','Önerilen'],['all','Tüm modeller'],['free','Çalışanlar']].map(([id,label])=><button className={filter===id?'active':''} onClick={()=>setFilter(id)} key={id}>{label}</button>)}</div><div className="model-list">{rows.map(m=>{const enabled=m.selectable||m.availability==='active';return <button key={m.id} disabled={!enabled} className={current?.id===m.id?'selected':''} onClick={()=>onSelect(m)}><Logo model={m}/><span className="model-copy"><b>{m.name}</b><small>{m.family||m.developer||m.provider_label} · {m.provider_label||m.provider}</small><em>{enabled?`~${m.estimated_1k_credits||1} kredi / 1K`:(m.status_reason||'Kullanılamıyor')}</em></span><span className={`status ${enabled?'ready':''}`}>{enabled?'Hazır':'Bekliyor'}</span></button>})}{!rows.length&&!loading&&<div className="empty-state">Bu filtrede model bulunamadı.</div>}{cursor&&<button className="load-more" onClick={()=>load(false)}>Daha fazla model</button>}{loading&&<div className="skeleton-list"><i/><i/><i/></div>}</div></section></div>
}

function Studio({user,refreshUser,notify}:{user:User;refreshUser:()=>void;notify:(s:string)=>void}){
  const [section,setSection]=useState('generate'),[models,setModels]=useState<ImageModel[]>([]),[model,setModel]=useState(''),[prompt,setPrompt]=useState(''),[ratio,setRatio]=useState('1:1'),[busy,setBusy]=useState(false),[image,setImage]=useState('')
  useEffect(()=>{const modality=['generate','edit','variation','upscale','background'].includes(section)?(section==='generate'?'image':section):section;setModels([]);setModel('');fetch(api(`/api/media/models?modality=${modality}`)).then(r=>r.json()).then(d=>{setModels(d.models||[]);setModel((d.models||[]).find((m:ImageModel)=>m.active)?.id||'')})},[section])
  const generate=async()=>{if(section!=='generate'){notify('Bu işlem için etkin sağlayıcı şeması bekleniyor');return}if(!prompt.trim()||!model)return;setBusy(true);try{const r=await fetch(api('/api/media/jobs'),{method:'POST',headers:headers(),body:JSON.stringify({operation:'generate',model,prompt,ratio,style:'auto',request_id:uid(),job_id:uid()})});const d=await r.json();if(!r.ok)throw new Error(d.error);let job=d.job;for(let i=0;i<50&&['queued','running'].includes(job.status);i++){await new Promise(x=>setTimeout(x,2000));job=await fetch(api(`/api/generation-jobs/${job.job_id}`),{headers:headers(false)}).then(x=>x.json()).then(x=>x.job)}if(job.status!=='completed')throw new Error(job.error||'Üretim zaman aşımına uğradı');setImage(job.image_url);refreshUser();notify('Görsel hazır')}catch(e:any){notify(e.message)}finally{setBusy(false)}}
  const tools=[['generate','Üret'],['edit','Düzenle'],['variation','Varyasyon'],['upscale','Upscale'],['background','Arka plan'],['video','Video'],['audio','Ses']]
  return <section className="page studio-page"><div className="page-heading"><div><p className="eyebrow">FROXY CREATIVE</p><h1>Medya Stüdyosu</h1><p>Tek bir çalışma alanında üret, düzenle ve geliştir.</p></div><span className="quota">{user.free_image_remaining??1} ücretsiz üretim</span></div><div className="tool-strip">{tools.map(([id,label])=><button className={section===id?'active':''} onClick={()=>setSection(id)} key={id}>{label}</button>)}</div><div className="studio-grid"><div className="studio-form"><label>Model</label><select value={model} onChange={e=>setModel(e.target.value)}>{models.map(m=><option key={m.id} value={m.id} disabled={!m.active}>{m.name}{m.active?'':` — ${m.status_reason}`}</option>)}</select><label>İstem</label><textarea value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder={section==='generate'?'Işık, kompozisyon, stil ve sahneyi anlat…':'Referans medya ve talimatlarını ekle…'} rows={6}/><div className="ratio-row">{['1:1','4:5','9:16','16:9'].map(x=><button className={ratio===x?'active':''} onClick={()=>setRatio(x)} key={x}>{x}</button>)}</div><button className="primary" onClick={generate} disabled={busy||!model}>{busy?'Üretiliyor…':section==='generate'?'Görseli üret':'İşlemi başlat'}</button></div><div className="canvas"><div className="canvas-top"><span>Çıktı</span><em>{busy?'İşleniyor':'Hazır'}</em></div>{image?<img src={image} alt="Üretilen görsel"/>:<div className="canvas-empty"><Icon name="studio" size={38}/><b>Üretimin burada görünecek</b><span>Bir model seç ve istemini yaz.</span></div>}</div></div></section>
}

function Store({user,refreshUser,notify}:{user:User;refreshUser:()=>void;notify:(s:string)=>void}){
  const [products,setProducts]=useState<Product[]>([]),[query,setQuery]=useState(''),[category,setCategory]=useState('all'),[cart,setCart]=useState<Record<string,number>>({}),[checkout,setCheckout]=useState(false),[detail,setDetail]=useState<Product|null>(null)
  useEffect(()=>{fetch(api('/api/products')).then(r=>r.json()).then(d=>setProducts(d.products||[]))},[])
  const filtered=products.filter(p=>(category==='all'||p.store_category===category)&&p.title.toLocaleLowerCase('tr').includes(query.toLocaleLowerCase('tr')))
  const items=Object.entries(cart).map(([id,qty])=>({id,qty}));const total=items.reduce((sum,x)=>sum+(products.find(p=>p.id===x.id)?.price_num||0)*x.qty,0);const count=items.reduce((a,b)=>a+b.qty,0)
  const add=(p:Product)=>{setCart({...cart,[p.id]:(cart[p.id]||0)+1});notify('Sepete eklendi')}
  return <section className="page store-page"><div className="store-hero"><div><p className="eyebrow">FROXY MARKET</p><h1>Dijital araçlarını tek yerden yönet.</h1><p>Net teslimat bilgisi, güvenli ödeme ve sade satın alma deneyimi.</p></div><div className="hero-balance"><small>Kullanılabilir bakiye</small><b>{money(user.wallet_balance||0)}</b><span>Shopier 3D Secure</span></div></div><div className="store-controls"><div className="library-search"><Icon name="search"/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Ürün ara"/></div><div className="category-row">{[['all','Tümü'],['chatgpt','OpenAI'],['gemini','Gemini'],['perplexity','Perplexity'],['credits','Kredi']].map(([id,label])=><button className={category===id?'active':''} onClick={()=>setCategory(id)} key={id}>{label}</button>)}</div></div><div className="product-grid">{filtered.map(p=><article className="product-card" key={p.id}><button className="product-open" onClick={()=>setDetail(p)}><ProductCover product={p}/></button><div className="product-info"><small>{p.delivery_label||'Dijital teslimat'}</small><h3>{p.title}</h3><div><b>{money(p.price_num)}</b><button onClick={()=>add(p)}><Icon name="plus" size={17}/>Sepete ekle</button></div></div></article>)}</div>{count>0&&<button className="floating-cart" onClick={()=>setCheckout(true)}><span><Icon name="cart"/><b>{count} ürün</b></span><strong>{money(total)} · Devam</strong></button>}{detail&&<div className="sheet-backdrop"><section className="checkout-sheet product-detail"><header><div><p className="eyebrow">ÜRÜN DETAYI</p><h2>{detail.title}</h2></div><button onClick={()=>setDetail(null)}><Icon name="close"/></button></header><ProductCover product={detail}/><p>{detail.description||detail.delivery_label||'Dijital teslimat'}</p><div className="checkout-total"><span>Fiyat</span><b>{money(detail.price_num)}</b></div><button className="primary" onClick={()=>{add(detail);setDetail(null)}}>Sepete ekle</button></section></div>}{checkout&&<Checkout products={products} cart={cart} total={total} user={user} close={()=>setCheckout(false)} done={()=>{setCart({});setCheckout(false);refreshUser()}} notify={notify}/>}</section>
}

function Checkout({products,cart,total,user,close,done,notify}:{products:Product[];cart:Record<string,number>;total:number;user:User;close:()=>void;done:()=>void;notify:(s:string)=>void}){
  const [mode,setMode]=useState<'wallet'|'card'|'hybrid_shortfall'>((user.wallet_balance||0)>=total?'wallet':'hybrid_shortfall'),[busy,setBusy]=useState(false)
  const submit=async()=>{setBusy(true);try{const r=await fetch(api('/api/checkout'),{method:'POST',headers:headers(),body:JSON.stringify({mode,items:Object.entries(cart).map(([id,qty])=>({id,qty})),idempotency_key:uid()})});const d=await r.json();if(!r.ok)throw new Error(d.error);if(d.completed){notify('Sipariş tamamlandı');done()}else if(d.payment_url){window.Telegram?.WebApp?.openLink?.(d.payment_url)||window.open(d.payment_url,'_blank');notify('Güvenli ödeme açıldı')}}catch(e:any){notify(e.message)}finally{setBusy(false)}}
  const short=Math.max(0,total-(user.wallet_balance||0))
  return <div className="sheet-backdrop"><section className="checkout-sheet"><header><div><p className="eyebrow">GÜVENLİ ÖDEME</p><h2>Sepetini tamamla</h2></div><button onClick={close}><Icon name="close"/></button></header><div className="checkout-items">{Object.entries(cart).map(([id,qty])=>{const p=products.find(x=>x.id===id)!;return <div key={id}><img src={p.image}/><span><b>{p.title}</b><small>{qty} × {money(p.price_num)}</small></span><strong>{money(p.price_num*qty)}</strong></div>})}</div><div className="checkout-total"><span>Toplam</span><b>{money(total)}</b></div><div className="pay-options"><button className={mode==='wallet'?'active':''} disabled={(user.wallet_balance||0)<total} onClick={()=>setMode('wallet')}><Icon name="wallet"/><span><b>Froxy bakiye</b><small>{money(user.wallet_balance||0)} kullanılabilir</small></span></button><button className={mode==='hybrid_shortfall'?'active':''} onClick={()=>setMode('hybrid_shortfall')}><Icon name="spark"/><span><b>Bakiyeyi kullan, farkı öde</b><small>{money(short)} Shopier ile</small></span></button><button className={mode==='card'?'active':''} onClick={()=>setMode('card')}><Icon name="cart"/><span><b>Tamamını kartla öde</b><small>Shopier 3D Secure</small></span></button></div><button className="primary" disabled={busy} onClick={submit}>{busy?'Hazırlanıyor…':mode==='wallet'?`${money(total)} bakiyeden öde`:'Shopier ile devam et'}</button></section></div>
}

function Account({user,refreshUser,notify}:{user:User;refreshUser:()=>void;notify:(s:string)=>void}){
  const [amount,setAmount]=useState(100),[watch,setWatch]=useState<any[]>([]),[topic,setTopic]=useState('')
  const loadWatch=()=>fetch(api('/api/research/watchlists'),{headers:headers(false)}).then(r=>r.ok?r.json():{watchlists:[]}).then(d=>setWatch(d.watchlists||[]));useEffect(()=>{loadWatch()},[])
  const topup=async()=>{const d=await fetch(api('/api/balance/create-dynamic-topup'),{method:'POST',headers:headers(),body:JSON.stringify({amount,idempotency_key:uid()})}).then(r=>r.json());if(d.payment_url){window.Telegram?.WebApp?.openLink?.(d.payment_url)||window.open(d.payment_url,'_blank')}else notify(d.error||'Ödeme açılamadı')}
  const addWatch=async()=>{if(!topic.trim())return;await fetch(api('/api/research/watchlists'),{method:'POST',headers:headers(),body:JSON.stringify({topic,query:topic})});setTopic('');loadWatch()}
  return <section className="page account-page"><div className="account-card"><div><p className="eyebrow">FROXY HESABIN</p><h1>{user.first_name||'Froxy kullanıcısı'}</h1></div><div className="account-balances"><span><small>Mağaza bakiyesi</small><b>{money(user.wallet_balance||0)}</b></span><span><small>AI kredisi</small><b>{(user.ai_credits||0).toLocaleString('tr-TR')}</b></span></div><div className="quota-grid"><span><b>{user.free_text_remaining??3}</b><small>ücretsiz sohbet</small></span><span><b>{user.free_image_remaining??1}</b><small>ücretsiz görsel</small></span></div></div><div className="panel"><div className="panel-heading"><div><h2>Bakiye yükle</h2><p>İstediğin tutarı Shopier ile güvenle ekle.</p></div></div><div className="amount-row">{[50,100,250,500].map(x=><button className={amount===x?'active':''} onClick={()=>setAmount(x)} key={x}>₺{x}</button>)}<input type="number" min="10" value={amount} onChange={e=>setAmount(Number(e.target.value))}/></div><button className="primary" onClick={topup}>Shopier ile {money(amount)} yükle</button></div><div className="panel"><div className="panel-heading"><div><h2>Takip listesi</h2><p>Güncel kalmak istediğin konuları kaydet.</p></div></div><div className="watch-form"><input value={topic} onChange={e=>setTopic(e.target.value)} placeholder="Örn. Yapay zekâ mevzuatı"/><button onClick={addWatch}><Icon name="plus"/></button></div><div className="watch-list">{watch.map(w=><article key={w.watch_id}><span><b>{w.topic}</b><small>{w.refreshed_at?'Sonuçlar güncel':'Yenilenmeyi bekliyor'}</small></span><button onClick={async()=>{await fetch(api(`/api/research/watchlists/${w.watch_id}/refresh`),{method:'POST',headers:headers()});loadWatch()}}><Icon name="globe" size={16}/>Yenile</button></article>)}{!watch.length&&<div className="empty-state">Henüz takip konusu yok.</div>}</div></div><div className="panel"><div className="panel-heading"><div><h2>Siparişler</h2><p>{user.orders?.length||0} kayıtlı sipariş</p></div><button onClick={refreshUser} className="text-button">Yenile</button></div></div></section>
}

export default App
