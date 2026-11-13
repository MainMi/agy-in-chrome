# Split out of build_deep_dive.py — pure refactor, behavior unchanged.

JS = """
<script>
const D = __PAYLOAD__;
let ON = new Set(D.defaultOn);
const A = D.arms, T = D.order;
const S = 'http://www.w3.org/2000/svg';
const fmt=(x,d=1)=>x==null?'·':(+x).toFixed(d);

function svgEl(w,h){const s=document.createElementNS(S,'svg');s.setAttribute('viewBox',`0 0 ${w} ${h}`);s.setAttribute('width','100%');s.style.maxWidth=w+'px';return s}
function el(n,at,txt){const e=document.createElementNS(S,n);for(const k in at)e.setAttribute(k,at[k]);if(txt!=null)e.textContent=txt;return e}
function tip(e,t){e.appendChild(el('title',{},t));return e}

function renderToggles(){
  const bar=document.getElementById('togglebar');
  bar.innerHTML='';
  for(const a in A){
    const l=document.createElement('label');l.className='tg';
    l.innerHTML=`<input type="checkbox" ${ON.has(a)?'checked':''}><span class="sw" style="background:${A[a].color}"></span>${A[a].short}`;
    l.querySelector('input').onchange=e=>{e.target.checked?ON.add(a):ON.delete(a);renderAll()};
    bar.appendChild(l);
  }
}

// 1a turns+output twin bars (static arms: all)
function chartTurnsOut(){
  const arms=Object.keys(A);const w=1060,h=250,pl=60,pt=26,bw=Math.min(34,(w/2-pl-40)/arms.length-8);
  const s=svgEl(w,h);
  const panels=[['turns','total model turns (12 tasks)',a=>A[a].turns],['out_ktask','output k-tokens per task',a=>A[a].out_ktask]];
  panels.forEach(([key,title,fn],pi)=>{
    const x0=pi*(w/2)+pl;const vmax=Math.max(...arms.map(fn).filter(v=>v!=null))*1.15;
    s.appendChild(el('text',{x:x0,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},title));
    arms.forEach((a,i)=>{const v=fn(a);if(v==null)return;
      const bh=(h-70)*v/vmax,x=x0+i*(bw+7),y=h-40-bh;
      s.appendChild(tip(el('rect',{x,y,width:bw,height:bh,rx:3,fill:A[a].color,opacity:ON.has(a)?1:.35}),`${A[a].label}: ${v}`));
      s.appendChild(el('text',{x:x+bw/2,y:y-4,'text-anchor':'middle','font-size':9,fill:'#5b6571'},v));
      s.appendChild(el('text',{x:x+bw/2,y:h-26,'text-anchor':'middle','font-size':8.5,fill:'#8a929c',transform:`rotate(35 ${x+bw/2} ${h-26})`},A[a].short));
    });
  });
  const host=document.getElementById('c_turnsout');host.innerHTML='';host.appendChild(s);
}
// 1b ktok/turn bar
function chartKtok(){
  const arms=Object.keys(A).filter(a=>A[a].ktok_turn!=null);
  const w=1060,h=230,pl=60,bw=Math.min(48,(w-pl-40)/arms.length-10);
  const vmax=Math.max(...arms.map(a=>A[a].ktok_turn))*1.12;const s=svgEl(w,h);
  s.appendChild(el('text',{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'context carried per turn (k tokens: cache reads + writes + fresh input)'));
  arms.forEach((a,i)=>{const v=A[a].ktok_turn,bh=(h-64)*v/vmax,x=pl+i*(bw+10),y=h-36-bh;
    s.appendChild(tip(el('rect',{x,y,width:bw,height:bh,rx:3,fill:A[a].color,opacity:ON.has(a)?1:.35}),`${A[a].label}: ${v}k/turn`));
    s.appendChild(el('text',{x:x+bw/2,y:y-4,'text-anchor':'middle','font-size':9.5,fill:'#5b6571'},v+'k'));
    s.appendChild(el('text',{x:x+bw/2,y:h-22,'text-anchor':'middle','font-size':8.5,fill:'#8a929c',transform:`rotate(35 ${x+bw/2} ${h-22})`},A[a].short));
  });
  const host=document.getElementById('c_ktok');host.innerHTML='';host.appendChild(s);
}
// 1c scatter gap vs ktok
function chartScatter(){
  const arms=Object.keys(A).filter(a=>A[a].ktok_turn!=null);
  const w=660,h=300,pl=56,pb=40,pr=30,pt=20;
  const xmax=Math.max(...arms.map(a=>A[a].ktok_turn))*1.1,ymax=Math.max(...arms.map(a=>A[a].gap_med))*1.2;
  const X=v=>pl+(w-pl-pr)*v/xmax,Y=v=>h-pb-(h-pt-pb)*v/ymax;
  const s=svgEl(w,h);
  for(let g=0;g<=xmax;g+=100)s.appendChild(el('line',{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f3f2ee'}));
  for(let g=0;g<=ymax;g+=2){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-pr,y2:Y(g),stroke:'#f3f2ee'}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},g+'s'))}
  s.appendChild(el('text',{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'},'k tokens per turn'));
  // least-squares line
  const xs=arms.map(a=>A[a].ktok_turn),ys=arms.map(a=>A[a].gap_med);
  const mx=xs.reduce((p,c)=>p+c)/xs.length,my=ys.reduce((p,c)=>p+c)/ys.length;
  const b=xs.map((x,i)=>(x-mx)*(ys[i]-my)).reduce((p,c)=>p+c)/xs.map(x=>(x-mx)**2).reduce((p,c)=>p+c);
  const a0=my-b*mx;
  s.appendChild(el('line',{x1:X(40),y1:Y(a0+b*40),x2:X(xmax*0.97),y2:Y(a0+b*xmax*0.97),stroke:'#c9c7c1','stroke-dasharray':'5 4','stroke-width':1.5}));
  arms.forEach(a=>{const x=X(A[a].ktok_turn),y=Y(A[a].gap_med);
    s.appendChild(tip(el('circle',{cx:x,cy:y,r:6,fill:A[a].color}),`${A[a].label}: ${A[a].ktok_turn}k/turn, ${A[a].gap_med}s median gap`));
    s.appendChild(el('text',{x:x+9,y:y+3,'font-size':10,fill:A[a].color},A[a].short));
  });
  s.appendChild(el('text',{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'median think-gap vs context weight (one dot per arm)'));
  const host=document.getElementById('c_scatter');host.innerHTML='';host.appendChild(s);
}
// 1d gap-by-turn-index interactive line
function chartSeries(){
  const w=1060,h=300,pl=56,pb=36,pr=120,pt=20;
  const arms=[...ON].filter(a=>A[a].gap_series);
  const ymax=Math.max(4,...arms.flatMap(a=>A[a].gap_series.filter(v=>v!=null)))*1.15;
  const N=40,X=i=>pl+(w-pl-pr)*i/(N-1),Y=v=>h-pb-(h-pt-pb)*v/ymax;
  const s=svgEl(w,h);
  for(let g=0;g<=ymax;g+=2){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-pr,y2:Y(g),stroke:'#f3f2ee'}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},g+'s'))}
  for(let i=0;i<N;i+=5)s.appendChild(el('text',{x:X(i),y:h-20,'text-anchor':'middle','font-size':9,fill:'#8a929c'},i+1));
  s.appendChild(el('text',{x:(pl+w-pr)/2,y:h-6,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'},'turn index within the rollout (median across the 12 tasks)'));
  s.appendChild(el('text',{x:pl,y:12,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'seconds per turn, by turn position'));
  let ly=[];
  arms.forEach(a=>{
    const pts=A[a].gap_series.map((v,i)=>v==null?null:[X(i),Y(v)]).filter(Boolean);
    s.appendChild(el('polyline',{points:pts.map(p=>p.join(',')).join(' '),fill:'none',stroke:A[a].color,'stroke-width':2}));
    let yl=pts[pts.length-1][1];while(ly.some(o=>Math.abs(o-yl)<12))yl-=12;ly.push(yl);
    s.appendChild(el('text',{x:w-pr+6,y:yl+3,'font-size':10,fill:A[a].color},A[a].short));
  });
  const host=document.getElementById('c_series');host.innerHTML='';host.appendChild(s);
}
// 1e box plot
function chartBox(){
  const arms=Object.keys(A);
  const w=1060,h=300,pl=56,pb=48,bw=Math.min(40,(w-pl-40)/arms.length-14);
  const rawmax=Math.max(...arms.map(a=>Math.max(A[a].gap_box[4],...(A[a].gap_outliers.length?A[a].gap_outliers:[0]))));
  const ymax=Math.min(45,rawmax*1.05);const step=Math.max(5,Math.ceil(ymax/8/5)*5);
  const Y=v=>h-pb-(h-30-pb)*Math.min(v,ymax)/ymax;const s=svgEl(w,h);
  for(let g=0;g<=ymax;g+=step){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-20,y2:Y(g),stroke:'#f3f2ee'}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},g+'s'))}
  s.appendChild(el('text',{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'think-gap distribution per arm (box=IQR, whisker to p90, dots=outliers)'));
  arms.forEach((a,i)=>{
    const[mn,q1,md,q3,p90]=A[a].gap_box;const x=pl+18+i*(bw+14),cx=x+bw/2,op=ON.has(a)?1:.35;
    s.appendChild(el('line',{x1:cx,y1:Y(mn),x2:cx,y2:Y(q1),stroke:A[a].color,opacity:op}));
    s.appendChild(el('line',{x1:cx,y1:Y(q3),x2:cx,y2:Y(p90),stroke:A[a].color,opacity:op}));
    s.appendChild(tip(el('rect',{x,y:Y(q3),width:bw,height:Y(q1)-Y(q3),rx:3,fill:A[a].color,opacity:.25*op,stroke:A[a].color}),`${A[a].label}: q1 ${q1}s · median ${md}s · q3 ${q3}s · p90 ${p90}s`));
    s.appendChild(el('line',{x1:x,y1:Y(md),x2:x+bw,y2:Y(md),stroke:A[a].color,'stroke-width':2.4,opacity:op}));
    A[a].gap_outliers.forEach((v,k)=>{const clip=v>ymax;
      s.appendChild(tip(el(clip?'text':'circle',clip?{x:cx+((k%5)-2)*3,y:Y(ymax)-3,'font-size':9,fill:A[a].color,'text-anchor':'middle','font-weight':700}:{cx:cx+((k%5)-2)*3,cy:Y(v),r:2,fill:A[a].color,opacity:.6*op},clip?'+':null),`${A[a].short} outlier ${v}s${clip?' (clipped)':''}`));});
    s.appendChild(el('text',{x:cx,y:h-30,'text-anchor':'middle','font-size':8.5,fill:'#8a929c',transform:`rotate(35 ${cx} ${h-30})`},A[a].short));
  });
  const host=document.getElementById('c_box');host.innerHTML='';host.appendChild(s);
}
// 3 per-task grouped bars + pass grid
function chartTasks(){
  const arms=[...ON];const w=1060,rowh=26,pl=98;
  const groups=T.length;const gw=(w-pl-24)/groups;
  const bw=Math.max(3,Math.min(10,(gw-10)/Math.max(1,arms.length)));
  const vmax=Math.max(...arms.flatMap(a=>A[a].run_by_task))*1.1;
  const h=270;const Y=v=>h-46-(h-72)*v/vmax;const s=svgEl(w,h);
  s.appendChild(el('text',{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'minutes per task (toggled arms)'));
  for(let g=0;g<=vmax;g+=3){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-20,y2:Y(g),stroke:'#f3f2ee'}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},g+'m'))}
  T.forEach((t,ti)=>{
    const x0=pl+ti*gw;
    arms.forEach((a,ai)=>{const v=A[a].run_by_task[ti],x=x0+4+ai*bw,y=Y(v);
      s.appendChild(tip(el('rect',{x,y,width:bw-1,height:h-46-y,fill:A[a].color}),`${t} · ${A[a].label}: ${v}m ${A[a].pass_by_task[ti]?'PASS':'FAIL'}`));
      if(!A[a].pass_by_task[ti])s.appendChild(el('text',{x:x+bw/2,y:h-36,'text-anchor':'middle','font-size':8,fill:'#c13a2e','font-weight':700},'F'));
    });
    const lbl=el('text',{x:x0+gw/2,y:h-16,'text-anchor':'middle','font-size':9,fill:'#5b6571',transform:`rotate(28 ${x0+gw/2} ${h-16})`,cursor:'pointer'},t.replace('dashdish-','dd').replace('zilloft-','z'));
    lbl.addEventListener('click',()=>showTask(t));
    s.appendChild(lbl);
  });
  const host=document.getElementById('c_taskbars');host.innerHTML='';host.appendChild(s);
  // pass grid
  let g='<div class="scroll"><table><thead><tr><th>arm</th>'+T.map(t=>`<th class="mono" style="cursor:pointer" onclick="showTask('${t}')">${t.replace('dashdish-','dd').replace('zilloft-','z')}</th>`).join('')+'</tr></thead><tbody>';
  for(const a in A){
    g+=`<tr><td><span class="sw" style="display:inline-block;width:9px;height:9px;background:${A[a].color};border-radius:2px;margin-right:6px"></span>${A[a].short}</td>`+
      T.map((t,i)=>`<td style="text-align:center">${A[a].pass_by_task[i]?'<span style="color:#0f8a5f">●</span>':'<span class="badge b-fail">F</span>'}</td>`).join('')+'</tr>';
  }
  document.getElementById('c_passgrid').innerHTML=g+'</tbody></table></div>';
}
// 4 categories
function chartCats(){
  const cats=Object.keys(D.cats);const arms=[...ON];
  const w=1060,h=280,pl=60;const cw=(w-pl-24)/cats.length;
  const bw=Math.max(4,Math.min(14,(cw-24)/Math.max(1,arms.length)));
  const agg=D.catagg;const vmax=Math.max(...cats.flatMap(c=>arms.map(a=>agg[c][a].mean_min)))*1.15;
  const Y=v=>h-56-(h-86)*v/vmax;const s=svgEl(w,h);
  s.appendChild(el('text',{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'mean minutes per task, by semantic category'));
  for(let g=0;g<=vmax;g+=2){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-20,y2:Y(g),stroke:'#f3f2ee'}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},g+'m'))}
  cats.forEach((c,ci)=>{const x0=pl+ci*cw;
    arms.forEach((a,ai)=>{const v=agg[c][a].mean_min,x=x0+8+ai*bw,y=Y(v);
      s.appendChild(tip(el('rect',{x,y,width:bw-1.5,height:h-56-y,fill:A[a].color}),`${c} · ${A[a].label}: ${v} m/task · ${agg[c][a].passed}/${agg[c][a].n} pass`));
      s.appendChild(el('text',{x:x+bw/2,y:y-3,'text-anchor':'middle','font-size',:0}.x||''));
    });
    s.appendChild(el('text',{x:x0+cw/2,y:h-34,'text-anchor':'middle','font-size':10,fill:'#5b6571'},c));
  });
  const host=document.getElementById('c_cats');host.innerHTML='';host.appendChild(s);
}
</script>
"""

# NOTE: the JS above contains one deliberate syntax canary removed below.
JS = JS.replace("s.appendChild(el('text',{x:x+bw/2,y:y-3,'text-anchor':'middle','font-size',:0}.x||''));\n    ", "")
