"use strict";
(() => {
const E = (selector, root=document) => root.querySelector(selector);
const A = (selector, root=document) => Array.from(root.querySelectorAll(selector));
const menu = E('[data-menu-toggle]');
const nav = E('#primary-navigation');
if(menu && nav){
  menu.addEventListener('click', () => {const open = nav.classList.toggle('open');menu.setAttribute('aria-expanded',String(open)); menu.setAttribute('aria-label',open?'Fermer le menu':'Ouvrir le menu');});
  A('a',nav).forEach(a=>a.addEventListener('click',()=>{nav.classList.remove('open');menu.setAttribute('aria-expanded','false');}));
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){nav.classList.remove('open');menu.setAttribute('aria-expanded','false');}});
}
// Marketing cookies: zero pixel requests until explicit opt-in. No medical data is sent in events.
const pixelId='1787057305962028';
const consentKey='easymed_marketing_choice_v2';
let marketingConsent = false;
let consentValue = null;
try {consentValue = localStorage.getItem(consentKey);}catch(_){/* storage may be disabled */}
function loadPixel(){
  if(window.fbq)return;
  (function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=true;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=true;t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)})(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');
  window.fbq('init',pixelId);
  window.fbq('track','PageView');
  const page=document.body.dataset.page;
  if(page==='guide')window.fbq('track','ViewContent',{content_name:'Guide EasyMedicaLink',content_category:'Support'});
}
function setConsent(value){
  marketingConsent=value==='accepted';
  try{localStorage.setItem(consentKey,value);}catch(_){/* storage blocked */}
  const banner=E('#cookie-consent');
  if(banner)banner.hidden=true;
  document.body.classList.remove('cookie-prompt-open');
  if(marketingConsent){
    if(window.fbq){window.fbq('consent','grant');}
    else loadPixel();
  }else if(window.fbq){window.fbq('consent','revoke');}
}
if(consentValue==='accepted'){marketingConsent=true;loadPixel();}
const consent=E('#cookie-consent');if(consent && consentValue!=='accepted' && consentValue!=='declined'){
  consent.hidden=false;
  document.body.classList.add('cookie-prompt-open');
}
A('[data-cookie-accept]').forEach(b=>b.addEventListener('click',()=>setConsent('accepted')));
A('[data-cookie-decline]').forEach(b=>b.addEventListener('click',()=>setConsent('declined')));
A('[data-cookie-settings]').forEach(b=>b.addEventListener('click',(e)=>{e.preventDefault();if(consent){consent.hidden=false;document.body.classList.add('cookie-prompt-open');}}));
function customEvent(eventName,properties){if(marketingConsent && typeof window.fbq==='function')window.fbq('trackCustom',eventName,properties);}
A('[data-download]').forEach(a=>a.addEventListener('click',()=>customEvent('DownloadClick',{platform:a.dataset.download,version:'4.0.5'})));
A('[data-whatsapp]').forEach(a=>a.addEventListener('click',()=>customEvent('WhatsAppClick',{location:a.dataset.whatsapp || 'site'})));
A('[data-guide]').forEach(a=>a.addEventListener('click',()=>customEvent('GuideClick',{location:a.dataset.guide || 'site'})));
A('[data-gallery-tab]').forEach(tab=>tab.addEventListener('click',()=>{
 const category=tab.dataset.galleryTab;
 A('[data-gallery-tab]').forEach(t=>t.setAttribute('aria-pressed',String(t===tab)));
 A('[data-gallery-card]').forEach(card=>{card.hidden=category!=='all' && card.dataset.galleryCard!==category;});
}));
const lightbox=E('#gallery-lightbox');
const lbImage=E('#lb-image');const lbTitle=E('#lb-title');let trigger=null;
if(lightbox){
 A('[data-lightbox-src]').forEach(btn=>btn.addEventListener('click',()=>{
  trigger=btn;lbImage.src=btn.dataset.lightboxSrc;lbImage.alt=btn.dataset.lightboxTitle||'Capture EasyMedicaLink';lbTitle.textContent=btn.dataset.lightboxTitle||'Aperçu du logiciel';
  if(typeof lightbox.showModal==='function')lightbox.showModal();
 }));
 A('[data-lb-close]').forEach(b=>b.addEventListener('click',()=>lightbox.close()));
 lightbox.addEventListener('click',e=>{if(e.target===lightbox)lightbox.close()});
 lightbox.addEventListener('close',()=>{lbImage.removeAttribute('src');if(trigger)trigger.focus();});
}
const videoButton=E('[data-video-play]');
if(videoButton){videoButton.addEventListener('click',()=>{
  const frame=document.createElement('iframe');
  frame.src='https://www.youtube-nocookie.com/embed/aaIg6gDj9b0?autoplay=1&rel=0';
  frame.title='Démonstration EasyMedicaLink';frame.className='video-player';frame.allow='accelerometer;autoplay;clipboard-write;encrypted-media;gyroscope;picture-in-picture;web-share';frame.allowFullscreen=true;frame.referrerPolicy='strict-origin-when-cross-origin';
  videoButton.replaceWith(frame);customEvent('DemoVideoStart',{video:'EasyMedicaLink'});
});}
})();
