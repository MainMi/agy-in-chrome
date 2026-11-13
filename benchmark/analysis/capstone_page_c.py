# Capstone page assembly for build_capstone.py — pure refactor,
# behavior unchanged.

from capstone_data import *

PAGE_C = f"""  const seg=a=>{{
    let segs=[];
    if(showPrep) a.prep_steps.forEach(st=>segs.push({{v:st.m,c:SM[st.k].color,lab:SM[st.k].label,k:st.k,prep:true}}));
    if(showTask) segs.push({{v:a.total,c:a.color,lab:'task time',prep:false}});
    return segs;
  }};
  const alignedMax=Math.max(...A.flatMap(a=>seg(a).map(s=>s.v)),1);
  const totalMax=Math.max(...A.map(a=>seg(a).reduce((p,s)=>p+s.v,0)),1);
  const w=1060,pl=150,pr=64;
  const rh=layout==='stacked'?30:(6+ (Math.max(...A.map(a=>seg(a).length),1))*8 +8);
  const hgt=20+rh*A.length+30;
  const xmax=(layout==='stacked'?totalMax:alignedMax)*1.03;
  const X=v=>pl+(w-pl-pr)*v/xmax;const s=sv(w,hgt);
  const defs=E('defs',{{}});usedSteps.forEach(k=>{{const pat=E('pattern',{{id:'hx-'+k,width:6,height:6,patternTransform:'rotate(45)',patternUnits:'userSpaceOnUse'}});pat.appendChild(E('rect',{{width:6,height:6,fill:'#fbfbf9'}}));pat.appendChild(E('line',{{x1:0,y1:0,x2:0,y2:6,stroke:SM[k].color,'stroke-width':3}}));defs.appendChild(pat);}});s.appendChild(defs);
  const fillOf=sg=>sg.prep?('url(#hx-'+sg.k+')'):sg.c;
  const strokeOf=sg=>sg.prep?SM[sg.k].color:'none';
  for(let g=0;g<=xmax;g+=15){{s.appendChild(E('line',{{x1:X(g),y1:14,x2:X(g),y2:hgt-24,stroke:'#f3f2ee'}}));s.appendChild(E('text',{{x:X(g),y:hgt-10,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g+'m'))}}
  // cold task-time reference (only meaningful when task shown, stacked)
  if(showTask&&layout==='stacked'&&!showPrep){{s.appendChild(E('line',{{x1:X(COLD.total),y1:14,x2:X(COLD.total),y2:hgt-24,stroke:'#0d9488','stroke-dasharray':'5 3'}}));s.appendChild(E('text',{{x:X(COLD.total),y:12,'text-anchor':'middle','font-size':9,fill:'#0d9488'}},'cold 23.4m'))}}
  A.forEach((a,i)=>{{const y0=18+i*rh;const segs=seg(a);
    s.appendChild(E('text',{{x:pl-8,y:y0+(layout==='stacked'?13:11),'text-anchor':'end','font-size':11.5,fill:'#1b1f24'}},a.label));
    if(layout==='stacked'){{
      let x=X(0);let tot=0;
      segs.forEach((sg,si)=>{{const wpx=X(sg.v)-pl;
        s.appendChild(tip(E('rect',{{x,y:y0,width:Math.max(1.5,wpx-(si<segs.length-1?2:0)),height:17,rx:2.5,fill:fillOf(sg),stroke:strokeOf(sg),'stroke-width':sg.prep?0.8:0}}),`${{a.label}} · ${{sg.lab}}: ${{sg.v}}m`));
        x+=wpx;tot+=sg.v;}});
      if(segs.length) s.appendChild(E('text',{{x:x+5,y:y0+13,'font-size':10.5,fill:'#5b6571'}},`${{tot.toFixed(0)}}m`));
    }} else {{ // aligned: each segment its own left-aligned mini-bar
      let yy=y0;
      segs.forEach(sg=>{{
        s.appendChild(tip(E('rect',{{x:X(0),y:yy,width:Math.max(1.5,X(sg.v)-pl),height:6,rx:1.5,fill:fillOf(sg),stroke:strokeOf(sg),'stroke-width':sg.prep?0.6:0}}),`${{a.label}} · ${{sg.lab}}: ${{sg.v}}m`));
        yy+=8;}});
    }}
  }});
  const host=document.getElementById('c_perf');host.innerHTML='';host.appendChild(s);
}}
function deltaChart(){{
  const w=1060,h=300,pl=40,pb=60;const bw=Math.min(56,(w-pl-20)/A.length-8);
  const vals=A.map(a=>a.mean_delta);const vmax=Math.max(...vals.map(Math.abs),0.5)*1.15;
  const Y=v=>34+(h-94)*(vmax-v)/(2*vmax);const s=sv(w,h);
  for(let g=-Math.ceil(vmax);g<=Math.ceil(vmax);g++){{s.appendChild(E('line',{{x1:pl,y1:Y(g),x2:w-10,y2:Y(g),stroke:g===0?'#c9c7c1':'#f3f2ee','stroke-width':g===0?2:1}}));s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},(g>0?'+':'')+g))}}
  s.appendChild(E('text',{{x:pl,y:16,'font-size':11,fill:'#5b6571'}},'slower than cold ▲ / ▼ faster than cold  (min per task)'));
  A.forEach((a,i)=>{{const x=pl+14+i*(bw+8),v=a.mean_delta,y0=Y(0),y1=Y(v);
    s.appendChild(tip(E('rect',{{x,y:Math.min(y0,y1),width:bw,height:Math.abs(y1-y0)||1,rx:3,fill:v<=0?'#0f8a5f':'#c13a2e',opacity:.85}}),`${{a.label}}: ${{v>0?'+':''}}${{v}}m/task, faster on ${{a.faster_vs_cold}}/12`));
    s.appendChild(E('text',{{x:x+bw/2,y:v<=0?y1-4:y1+12,'text-anchor':'middle','font-size':9.5,fill:'#5b6571'}},(v>0?'+':'')+v));
    s.appendChild(E('text',{{x:x+bw/2,y:h-pb+14,'text-anchor':'middle','font-size':9,fill:'#5b6571',transform:`rotate(35 ${{x+bw/2}} ${{h-pb+14}})`}},a.short));
  }});
  document.getElementById('c_deltas').appendChild(s);
}}
function ktokChart(){{
  const w=1060,h=280,pl=44,pb=60;const bw=Math.min(56,(w-pl-20)/A.length-8);
  const vmax=Math.max(...A.map(a=>a.ktok))*1.1;const Y=v=>h-pb-(h-30-pb)*v/vmax;const s=sv(w,h);
  for(let g=0;g<=vmax;g+=100){{s.appendChild(E('line',{{x1:pl,y1:Y(g),x2:w-10,y2:Y(g),stroke:'#f3f2ee'}}));s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},g+'k'))}}
  A.forEach((a,i)=>{{const x=pl+14+i*(bw+8),y=Y(a.ktok);
    s.appendChild(tip(E('rect',{{x,y,width:bw,height:Y(0)-y,rx:3,fill:a.color}}),`${{a.label}}: ${{a.ktok}}k tokens/turn`));
    s.appendChild(E('text',{{x:x+bw/2,y:y-4,'text-anchor':'middle','font-size':10,fill:'#5b6571'}},a.ktok+'k'));
    s.appendChild(E('text',{{x:x+bw/2,y:h-pb+14,'text-anchor':'middle','font-size':9,fill:'#5b6571',transform:`rotate(35 ${{x+bw/2}} ${{h-pb+14}})`}},a.short));
  }});
  document.getElementById('c_ktok').appendChild(s);
}}
function lawScatter(){{
  const w=1060,h=330,pl=56,pb=44,pr=30,pt=20;
  const xmax=Math.max(...A.map(a=>a.ktok))*1.08,ymin=Math.min(...A.map(a=>a.mean_delta))-0.2,ymax=Math.max(...A.map(a=>a.mean_delta))*1.15;
  const X=v=>pl+(w-pl-pr)*v/xmax,Y=v=>pt+(h-pt-pb)*(ymax-v)/(ymax-ymin);const s=sv(w,h);
  for(let g=0;g<=xmax;g+=100){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f3f2ee'}}));s.appendChild(E('text',{{x:X(g),y:h-28,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g+'k'))}}
  s.appendChild(E('line',{{x1:pl,y1:Y(0),x2:w-pr,y2:Y(0),stroke:'#c9c7c1','stroke-width':2}}));
  for(let g=Math.ceil(ymin);g<=ymax;g++){{s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},(g>0?'+':'')+g+'m'))}}
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'}},'context carried per turn (k tokens)'));
  s.appendChild(E('text',{{x:16,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 16 ${{(pt+h-pb)/2}})`}},'time penalty vs cold (min/task)'));
  const xs=A.map(a=>a.ktok),ys=A.map(a=>a.mean_delta);
  const mx=xs.reduce((p,c)=>p+c)/xs.length,my=ys.reduce((p,c)=>p+c)/ys.length;
  const b=xs.map((x,i)=>(x-mx)*(ys[i]-my)).reduce((p,c)=>p+c)/xs.map(x=>(x-mx)**2).reduce((p,c)=>p+c),a0=my-b*mx;
  s.appendChild(E('line',{{x1:X(40),y1:Y(a0+b*40),x2:X(xmax*.96),y2:Y(a0+b*xmax*.96),stroke:'#5b6571','stroke-width':2,'stroke-dasharray':'7 5'}}));
  A.forEach(a=>{{const x=X(a.ktok),y=Y(a.mean_delta);
    s.appendChild(tip(E('circle',{{cx:x,cy:y,r:6,fill:a.color}}),`${{a.label}}: ${{a.ktok}}k/turn, ${{a.mean_delta>0?'+':''}}${{a.mean_delta}}m/task`));
    s.appendChild(E('text',{{x:x+9,y:y+3,'font-size':10,fill:a.color}},a.short));
  }});
  document.getElementById('c_lawscatter').appendChild(s);
}}

const D_LAND=D.landscape;
const DIFF_LEGS=A.filter(a=>!['exp1a-fixed-chrome','exp1b-cinc-parity'].includes(a.id)); // drop redundant cold legs
let SCON=new Set(['exp1a-fixed-brave','exp4a-experiential-fork','exp4b-expert-fork','exp5d-warmup-recipe','exp3c-analysis']);
function sensBar(){{
  const rows=DIFF_LEGS.slice().sort((x,y)=>x.diff_slope-y.diff_slope);
  const w=1060,rh=26,pl=150;const hgt=20+rh*rows.length+26;
  const smax=Math.max(...rows.map(a=>Math.abs(a.diff_slope)),0.1)*1.15;
  const X=v=>pl+((w-pl-90)/2)*(1+v/smax);const s=sv(w,hgt);
  s.appendChild(E('line',{{x1:X(0),y1:14,x2:X(0),y2:hgt-16,stroke:'#c9c7c1','stroke-width':2}}));
  s.appendChild(E('text',{{x:X(-smax*.6),y:12,'text-anchor':'middle','font-size':10,fill:'#0f8a5f'}},'← robust (improves w/ difficulty)'));
  s.appendChild(E('text',{{x:X(smax*.6),y:12,'text-anchor':'middle','font-size':10,fill:'#c13a2e'}},'degrades w/ difficulty →'));
  rows.forEach((a,i)=>{{const y=18+i*rh;const v=a.diff_slope;const x0=X(0),x1=X(v);
    s.appendChild(E('text',{{x:pl-8,y:y+13,'text-anchor':'end','font-size':11.5,fill:'#1b1f24'}},a.label));
    s.appendChild(tip(E('rect',{{x:Math.min(x0,x1),y,width:Math.max(2,Math.abs(x1-x0)),height:17,rx:2.5,fill:v<=0?'#0f8a5f':'#c13a2e',opacity:.85}}),`${{a.label}}: slope ${{v>0?'+':''}}${{v}} min/difficulty-pt, Spearman ${{a.diff_spear>0?'+':''}}${{a.diff_spear}}`));
    s.appendChild(E('text',{{x:x1+(v>=0?5:-5),y:y+13,'text-anchor':v>=0?'start':'end','font-size':10,fill:'#5b6571'}},`${{v>0?'+':''}}${{v}}`));
  }});
  const h=document.getElementById('c_sens');h.innerHTML='';h.appendChild(s);
}}
function diffScatterCtl(){{
  const bar=document.getElementById('sc_ctl');bar.innerHTML='';
  DIFF_LEGS.forEach(a=>{{const l=document.createElement('label');l.innerHTML=`<input type="checkbox" ${{SCON.has(a.id)?'checked':''}}><span class="sw" style="background:${{a.color}}"></span>${{a.short}}`;
    l.querySelector('input').onchange=e=>{{e.target.checked?SCON.add(a.id):SCON.delete(a.id);diffScatter2();}};bar.appendChild(l);}});
}}
function diffScatter2(){{
  const legs=DIFF_LEGS.filter(a=>SCON.has(a.id));
  const w=1060,h=360,pl=56,pb=44,pr=30,pt=22;
  const xs=A[0].perf_pts.map(p=>p.x);const xmax=Math.max(...xs)*1.04;
  const ally=legs.flatMap(a=>a.perf_pts.map(p=>p.y));
  const ymin=Math.min(-0.5,...ally),ymax=Math.max(0.5,...ally)*1.08;
  const X=v=>pl+(w-pl-pr)*v/xmax,Y=v=>pt+(h-pt-pb)*(ymax-v)/(ymax-ymin);const s=sv(w,h);
  for(let g=0;g<=xmax;g+=2){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f3f2ee'}}));s.appendChild(E('text',{{x:X(g),y:h-28,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g))}}
  s.appendChild(E('line',{{x1:pl,y1:Y(0),x2:w-pr,y2:Y(0),stroke:'#c9c7c1','stroke-width':2}}));
  for(let g=Math.ceil(ymin);g<=ymax;g+=2){{s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},(g>0?'+':'')+g+'m'))}}
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'}},'task difficulty (0-10: classification + denoised baseline time)'));
  s.appendChild(E('text',{{x:16,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 16 ${{(pt+h-pb)/2}})`}},'minutes vs baseline (below 0 = faster)'));
  legs.forEach(a=>{{
    a.perf_pts.forEach(p=>s.appendChild(tip(E('circle',{{cx:X(p.x),cy:Y(p.y),r:3.4,fill:a.color,opacity:.62}}),`${{a.label}} · ${{p.t}} (${{p.cls}}, diff ${{p.x}}): ${{p.y>0?'+':''}}${{p.y}}m`)));
    const px=a.perf_pts.map(p=>p.x),py=a.perf_pts.map(p=>p.y);const mx=px.reduce((q,c)=>q+c)/px.length,my=py.reduce((q,c)=>q+c)/py.length;
    const b=px.map((x,i)=>(x-mx)*(py[i]-my)).reduce((q,c)=>q+c)/px.map(x=>(x-mx)**2).reduce((q,c)=>q+c),a0=my-b*mx;
    s.appendChild(E('line',{{x1:X(0.1),y1:Y(a0+b*0.1),x2:X(xmax*.97),y2:Y(a0+b*xmax*.97),stroke:a.color,'stroke-width':2.2,'stroke-dasharray':'6 4'}}));
  }});
  let ly=30;legs.forEach(a=>{{s.appendChild(E('circle',{{cx:w-176,cy:ly,r:4,fill:a.color}}));s.appendChild(E('text',{{x:w-167,y:ly+4,'font-size':10,fill:a.color}},a.short));ly+=14;}});
  const hh=document.getElementById('c_diffscatter2');hh.innerHTML='';hh.appendChild(s);
}}


const IT_LEGS=A.filter(a=>a.phase!=='cold');       // the non-phase-1 legs
const IT_BASE={{}};D.landscape.forEach(r=>IT_BASE[r.t]=r.dur);
let ITON=new Set(['exp3c-analysis','exp4a-experiential-fork','exp5d-warmup-recipe']);
let ITMODE='delta';                                 // 'abs' | 'delta'
function itMode(){{
  const b=document.getElementById('it_mode');b.innerHTML='';
  [['delta','vs baseline (minutes)'],['rel','vs baseline (% faster/slower)'],['abs','absolute minutes']].forEach(m=>{{
    const l=document.createElement('label');
    l.innerHTML=`<input type="radio" name="itm" ${{ITMODE===m[0]?'checked':''}}>${{m[1]}}`;
    l.querySelector('input').onchange=()=>{{ITMODE=m[0];itemized();}};b.appendChild(l);
  }});
}}
function itCtl(){{
  const b=document.getElementById('it_ctl');b.innerHTML='';
  IT_LEGS.forEach(a=>{{const l=document.createElement('label');
    l.innerHTML=`<input type="checkbox" ${{ITON.has(a.id)?'checked':''}}><span class="sw" style="background:${{a.color}}"></span>${{a.short}}`;
    l.querySelector('input').onchange=e=>{{e.target.checked?ITON.add(a.id):ITON.delete(a.id);itemized();}};b.appendChild(l);}});
}}
function itemized(){{
  const legs=IT_LEGS.filter(a=>ITON.has(a.id));
  const tasks=D.landscape.slice().sort((x,y)=>x.dur-y.dur);
  const rh=32, pl=168, pr=150, pt=16, w=1060;
  const val=(a,t)=>{{const c=a.per_task.find(c=>c.t===t);return c?c.min:null;}};
  const CAP=150; // % clamp for rel mode; points beyond render as an edge marker
  const pv=(v,b)=> ITMODE==='abs'? v : ITMODE==='delta'? v-b : 100*(v-b)/b;
  let xmin,xmax;
  if(ITMODE==='abs'){{xmin=0;xmax=Math.max(...tasks.map(t=>Math.max(t.dur,...legs.map(a=>val(a,t.t)||0))))*1.06||1;}}
  else{{const ds=[];tasks.forEach(t=>legs.forEach(a=>{{const v=val(a,t.t);if(v!=null)ds.push(pv(v,t.dur));}}));
        if(!ds.length)ds.push(0);
        if(ITMODE==='rel'){{let lo=Math.min(...ds),hi=Math.min(Math.max(...ds),CAP);
          xmin=Math.min(lo*1.08,-10);xmax=Math.max(hi*1.08,10);}}
        else{{const mx=Math.max(0.5,...ds.map(Math.abs));xmin=-mx*1.08;xmax=mx*1.08;}}}}
  const X=v=>pl+(w-pl-pr)*(v-xmin)/(xmax-xmin);
  // per-leg average across all tasks (in the current mode); pack labels into lanes
  const avgs=[];
  legs.forEach(a=>{{const vs=tasks.map(t=>{{const v=val(a,t.t);return v==null?null:pv(v,t.dur);}}).filter(v=>v!=null);
    if(vs.length)avgs.push({{a,m:vs.reduce((p,c)=>p+c,0)/vs.length}});}});
  avgs.forEach(r=>r.x=X(Math.max(xmin,Math.min(xmax,r.m))));
  avgs.sort((p,q)=>p.x-q.x);
  const lanes=[];avgs.forEach(r=>{{let L=0;while(lanes[L]!=null&&r.x-lanes[L]<95)L++;lanes[L]=r.x;r.lane=L;}});
  const nlane=Math.max(1,lanes.length);
  const PB=pt+rh*tasks.length+6, h=PB+30+nlane*12+8;
  const s=sv(w,h);
  // x grid + axis labels
  const tset=ITMODE==='abs'?[0,2,4,6,8,10,12]:ITMODE==='delta'?[-6,-4,-2,0,2,4,6]:[-50,-25,0,25,50,75,100,125,150];
  const unit=ITMODE==='rel'?'%':'m';
  tset.filter(g=>g>=xmin&&g<=xmax).forEach(g=>{{
    s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:PB,stroke:g===0?'#c9c7c1':'#f5f4f0','stroke-width':g===0?1.5:1}}));
    s.appendChild(E('text',{{x:X(g),y:PB+13,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},(ITMODE!=='abs'&&g>0?'+':'')+g+unit));
  }});
  const axl=ITMODE==='abs'?'run time (minutes)':ITMODE==='delta'?'time vs phase-1 baseline (left = faster)':'relative to phase-1 baseline, % (left = faster)';
  s.appendChild(E('text',{{x:pl+(w-pl-pr)/2,y:h-4,'text-anchor':'middle','font-size':10,fill:'#5b6571'}},axl));
  const CLR={{easy:'#0f8a5f',medium:'#b45309',hard:'#c13a2e'}};
  tasks.forEach((t,i)=>{{
"""
