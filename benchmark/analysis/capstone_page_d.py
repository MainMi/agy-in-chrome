# Capstone page assembly for build_capstone.py — pure refactor,
# behavior unchanged.

from capstone_data import *

PAGE_D = f"""    const y=pt+i*rh+rh/2;
    if(i%2)s.appendChild(E('rect',{{x:pl-6,y:y-rh/2,width:w-pl-pr+12,height:rh,fill:'#faf9f6'}}));
    s.appendChild(E('circle',{{cx:14,cy:y,r:4,fill:CLR[t.cls],opacity:.8}}));
    s.appendChild(E('text',{{x:24,y:y+4,'font-size':11.5,fill:'#1b1f24'}},t.t));
    s.appendChild(E('text',{{x:pl-12,y:y+4,'text-anchor':'end','font-size':10,fill:'#8a929c','font-family':'"SF Mono",monospace'}},'base '+t.dur.toFixed(1)+'m'));
    // baseline anchor: abs = per-row diamond; delta/rel = the darker 0 gridline
    if(ITMODE==='abs'){{const bx=X(t.dur);
      s.appendChild(E('line',{{x1:bx,y1:y-11,x2:bx,y2:y+11,stroke:'#b8b6b0','stroke-width':1.2}}));
      s.appendChild(tip(E('path',{{d:`M ${{bx}} ${{y-6}} L ${{bx+6}} ${{y}} L ${{bx}} ${{y+6}} L ${{bx-6}} ${{y}} Z`,fill:'#8a929c'}}),`${{t.t}} phase-1 baseline: ${{t.dur.toFixed(2)}}m`));
    }}
    // leg marks
    legs.forEach(a=>{{const v=val(a,t.t);if(v==null)return;
      const raw=pv(v,t.dur), pct=100*(v-t.dur)/t.dur;
      const fac=v>=t.dur?(v/t.dur).toFixed(1)+'x slower':(t.dur/v).toFixed(1)+'x faster';
      const tt=ITMODE==='rel'
        ?`${{a.short}} · ${{t.t}}: ${{pct>=0?'+':''}}${{pct.toFixed(0)}}% (${{fac}}), ${{v.toFixed(2)}}m vs ${{t.dur.toFixed(2)}}m base`
        :`${{a.short}} · ${{t.t}}: ${{v.toFixed(2)}}m (${{v-t.dur>=0?'+':''}}${{(v-t.dur).toFixed(2)}}m vs base)`;
      if(ITMODE==='rel' && raw>xmax){{const ex=X(xmax);
        s.appendChild(tip(E('path',{{d:`M ${{ex+4}} ${{y}} L ${{ex-4}} ${{y-5}} L ${{ex-4}} ${{y+5}} Z`,fill:a.color,opacity:.9,stroke:'#fff','stroke-width':1}}),tt));
        s.appendChild(E('text',{{x:ex-9,y:y+3.5,'text-anchor':'end','font-size':9,fill:a.color}},`+${{Math.round(pct)}}%`));
      }} else {{
        s.appendChild(tip(E('circle',{{cx:X(raw),cy:y,r:5,fill:a.color,opacity:.82,stroke:'#fff','stroke-width':1.1}}),tt));
      }}
    }});
  }});
  // per-leg average lines across all tasks, with the value labeled underneath
  avgs.forEach(r=>{{
    s.appendChild(E('line',{{x1:r.x,y1:pt,x2:r.x,y2:PB,stroke:r.a.color,'stroke-width':1.4,'stroke-dasharray':'5 4',opacity:.9}}));
    const lab=ITMODE==='abs'?r.m.toFixed(1)+'m':ITMODE==='rel'?(r.m>=0?'+':'')+Math.round(r.m)+'%':(r.m>=0?'+':'')+r.m.toFixed(1)+'m';
    s.appendChild(E('text',{{x:r.x,y:PB+24+r.lane*12,'text-anchor':'middle','font-size':9,'font-weight':600,fill:r.a.color}},`${{r.a.short}} avg ${{lab}}`));
  }});
  // legend (right gutter)
  let ly=pt+8;legs.forEach(a=>{{s.appendChild(E('circle',{{cx:w-pr+22,cy:ly,r:4.5,fill:a.color}}));s.appendChild(E('text',{{x:w-pr+31,y:ly+4,'font-size':10.5,fill:'#5b6571'}},a.short));ly+=17;}});
  ly+=4;
  if(ITMODE==='abs')s.appendChild(E('path',{{d:`M ${{w-pr+22}} ${{ly-4}} L ${{w-pr+27}} ${{ly}} L ${{w-pr+22}} ${{ly+4}} L ${{w-pr+17}} ${{ly}} Z`,fill:'#8a929c'}}));
  else s.appendChild(E('line',{{x1:w-pr+22,y1:ly-5,x2:w-pr+22,y2:ly+5,stroke:'#c9c7c1','stroke-width':1.5}}));
  s.appendChild(E('text',{{x:w-pr+31,y:ly+4,'font-size':10,fill:'#8a929c'}},ITMODE==='abs'?'phase-1 base':'phase-1 base (0)'));
  const hh=document.getElementById('c_itemized');hh.innerHTML='';hh.appendChild(s);
}}

function themeTable(){{
  const T=D.themes;const cold=D.coldtotal;
  let html='<thead><tr><th>Theme</th><th>Arms</th><th class="num">tok/turn</th><th class="num">s/turn</th><th class="num">total min</th><th class="num">vs cold</th><th class="num">turns</th><th class="num">accuracy</th></tr></thead><tbody>';
  T.forEach(t=>{{
    const d=t.dtime;const dc=d<=-0.5?'#0f8a5f':d>=3?'#c13a2e':'#5b6571';
    html+=`<tr><td><span class="sw" style="display:inline-block;background:${{t.color}}"></span> ${{t.label}}<div class="note" style="margin:2px 0 0">${{t.desc}}</div></td>`+
      `<td class="mono" style="font-size:11px">${{t.arms.join(', ')}}</td>`+
      `<td class="num">${{t.ktok}}k</td><td class="num">${{t.secturn}}</td><td class="num">${{t.total}}</td>`+
      `<td class="num" style="color:${{dc}};font-weight:600">${{d>0?'+':''}}${{d}}</td>`+
      `<td class="num">${{t.turns}}</td><td class="num">${{t.acc}}/12</td></tr>`;
  }});
  html+='</tbody>';document.getElementById('themetab').innerHTML=html;
}}
function themeScatter(){{
  const T=D.themes, cold=D.coldtask_min;  // cold per-task minutes (highlighted iso curve)
  const TCsec={{}}; D.turncost.arms.forEach(a=>TCsec[a.short]=a.sec);  // real per-turn latency
  const arms=A.map(a=>({{...a, secturn:(TCsec[a.short]!=null?TCsec[a.short]:a.total*60/a.turns), color:(T.find(t=>t.key===a.theme)||{{}}).color||'#8a929c'}}));
  const w=1060,h=440,pl=58,pr=150,pt=20,pb=46;
  const xmax=Math.max(...arms.map(a=>a.turns))*1.1, ymax=Math.max(...arms.map(a=>a.secturn))*1.14;
  const X=v=>pl+(w-pl-pr)*v/xmax, Y=v=>pt+(h-pt-pb)*(1-v/ymax);
  const s=sv(w,h);
  // iso-time curves: seconds/turn = (per-task minutes)*60 / turns
  [1.5,2,2.5,3,4,5].forEach(tm=>{{
    let d='';for(let tn=Math.max(1,tm*60/ymax);tn<=xmax;tn+=1){{const sc=tm*60/tn;if(sc>ymax)continue;d+=(d?'L':'M')+X(tn).toFixed(1)+' '+Y(sc).toFixed(1)+' ';}}
    const hot=Math.abs(tm-cold)<0.35;
    s.appendChild(E('path',{{d,fill:'none',stroke:hot?'#b8b6b0':'#e2e0da','stroke-width':hot?1.6:1,'stroke-dasharray':hot?'':'3 3'}}));
    const tn=xmax*0.96,sc=tm*60/tn;if(sc<ymax&&sc>0)s.appendChild(E('text',{{x:X(tn)+3,y:Y(sc)+3,'font-size':9,fill:hot?'#8a929c':'#b0aea8'}},tm+'m'));
  }});
  // axes
  s.appendChild(E('line',{{x1:pl,y1:h-pb,x2:w-pr,y2:h-pb,stroke:'#c9c7c1'}}));
  s.appendChild(E('line',{{x1:pl,y1:pt,x2:pl,y2:h-pb,stroke:'#c9c7c1'}}));
  for(let g=0;g<=xmax;g+=20)s.appendChild(E('text',{{x:X(g),y:h-pb+15,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g));
  for(let g=0;g<=ymax;g+=1)s.appendChild(E('text',{{x:pl-7,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},g+'s'));
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-6,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'}},'turns (steps taken)'));
  s.appendChild(E('text',{{x:16,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 16 ${{(pt+h-pb)/2}})`}},'seconds per turn (real per-turn latency)'));
  // arm dots
  arms.forEach(a=>{{const cx=X(a.turns),cy=Y(a.secturn);
    s.appendChild(tip(E('circle',{{cx,cy,r:6,fill:a.color,opacity:.85,stroke:'#fff','stroke-width':1.3}}),`${{a.short}} (${{a.label}}): ${{a.turns}} turns, ${{a.secturn.toFixed(2)}}s/turn, ${{(a.turns*a.secturn/60).toFixed(1)}}m/task, ${{a.total.toFixed(1)}}m suite`));
    s.appendChild(E('text',{{x:cx+(a.turns>xmax*0.7?-9:9),y:cy+3,'text-anchor':a.turns>xmax*0.7?'end':'start','font-size':9,fill:'#1b1f24'}},a.short));
  }});
  // theme legend
  let ly=pt+6;T.forEach(t=>{{s.appendChild(E('circle',{{cx:w-pr+22,cy:ly,r:5,fill:t.color,opacity:.85}}));s.appendChild(E('text',{{x:w-pr+31,y:ly+4,'font-size':10,fill:'#5b6571'}},t.label));ly+=17;}});
  const hh=document.getElementById('c_theme');hh.innerHTML='';hh.appendChild(s);
}}

function thinkBar(){{
  const T=D.thinking, arms=T.arms, cold=T.coldmean;
  const w=1060,pl=64,pr=90,pt=16,rh=26,gap=8;const h=pt+rh*arms.length+34;
  const xmax=Math.max(...arms.map(a=>a.outturn))*1.08;
  const X=v=>pl+(w-pl-pr)*v/xmax;const s=sv(w,h);
  for(let g=0;g<=xmax;g+=25){{s.appendChild(E('line',{{x1:X(g),y1:pt-4,x2:X(g),y2:pt+rh*arms.length,stroke:'#f3f2ee'}}));s.appendChild(E('text',{{x:X(g),y:pt+rh*arms.length+16,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g));}}
  // cold reference line
  s.appendChild(E('line',{{x1:X(cold),y1:pt-4,x2:X(cold),y2:pt+rh*arms.length,stroke:'#8a929c','stroke-width':1.5,'stroke-dasharray':'5 4'}}));
  s.appendChild(E('text',{{x:X(cold),y:pt-7,'text-anchor':'middle','font-size':9.5,fill:'#5b6571'}},`cold ~${{cold}}`));
  s.appendChild(E('text',{{x:pl+(w-pl-pr)/2,y:h-3,'text-anchor':'middle','font-size':10,fill:'#5b6571'}},'output tokens generated per turn'));
  arms.forEach((a,i)=>{{const y=pt+i*rh;
    s.appendChild(E('text',{{x:pl-10,y:y+rh/2-gap/2+4,'text-anchor':'end','font-size':11,fill:'#1b1f24','font-weight':600}},a.short));
    s.appendChild(tip(E('rect',{{x:X(0),y:y,width:Math.max(1,X(a.outturn)-X(0)),height:rh-gap,rx:2.5,fill:a.color,opacity:.88}}),`${{a.short}}: ${{a.outturn}} tokens/turn (sd ${{a.sd}}), ${{a.turns}} turns/task`));
    s.appendChild(E('text',{{x:X(a.outturn)+7,y:y+rh/2-gap/2+4,'font-size':10,fill:'#5b6571'}},a.outturn));
  }});
  const hh=document.getElementById('c_thinkbar');hh.innerHTML='';hh.appendChild(s);
}}
function turnDelta(){{
  const T=D.turns, arms=T.arms;  // sorted ascending by delta (most-negative first)
  const w=1060,pl=64,pr=120,pt=18,rh=26,gap=8;const h=pt+rh*arms.length+34;
  const dmax=Math.max(...arms.map(a=>Math.abs(a.delta)),1)*1.15;
  const X=v=>pl+((w-pl-pr))*(v+dmax)/(2*dmax);const s=sv(w,h);
  s.appendChild(E('line',{{x1:X(0),y1:pt-4,x2:X(0),y2:pt+rh*arms.length,stroke:'#c9c7c1','stroke-width':2}}));
  s.appendChild(E('text',{{x:X(-dmax*.6),y:pt-6,'text-anchor':'middle','font-size':10,fill:'#0f8a5f'}},'← fewer turns (more direct)'));
  s.appendChild(E('text',{{x:X(dmax*.55),y:pt-6,'text-anchor':'middle','font-size':10,fill:'#c13a2e'}},'more turns (extra steps) →'));
  s.appendChild(E('text',{{x:X(0),y:pt+rh*arms.length+16,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},`cold = ${{T.coldmean}} turns`));
  arms.forEach((a,i)=>{{const y=pt+i*rh;const x0=X(0),x1=X(a.delta);const pos=a.delta>0;
    s.appendChild(E('text',{{x:pl-10,y:y+rh/2-gap/2+4,'text-anchor':'end','font-size':11,fill:'#1b1f24','font-weight':600}},a.short));
    s.appendChild(tip(E('rect',{{x:Math.min(x0,x1),y:y,width:Math.max(2,Math.abs(x1-x0)),height:rh-gap,rx:2.5,fill:pos?'#c13a2e':'#0f8a5f',opacity:.82}}),`${{a.short}}: ${{a.turns}} turns, ${{a.delta>0?'+':''}}${{a.delta}} vs cold (${{a.pct>0?'+':''}}${{a.pct}}%)`));
    s.appendChild(E('text',{{x:x1+(pos?5:-5),y:y+rh/2-gap/2+4,'text-anchor':pos?'start':'end','font-size':10,fill:'#5b6571'}},`${{a.pct>0?'+':''}}${{a.pct}}%`));
  }});
  const hh=document.getElementById('c_turndelta');hh.innerHTML='';hh.appendChild(s);
}}
function turnScale(){{
  const L=D.turns.scale, C=D.dist_byleg.color, sel=D.dist_byleg.order.filter(k=>TSsel.has(k));
  const w=1060,h=360,pl=56,pr=112,pt=20,pb=48;
  const xmax=Math.max(...L.tasks.map(t=>t.bturns))*1.06;
  const ally=sel.flatMap(k=>L.tasks.map(t=>t.sv[k]).filter(v=>v!=null));
  const ymin=Math.min(...ally,-6)*1.12, ymax=Math.max(...ally,6)*1.12;
  const X=v=>pl+(w-pl-pr)*v/xmax, Y=v=>pt+(h-pt-pb)*(ymax-v)/(ymax-ymin);const s=sv(w,h);
  for(let g=0;g<=xmax;g+=10){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f3f2ee'}}));s.appendChild(E('text',{{x:X(g),y:h-30,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g));}}
  s.appendChild(E('line',{{x1:pl,y1:Y(0),x2:w-pr,y2:Y(0),stroke:'#c9c7c1','stroke-width':1.5}}));
  s.appendChild(E('text',{{x:w-pr+4,y:Y(0)+3,'font-size':9,fill:'#8a929c'}},'cold'));
  for(let g=Math.ceil(ymin/10)*10;g<=ymax;g+=10){{if(g===0)continue;s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},(g>0?'+':'')+g));}}
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'}},'baseline task length (naive cold turns)'));
  s.appendChild(E('text',{{x:15,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 15 ${{(pt+h-pb)/2}})`}},'turns saved vs cold (up = shorter path)'));
  if(!sel.length)s.appendChild(E('text',{{x:(pl+w-pr)/2,y:(pt+h-pb)/2,'text-anchor':'middle','font-size':11,fill:'#8a929c'}},'select one or more legs'));
  sel.forEach(k=>{{const col=C[k], f=L.fits[k];
    L.tasks.forEach(t=>{{const v=t.sv[k];if(v==null)return;
      s.appendChild(tip(E('circle',{{cx:X(t.bturns),cy:Y(v),r:4,fill:col,opacity:.72}}),`${{k}} · ${{t.t}} (${{t.cls}}, ${{t.bturns}} base turns): ${{v>0?'+':''}}${{v}} turns saved`));}});
    s.appendChild(E('line',{{x1:X(1),y1:Y(f.intercept+f.slope*1),x2:X(xmax*.98),y2:Y(f.intercept+f.slope*xmax*.98),stroke:col,'stroke-width':2.4,'stroke-dasharray':'6 4'}}));}});
  let ly=pt+8;sel.forEach(k=>{{const cc=L.fits[k].corr;
    s.appendChild(E('circle',{{cx:w-pr+14,cy:ly,r:4.5,fill:C[k]}}));
    s.appendChild(E('text',{{x:w-pr+22,y:ly+3.5,'font-size':10,fill:'#5b6571'}},k));
    s.appendChild(E('text',{{x:w-pr+52,y:ly+3.5,'font-size':9,fill:cc>0?'#0f8a5f':'#c13a2e'}},`${{cc>0?'+':''}}${{cc}}`));ly+=16;}});
  const hh=document.getElementById('c_turnscale');hh.innerHTML='';hh.appendChild(s);
}}
let LSsel=new Set(['6b','5b','4a']);
let TSsel=new Set(['6b','5b','2b']);
function scaleCtl(ctlId,sel,redraw){{
  const bar=document.getElementById(ctlId);bar.innerHTML='';
  D.dist_byleg.order.forEach(k=>{{const l=document.createElement('label');
    l.innerHTML=`<input type="checkbox" ${{sel.has(k)?'checked':''}}><span class="sw" style="background:${{D.dist_byleg.color[k]}}"></span>${{k}}`;
    l.querySelector('input').onchange=e=>{{e.target.checked?sel.add(k):sel.delete(k);redraw();}};bar.appendChild(l);}});
}}
function lengthScale(){{
  const L=D.lengthscale, C=D.dist_byleg.color, sel=D.dist_byleg.order.filter(k=>LSsel.has(k));
  const w=1060,h=380,pl=60,pr=112,pt=20,pb=48;
  const xmax=Math.max(...L.tasks.map(t=>t.bturns))*1.06;
  const ymin=-210,ymax=120;
  const X=v=>pl+(w-pl-pr)*v/xmax, Y=v=>pt+(h-pt-pb)*(ymax-Math.max(ymin,Math.min(ymax,v)))/(ymax-ymin);
  const s=sv(w,h);
  for(let g=0;g<=xmax;g+=10){{s.appendChild(E('line',{{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f3f2ee'}}));s.appendChild(E('text',{{x:X(g),y:h-30,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},g));}}
  s.appendChild(E('line',{{x1:pl,y1:Y(0),x2:w-pr,y2:Y(0),stroke:'#c9c7c1','stroke-width':1.5}}));
  s.appendChild(E('text',{{x:w-pr+4,y:Y(0)+3,'font-size':9,fill:'#8a929c'}},'cold'));
  for(let g=-180;g<=ymax;g+=60){{if(g===0)continue;s.appendChild(E('line',{{x1:pl,y1:Y(g),x2:w-pr,y2:Y(g),stroke:'#f7f6f2'}}));s.appendChild(E('text',{{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'}},(g>0?'+':'')+g+'s'));}}
  s.appendChild(E('text',{{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'}},'baseline task length (naive cold turns)'));
  s.appendChild(E('text',{{x:15,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 15 ${{(pt+h-pb)/2}})`}},'seconds saved vs cold (up = faster)'));
  s.appendChild(E('text',{{x:X(1),y:Y(ymax)+2,'font-size':9,'font-style':'italic',fill:'#0f8a5f'}},'saves time'));
  s.appendChild(E('text',{{x:X(1),y:Y(ymin)+6,'font-size':9,'font-style':'italic',fill:'#c13a2e'}},'loses time'));
  if(!sel.length)s.appendChild(E('text',{{x:(pl+w-pr)/2,y:(pt+h-pb)/2,'text-anchor':'middle','font-size':11,fill:'#8a929c'}},'select one or more legs'));
  sel.forEach(k=>{{const col=C[k], f=L.fits[k];
    L.tasks.forEach(t=>{{const v=t.sv[k];if(v==null)return;const off=v<ymin;
      const node=off?E('path',{{d:`M ${{X(t.bturns)}} ${{Y(ymin)+7}} L ${{X(t.bturns)-5}} ${{Y(ymin)-1}} L ${{X(t.bturns)+5}} ${{Y(ymin)-1}} Z`,fill:col,opacity:.85,stroke:'#fff','stroke-width':1}})
                        :E('circle',{{cx:X(t.bturns),cy:Y(v),r:4,fill:col,opacity:.72}});
      s.appendChild(tip(node,`${{k}} · ${{t.t}} (${{t.cls}}, ${{t.bturns}} base turns): ${{v>0?'+':''}}${{v}}s vs cold${{off?' (off-scale)':''}}`));}});
    s.appendChild(E('line',{{x1:X(1),y1:Y(f.intercept+f.slope*1),x2:X(xmax*.98),y2:Y(f.intercept+f.slope*xmax*.98),stroke:col,'stroke-width':2.4,'stroke-dasharray':'6 4'}}));}});
  let ly=pt+8;sel.forEach(k=>{{const cc=L.fits[k].corr;
    s.appendChild(E('circle',{{cx:w-pr+14,cy:ly,r:4.5,fill:C[k]}}));
    s.appendChild(E('text',{{x:w-pr+22,y:ly+3.5,'font-size':10,fill:'#5b6571'}},k));
    s.appendChild(E('text',{{x:w-pr+52,y:ly+3.5,'font-size':9,fill:cc>0?'#0f8a5f':'#c13a2e'}},`${{cc>0?'+':''}}${{cc}}`));ly+=16;}});
  const hh=document.getElementById('c_lengthscale');hh.innerHTML='';hh.appendChild(s);
}}

function slopeChart(){{
  const R=D.rankcompare, arms=R.arms;
  const tmin=R.turns_spread[0], tmax=R.turns_spread[1];
  const mmin=R.lat_spread[0], mmax=R.lat_spread[1];
  const w=1060,pt=52,pb=34,h=470,H=h-pt-pb, xL=452,xR=608;
  const yT=v=>pt+H*(v-tmin)/(tmax-tmin);   // fewest turns at top
  const yM=v=>pt+H*(v-mmin)/(mmax-mmin);   // fastest at top
  const s=sv(w,h);
  s.appendChild(E('text',{{x:xL,y:pt-22,'text-anchor':'middle','font-size':11,'font-weight':700,fill:'#1b1f24'}},'turns'));
  s.appendChild(E('text',{{x:xL,y:pt-10,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},'height \u221d turns (fewest on top)'));
  s.appendChild(E('text',{{x:xR,y:pt-22,'text-anchor':'middle','font-size':11,'font-weight':700,fill:'#1b1f24'}},'latency'));
  s.appendChild(E('text',{{x:xR,y:pt-10,'text-anchor':'middle','font-size':9,fill:'#8a929c'}},'height \u221d minutes (fastest on top)'));
  // axis lines + value scale anchors
  [[xL,yT,tmin,tmax,'t'],[xR,yM,mmin,mmax,'m']].forEach(([x,yfn,lo,hi,u])=>{{
    s.appendChild(E('line',{{x1:x,y1:pt,x2:x,y2:pt+H,stroke:'#ececE6','stroke-width':1}}));
    s.appendChild(E('line',{{x1:x,y1:pt,x2:x,y2:pt+H,stroke:'#e7e6e1','stroke-width':1}}));
    [lo,(lo+hi)/2,hi].forEach(v=>{{s.appendChild(E('line',{{x1:x-3,y1:yfn(v),x2:x+3,y2:yfn(v),stroke:'#c9c7c1'}}));}});
  }});
  // connecting lines colored by which side is relatively worse (value-normalized)
  arms.forEach(a=>{{const y1=yT(a.turns),y2=yM(a.min);
    const pT=(a.turns-tmin)/(tmax-tmin), pM=(a.min-mmin)/(mmax-mmin);
"""
