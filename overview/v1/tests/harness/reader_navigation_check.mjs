import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import * as navigation from '../../static/js/reader-navigation.mjs';
import * as navShell from '../../static/js/nav-shell.mjs';
import * as reconcile from '../../static/js/dom-reconcile.mjs';
const read = path => readFileSync(new URL(path, import.meta.url), 'utf8');
class Element {
  constructor() { this.children=[];this.listeners={};this.value='';this.options=[];this.style={};this.dataset={};this.hidden=false;this.classList={add(){},remove(){},toggle(){}};this.textContent='';this.innerHTML='';this.scrollLeft=0;this.scrollWidth=0;this.clientWidth=0; }
  append(...nodes){this.children.push(...nodes);}
  appendChild(node){this.append(node);}
  replaceChildren(...nodes){this.children=nodes.length?nodes:[];}
  add(node){this.options.push(node);}
  addEventListener(type,fn){(this.listeners[type] ||= []).push(fn);}
  async fire(type,event={}){for(const fn of this.listeners[type] || [])await fn({preventDefault(){},...event});await settle();}
  setAttribute(name,value){this[name]=value;}
  getAttribute(name){return this[name];}
  querySelector(selector){
    if(selector==='.bp-nav') return this._nav || null;
    if(selector==='.bp-nav a[aria-current="page"]') return this._current || null;
    return new Element();
  }
  getBoundingClientRect(){return {left:0,top:0,width:this.clientWidth || 100,height:20};}
  focus(){}
  scrollIntoView(){this._scrolledIntoView=true;}
  scrollTo({left}){this.scrollLeft=left;}
}
class TemplateElement extends Element {
  set innerHTML(value) { this._html = value || ''; this._parsed=[]; for(const match of (value||'').matchAll(/<img\b[^>]*>/gi)) this._parsed.push(match[0]); }
  get content() {
    const frag = new Element();
    if(!this._html) return frag;
    if(this._parsed?.length) {
      for(const tag of this._parsed) {
        const node = new Element();
        node.outerHTML = tag;
        frag.children.push(node);
      }
      return frag;
    }
    const node = new Element();
    node.textContent = this._html || '';
    frag.children.push(node);
    return frag;
  }
}
const settle = async()=>{for(let i=0;i<20;i++)await Promise.resolve();};
function environment(path) {
  const nodes=new Map(), get=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
  const context={URL,URLSearchParams,AbortController,AbortSignal,Event,console,navigation,reconcile,location:new URL(path,'https://desk.example'),setInterval(){},setTimeout(){},clearTimeout(){},Option:class extends Element {constructor(text,value){super();this.textContent=text;this.value=value;}},localStorage:{getItem(){return null;}}};
  context.navigation={...navigation,readerHref:href=>navigation.readerHref(href,context.location)};
  context.navShell=navShell;
  context.document={getElementById:get,createElement:tag=>tag==='template'?new TemplateElement():new Element(),querySelector:get,body:new Element(),scrollingElement:new Element(),addEventListener(){},dispatchEvent(){}};
  context.window={addEventListener(){},dispatchEvent(){},scrollTo(calls){context.window._scrollCalls=(context.window._scrollCalls||[]).concat([calls]);},__MAP_V1_AUTOBOOT__:false,_scrollY:0,get scrollY(){return this._scrollY;}};
  context.sessionStorage={store:{},getItem(key){return this.store[key]||null;},setItem(key,value){this.store[key]=value;},removeItem(key){delete this.store[key];}};
  context.history={state:null,replaceState(state,unused,url){context.location=new URL(url,context.location);}};
  context.CustomEvent=class {};
  return {context:vm.createContext(context),get};
}
async function run(name,env) {
  // Inject the real shared module without Node needing browser absolute imports.
  const source=read('../../static/js/'+name)
    .replace("await import('/js/reader-navigation.mjs')",'navigation')
    .replace("await import('/js/nav-shell.mjs')",'navShell');
  vm.runInContext(source,env.context);
  await settle();
}
const work='/work?project=example&assignment=worker%3Abuilder&status=in_progress&q=a%26b+%23%2F#row%20two';
const map='/map?path=example%2Fdocs&md=example%2Fdocs%2FGuide.md#section%202';
const calendar='/calendar?project=product&day=2026-09-13';
const timeline='/timeline?project=example&source=worklane&actor=you';
for(const target of [work,map,calendar,timeline,'/work/','/calendar/','/timeline/','#bad','/map?path=a%25b#hash']) {
  const expected=target==='#bad'?'/work':target;
  assert.equal(navigation.safeReturnTo(target),expected);
}
const unsafe=[null,'','https://evil.example/work','https://desk.example/work','//evil.example','///evil.example','javascript:alert(1)','data:text/html,test','/\\evil.example','/work\\@evil.example',' /map','/map\n?path=x','/map\t','/%2f%2fevil.example','/work/../settings','/map/%2e%2e/settings','/api/work-order/action','/work-order?id=x','/mapx','/calendarx','/work%3f@evil.example'];
for(const target of unsafe)assert.equal(navigation.safeReturnTo(target),'/work',String(target));
for(const target of [work,map,timeline,...unsafe.filter(x=>typeof x==='string')]) {
  const env=environment('/work-order?project=example&id=ex-1&'+new URLSearchParams({return_to:target}));
  const calls=[];
  env.context.fetch=async url=>{calls.push(url);return {ok:true,json:async()=>({project:'example',ext_id:'ex-1',comments:[]})};};
  await run('work-order.js',env);
  assert.equal(env.get('reader-back').href,navigation.safeReturnTo(target));
  assert.equal(calls.length,1);
  assert.ok(calls[0].startsWith('/api/work-order?'));
  assert.equal(env.get('order').hidden,false);
}
{
  const env=environment('/work-order?project=example&id=ex-1');
  env.context.fetch=async()=>({ok:false,json:async()=>({error:'Unavailable'})});
  await run('work-order.js',env);
  assert.equal(env.get('reader-back').href,'/work');
  assert.equal(env.get('message').textContent,'Unavailable');
}
{
  const env=environment(work);
  // Expose only the existing URL factory for assertion; the full script runs.
  const source=read('../../static/js/operations.js').replace("await import('/js/reader-navigation.mjs')",'navigation').replace("await import('/js/change-feed.mjs')",'{connectChanges(){return {stop(){}};}}').replace("await import('/js/dom-reconcile.mjs')",'reconcile').replace("await import('/js/calendar.v1.js')",'{buildLoadByDay(){return {state:"empty",origin:"",days:[],total:0};},paintLoad(){},paintDoors(){}}').replace('function orderRow(order)', 'window.testWorkUrl = workUrl;\nfunction orderRow(order)');
  env.context.fetch=async()=>({ok:false});
  await vm.runInContext(source,env.context);await settle();
  const href=env.context.window.testWorkUrl({project:'example',id:'ex-1'});
  assert.equal(new URL(href,'https://desk.example').searchParams.get('return_to'),work);
  env.get('search').value='new & query';
  await env.get('search').fire('input');
  assert.equal(env.context.location.hash,'#row%20two');
  assert.equal(env.context.location.searchParams.get('q'),'new & query');
}
{
  const env=environment(calendar);
  const source=read('../../static/js/operations.js').replace("await import('/js/reader-navigation.mjs')",'navigation').replace("await import('/js/change-feed.mjs')",'{connectChanges(){return {stop(){}};}}').replace("await import('/js/dom-reconcile.mjs')",'reconcile').replace("await import('/js/calendar.v1.js')",'{buildLoadByDay(){return {state:"empty",origin:"",days:[],total:0};},paintLoad(){},paintDoors(){}}').replace('function datedHref(event)', 'window.testDatedHref = datedHref;\nfunction datedHref(event)');
  env.context.fetch=async()=>({ok:false});
  await vm.runInContext(source,env.context);await settle();
  const href=env.context.window.testDatedHref({product:'product',task_id:'pc-1'});
  assert.equal(new URL(href,'https://desk.example').searchParams.get('return_to'),calendar);
}
{
  const env=environment('/work-order?project=example&id=ex-1&'+new URLSearchParams({return_to:calendar}));
  env.context.fetch=async()=>({ok:true,json:async()=>({project:'example',ext_id:'ex-1',comments:[]})});
  await run('work-order.js',env);
  assert.equal(env.get('reader-back').href,calendar);
  assert.equal(env.get('reader-back').textContent,'Back to Calendar');
}
{
  const env=environment('/work-order?project=example&id=ex-1&'+new URLSearchParams({return_to:timeline}));
  env.context.fetch=async()=>({ok:true,json:async()=>({project:'example',ext_id:'ex-1',comments:[]})});
  await run('work-order.js',env);
  assert.equal(env.get('reader-back').href,timeline);
  assert.equal(env.get('reader-back').textContent,'Back to Timeline');
}
{
  const env=environment(map);
  env.context.fetch=async()=>({ok:true,json:async()=>({total:2,issues:[],scope:'Workspace',limit:50,results:[
    {href:'/work-order?project=example&id=ex-1',title:'Example'},
    {href:'/map?path=other',title:'Folder'}
  ]})});
  await run('workspace-search.js',env);
  env.get('workspace-query').value='Example';
  await env.get('workspace-search-form').fire('submit');
  const [link,folder]=env.get('workspace-search-hits').children;
  assert.equal(new URL(link.href,'https://desk.example').searchParams.get('return_to'),map);
  assert.equal(folder.href,'/map?path=other');
  for(const action of ['click','auxclick','contextmenu']){
    env.context.location=new URL('/map?path='+action+'#retained','https://desk.example');
    await link.fire(action);
    assert.equal(new URL(link.href,'https://desk.example').searchParams.get('return_to'),'/map?path='+action+'#retained');
  }
}
// Execute the Map host with real view state and stubbed painting/data/reader.
{
  const env=environment(map);
  const viewSource=read('../../../../map/v1/static/js/view-state.js');
  const {createViewState}=await import('data:text/javascript;base64,'+Buffer.from(viewSource).toString('base64'));
  let md=null, closeCallback;
  Object.assign(env.context,{
    createViewState, fetch:async()=>{throw new Error("Unexpected Map request");},
    createMapTree:()=>({binder:{name:'Workspace'},load:async()=>{},topLots:()=>[],childrenAt:async()=>[{name:'Guide.md',relPath:'other/Guide.md',hasMd:true}]}),
    createMdViewer:({onClose})=>{closeCallback=onClose;return {mount(){},open:async path=>{md=path;},currentPath:()=>md,isOpen:()=>!!md,close(){md=null;onClose();}};},
    createHitRouter:()=>({classify:()=>({layer:'empty'})}),
    ensureLayers(){},paintHub(){},paintLots(){},paintDigIn(){},clearDigIn(){},fitTransform(){return '';}
  });
  let source=read('../../../../map/v1/static/js/workspace_map_app.v1.js').replace(/import[\s\S]*?from '[^']+';/g,'').replace('export async function boot','async function boot');
  vm.runInContext(source+'\nwindow.testBoot=boot;',env.context);
  const app=await env.context.window.testBoot();await settle();
  assert.equal(env.context.location.searchParams.get('path'),'example/docs');
  assert.equal(env.context.location.searchParams.get('md'),'example/docs/Guide.md');
  assert.equal(env.context.location.hash,'#section%202');
  app.viewer.close();await settle();
  assert.equal(env.context.location.searchParams.has('md'),false);
  await app.digInto({relPath:'other',name:'Other'});await settle();
  assert.equal(env.context.location.searchParams.get('path'),'other');
  await env.get('map-browser-list').children.find(node=>node.listeners.click).fire('click');
  assert.equal(env.context.location.searchParams.get('md'),'other/Guide.md');
  app.viewer.close();app.resetView();await settle();
  assert.equal(env.context.location.pathname,'/map');
  assert.equal(env.context.location.searchParams.has('path'),false);
  assert.equal(env.context.location.searchParams.has('md'),false);
}
{
  const nav=new Element(); nav.clientWidth=200; nav.scrollWidth=600; nav.scrollLeft=0;
  const current=new Element(); current.clientWidth=80; current.setAttribute('aria-current','page');
  current.getBoundingClientRect=()=>({left:300,top:0,width:80,height:20});
  nav.getBoundingClientRect=()=>({left:0,top:0,width:200,height:20});
  const root={
    querySelector(sel){
      if(sel==='.bp-nav') return nav;
      if(sel==='.bp-nav a[aria-current="page"]') return current;
      return null;
    },
    body:{classList:{contains(){return false;}}}
  };
  navShell.ensureActiveNavVisible(root);
  assert.ok(nav.scrollLeft>0,'nav scrollLeft should move active tab into view');
  assert.equal(current._scrolledIntoView,undefined,'active tab must not scrollIntoView the document');
}
{
  const payload='<img src=x onerror=alert(1)>';
  const env=environment('/work-order?project=example&id=ex-1');
  env.context.fetch=async()=>({ok:true,json:async()=>({
    project:'example',ext_id:'ex-1',title:'Test',priority:3,status:'in_progress',
    description_html:'<p>safe</p>',comments:[{author:'you',created_at:'2026-09-13',body:payload}]
  })});
  await run('work-order.js',env);
  const painted=env.context.window.paintComment({author:'you',created_at:'2026-09-13',body:payload});
  const body=painted.children[1];
  assert.equal(body.textContent,payload);
  assert.equal(body.children.length,0);
}
console.log('Reader navigation: security, query/hash round trips, reader request count, Work filters, search activation, Map state, nav scroll, and untrusted comment paint passed.');
