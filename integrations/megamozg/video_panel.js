// Insert inside the existing workboard closure; use the same identity and routing.
async function videoPanel(t,root,generation){
 root.dataset.videoTaskId=t.id;root.dataset.videoTaskRevision=String(t.revision);
 if(!['owner','employee'].includes(me.role))return;
 const panel=node('section','');panel.dataset.videoObservation='true';root.append(panel);
 let d;try{d=await call('/api/workboard/tasks/'+encodeURIComponent(t.id)+'/video')}
 catch(e){if(generation===detailGeneration&&panel.isConnected)panel.append(node('p','Состояние видео недоступно'));return}
 if(generation!==detailGeneration||!panel.isConnected)return;
 if(d.state==='not_bound'){panel.remove();return}
 panel.append(node('h4','Видеопроизводство'));
 const labels={observed:'Состояние заказа прочитано',stale:'Сведения устарели',binding_stale:'Поручение изменилось. Нужна повторная привязка заказа',binding_mismatch:'Привязка заказа не подтверждена',unavailable:'Сведения о заказе недоступны'};
 panel.append(node('p',labels[d.state]||labels.unavailable));
 if(d.observed_at)panel.append(node('small','Проверено: '+new Date(d.observed_at*1000).toLocaleString()));
 if(['observed','stale'].includes(d.state)){
  const states={queued:'в очереди',running:'выполняется',recovering:'проверка после сбоя',cancelling:'отмена',cancelled:'отменено',failed:'ошибка',blocked:'требуется действие',awaiting_review:'на проверке',not_requested:'не запрошено',ready:'технически готово',unavailable:'неизвестно'};
  for(const [key,title] of [['preparation','Материалы'],['analysis','Разбор'],['preview','Черновик']])panel.append(node('p',title+': '+(states[d[key]]||'неизвестно')));
  if(d.plan_revision)panel.append(node('p','План сцен: версия '+d.plan_revision));
  const review={pending:'План ожидает проверки',recorded_acceptance_unverified:'Сохранено локальное решение по плану. Актуальность материалов и личность проверяющего здесь не проверены',changes_requested:'Для плана запрошены изменения',not_observed:'Решение по плану не получено'};
  panel.append(node('p',review[d.plan_review]||review.not_observed));
 }
 panel.append(node('p','Приёмка готового фильма этим состоянием не подтверждается.'));
 if(d.state==='observed'){
  let media;try{media=await call('/api/workboard/tasks/'+encodeURIComponent(t.id)+'/video/media')}
  catch(e){return}
  if(generation!==detailGeneration||!panel.isConnected)return;
  for(const item of media.versions||[]){
   const base='/api/workboard/tasks/'+encodeURIComponent(t.id)+'/video/media/'+encodeURIComponent(item.revision);
   panel.append(node('p','Версия '+item.revision.slice(0,12)));
   if(item.kinds.includes('video')){const video=node('video','');video.controls=true;video.preload='metadata';video.style.maxWidth='100%';video.src=base+'/video';panel.append(video)}
   if(item.kinds.includes('project')){const link=node('a','Скачать монтажный комплект');link.href=base+'/project';panel.append(link)}
  }
 }
}
