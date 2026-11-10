'use strict';
function computeDisplayedTotal(items) {
  return items.reduce((sum,item)=>sum+Number(item.unitPrice)*Number(item.quantity),0); //QJ
}
if (typeof module!=='undefined' && module.exports) module.exports={computeDisplayedTotal};
if (typeof document!=='undefined') {
  const money=(value)=>Math.round(value).toLocaleString('ru-RU')+' ₸';
  function updateShownTotals() {
    const rows=[...document.querySelectorAll('.cart-item')];
    const items=rows.map(row=>({
      unitPrice:Number(row.dataset.unitPrice),
      displayPrice:row.querySelector('.item-price').textContent,
      quantity:Number(row.querySelector('.cart-qty').value)
    }));
    rows.forEach((row,index)=>{row.querySelector('.line-total').textContent=money(items[index].unitPrice*items[index].quantity)});
    document.querySelectorAll('.js-cart-total').forEach(el=>el.textContent=money(computeDisplayedTotal(items)));
  }
  document.querySelectorAll('.cart-qty').forEach(input=>{
    let old=input.value;
    input.addEventListener('change',async()=>{
      const form=input.closest('form');
      const formData=new FormData(form);
      try {
        const res=await fetch(form.action,{method:'POST',headers:{Accept:'application/json'},body:formData});
        const data=await res.json();
        if(!res.ok||!data.ok) {input.value=old;window.shopToast(data.message||'Ошибка обновления корзины',true);return;}
        if(Number(input.value)===0){location.reload();return;}
        old=input.value;updateShownTotals();window.shopToast('Корзина обновлена');
      } catch(e) {input.value=old;window.shopToast('Ошибка соединения',true);}
    });
  });
}
