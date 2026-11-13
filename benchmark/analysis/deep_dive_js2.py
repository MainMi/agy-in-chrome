# Split out of build_deep_dive.py — pure refactor, behavior unchanged.


JS2 = """
<script>
function catTable(){
  const cats=Object.keys(D.cats);const agg=D.catagg;
  let h='<div class="scroll"><table><thead><tr><th>category</th><th>tasks</th>'+Object.keys(A).map(a=>`<th style="color:${A[a].color}">${A[a].short}</th>`).join('')+'</tr></thead><tbody>';
  for(const c of cats){
    h+=`<tr><td><b>${c}</b></td><td class="mono">${D.cats[c].map(t=>t.replace('dashdish-','dd').replace('zilloft-','z')).join(' ')}</td>`;
    for(const a in A){const g=agg[c][a];
      h+=`<td class="num">${g.passed}/${g.n} · ${g.mean_min.toFixed(1)}m</td>`}
    h+='</tr>';
  }
  document.getElementById('cat_table').innerHTML=h+'</tbody></table></div>';
  document.getElementById('cat_notes').innerHTML=
    '<b>Reading:</b> cart flows separate harnesses (OCIC arms sweep CinC arms task-for-task) and punish forks least in relative terms; '+
    'tour forms are the longest tasks, where analysis docs (3C) win time via the header-count recipe and forks pay the biggest absolute tax; '+
    'filtered counting is where nearly all accuracy variance lives, and it is judge-phrasing variance, not capability; '+
    'homepage reading is sub-minute everywhere, with dashdish-8 unwinnable by rubric in all 18 arms.';
}
function taskIndex(){
  let h='<thead><tr><th>task</th><th>category</th><th>difficulty</th><th>goal</th><th>pass rate</th><th>time range</th></tr></thead><tbody>';
  D.order.forEach((t,i)=>{
    const cat=Object.keys(D.cats).find(c=>D.cats[c].includes(t));
    const arms=Object.keys(A);
    const p=arms.filter(a=>A[a].pass_by_task[i]).length;
    const times=arms.map(a=>A[a].run_by_task[i]);
    h+=`<tr class="clickable" onclick="showTask('${t}')"><td class="mono">${t}</td><td>${cat}</td><td>${D.difficulty[t]}</td>`+
       `<td class="note">${D.goals[t].slice(0,90)}...</td><td class="num">${p}/${arms.length}</td>`+
       `<td class="num">${Math.min(...times).toFixed(1)}-${Math.max(...times).toFixed(1)}m</td></tr>`;
  });
  document.getElementById('taskindex').innerHTML=h+'</tbody>';
}
function showTask(t){
  const i=D.order.indexOf(t);
  let h=`<h3 style="margin:2px 0">${t} <span class="note">(${D.difficulty[t]} · ${Object.keys(D.cats).find(c=>D.cats[c].includes(t))})</span></h3>
  <p class="note" style="margin:2px 0 8px">${D.goals[t]}</p>
  <div class="scroll"><table><thead><tr><th>arm</th><th>verdict</th><th>min</th><th>turns</th><th>s/turn (median gap)</th><th>first action</th><th>failing answer</th></tr></thead><tbody>`;
  for(const a in A){
    const ar=A[a];const fail=(D.tasks[t][a]||{}).fail||'';
    h+=`<tr><td><span class="sw" style="display:inline-block;width:9px;height:9px;background:${ar.color};border-radius:2px;margin-right:6px"></span>${ar.label}</td>
      <td>${ar.pass_by_task[i]?'<span class="badge b-pass">PASS</span>':'<span class="badge b-fail">FAIL</span>'}</td>
      <td class="num">${ar.run_by_task[i].toFixed(1)}</td><td class="num">${ar.turns_by_task[i]}</td>
      <td class="num">${ar.gapmed_by_task[i]==null?'·':ar.gapmed_by_task[i].toFixed(2)}s</td>
      <td class="num">${ar.first_by_task[i]==null?'·':ar.first_by_task[i].toFixed(0)+'s'}</td>
      <td class="note">${fail}</td></tr>`;
  }
  document.getElementById('detailbody').innerHTML=h+'</tbody></table></div>';
  document.getElementById('detail').classList.add('open');
}
function chartTierBenefit(){
  const M=D.diff.methods;const tiers=['easy','medium','hard'];
  const w=1060,h=290,pl=64;const cw=(w-pl-30)/M.length;const bw=Math.min(26,(cw-26)/3);
  const vmin=-5,vmax=1;const Y=v=>{const c=Math.max(vmin,Math.min(vmax,v));return 34+(h-116)*(vmax-c)/(vmax-vmin)};
  const s=svgEl(w,h);
  s.appendChild(el('text',{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'time benefit vs cold by labeled tier, methods ordered by machinery (min/task; positive = faster than cold)'));
  for(let g=vmin;g<=vmax;g+=1){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-20,y2:Y(g),stroke:g===0?'#c9c7c1':'#f3f2ee','stroke-width':g===0?2:1}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},(g>0?'+':'')+g+'m'))}
  const shade={easy:.45,medium:.7,hard:1};
  M.forEach((m,mi)=>{
    const x0=pl+10+mi*cw;const col={raw:'#0d9488',analysis:'#10b981',fork:'#9d174d'}[m.mode];
    tiers.forEach((tr,ti)=>{
      const v=m.tier[tr].mean;const x=x0+ti*(bw+5);const y0=Y(0),y1=Y(v);
      s.appendChild(tip(el('rect',{x,y:Math.min(y0,y1),width:bw,height:Math.abs(y1-y0)||1,rx:2.5,fill:col,opacity:shade[tr]}),`${m.label} · ${tr}: ${v>0?'+':''}${v}m/task (${m.tier[tr].wins}/${m.tier[tr].n} tasks faster)`));
      s.appendChild(el('text',{x:x+bw/2,y:v>=0?y1-3:y1+10,'text-anchor':'middle','font-size':8.5,fill:'#5b6571'},(v>0?'+':'')+v.toFixed(1)));
    });
    s.appendChild(el('text',{x:x0+1.5*bw,y:h-58,'text-anchor':'middle','font-size':9.5,fill:'#5b6571'},m.label));
  });
  s.appendChild(el('text',{x:pl,y:h-36,'font-size':10,fill:'#8a929c'},'bar shade within each method: light=easy, mid=medium, dark=hard · teal/green = mounted, crimson = fork'));
  s.appendChild(el('text',{x:pl,y:h-22,'font-size':10,fill:'#8a929c'},'3D hard = one task (zilloft-10 hand-pagination disaster); every other mounted cell is within noise of zero'));
  const host=document.getElementById('c_tierben');host.innerHTML='';host.appendChild(s);
}
function chartDiffScatter(){
  const pts=D.diff.scatter;const w=1060,h=330,pl=60,pb=44,pr=30,pt=22;
  const xmax=Math.max(...pts.map(p=>p.x))*1.08;
  const ymin=Math.min(...pts.map(p=>p.y)),ymax=Math.max(...pts.map(p=>p.y));
  const X=v=>pl+(w-pl-pr)*v/xmax,Y=v=>pt+(h-pt-pb)*(ymax-v)/(ymax-ymin);
  const s=svgEl(w,h);
  s.appendChild(el('text',{x:pl,y:12,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'per-task benefit vs empirical hardness (post-fix; cold minutes on the task)'));
  for(let g=0;g<=xmax;g+=1)if(g%1===0&&g<=xmax)s.appendChild(el('text',{x:X(g),y:h-26,'text-anchor':'middle','font-size':9,fill:'#8a929c'},g+'m'));
  for(let g=Math.ceil(ymin/2)*2;g<=ymax;g+=2){
    s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-pr,y2:Y(g),stroke:'#f3f2ee'}));
    s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},(g>0?'+':'')+g+'m'));
  }
  s.appendChild(el('line',{x1:pl,y1:Y(0),x2:w-pr,y2:Y(0),stroke:'#c9c7c1','stroke-width':2}));
  s.appendChild(el('text',{x:pl-6,y:Y(0)+3,'text-anchor':'end','font-size':9,'font-weight':700,fill:'#5b6571'},'0m'));
  s.appendChild(el('text',{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'},'cold minutes on the task'));
  s.appendChild(el('text',{x:16,y:(pt+h-pb)/2,'font-size':10.5,fill:'#5b6571','text-anchor':'middle',transform:`rotate(-90 16 ${(pt+h-pb)/2})`},'benefit vs cold (min/task): + = faster than cold'));
  const groups={raw:'#0d9488',analysis:'#10b981',fork:'#9d174d'};
  for(const g in groups){
    const gp=pts.filter(p=>p.g===g);
    gp.forEach(p=>s.appendChild(tip(el('circle',{cx:X(p.x),cy:Y(p.y),r:3.4,fill:groups[g],opacity:.6}),`${p.t} (${p.tier}) · ${p.arm}: cold ${p.x}m, benefit ${p.y>0?'+':''}${p.y}m`)));
    const xs=gp.map(p=>p.x),ys=gp.map(p=>p.y);
    const mx=xs.reduce((a,b)=>a+b)/xs.length,my=ys.reduce((a,b)=>a+b)/ys.length;
    const b=xs.map((x,i)=>(x-mx)*(ys[i]-my)).reduce((a,c)=>a+c)/xs.map(x=>(x-mx)**2).reduce((a,c)=>a+c);
    const a0=my-b*mx;
    s.appendChild(el('line',{x1:X(0.1),y1:Y(a0+b*0.1),x2:X(xmax*0.96),y2:Y(a0+b*xmax*0.96),stroke:groups[g],'stroke-width':2.2,'stroke-dasharray':'6 4'}));
  }
  let ly=30;
  for(const g in groups){s.appendChild(el('circle',{cx:w-190,cy:ly,r:4,fill:groups[g]}));s.appendChild(el('text',{x:w-180,y:ly+4,'font-size':10.5,fill:'#5b6571'},g+' mounts'.replace(g==='fork'?' mounts':'',g==='fork'?'s':'')));ly+=16}
  const host=document.getElementById('c_diffscatter');host.innerHTML='';host.appendChild(s);
}
function chartFlips(){
  const M=D.diff.methods;const w=660,h=230,pl=64;const tiers=['easy','medium','hard'];
  const agg=tiers.map(tr=>M.reduce((acc,m)=>acc+m.tier[tr].regress,0));
  const vmax=6;const Y=v=>h-56-(h-92)*v/vmax;const bw=64;const s=svgEl(w,h);
  s.appendChild(el('text',{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'accuracy regressions vs cold by tier (all six methods pooled; rescues were zero)'));
  for(let g=0;g<=vmax;g+=2){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-20,y2:Y(g),stroke:'#f3f2ee'}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},g))}
  tiers.forEach((tr,i)=>{
    const x=pl+40+i*((w-pl-80)/3);const v=agg[i];
    s.appendChild(tip(el('rect',{x,y:Y(v),width:bw,height:Y(0)-Y(v)||1,rx:3,fill:'#c13a2e',opacity:.8}),`${tr}: ${v} regressions across 6 methods`));
    s.appendChild(el('text',{x:x+bw/2,y:Y(v)-4,'text-anchor':'middle','font-size':10.5,fill:'#c13a2e','font-weight':700},v));
    s.appendChild(el('text',{x:x+bw/2,y:h-38,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'},tr));
  });
  const host=document.getElementById('c_flips');host.innerHTML='';host.appendChild(s);
}
function rhoTable(){
  let h='<div class="scroll"><table><thead><tr><th>method</th><th>class</th><th>rho(benefit, cold-time)</th><th>drop zilloft-9</th><th>hard-tier mean</th></tr></thead><tbody>';
  D.diff.methods.forEach(r=>{h+=`<tr><td class="mono">${r.label}</td><td>${r.mode}</td><td class="num">${r.rho>0?'+':''}${r.rho.toFixed(2)}</td><td class="num">${r.rho_noz9>0?'+':''}${r.rho_noz9.toFixed(2)}</td><td class="num">${r.tier.hard.mean>0?'+':''}${r.tier.hard.mean.toFixed(2)}m</td></tr>`});
  document.getElementById('rho_table').innerHTML=h+'</tbody></table></div>';
}
function chartWaterfall(){
  const W=D.waterfall;const arms=Object.keys(W);
  const w=1060,h=300,pw=(w-40)/2;
  const s=svgEl(w,h);
  arms.forEach((a,ai)=>{
    const d=W[a];const x0=20+ai*pw;const lbl=A[a].label;
    const hypo=d.cold+d.extra;             // fork's work at cold pace
    const vmax=Math.max(d.fork,d.cold)*1.18;
    const Y=v=>h-56-(h-96)*v/vmax;const bw=Math.min(72,(pw-90)/4);
    s.appendChild(el('text',{x:x0+pw/2,y:16,'text-anchor':'middle','font-size':11.5,'font-weight':600,fill:'#1b1f24'},lbl+': cold '+d.cold+'m \u2192 fork '+d.fork+'m'));
    const steps=[
      {x:0,base:0,top:d.cold,fill:'#0d9488',lab:d.cold+'m',cap:'cold actual',tip:'cold baseline, 12-task total'},
      {x:1,base:Math.min(d.cold,hypo),top:Math.max(d.cold,hypo),fill:d.extra<0?'#0f8a5f':'#c13a2e',lab:(d.extra>0?'+':'')+d.extra+'m',cap:d.extra<0?'work saved':'extra work',tip:d.extra<0?'turns the fork did not need, priced at cold pace':'extra turns the fork took, priced at cold pace'},
      {x:2,base:hypo,top:hypo+d.tax,fill:'#c13a2e',lab:'+'+d.tax+'m',cap:'reading tax',tip:'the per-turn context toll summed over all fork turns'},
      {x:3,base:0,top:d.fork,fill:'#9d174d',lab:d.fork+'m',cap:'fork actual',tip:'fork arm, 12-task total'}
    ];
    steps.forEach((st,i)=>{
      const x=x0+30+i*(bw+18);
      s.appendChild(tip(el('rect',{x,y:Y(st.top),width:bw,height:Math.max(2,Y(st.base)-Y(st.top)),rx:3,fill:st.fill,opacity:i===1||i===2?0.85:1}),st.cap+': '+st.tip));
      s.appendChild(el('text',{x:x+bw/2,y:Y(st.top)-5,'text-anchor':'middle','font-size':10.5,'font-weight':700,fill:st.fill},st.lab));
      s.appendChild(el('text',{x:x+bw/2,y:h-38,'text-anchor':'middle','font-size':9.5,fill:'#5b6571'},st.cap));
      if(i>0&&i<3){const px=x0+30+(i-1)*(bw+18)+bw;
        s.appendChild(el('line',{x1:px,y1:Y(st.base===hypo&&i===2?hypo:(i===1?d.cold:hypo)),x2:x,y2:Y(i===1?d.cold:hypo),stroke:'#c9c7c1','stroke-dasharray':'3 3'}));}
    });
    s.appendChild(el('line',{x1:x0+30+2*(bw+18)+bw,y1:Y(d.fork),x2:x0+30+3*(bw+18),y2:Y(d.fork),stroke:'#c9c7c1','stroke-dasharray':'3 3'}));
  });
  s.appendChild(el('text',{x:20,y:h-14,'font-size':10,fill:'#8a929c'},'fork time = cold time - work saved + reading tax · green = knowledge helping · red = delivery cost · RUN TIME ONLY: the one-time study/prep (37m experiential, 44m expert) is excluded here and tracked as prep in the main report'));
  const host=document.getElementById('c_waterfall');host.innerHTML='';host.appendChild(s);
}
function chartTurnsCmp(){
  const a4='exp4a-experiential-fork',ac='exp1a-fixed-brave';
  const w=1060,h=260,pl=64;const gw=(w-pl-24)/T.length;const bw=Math.min(16,(gw-14)/2);
  const vmax=Math.max(...A[ac].turns_by_task,...A[a4].turns_by_task)*1.15;
  const Y=v=>h-52-(h-84)*v/vmax;const s=svgEl(w,h);
  s.appendChild(el('text',{x:pl,y:14,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'work per task: model turns, cold vs experiential fork'));
  for(let g=0;g<=vmax;g+=40){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-20,y2:Y(g),stroke:'#f3f2ee'}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},g))}
  T.forEach((t,i)=>{
    const x0=pl+6+i*gw;
    const vc=A[ac].turns_by_task[i],vf=A[a4].turns_by_task[i];
    s.appendChild(tip(el('rect',{x:x0,y:Y(vc),width:bw,height:Y(0)-Y(vc),rx:2,fill:'#0d9488'}),t+' · cold: '+vc+' turns'));
    s.appendChild(tip(el('rect',{x:x0+bw+3,y:Y(vf),width:bw,height:Y(0)-Y(vf),rx:2,fill:'#9d174d'}),t+' · fork: '+vf+' turns'));
    const d=vf-vc;
    s.appendChild(el('text',{x:x0+bw+1,y:Y(Math.max(vc,vf))-5,'text-anchor':'middle','font-size':8.5,'font-weight':700,fill:d<0?'#0f8a5f':'#c13a2e'},(d>0?'+':'')+d));
    s.appendChild(el('text',{x:x0+bw+1,y:h-36,'text-anchor':'middle','font-size':8.5,fill:'#8a929c',transform:'rotate(28 '+(x0+bw+1)+' '+(h-36)+')'},t.replace('dashdish-','dd').replace('zilloft-','z')));
  });
  s.appendChild(el('text',{x:pl,y:h-12,'font-size':10,fill:'#8a929c'},'teal = cold turns · crimson = fork turns · signed number = turns saved (green) or added (red) by the fork'));
  const host=document.getElementById('c_turnscmp');host.innerHTML='';host.appendChild(s);
}
function chartCtxCurve(){
  const P=D.ctx;const w=1060,h=330,pl=60,pb=44,pr=30,pt=22;
  const xmax=Math.max(...P.map(p=>p.ktok))*1.06;
  const ymax=Math.max(...P.map(p=>p.spt))*1.1;
  const X=v=>pl+(w-pl-pr)*v/xmax,Y=v=>pt+(h-pt-pb)*(1-v/ymax);
  const s=svgEl(w,h);
  s.appendChild(el('text',{x:pl,y:12,'font-size':11.5,'font-weight':600,fill:'#1b1f24'},'seconds per turn vs context carried per turn: one dot per task rollout'));
  for(let g=0;g<=xmax;g+=100){s.appendChild(el('line',{x1:X(g),y1:pt,x2:X(g),y2:h-pb,stroke:'#f3f2ee'}));s.appendChild(el('text',{x:X(g),y:h-28,'text-anchor':'middle','font-size':9,fill:'#8a929c'},g+'k'))}
  for(let g=0;g<=ymax;g+=2){s.appendChild(el('line',{x1:pl,y1:Y(g),x2:w-pr,y2:Y(g),stroke:'#f3f2ee'}));s.appendChild(el('text',{x:pl-6,y:Y(g)+3,'text-anchor':'end','font-size':9,fill:'#8a929c'},g+'s'))}
  s.appendChild(el('text',{x:(pl+w-pr)/2,y:h-8,'text-anchor':'middle','font-size':10.5,fill:'#5b6571'},'k tokens carried per turn (cache reads + writes + fresh input, per rollout)'));
  // fit
  const xs=P.map(p=>p.ktok),ys=P.map(p=>p.spt);
  const mx=xs.reduce((a,b)=>a+b)/xs.length,my=ys.reduce((a,b)=>a+b)/ys.length;
  const b=xs.map((x,i)=>(x-mx)*(ys[i]-my)).reduce((a,c)=>a+c)/xs.map(x=>(x-mx)**2).reduce((a,c)=>a+c);
  const a0=my-b*mx;
  s.appendChild(el('line',{x1:X(20),y1:Y(a0+b*20),x2:X(xmax*.97),y2:Y(a0+b*xmax*.97),stroke:'#5b6571','stroke-width':2,'stroke-dasharray':'7 5'}));
  s.appendChild(el('text',{x:X(xmax*.55),y:Y(a0+b*xmax*.55)-10,'font-size':10.5,fill:'#5b6571'},'fit: '+a0.toFixed(1)+'s + '+(b*100).toFixed(1)+'s per 100k tokens (r=0.88)'));
  P.forEach(p=>{
    const c=(A[p.arm]||{}).color||'#8a929c';
    s.appendChild(tip(el('circle',{cx:X(p.ktok),cy:Y(p.spt),r:3.6,fill:c,opacity:.7}),(A[p.arm]||{label:p.arm}).label+' · '+p.task+': '+p.ktok+'k/turn, '+p.spt+'s/turn ('+p.turns+' turns)'));
  });
  let ly=26;
  ['exp1a-fixed-brave','exp3c-analysis','exp2b-fixed-brave','exp4b-expert-fork','exp4a-experiential-fork'].forEach(a=>{
    s.appendChild(el('circle',{cx:w-238,cy:ly,r:4,fill:A[a].color}));
    s.appendChild(el('text',{x:w-228,y:ly+4,'font-size':10,fill:'#5b6571'},A[a].label));ly+=15;
  });
  const host=document.getElementById('c_ctxcurve');host.innerHTML='';host.appendChild(s);
}
function renderAll(){chartCtxCurve();chartTurnsOut();chartKtok();chartScatter();chartSeries();chartBox();chartTasks();chartCats();catTable();chartTierBenefit();chartDiffScatter();chartFlips();rhoTable();chartWaterfall();chartTurnsCmp();}
renderToggles();renderAll();taskIndex();
</script>
</div></body></html>
"""
