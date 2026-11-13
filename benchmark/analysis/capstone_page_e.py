# Capstone page assembly for build_capstone.py — pure refactor,
# behavior unchanged.

from capstone_data import *

PAGE_E = f"""    const col=pM>pT+0.03?'#c13a2e':pM<pT-0.03?'#0f8a5f':'#b8b6b0';
    s.appendChild(tip(E('line',{{x1:xL,y1,x2:xR,y2,stroke:col,'stroke-width':Math.abs(a.drank)>=5?2.6:1.6,opacity:.8}}),`${{a.short}}: ${{a.turns}} turns (rank ${{a.rt}}) -> ${{a.min}}m (rank ${{a.rl}}), moves ${{a.drank>0?'+':''}}${{a.drank}} places`));
    s.appendChild(E('circle',{{cx:xL,cy:y1,r:4,fill:a.color,stroke:'#fff','stroke-width':1.2}}));
    s.appendChild(E('circle',{{cx:xR,cy:y2,r:4,fill:a.color,stroke:'#fff','stroke-width':1.2}}));
  }});
  // de-collide labels vertically (dots stay at true positions; leaders connect)
  const gap=15;
  function place(items,yfn,key){{const so=[...items].sort((p,q)=>yfn(p)-yfn(q));let last=-1e9;
    so.forEach(a=>{{a[key]=Math.max(yfn(a),last+gap);last=a[key];}});
    const over=last-(pt+H);if(over>0){{let sh=over;so.slice().reverse().forEach(a=>{{}});so.forEach(a=>{{a[key]=Math.max(pt+6,a[key]-sh);}});}}
  }}
  place(arms,a=>yT(a.turns),'ylL'); place(arms,a=>yM(a.min),'ylR');
  arms.forEach(a=>{{const y1=yT(a.turns),y2=yM(a.min);
    if(Math.abs(a.ylL-y1)>2) s.appendChild(E('line',{{x1:xL-7,y1:a.ylL,x2:xL-1,y2:y1,stroke:'#d8d5cd','stroke-width':1}}));
    s.appendChild(E('text',{{x:xL-11,y:a.ylL+3.5,'text-anchor':'end','font-size':10,fill:'#1b1f24'}},`${{a.turns}}t \u00b7 ${{a.short}}`));
    if(Math.abs(a.ylR-y2)>2) s.appendChild(E('line',{{x1:xR+1,y1:y2,x2:xR+7,y2:a.ylR,stroke:'#d8d5cd','stroke-width':1}}));
    s.appendChild(E('text',{{x:xR+11,y:a.ylR+3.5,'font-size':10,fill:'#1b1f24'}},`${{a.short}} \u00b7 ${{a.min}}m`));
  }});
  s.appendChild(E('text',{{x:80,y:pt+H+18,'font-size':10,fill:'#0f8a5f'}},'green rises = faster than its turn count suggests'));
  s.appendChild(E('text',{{x:w-80,y:pt+H+18,'text-anchor':'end','font-size':10,fill:'#c13a2e'}},'red falls = slower than its turn count suggests'));
  const hh=document.getElementById('c_slope');hh.innerHTML='';hh.appendChild(s);
}}
function rankScatter(){{
  const R=D.rankcompare, arms=R.arms;
  const w=1060,h=436,pl=58,pr=30,pt=30,pb=50;
  const xmax=Math.max(...arms.map(a=>a.turns))*1.08, xmin=Math.min(...arms.map(a=>a.turns))-3;
  const ymax=Math.max(...arms.map(a=>a.min))*1.06, ymin=Math.min(...arms.map(a=>a.min))-2;
  const X=v=>pl+(w-pl-pr)*(v-xmin)/(xmax-xmin), Y=v=>pt+(h-pt-pb)*(ymax-v)/(ymax-ymin);
  const s=sv(w,h);
  for(let g=25;g<=xmax;g+=5){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f5f4f0'}}));s.appendChild(E('text',{{x:X(g),y:h-32,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g));}}
  for(let g=20;g<=ymax;g+=10){{s.appendChild(E('line',{{x1:pl,y1:Y(g),x2:w-pr,y2:Y(g),stroke:'#f8f7f3'}}));s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},g+'m'));}}
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'}},'turns per task (path length)'));
  s.appendChild(E('text',{{x:15,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 15 ${{(pt+h-pb)/2}})`}},'latency (minutes, suite)'));
  // discovered groupings: delivery mechanism carves the plane. Drawn behind the dots.
  const GROUPS=[
    {{lab:'Prompt-embedded',sub:'recipe + warm-up: few turns, fast',col:'#0f8a5f',ms:['5a','5b','6a','6b'],lp:'above'}},
    {{lab:'Cold + on-disk retrieval',sub:'cheap context, but a longer path',col:'#3f6ea8',ms:['1c','1b','1a','2a','2b','3b'],lp:'above'}},
    {{lab:'In-context forks',sub:'context tax: slow at any turn count',col:'#c13a2e',ms:['4a','4b'],lp:'below'}}
  ];
  const by={{}}; arms.forEach(a=>by[a.short]=a);
  GROUPS.forEach(g=>{{
    const pts=g.ms.map(m=>by[m]).filter(Boolean).map(a=>[X(a.turns),Y(a.min)]);
    const xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);
    const cx=(Math.min(...xs)+Math.max(...xs))/2, cy=(Math.min(...ys)+Math.max(...ys))/2;
    const rx=(Math.max(...xs)-Math.min(...xs))/2+30, ry=(Math.max(...ys)-Math.min(...ys))/2+24;
    s.appendChild(E('ellipse',{{cx,cy,rx,ry,fill:g.col,'fill-opacity':.06,stroke:g.col,'stroke-width':1.4,'stroke-dasharray':'6 4'}}));
    const ly=g.lp==='above'?cy-ry-13:cy+ry+14;
    s.appendChild(E('text',{{x:cx,y:ly,'text-anchor':'middle','font-size':10.5,'font-weight':700,fill:g.col}},g.lab));
    s.appendChild(E('text',{{x:cx,y:ly+11,'text-anchor':'middle','font-size':9,fill:'#5b6571'}},g.sub));
  }});
  // arm dots
  arms.forEach(a=>{{const cx=X(a.turns),cy=Y(a.min);
    s.appendChild(tip(E('circle',{{cx,cy,r:5.5,fill:a.color,opacity:.9,stroke:'#fff','stroke-width':1.3}}),`${{a.short}}: ${{a.turns}} turns, ${{a.min}}m`));
    s.appendChild(E('text',{{x:cx+(a.turns>xmax-6?-9:9),y:cy+3.5,'text-anchor':a.turns>xmax-6?'end':'start','font-size':9.5,fill:'#1b1f24'}},a.short));
  }});
  const hh=document.getElementById('c_rankscatter');hh.innerHTML='';hh.appendChild(s);
}}

const OVsel={{lat:new Set(['1c','4a','6b','3a']),turns:new Set(['1c','6b','2b','4a']),acc:new Set(D.dist_byleg.order)}};
function ovCtl(kind,ctlId){{
  const B=D.dist_byleg,sel=OVsel[kind],bar=document.getElementById(ctlId);bar.innerHTML='';
  B.order.forEach(k=>{{const l=document.createElement('label');
    l.innerHTML=`<input type="checkbox" ${{sel.has(k)?'checked':''}}><span class="sw" style="background:${{B.color[k]}}"></span>${{k}}`;
    l.querySelector('input').onchange=e=>{{e.target.checked?sel.add(k):sel.delete(k);ovDraw(kind);}};bar.appendChild(l);}});
}}
function ovDraw(kind){{
  if(kind==='acc')return accDots();
  const B=D.dist_byleg,series=B[kind],sel=OVsel[kind];
  const o=kind==='lat'?{{lo:0,hi:12,bw:0.55,tickstep:2,unit:'m',xlabel:'per-task latency (minutes)',cid:'c_dist_lat'}}:{{lo:0,hi:125,bw:6,tickstep:20,unit:'',xlabel:'per-task turn count (num_turns)',cid:'c_dist_turns'}};
  const w=1060,h=236,pl=48,pr=132,pt=16,pb=42;
  const active=B.order.filter(k=>sel.has(k));
  const grid=[],step=(o.hi-o.lo)/220;for(let x=o.lo;x<=o.hi+1e-9;x+=step)grid.push(x);
  const sq=Math.sqrt(2*Math.PI);
  const curves=active.map(k=>{{const data=series[k],n=data.length,cst=1/(n*o.bw*sq);
    return {{k,dens:grid.map(x=>data.reduce((sm,v)=>sm+Math.exp(-.5*((x-v)/o.bw)**2),0)*cst)}};}});
  const ymax=Math.max(0.02,...curves.flatMap(c=>c.dens))*1.16;
  const X=v=>pl+(w-pl-pr)*(v-o.lo)/(o.hi-o.lo),Y=v=>pt+(h-pt-pb)*(1-v/ymax);
  const s=sv(w,h);
  for(let g=o.lo;g<=o.hi+1e-9;g+=o.tickstep){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f7f6f2'}}));s.appendChild(E('text',{{x:X(g),y:h-25,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g+o.unit));}}
  s.appendChild(E('line',{{x1:pl,y1:Y(0),x2:w-pr,y2:Y(0),stroke:'#c9c7c1'}}));
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-6,'text-anchor':'middle','font-size':10,fill:'#5b6571'}},o.xlabel));
  s.appendChild(E('text',{{x:13,y:(pt+h-pb)/2,'font-size':9.5,fill:'#8a929c','text-anchor':'middle',transform:`rotate(-90 13 ${{(pt+h-pb)/2}})`}},'density'));
  if(!active.length)s.appendChild(E('text',{{x:(pl+w-pr)/2,y:(pt+h-pb)/2,'text-anchor':'middle','font-size':11,fill:'#8a929c'}},'select one or more legs'));
  curves.forEach((c,ci)=>{{const col=B.color[c.k];let d='';
    c.dens.forEach((yv,i)=>{{d+=(d?'L':'M')+X(grid[i]).toFixed(1)+' '+Y(Math.min(yv,ymax)).toFixed(1)+' ';}});
    s.appendChild(tip(E('path',{{d,fill:'none',stroke:col,'stroke-width':2.1,opacity:.92}}),`${{c.k}}: mean ${{(series[c.k].reduce((a,b)=>a+b,0)/series[c.k].length).toFixed(1)}}${{o.unit}}, n=${{series[c.k].length}}`));
    series[c.k].forEach(v=>s.appendChild(E('line',{{x1:X(v),y1:h-pb+2+ci*2,x2:X(v),y2:h-pb+5+ci*2,stroke:col,'stroke-width':1,opacity:.55}})));
  }});
  let ly=pt+8;active.forEach(k=>{{s.appendChild(E('line',{{x1:w-pr+12,y1:ly,x2:w-pr+30,y2:ly,stroke:B.color[k],'stroke-width':2.6}}));s.appendChild(E('text',{{x:w-pr+35,y:ly+3.5,'font-size':10,fill:'#5b6571'}},k));ly+=15;}});
  document.getElementById(o.cid).innerHTML='';document.getElementById(o.cid).appendChild(s);
}}
function accDots(){{
  const B=D.dist_byleg,sel=OVsel.acc,order=B.order.filter(k=>sel.has(k));
  const w=1060,h=214,pl=48,pr=24,pt=18,pb=40,lo=7.5,hi=12;
  const X=v=>pl+(w-pl-pr)*(v-lo)/(hi-lo);const s=sv(w,h);
  for(let g=8;g<=12;g++){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f5f4f0'}}));s.appendChild(E('text',{{x:X(g),y:h-24,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g+'/12'));}}
  const byscore={{}};order.forEach(k=>{{const sc=B.acc[k];(byscore[sc]=byscore[sc]||[]).push(k);}});
  Object.keys(byscore).forEach(sc=>{{byscore[sc].forEach((k,i)=>{{const cy=pt+14+i*17,cx=X(+sc);
    s.appendChild(tip(E('circle',{{cx,cy,r:6,fill:B.color[k],opacity:.9,stroke:'#fff','stroke-width':1.3}}),`${{k}}: ${{sc}}/12`));
    s.appendChild(E('text',{{x:cx+11,y:cy+3.5,'font-size':9.5,fill:'#1b1f24'}},k));}});}});
  s.appendChild(E('line',{{x1:pl,y1:h-pb,x2:w-pr,y2:h-pb,stroke:'#c9c7c1'}}));
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-6,'text-anchor':'middle','font-size':10,fill:'#5b6571'}},'accuracy per leg (tasks passed of 12)'));
  document.getElementById('c_dist_acc').innerHTML='';document.getElementById('c_dist_acc').appendChild(s);
}}
function initDist(){{ovCtl('lat','ov_lat_ctl');ovDraw('lat');ovCtl('turns','ov_turns_ctl');ovDraw('turns');ovCtl('acc','ov_acc_ctl');accDots();}}
function reliabilityScatter(){{
  const R=D.reliability, arms=R.arms, k=R.kcv;
  const w=1060,h=340,pl=56,pr=150,pt=22,pb=48;
  const xmax=Math.max(...arms.map(a=>a.lm))*1.12, ymax=Math.max(...arms.map(a=>a.ls))*1.15;
  const X=v=>pl+(w-pl-pr)*v/xmax, Y=v=>pt+(h-pt-pb)*(1-v/ymax);
  const s=sv(w,h);
  for(let g=1;g<=xmax;g+=1){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f5f4f0'}}));s.appendChild(E('text',{{x:X(g),y:h-30,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g+'m'));}}
  for(let g=1;g<=ymax;g+=1){{s.appendChild(E('line',{{x1:pl,y1:Y(g),x2:w-pr,y2:Y(g),stroke:'#f8f7f3'}}));s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},g+'m'));}}
  // reference line SD = k * mean
  const xe=xmax, ye=Math.min(ymax,k*xmax);
  s.appendChild(E('line',{{x1:X(0),y1:Y(0),x2:X(xe),y2:Y(ye),stroke:'#8a929c','stroke-width':1.6,'stroke-dasharray':'6 4'}}));
  s.appendChild(E('text',{{x:X(xe)-4,y:Y(ye)-6,'text-anchor':'end','font-size':9,'font-style':'italic',fill:'#8a929c'}},`typical spread (SD = ${{k}} x mean)`));
  s.appendChild(E('text',{{x:X(0.15),y:Y(ymax*.94),'font-size':9.5,'font-style':'italic',fill:'#c13a2e'}},'above = erratic (spread beyond what speed predicts)'));
  s.appendChild(E('text',{{x:X(xmax*.98),y:Y(0.12),'text-anchor':'end','font-size':9.5,'font-style':'italic',fill:'#0f8a5f'}},'below = consistent (tighter than its speed predicts)'));
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'}},'mean latency per task (minutes)'));
  s.appendChild(E('text',{{x:15,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 15 ${{(pt+h-pb)/2}})`}},'SD of latency (minutes)'));
  arms.forEach(a=>{{const cx=X(a.lm),cy=Y(a.ls);const erratic=a.lcv>k+0.03;
    s.appendChild(tip(E('circle',{{cx,cy,r:5.5,fill:a.color,opacity:.88,stroke:'#fff','stroke-width':1.3}}),`${{a.short}}: mean ${{a.lm}}m, SD ${{a.ls}}m, CV ${{a.lcv}} (turn CV ${{a.tcv}})`));
    s.appendChild(E('text',{{x:cx+(a.lm>xmax*.72?-9:9),y:cy+3.5,'text-anchor':a.lm>xmax*.72?'end':'start','font-size':9.5,'font-weight':a.lcv>0.9||a.lcv<0.52?'700':'400',fill:'#1b1f24'}},`${{a.short}}`));
  }});
  let ly=pt+8;const seen={{}};
  const hh=document.getElementById('c_reliability');hh.innerHTML='';hh.appendChild(s);
}}
function landscape(){{
  const L=D_LAND;const w=1060,h=430,pl=64,pb=52,pr=140,pt=26;
  const CLR={{easy:'#0f8a5f',medium:'#b45309',hard:'#c13a2e'}};
  const xmax=Math.max(...L.map(r=>r.dur))*1.12, ymax=1.0;
  const X=v=>pl+(w-pl-pr)*v/xmax, Y=v=>pt+(h-pt-pb)*(1-v/ymax);
  const s=sv(w,h);
  const xmed=[...L.map(r=>r.dur)].sort((a,b)=>a-b)[Math.floor(L.length/2)];
  const yth=0.15;
  // quadrant guides
  s.appendChild(E('line',{{x1:X(xmed),y1:pt,x2:X(xmed),y2:h-pb,stroke:'#e7e6e1','stroke-dasharray':'4 4'}}));
  s.appendChild(E('line',{{x1:pl,y1:Y(yth),x2:w-pr,y2:Y(yth),stroke:'#e7e6e1','stroke-dasharray':'4 4'}}));
  const ql=[[X(xmed)-8,Y(yth)+16,'end','quick & safe','#8a929c'],
            [X(xmed)+8,Y(yth)+16,'start','long haul','#8a929c'],
            [X(xmed)-8,pt+12,'end','brittle / traps','#c13a2e'],
            [X(xmed)+8,pt+12,'start','long AND brittle','#c13a2e']];
  ql.forEach(q=>s.appendChild(E('text',{{x:q[0],y:q[1],'text-anchor':q[2],'font-size':10,'font-style':'italic',fill:q[4]}},q[3])));
  // axes ticks
  for(let g=0;g<=xmax;g+=1){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f7f6f2'}}));s.appendChild(E('text',{{x:X(g),y:h-34,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g+'m'))}}
  [0,.25,.5,.75,1].forEach(g=>s.appendChild(E('text',{{x:pl-8,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},Math.round(g*100)+'%')));
  s.appendChild(E('line',{{x1:pl,y1:h-pb,x2:w-pr,y2:h-pb,stroke:'#c9c7c1'}}));
  s.appendChild(E('line',{{x1:pl,y1:pt,x2:pl,y2:h-pb,stroke:'#c9c7c1'}}));
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-10,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'}},'duration: denoised cold-baseline minutes (how long)'));
  s.appendChild(E('text',{{x:18,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 18 ${{(pt+h-pb)/2}})`}},'failure rate across 22 arms (how hard)'));
  // dots
  const ann={{'zilloft-9':'the marathon','zilloft-10':'the trap','dashdish-8':'broken rubric'}};
  // selective labels: annotate the narrative tasks only; the low-failure "safe
  // pile" clusters near 2m and would collide, so those are dots-plus-hover.
  const LABEL=new Set(['zilloft-9','zilloft-10','dashdish-8','zilloft-2','zilloft-5','dashdish-1']);
  L.forEach(r=>{{
    const cx=X(r.dur),cy=Y(r.fail);const rad=r.broken?7:6.5;
    const c=E('circle',{{cx,cy,r:rad,fill:CLR[r.cls],opacity:r.broken?0.35:0.82,stroke:r.broken?'#c13a2e':'#fff','stroke-width':r.broken?1.6:1.2}});
    if(r.broken)c.setAttribute('stroke-dasharray','2 2');
    s.appendChild(tip(c,`${{r.t}} (${{r.cls}}): ${{r.dur}}m, ${{r.turns}} turns, fails ${{Math.round(r.fail*100)}}% (${{r.nfail}}/${{r.n}}) · diff-score ${{r.diffscore}}`));
    if(!LABEL.has(r.t))return;
    const lab=ann[r.t]?`${{r.t}} · ${{ann[r.t]}}`:r.t;
    const dx=(r.dur>xmed?-10:10), ta=(r.dur>xmed?'end':'start');
    s.appendChild(E('text',{{x:cx+dx,y:cy+(r.fail>0.85?16:3.5),'text-anchor':ta,'font-size':9.5,fill:ann[r.t]?(r.broken?'#8a929c':'#1b1f24'):'#5b6571','font-weight':ann[r.t]?'600':'400'}},lab));
  }});
  s.appendChild(E('text',{{x:X(2.05),y:Y(0)+30,'text-anchor':'middle','font-size':9.5,'font-style':'italic',fill:'#8a929c'}},'the quick & reliable pile (7 tasks, hover for detail)'));
  // legend
  let ly=pt+6;[['easy','#0f8a5f'],['medium','#b45309'],['hard','#c13a2e']].forEach(k=>{{
    s.appendChild(E('circle',{{cx:w-pr+22,cy:ly,r:5,fill:k[1],opacity:.82}}));
    s.appendChild(E('text',{{x:w-pr+32,y:ly+4,'font-size':10.5,fill:'#5b6571'}},k[0]));ly+=18;}});
  ly+=6;
  s.appendChild(E('circle',{{cx:w-pr+22,cy:ly,r:5,fill:'none',stroke:'#c13a2e','stroke-dasharray':'2 2','stroke-width':1.4}}));
  s.appendChild(E('text',{{x:w-pr+32,y:ly+4,'font-size':10,fill:'#8a929c'}},'broken rubric'));
  const hh=document.getElementById('c_landscape');hh.innerHTML='';hh.appendChild(s);
}}
function diffBars(){{
  // arms that help somewhere: recipe + warmup + analysis + 5D
  const pick=['exp3c-analysis','exp5a-recipe-site','exp5c-atomic-warmup','exp5d-warmup-recipe','exp4b-expert-fork'];
  const tiers=['easy','medium','hard'];
  const w=1060,h=300,pl=48;const cw=(w-pl-20)/pick.length;const bw=Math.min(30,(cw-30)/3);
  const cell={{}};pick.forEach(id=>{{const a=BY[id];cell[id]={{}};tiers.forEach(tr=>{{
    const ts=ORDER.filter(t=>DIFF[t]===tr);
    cell[id][tr]=ts.reduce((s,t)=>s+(COLD.per_task.find(x=>x.t===t).min - a.per_task.find(x=>x.t===t).min),0)/ts.length;}});}});
  const vmax=Math.max(...pick.flatMap(id=>tiers.map(tr=>Math.abs(cell[id][tr]))),0.5)*1.15;
  const Y=v=>34+(h-96)*(vmax-Math.max(-vmax,Math.min(vmax,v)))/(2*vmax);const s=sv(w,h);
  s.appendChild(E('text',{{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'}},'time benefit vs cold by task difficulty (min/task saved; + = faster than cold)'));
  for(let g=-Math.ceil(vmax);g<=vmax;g++){{s.appendChild(E('line',{{x1:pl,y1:Y(g),x2:w-10,y2:Y(g),stroke:g===0?'#c9c7c1':'#f3f2ee','stroke-width':g===0?2:1}}));s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},(g>0?'+':'')+g))}}
  pick.forEach((id,pi)=>{{const a=BY[id];const x0=pl+14+pi*cw;
    tiers.forEach((tr,ti)=>{{const v=cell[id][tr];const x=x0+ti*(bw+6),y0=Y(0),y1=Y(v);
      const shade={{easy:.4,medium:.68,hard:1}}[tr];
      s.appendChild(tip(E('rect',{{x,y:Math.min(y0,y1),width:bw,height:Math.abs(y1-y0)||1,rx:2.5,fill:v>=0?'#0f8a5f':'#c13a2e',opacity:shade}}),`${{a.label}} · ${{tr}}: ${{v>0?'+':''}}${{v.toFixed(2)}}m/task`));
      s.appendChild(E('text',{{x:x+bw/2,y:v>=0?y1-3:y1+10,'text-anchor':'middle','font-size':8.5,fill:'#5b6571'}},tr[0]));
    }});
    s.appendChild(E('text',{{x:x0+1.5*bw,y:h-30,'text-anchor':'middle','font-size':10,fill:'#5b6571'}},a.short));
  }});
  s.appendChild(E('text',{{x:pl,y:h-12,'font-size':10,fill:'#8a929c'}},'bar shade: light=easy, mid=medium, dark=hard · every positive bar sits in the hard tier'));
  document.getElementById('c_diffbars').appendChild(s);
}}
// census + detail
let sk='total',sd=1;
function census(){{
  const cols=[['label','arm',0],['phase','phase',0],['passed','pass',1],['total','run m',1],['prep','prep m',1],['mean_task','m/task',1],['turns','turns',1],['ktok','tok/turn',1],['first','first-act s',1],['mean_delta','Δ vs cold',1]];
  const rows=A.slice().sort((x,y)=>{{const a=x[sk],b=y[sk];return((a<b?-1:a>b?1:0))*sd}});
  let h='<thead><tr>'+cols.map(([k,l])=>`<th class="sortable" onclick="csort('${{k}}')">${{l}}${{sk===k?(sd<0?' ▾':' ▴'):''}}</th>`).join('')+'</tr></thead><tbody>';
  rows.forEach(a=>{{h+=`<tr class="clickable" onclick="showArm('${{a.id}}')"><td><span class="sw" style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${{a.color}};margin-right:6px"></span>${{a.label}}</td>`+
    `<td>${{a.phase}}</td><td class="num">${{a.passed}}/12</td><td class="num">${{a.total.toFixed(1)}}</td><td class="num">${{a.prep.toFixed(0)}}</td><td class="num">${{a.mean_task.toFixed(2)}}</td><td class="num">${{a.turns.toFixed(0)}}</td><td class="num">${{a.ktok}}k</td><td class="num">${{a.first==null?'·':a.first.toFixed(0)}}</td><td class="num" style="color:${{a.mean_delta<=0?'#0f8a5f':'#c13a2e'}}">${{a.mean_delta>0?'+':''}}${{a.mean_delta}}</td></tr>`;}});
  document.getElementById('census').innerHTML=h+'</tbody>';
}}
function csort(k){{if(sk===k)sd*=-1;else{{sk=k;sd=-1}}census()}}
function openD(html){{document.getElementById('detailbody').innerHTML=html;document.getElementById('detail').classList.add('open')}}
function showArm(id){{const a=BY[id];
  let h=`<h3 style="margin:2px 0"><span class="sw" style="display:inline-block;width:11px;height:11px;background:${{a.color}};border-radius:3px;margin-right:7px"></span>${{a.label}} <span class="note">· ${{a.passed}}/12 · ${{a.total}}m · ${{a.ktok}}k tok/turn</span></h3>
  <p class="note" style="margin:2px 0 8px">${{a.desc}}</p><div class="scroll"><table><thead><tr><th>task</th><th>diff</th><th>verdict</th><th>min</th><th>turns</th><th>first-act</th><th>tok/turn</th><th>failing answer</th></tr></thead><tbody>`;
  a.per_task.forEach(c=>{{h+=`<tr class="clickable" onclick="showTask('${{c.t}}')"><td class="mono">${{c.t}}</td><td>${{DIFF[c.t]}}</td><td>${{c.passed?(c.slow?'<span class="badge" style="background:#ca8a0418;color:#ca8a04">SLOW</span>':'<span class="badge b-pass">PASS</span>'):'<span class="badge b-fail">FAIL</span>'}}</td><td class="num">${{c.min.toFixed(1)}}</td><td class="num">${{c.turns}}</td><td class="num">${{c.fa==null?'·':c.fa+'s'}}</td><td class="num">${{c.kt}}k</td><td class="note">${{c.fail||''}}</td></tr>`;}});
  openD(h+'</tbody></table></div>');
}}
function showTask(t){{
  let h=`<h3 style="margin:2px 0">${{t}} <span class="note">(${{DIFF[t]}})</span></h3><p class="note" style="margin:2px 0 8px">${{D.goals[t]}}</p>
  <div class="scroll"><table><thead><tr><th>arm</th><th>verdict</th><th>min</th><th>turns</th><th>tok/turn</th><th>failing answer</th></tr></thead><tbody>`;
  A.forEach(a=>{{const c=a.per_task.find(x=>x.t===t);h+=`<tr><td><span class="sw" style="display:inline-block;width:9px;height:9px;background:${{a.color}};border-radius:2px;margin-right:6px"></span>${{a.label}}</td><td>${{c.passed?'<span class="badge b-pass">PASS</span>':'<span class="badge b-fail">FAIL</span>'}}</td><td class="num">${{c.min.toFixed(1)}}</td><td class="num">${{c.turns}}</td><td class="num">${{c.kt}}k</td><td class="note">${{c.fail||''}}</td></tr>`;}});
  openD(h+'</tbody></table></div>');
}}
accChart();accGrid();renderPerf();deltaChart();ktokChart();lawScatter();diffBars();scaleCtl('ls_ctl',LSsel,lengthScale);lengthScale();thinkBar();turnDelta();scaleCtl('ts_ctl',TSsel,turnScale);turnScale();slopeChart();rankScatter();initDist();reliabilityScatter();sensBar();diffScatterCtl();diffScatter2();landscape();itMode();itCtl();itemized();themeTable();themeScatter();census();
document.querySelector('.navtoggle').onclick=()=>document.body.classList.toggle('navhidden');
</script>
</div></body></html>"""
