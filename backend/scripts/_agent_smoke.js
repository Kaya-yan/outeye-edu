(function(){
if(window.__veAgent)return;window.__veAgent=true;
var CH="smoke-ch";
function send(t,p){try{parent.postMessage({ve:1,ch:CH,type:t,payload:p||{}},'*')}catch(e){}}
var pickOn=false,curSel=null,hoverBox=null,freezeEl=null;
var patchesDom=[],lastCss='',applying=false;
var editing=false,editEl=null,editOrig=null;
var mo=null,moTimer=0;
var dragPending=null,drag=null,lineEl=null,ghostBox=null,dragStyle=null,handleEl=null;
function ensureHover(){
if(hoverBox)return;
hoverBox=document.createElement('div');
hoverBox.id='ve-hover-box';
hoverBox.setAttribute('data-ve-ui','hover');
hoverBox.style.cssText='position:fixed;pointer-events:none;z-index:2147483646;border:1.5px dashed #2563eb;background:rgba(37,99,235,.06);display:none';
document.documentElement.appendChild(hoverBox);
}
function setFreeze(on){
if(on&&!freezeEl){freezeEl=document.createElement('style');freezeEl.id='ve-freeze';
freezeEl.textContent='*,*::before,*::after{animation-play-state:paused !important;transition:none !important}';
(document.head||document.documentElement).appendChild(freezeEl);}
if(!on&&freezeEl){freezeEl.parentNode.removeChild(freezeEl);freezeEl=null;}
}
function attrSel(name,val){
var v=String(val).replace(/\\/g,'\\\\').replace(/"/g,'\\"');
return '['+name+'="'+v+'"]';
}
function stableAttr(el){
if(!el.getAttribute)return null;
var oe=el.getAttribute('data-oe-id');
if(oe)return attrSel('data-oe-id',oe);
var vi=el.getAttribute('data-ve-insert');
if(vi)return attrSel('data-ve-insert',vi);
var pg=el.getAttribute('data-page');
if(pg)return attrSel('data-page',pg);
return null;
}
function cssPath(el){
if(!el||el.nodeType!==1)return '';
if(el===document.documentElement)return 'html';
if(el===document.body)return 'body';
var parts=[],e=el,depth=0;
while(e&&e.nodeType===1&&depth<9){
var anchor=stableAttr(e);
if(anchor){parts.unshift(anchor);break;}
var s=e.tagName.toLowerCase();
var n=1,p=e.previousElementSibling;
while(p){if(p.tagName===e.tagName)n++;p=p.previousElementSibling;}
var hasSame=false,q=e.nextElementSibling;
while(q){if(q.tagName===e.tagName){hasSame=true;break;}q=q.nextElementSibling;}
if(n>1||hasSame)s+=':nth-of-type('+n+')';
parts.unshift(s);
if(e===document.body)break;
e=e.parentElement;depth++;
}
return parts.join(' > ');
}
function info(el){
var r=el.getBoundingClientRect(),cs=getComputedStyle(el);
var chain=[],e=el;
while(e&&e.nodeType===1&&chain.length<9){
chain.unshift({tag:e.tagName.toLowerCase(),component:(e.getAttribute&&e.getAttribute('data-component'))||'',selector:cssPath(e)});
e=e.parentElement;}
var sibs=[];
if(el.parentNode){
var cs2=el.parentNode.children;
for(var k=0;k<cs2.length;k++){var c=cs2[k];
if(c.tagName===el.tagName&&!c.hasAttribute('data-ve-insert'))sibs.push(c);}
}
return {
tag:el.tagName.toLowerCase(),
id:el.id||'',
cls:(el.getAttribute('class')||'').slice(0,140),
component:el.getAttribute('data-component')||'',
page:el.getAttribute('data-page')||'',
pageTitle:el.getAttribute('data-title')||'',
selector:cssPath(el),
oeId:el.getAttribute('data-oe-id')||'',
src:el.tagName==='IMG'?(el.getAttribute('src')||'').slice(0,300):'',
rect:{x:r.left,y:r.top,w:r.width,h:r.height},
text:(el.innerText||'').replace(/\s+/g,' ').slice(0,120),
childCount:el.childElementCount,
siblingIndex:sibs.indexOf(el),
siblingCount:sibs.length,
styles:{display:cs.display,fontSize:cs.fontSize,fontWeight:cs.fontWeight,fontFamily:String(cs.fontFamily).slice(0,60),color:cs.color,background:cs.backgroundColor,textAlign:cs.textAlign,lineHeight:cs.lineHeight,margin:cs.margin,padding:cs.padding},
chain:chain
};
}
function moveToIndex(el,idx){
var par=el.parentNode;if(!par)return;
var kids=[],all=par.children;
for(var k=0;k<all.length;k++){var c=all[k];
if(c.tagName===el.tagName&&c!==el&&!c.hasAttribute('data-ve-insert'))kids.push(c);}
var i=Math.max(0,Math.min(Math.round(idx||0),kids.length));
if(i===kids.length)par.appendChild(el);
else par.insertBefore(el,kids[i]);
}
function dragSiblings(el){
var par=el.parentNode;
if(!par||par.nodeType!==1||par===document.documentElement)return null;
var all=par.children,kids=[],i,c;
for(i=0;i<all.length;i++){c=all[i];
if(c!==el&&c.tagName===el.tagName&&!c.hasAttribute('data-ve-insert')&&!c.hasAttribute('data-ve-ui'))kids.push(c);}
return kids;
}
function dragListIndex(el){
var par=el.parentNode;if(!par)return -1;
var all=par.children,L=[],i,c;
for(i=0;i<all.length;i++){c=all[i];
if(c.tagName===el.tagName&&!c.hasAttribute('data-ve-insert')&&!c.hasAttribute('data-ve-ui'))L.push(c);}
return L.indexOf(el);
}
function ensureDragUi(){
if(!lineEl){
lineEl=document.createElement('div');
lineEl.id='ve-drag-line';
lineEl.setAttribute('data-ve-ui','drag');
lineEl.style.cssText='position:fixed;display:none;pointer-events:none;z-index:2147483645;background:#2563eb;border-radius:2px;box-shadow:0 0 0 2px rgba(37,99,235,.25)';
document.documentElement.appendChild(lineEl);
}
if(!ghostBox){
ghostBox=document.createElement('div');
ghostBox.id='ve-drag-ghost';
ghostBox.setAttribute('data-ve-ui','drag');
ghostBox.style.cssText='position:fixed;display:none;pointer-events:none;z-index:2147483644;border:1.5px dashed #2563eb;background:rgba(37,99,235,.07);align-items:center;justify-content:center;font:12px/1.4 system-ui,sans-serif;color:#2563eb;overflow:hidden;padding:4px;opacity:.9';
document.documentElement.appendChild(ghostBox);
}
if(!dragStyle){
dragStyle=document.createElement('style');
dragStyle.id='ve-drag-style';
dragStyle.textContent='body{cursor:grabbing !important;user-select:none !important;-webkit-user-select:none !important}';
}
}
function ensureHandle(){
if(handleEl)return;
handleEl=document.createElement('div');
handleEl.id='ve-drag-handle';
handleEl.setAttribute('data-ve-ui','handle');
handleEl.setAttribute('title','按住拖动调整位置（Esc 取消）');
handleEl.textContent='⋮⋮';
handleEl.style.cssText='position:fixed;display:none;pointer-events:auto;z-index:2147483646;background:#2563eb;color:#fff;font:12px/1 system-ui,sans-serif;padding:5px 7px;border-radius:6px;cursor:grab;user-select:none;-webkit-user-select:none;box-shadow:0 1px 5px rgba(30,58,95,.35)';
document.documentElement.appendChild(handleEl);
}
function positionHandle(){
ensureHandle();
if(!pickOn||!curSel||!curSel.parentNode||drag||editing){handleEl.style.display='none';return;}
var kids=dragSiblings(curSel);
if(!kids||kids.length<1){handleEl.style.display='none';return;}
var r=curSel.getBoundingClientRect();
if(r.width<1&&r.height<1){handleEl.style.display='none';return;}
handleEl.style.display='block';
handleEl.style.left=r.left+'px';
handleEl.style.top=(r.top>24?(r.top-22):2)+'px';
}
function startDrag(ev){
drag={el:dragPending.el,kids:dragPending.kids,drop:-1,pid:ev.pointerId,w:0,h:0,prevOpacity:''};
dragPending=null;
try{if(drag.el.setPointerCapture)drag.el.setPointerCapture(ev.pointerId);}catch(e){}
ensureDragUi();
(document.head||document.documentElement).appendChild(dragStyle);
if(hoverBox)hoverBox.style.display='none';
if(handleEl)handleEl.style.display='none';
var r=drag.el.getBoundingClientRect();
drag.w=r.width;drag.h=r.height;
drag.prevOpacity=drag.el.style.opacity;
drag.el.style.opacity='.35';
ghostBox.textContent=((drag.el.innerText||'').replace(/\s+/g,' ').slice(0,24))||drag.el.tagName.toLowerCase();
ghostAt(ev.clientX,ev.clientY);
}
function ghostAt(x,y){
var w=Math.max(56,Math.min(drag.w,240)),h=Math.max(30,Math.min(drag.h,140));
var l=Math.max(4,Math.min(x+14,window.innerWidth-w-8));
var t=Math.max(4,Math.min(y+14,window.innerHeight-h-8));
ghostBox.style.display='flex';
ghostBox.style.left=l+'px';ghostBox.style.top=t+'px';
ghostBox.style.width=w+'px';ghostBox.style.height=h+'px';
}
function updateDrop(ev){
var kids=drag.kids,el=drag.el,n=kids.length,i,r;
var rects=[],minX=1e9,maxX=-1e9,minY=1e9,maxY=-1e9;
for(i=0;i<n;i++){r=kids[i].getBoundingClientRect();rects.push(r);
if(r.left<minX)minX=r.left;if(r.right>maxX)maxX=r.right;
if(r.top<minY)minY=r.top;if(r.bottom>maxY)maxY=r.bottom;}
var er=el.getBoundingClientRect();
if(er.left<minX)minX=er.left;if(er.right>maxX)maxX=er.right;
if(er.top<minY)minY=er.top;if(er.bottom>maxY)maxY=er.bottom;
var ra=rects[0],rb=n>1?rects[n-1]:er;
var ox=Math.min(ra.right,rb.right)-Math.max(ra.left,rb.left);
var horiz=ox<0.4*Math.min(ra.width||1,rb.width||1);
var drop=0;
for(i=0;i<n;i++){r=rects[i];
if(horiz){if(ev.clientX>r.left+r.width/2)drop=i+1;}
else{if(ev.clientY>r.top+r.height/2)drop=i+1;}}
if(drop===dragListIndex(el)){drag.drop=-1;lineEl.style.display='none';return;}
drag.drop=drop;
lineEl.style.display='block';
if(horiz){
lineEl.style.width='3px';lineEl.style.height=Math.max(8,maxY-minY)+'px';
lineEl.style.left=(drop<n?rects[drop].left-2:maxX+1)+'px';
lineEl.style.top=minY+'px';
}else{
lineEl.style.height='3px';lineEl.style.width=Math.max(8,maxX-minX)+'px';
lineEl.style.top=(drop<n?rects[drop].top-2:maxY+1)+'px';
lineEl.style.left=minX+'px';
}
}
function endDrag(commit){
var d=drag;drag=null;dragPending=null;
if(lineEl)lineEl.style.display='none';
if(ghostBox)ghostBox.style.display='none';
if(dragStyle&&dragStyle.parentNode)dragStyle.parentNode.removeChild(dragStyle);
if(d&&d.el){try{d.el.style.opacity=d.prevOpacity||'';}catch(e){}}
positionHandle();
if(!d||!d.el)return;
try{if(d.pid!=null&&d.el.releasePointerCapture)d.el.releasePointerCapture(d.pid);}catch(e){}
if(commit&&d.drop>=0){
var el=d.el,r=el.getBoundingClientRect();
send('ve:move:commit',{
selector:cssPath(el),
oeId:el.getAttribute('data-oe-id')||'',
targetIndex:d.drop,
tag:el.tagName.toLowerCase(),
component:el.getAttribute('data-component')||'',
childCount:el.childElementCount,
text:(el.innerText||'').replace(/\s+/g,' ').slice(0,40),
w:Math.round(r.width),h:Math.round(r.height)});
}
}
function select(el){curSel=el;send('ve:pick',info(el));positionHandle();}
function sendRect(){
if(curSel&&curSel.parentNode){var r=curSel.getBoundingClientRect();send('ve:rect',{rect:{x:r.left,y:r.top,w:r.width,h:r.height}});}
positionHandle();
}
function applyAll(css,dom){
lastCss=css||'';patchesDom=dom||[];
applying=true;
try{
var staleInserts=document.querySelectorAll('[data-ve-insert]');
for(var si=0;si<staleInserts.length;si++){if(staleInserts[si].parentNode)staleInserts[si].parentNode.removeChild(staleInserts[si]);}
var st=document.getElementById('ve-live-patches');
if(!st){st=document.createElement('style');st.id='ve-live-patches';st.setAttribute('data-ve-ui','patches');(document.head||document.documentElement).appendChild(st);}
st.textContent=lastCss;
var movedSel=false;
for(var i=0;i<patchesDom.length;i++){
var p=patchesDom[i];
if(p.kind!=='move')continue;
var mel=null;
try{if(p.moveId)mel=document.querySelector('[data-oe-id="'+p.moveId+'"]')}catch(e){}
if(!mel){try{mel=document.querySelector(p.selector)}catch(e){}}
if(!mel||!mel.parentNode)continue;
if(editing&&mel===editEl)continue;
if(p.moveId&&!mel.getAttribute('data-oe-id'))mel.setAttribute('data-oe-id',p.moveId);
if(typeof p.toPage==='number'){
var tsec=null;try{tsec=document.querySelector('section.page[data-page="'+p.toPage+'"]')}catch(e){}
var thost=tsec?(tsec.querySelector('.page-focus')||tsec):null;
if(thost&&thost!==mel.parentNode){
if(mel===curSel)movedSel=true;
thost.appendChild(mel);
}
continue;
}
var prevNext=mel.nextSibling,prevPar=mel.parentNode;
moveToIndex(mel,p.targetIndex);
if(mel===curSel&&(mel.nextSibling!==prevNext||mel.parentNode!==prevPar))movedSel=true;
}
if(movedSel&&curSel&&curSel.parentNode)select(curSel);
for(var j=0;j<patchesDom.length;j++){
var q=patchesDom[j],el=null;
if(q.kind==='move')continue;
try{el=document.querySelector(q.selector)}catch(e){}
if(!el)continue;
if(editing&&el===editEl)continue;
var p=q;
if(p.kind==='text'){if(el.childElementCount===0&&typeof p.newText==='string')el.textContent=p.newText;}
else if(p.kind==='image'){if(el.tagName==='IMG'&&p.newSrc)el.setAttribute('src',p.newSrc);}
else if(p.kind==='insert'&&p.html&&p.position){
var wrap=document.createElement('div');
wrap.setAttribute('data-ve-insert',p.id);
wrap.innerHTML=p.html;
if(p.position==='append')el.appendChild(wrap);
else if(p.position==='before'){if(el.parentNode)el.parentNode.insertBefore(wrap,el);}
else{if(el.parentNode)el.parentNode.insertBefore(wrap,el.nextSibling);}
}
}
}catch(e){}
setTimeout(function(){applying=false;},60);
sendRect();
startObserver();
}
function startObserver(){
if(mo||!window.MutationObserver)return;
mo=new MutationObserver(function(muts){
if(applying||editing||drag||patchesDom.length===0&&lastCss==='')return;
var relevant=false;
for(var i=0;i<muts.length;i++){
var m=muts[i];
if(m.type==='childList'||m.type==='characterData'){relevant=true;break;}
if(m.type==='attributes'&&(m.attributeName==='style'||m.attributeName==='src'||m.attributeName==='class')){relevant=true;break;}
}
if(!relevant)return;
clearTimeout(moTimer);
moTimer=setTimeout(function(){if(!applying&&!editing)applyAll(lastCss,patchesDom);},300);
});
mo.observe(document.documentElement,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['style','src','class']});
}
function startTextEdit(el){
if(editing)return;
editing=true;editEl=el;editOrig=el.textContent;
el.setAttribute('contenteditable','true');
try{el.focus();
var rng=document.createRange();rng.selectNodeContents(el);
var sel=window.getSelection();sel.removeAllRanges();sel.addRange(rng);
}catch(e){}
send('ve:text:started',{selector:cssPath(el)});
}
function endTextEdit(commit){
if(!editing||!editEl)return;
var el=editEl,txt=el.textContent,orig=editOrig;
el.removeAttribute('contenteditable');
try{el.blur();}catch(e){}
editing=false;editEl=null;editOrig=null;
if(commit){send('ve:text:commit',{selector:cssPath(el),text:txt});}
else{el.textContent=orig;}
}
function exportHtml(css){
if(editing)endTextEdit(true);
var clone=document.documentElement.cloneNode(true);
var cbd=clone.querySelector('body');
if(cbd)cbd.classList.remove('oe-edit-all');
var secs=clone.querySelectorAll('section.page');
for(var sn=0;sn<secs.length;sn++)secs[sn].setAttribute('data-page',String(sn+1));
var ce=clone.querySelectorAll('[contenteditable]');
for(var i=0;i<ce.length;i++)ce[i].removeAttribute('contenteditable');
var junk=clone.querySelectorAll('#ve-hover-box,#ve-freeze,#ve-drag-line,#ve-drag-ghost,#ve-drag-style,#ve-drag-handle,[data-ve-agent]');
for(var j=0;j<junk.length;j++){if(junk[j].parentNode)junk[j].parentNode.removeChild(junk[j]);}
var live=clone.querySelector('#ve-live-patches');
if(live){
if(css){live.id='ve-export-patches';live.removeAttribute('data-ve-ui');live.textContent=css;}
else if(live.parentNode){live.parentNode.removeChild(live);}
}
send('ve:export:result',{html:'<!DOCTYPE html>\n'+clone.outerHTML});
}
document.addEventListener('click',function(ev){
if(!pickOn||editing)return;
ev.preventDefault();ev.stopPropagation();
var el=ev.target;
if(!el||el.nodeType!==1||el===hoverBox)return;
select(el);
},true);
document.addEventListener('dblclick',function(ev){
if(!pickOn||editing)return;
var el=ev.target;
if(!el||el.nodeType!==1||el===hoverBox)return;
if(el.childElementCount>0)return;
ev.preventDefault();ev.stopPropagation();
startTextEdit(el);
},true);
document.addEventListener('mouseover',function(ev){
if(!pickOn||editing)return;
var el=ev.target;
if(!el||el.nodeType!==1||el===hoverBox)return;
ensureHover();
var r=el.getBoundingClientRect();
hoverBox.style.display='block';
hoverBox.style.left=r.left+'px';hoverBox.style.top=r.top+'px';
hoverBox.style.width=r.width+'px';hoverBox.style.height=r.height+'px';
},true);
document.addEventListener('mouseout',function(ev){
if(hoverBox&&ev.target!==hoverBox)hoverBox.style.display='none';
},true);
document.addEventListener('keydown',function(ev){
if(drag&&ev.key==='Escape'){ev.preventDefault();endDrag(false);return;}
if(!editing)return;
if(ev.key==='Escape'){ev.preventDefault();endTextEdit(false);}
else if(ev.key==='Enter'&&!ev.shiftKey){ev.preventDefault();endTextEdit(true);}
},true);
document.addEventListener('focusout',function(){
if(editing)setTimeout(function(){if(editing)endTextEdit(true);},0);
},true);
document.addEventListener('pointerdown',function(ev){
if(!pickOn||editing||drag)return;
var el=ev.target;
if(!el||el.nodeType!==1)return;
if(el===handleEl){
if(curSel&&curSel.parentNode){
var hk=dragSiblings(curSel);
if(hk&&hk.length>=1){ev.preventDefault();dragPending={el:curSel,x:ev.clientX,y:ev.clientY,kids:hk};}
}
return;
}
if(el===hoverBox||(el.hasAttribute&&el.hasAttribute('data-ve-ui')))return;
var t=el.tagName;
if(t==='HTML'||t==='BODY'||t==='HEAD'||t==='SCRIPT'||t==='STYLE'||t==='LINK'||t==='META'||t==='TITLE'||t==='BR'||t==='HR')return;
var kids=dragSiblings(el);
if(!kids||kids.length<1)return;
dragPending={el:el,x:ev.clientX,y:ev.clientY,kids:kids};
},true);
document.addEventListener('pointermove',function(ev){
if(dragPending&&!drag){
var dx=ev.clientX-dragPending.x,dy=ev.clientY-dragPending.y;
if(dx*dx+dy*dy<36)return;
startDrag(ev);
}
if(!drag)return;
ev.preventDefault();
updateDrop(ev);
ghostAt(ev.clientX,ev.clientY);
},true);
document.addEventListener('pointerup',function(){
dragPending=null;
if(!drag)return;
endDrag(true);
},true);
document.addEventListener('pointercancel',function(){
if(drag)endDrag(false);
},true);
var scrollTimer=0;
function onScrollResize(){
if(!curSel)return;
clearTimeout(scrollTimer);
scrollTimer=setTimeout(sendRect,80);
}
window.addEventListener('scroll',onScrollResize,true);
window.addEventListener('resize',onScrollResize);
window.addEventListener('message',function(ev){
var d=ev.data;
if(!d||d.ve!==1||d.ch!==CH)return;
if(d.type==='ve:pick:set'){
if(editing)endTextEdit(true);
if(drag)endDrag(false);
pickOn=!!(d.payload&&d.payload.enabled);
setFreeze(pickOn);
if(!pickOn&&hoverBox)hoverBox.style.display='none';
positionHandle();
send('ve:pick:mode',{enabled:pickOn});
}
if(d.type==='ve:pick:goto'){
if(editing)endTextEdit(true);
var el=null;
try{el=document.querySelector((d.payload&&d.payload.selector)||'')}catch(e){}
if(el)select(el);
}
if(d.type==='ve:patches:applyAll'){
applyAll((d.payload&&d.payload.css)||'',(d.payload&&d.payload.patches)||[]);
}
if(d.type==='ve:patches:apply'){
applyAll((d.payload&&d.payload.css)||'',patchesDom);
}
if(d.type==='ve:text:edit'){
var te=null;
try{te=document.querySelector((d.payload&&d.payload.selector)||'')}catch(e){}
if(te&&te.childElementCount===0)startTextEdit(te);
}
if(d.type==='ve:export'){
exportHtml((d.payload&&d.payload.css)||'');
}
if(d.type==='ve:verify'){
var items=(d.payload&&d.payload.items)||[],results=[];
for(var j=0;j<items.length;j++){
var it=items[j],vel=null,ok=false,reason='';
try{vel=document.querySelector(it.selector)}catch(e){}
if(!vel){reason='目标已不存在';}
else if(vel.tagName.toLowerCase()!==(it.tag||'')){reason='元素类型已变化';}
else if(!it.skipDetail&&vel.childElementCount!==(it.childCount|0)){reason='结构已变化';}
else if(!it.skipDetail&&((vel.textContent||'').replace(/\s+/g,' ').trim().slice(0,40))!==(it.text||'')){reason='内容已变化';}
else ok=true;
results.push({id:it.id,ok:ok,reason:reason});
}
send('ve:verify:result',{results:results});
}
});
function ready(){
if(document.body)document.body.classList.add('oe-edit-all');
var pages=[];
var secs=document.querySelectorAll('[data-page]');
for(var i=0;i<secs.length;i++){var s=secs[i];
pages.push({n:s.getAttribute('data-page')||String(i+1),title:s.getAttribute('data-title')||'',component:s.getAttribute('data-component')||''});}
send('ve:ready',{pages:pages,title:document.title||''});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ready);else ready();
})();