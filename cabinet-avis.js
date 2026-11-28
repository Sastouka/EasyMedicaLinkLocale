'use strict';
(() => {
  const form = document.querySelector('#cab-review-form');
  if (!form) return;
  form.querySelector('button[type=submit]').disabled = false;
  const status = document.querySelector('#cab-review-status');
  const label = document.querySelector('#cab-review-rating-label');
  form.addEventListener('change', e => {
    if (e.target.name === 'rating') label.textContent = e.target.value + ' / 5';
  });
  form.addEventListener('submit', e => {
    e.preventDefault();
    if (!form.reportValidity()) return;
    const data = new FormData(form), rating=Number(data.get('rating')), message=String(data.get('review') || '').trim();
    if (!Number.isInteger(rating) || rating<1 || rating>5 || message.length<12) {
      status.textContent='Choisissez une note et écrivez un commentaire d’au moins 12 caractères.';
      return;
    }
    const body = 'Note : '+rating+' / 5\n\n'+message+'\n\nAutorisation de publication du commentaire : '+(data.has('permission')?'oui, sans nom ni adresse e-mail':'non');
    const link=document.querySelector('#cab-review-mail');
    link.href = 'mailto:sastoukadigital@gmail.com?subject='+encodeURIComponent('Avis sur EasyMedicaLink')+'&body='+encodeURIComponent(body);
    link.hidden=false;
    status.textContent='Votre e-mail est prêt. Cliquez ci-dessous pour l’ouvrir, puis envoyez-le depuis votre messagerie.';
    link.focus();
  });
  form.addEventListener('input', () => {
    const link=document.querySelector('#cab-review-mail');
    link.hidden=true;link.removeAttribute('href');status.textContent='';
  });
})();
