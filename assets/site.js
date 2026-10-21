/* Shared chrome for every lab page: top bar, language, 1280x720 fit, Esc to home. */
(function(){
  const PAGES=[
    ['home','index.html','처음','Home'],
    ['map','map.html','연구 아키텍처','Architecture'],
    ['maia','maia.html','MAIA 진단','MAIA check'],
    ['record','record.html','실적','Track record'],
    ['open','open.html','개발 현황','Development'],
    ['data','data.html','공개 자료','Data & code'],
    ['work','#','함께하기','Work with us',true],
    ['about','#','소개','About',true]
  ];
  const here=document.body.dataset.page||'home';
  let lang=(()=>{try{const s=localStorage.getItem('lab-lang');if(s)return s}catch(e){}return (navigator.language||'en').toLowerCase().startsWith('ko')?'ko':'en'})();
  window.LAB={lang:()=>lang,T:(ko,en)=>lang==='ko'?ko:en,onLang:[]};

  const top=document.createElement('div');top.className='top';
  top.innerHTML='<a class="brand" href="index.html"><svg viewBox="0 0 24 24" fill="none" stroke="#b9a37a" stroke-width="1.4"><path d="M3 8 12 3l9 5-9 5z"/><path d="M3 12.5 12 17.5l9-5"/><path d="M3 17l9 5 9-5"/></svg><span data-ko="안창한 연구실" data-en="Ahn Research Group"></span></a>'
    +'<nav class="menu">'+PAGES.map(p=>'<a href="'+p[1]+'" class="'+(p[0]===here?'on':'')+(p[4]?' soon':'')+'" data-ko="'+p[2]+'" data-en="'+p[3]+'"></a>').join('')+'</nav>'
    +'<div class="lang"><button data-l="ko">KO</button><button data-l="en">EN</button></div>';
  document.getElementById('page').prepend(top);

  function apply(){
    document.documentElement.lang=lang;
    document.querySelectorAll('[data-ko]').forEach(e=>{const v=e.dataset[lang];if(e instanceof SVGElement)e.textContent=v;else e.innerHTML=v});
    document.querySelectorAll('.lang button').forEach(b=>b.classList.toggle('on',b.dataset.l===lang));
    window.LAB.onLang.forEach(f=>f());
  }
  window.LAB.apply=apply;
  document.addEventListener('click',e=>{const b=e.target.closest('.lang button');if(!b)return;lang=b.dataset.l;try{localStorage.setItem('lab-lang',lang)}catch(_){}apply()});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&here!=='home'&&!e.target.matches('input'))location.href='index.html'});
  function fit(){const s=document.getElementById('stage');const k=Math.min(s.clientWidth/1280,s.clientHeight/720);document.getElementById('page').style.transform='scale('+k+')'}
  window.addEventListener('resize',fit);fit();
  window.LAB.ago=function(iso){const s=Math.max(0,(Date.now()-new Date(iso).getTime())/1000);const T=window.LAB.T;if(s<60)return T(Math.round(s)+'초 전',Math.round(s)+'s ago');if(s<3600)return T(Math.round(s/60)+'분 전',Math.round(s/60)+'m ago');if(s<86400)return T(Math.round(s/3600)+'시간 전',Math.round(s/3600)+'h ago');return T(Math.round(s/86400)+'일 전',Math.round(s/86400)+'d ago')};
  window.LAB.big=function(n){if(lang==='ko'){if(n>=1e8)return (n/1e8).toFixed(1)+'억';if(n>=1e4)return Math.round(n/1e4).toLocaleString()+'만';return Math.round(n).toLocaleString()}if(n>=1e9)return (n/1e9).toFixed(2)+'B';if(n>=1e6)return (n/1e6).toFixed(1)+'M';if(n>=1e3)return (n/1e3).toFixed(1)+'K';return Math.round(n).toLocaleString()};
  window.LAB.count=function(node,to,ms,fmt){const t0=performance.now();(function f(n){const k=Math.min(1,(n-t0)/ms);const e=1-Math.pow(1-k,3);node.textContent=fmt(to*e);if(k<1)requestAnimationFrame(f)})(t0)};
  document.addEventListener('DOMContentLoaded',apply);
})();
