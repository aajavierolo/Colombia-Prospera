/** @OnlyCurrentDoc */
const ALTIUM24_ESTADO='ALTIUM24_DATOS_15X20';
function claveAltium24_(x){return String(x==null?'':x).trim().normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase();}
function posicionesAltium24_(){return Array.from({length:15},(_,i)=>({r:1+23*Math.floor(i/5),c:1+5*(i%5)}));}
function onEdit(e){
 if(!e||!e.range)return;
 const sh=e.range.getSheet(),name=sh.getName();
 if(!['Datos','Mapeo','Transaccional','Gastos','Ingresos'].includes(name))return;
 if(name==='Ingresos'){
  if(e.range.getColumn()<=2&&e.range.getLastColumn()>=2&&e.range.getLastRow()>=2){
   const r=Math.max(2,e.range.getRow()),n=e.range.getLastRow()-r+1;
   sh.getRange(r,1,n,1).setFormulas(Array.from({length:n},(_,i)=>['=IF(B'+(r+i)+'="";"";UPPER(TEXT(B'+(r+i)+';"mmmm")))']));
  }
  return;
 }
 const lock=LockService.getDocumentLock();if(!lock.tryLock(20000))return;
 try{
  moverControlAJ24_(e.source);
  separarIngresos24_(e.source);
  trasladarFondosAhorros24_(e.source);
  trasladarTransporte24_(e.source);
  aclararFamilia24_(e.source);
  ordenarVehiculos24_(e.source);
  agregarPapelesAccesorios24_(e.source);
  crearGastosPersonales24_(e.source);
  compactarDatos24_(e.source);
  reordenarColumnasDatos24_(e.source);
  configurarControlAltium24_(e.source);
  separarCategoriasAltium24_(e.source);
  configurarPrioridadesAltium24_(e.source);
  if(name==='Datos')proponerPrioridadesIniciales24_(e.source);
  if(name==='Transaccional'||name==='Gastos'){
   if(e.range.getColumn()<=13&&e.range.getLastColumn()>=13&&e.range.getLastRow()>=2){
    const r=Math.max(2,e.range.getRow()),n=e.range.getLastRow()-r+1;
    sh.getRange(r,12,n,1).setFormulas(Array.from({length:n},(_,i)=>['=IF(M'+(r+i)+'="";"";UPPER(TEXT(M'+(r+i)+';"mmmm")))']));
   }
   if(e.range.getColumn()===3&&e.range.getRow()>3&&e.range.getNumRows()===1&&e.range.getNumColumns()===1){const f=sh.getRange(e.range.getRow(),2);if(e.range.getValue()!=='')f.setValue(new Date());else f.clearContent();}
   if(e.range.getColumn()<=6&&e.range.getLastColumn()>=5)listasAltium24_(e.source,e.range.getRow(),e.range.getNumRows());return;
  }
  if(!PropertiesService.getDocumentProperties().getProperty(ALTIUM24_ESTADO))ampliarDatos24_(e.source);
  else sincronizarAltium24_(e.source,e.range);
 }finally{lock.releaseLock();}
}
function compactarDatos24_(ss){
 const props=PropertiesService.getDocumentProperties();if(props.getProperty('ALTIUM24_DATOS_COMPACTOS'))return;
 const d=ss.getSheetByName('Datos'),jobs=posicionesAltium24_().map(p=>{
  const range=d.getRange(p.r+1,p.c,20,4),values=range.getValues(),notes=range.getNotes(),formulas=range.getFormulas();
  const indexes=values.map((row,i)=>i).filter(i=>String(values[i][0]||'').trim()).concat(values.map((row,i)=>i).filter(i=>!String(values[i][0]||'').trim()));
  if(indexes.every((v,i)=>v===i))return null;
  if(formulas.some(row=>row.some(Boolean)))throw new Error('Revisar formulas antes de compactar '+range.getA1Notation());
  return {range,values:indexes.map(i=>values[i]),notes:indexes.map(i=>notes[i])};
 }).filter(Boolean);
 jobs.forEach(j=>j.range.setValues(j.values).setNotes(j.notes));
 mapeoAltium24_(ss);sincronizarAltium24_(ss);props.setProperty('ALTIUM24_DATOS_COMPACTOS','1');
}
function crearGastosPersonales24_(ss){
 const props=PropertiesService.getDocumentProperties();if(props.getProperty('ALTIUM24_GASTOS_PERSONALES'))return;
 const d=ss.getSheetByName('Datos'),t=hojaGastosAltium25_(ss),h=ss.getSheetByName('Historico_presupuesto'),state=estadoAltium24_(ss),pos=posicionesAltium24_();
 if(state.slots.some(s=>claveAltium24_(s.cat)==='GASTOS PERSONALES'))throw new Error('Ya existe GASTOS PERSONALES; revisar antes de trasladar.');
 const dst=state.slots.findIndex((s,i)=>!s.cat&&!s.items.length&&!d.getRange(pos[i].r+1,pos[i].c,20,4).getValues().some(row=>row.some(v=>v!=='')));
 const src=state.slots.findIndex(s=>claveAltium24_(s.cat)==='GUSTOS');if(dst<0||src<0)throw new Error('Falta bloque libre u origen GUSTOS.');
 const p=pos[dst],q=pos[src],dv=d.getRange(q.r+1,q.c,20,4).getValues(),hv=h.getRange(2,1,h.getLastRow()-1,12).getValues(),free=[];
 hv.forEach((r,i)=>{if(Number(r[10])===dst+1&&!r[1]&&!r.slice(3,10).some(v=>v!==''&&v!==null))free.push(i+2);});if(free.length<3)throw new Error('Faltan reservas historicas.');
 const jobs=[['Vestuario/Calzado','Vestuario y calzado'],['Peluquería/Maquillaje','Cuidado personal']].map(([old,name])=>{
  const rows=dv.map((r,i)=>({r,i})).filter(x=>claveAltium24_(x.r[0])===claveAltium24_(old)),hist=hv.map((r,i)=>({r,i})).filter(x=>claveAltium24_(x.r[0])==='GUSTOS'&&claveAltium24_(x.r[1])===claveAltium24_(old));
  if(rows.length!==1||hist.length!==1)throw new Error('Origen ambiguo: '+old);return {old,name,data:rows[0],hr:hist[0].i+2};
 });
 const tv=t.getRange(2,5,t.getLastRow()-1,2).getValues();
 d.getRange(p.r,p.c).setValue('GASTOS PERSONALES');
 jobs.forEach((j,i)=>{
  const row=j.data.r.slice();row[0]=j.name;d.getRange(p.r+1+i,p.c,1,4).setValues([row]);d.getRange(q.r+1+j.data.i,q.c,1,4).clearContent();
  h.getRange(j.hr,1,1,12).copyTo(h.getRange(free[i],1,1,12));h.getRange(free[i],1,1,2).setValues([['GASTOS PERSONALES',j.name]]);h.getRange(free[i],11,1,2).setValues([[dst+1,'Concepto']]);h.getRange(j.hr,1,1,12).clearContent();h.getRange(j.hr,11,1,2).setValues([[src+1,'Reserva']]);
  tv.forEach(r=>{if(claveAltium24_(r[0])==='GUSTOS'&&claveAltium24_(r[1])===claveAltium24_(j.old)){r[0]='GASTOS PERSONALES';r[1]=j.name;}});
 });
 d.getRange(p.r+3,p.c,1,4).setValues([['Tecnología','',0,'']]);d.getRange(p.r,p.c,21,1).setWrap(true);
 t.getRange(2,5,tv.length,2).clearDataValidations().setValues(tv);mapeoAltium24_(ss);sincronizarAltium24_(ss);props.setProperty('ALTIUM24_GASTOS_PERSONALES','1');
}
function agregarPapelesAccesorios24_(ss){
 const props=PropertiesService.getDocumentProperties();if(props.getProperty('ALTIUM24_PAPELES_ACCESORIOS'))return;
 const d=ss.getSheetByName('Datos'),t=hojaGastosAltium25_(ss),state=estadoAltium24_(ss),pos=posicionesAltium24_();
 const jobs=['CARRO','MOTO'].map(cat=>{
  const slot=state.slots.findIndex(s=>claveAltium24_(s.cat)===cat);if(slot<0)throw new Error('Falta '+cat);
  const p=pos[slot],v=d.getRange(p.r+1,p.c,20,4).getValues(),free=v.map((r,i)=>({r,i})).filter(x=>!x.r.some(z=>z!==''));
  if(free.length<2||v.some(r=>['PAPELES','ACCESORIOS'].includes(claveAltium24_(r[0]))))throw new Error('Revisar espacios o duplicados en '+cat);
  return {p,free};
 });
 const changes=[{r:499,cat:'CARRO',desc:'FIRMA VENTANILLA UNICA',amount:8000,name:'Papeles'},{r:582,cat:'MOTO',desc:'MOTO PAPELES',amount:630000,name:'Papeles'},{r:605,cat:'MOTO',desc:'CUELLERO MOTO',amount:7000,name:'Accesorios'}];
 changes.forEach(j=>{const v=t.getRange(j.r,3,1,4).getValues()[0];if(v[0]!==j.amount||claveAltium24_(v[1])!==j.desc||claveAltium24_(v[2])!==j.cat||claveAltium24_(v[3])!=='OTROS GASTOS DEL VEHICULO')throw new Error('El movimiento cambio: fila '+j.r);});
 jobs.forEach(j=>{['Papeles','Accesorios'].forEach((name,i)=>d.getRange(j.p.r+1+j.free[i].i,j.p.c,1,4).setValues([[name,'',0,'']]));});
 changes.forEach(j=>t.getRange(j.r,6).clearDataValidations().setValue(j.name));
 mapeoAltium24_(ss);sincronizarAltium24_(ss);props.setProperty('ALTIUM24_PAPELES_ACCESORIOS','1');
}
function ordenarVehiculos24_(ss){
 const props=PropertiesService.getDocumentProperties();if(props.getProperty('ALTIUM24_VEHICULOS_SEPARADOS'))return;
 const d=ss.getSheetByName('Datos'),t=hojaGastosAltium25_(ss),h=ss.getSheetByName('Historico_presupuesto'),state=estadoAltium24_(ss),pos=posicionesAltium24_();
 const tv=t.getRange(2,1,t.getLastRow()-1,10).getValues(),hv=h.getRange(2,1,h.getLastRow()-1,2).getValues();
 const jobs=['CARRO','MOTO'].map(cat=>{
  const slot=state.slots.findIndex(s=>claveAltium24_(s.cat)===cat);if(slot<0)throw new Error('Falta '+cat);
  const p=pos[slot],v=d.getRange(p.r+1,p.c,20,4).getValues();
  const mapping={};mapping['PARQUEADERO '+cat]='Parqueadero mensual';mapping['PARQUEO DIARIO']='Parqueadero diario y diligencias';mapping['OTROS/IMPREVISTOS/MULTAS/PARQUEO SUELTO']='Otros gastos del vehículo';
  Object.keys(mapping).forEach(old=>{if(v.filter(r=>claveAltium24_(r[0])===old).length!==1)throw new Error('Revisar '+cat+' '+old);});
  const free=v.map((r,i)=>({r,i})).filter(x=>!x.r.some(z=>z!==''));if(free.length<2)throw new Error('Faltan espacios '+cat);
  return {cat,p,v,mapping,free};
 });
 jobs.forEach(j=>{
  j.v.forEach((row,i)=>{const name=j.mapping[claveAltium24_(row[0])];if(name)d.getRange(j.p.r+1+i,j.p.c).setValue(name);});
  [['Imprevistos del vehículo','Básicos'],['Multas de tránsito','']].forEach((item,i)=>d.getRange(j.p.r+1+j.free[i].i,j.p.c,1,4).setValues([[item[0],item[1],0,'']]));
  tv.forEach(row=>{if(claveAltium24_(row[4])!==j.cat)return;const old=claveAltium24_(row[5]),name=j.mapping[old];if(!name)return;
   row[5]=name;
   if(old==='OTROS/IMPREVISTOS/MULTAS/PARQUEO SUELTO'){
    const desc=claveAltium24_(row[3])+' '+claveAltium24_(row[7]);
    if(/PARQUE|PARQUEO|PARKING/.test(desc))row[5]='Parqueadero diario y diligencias';
    else if(/MULTA|COMPARENDO/.test(desc))row[5]='Multas de tránsito';
    else if(/LAVADA|LAVADO|ASEO/.test(desc))row[5]='Aseo '+j.cat.toLowerCase();
   }
  });
  hv.forEach(row=>{if(claveAltium24_(row[0])===j.cat&&j.mapping[claveAltium24_(row[1])])row[1]=j.mapping[claveAltium24_(row[1])];});
  d.getRange(j.p.r+1,j.p.c,20,1).setWrap(true);
  const other=j.v.findIndex(r=>claveAltium24_(r[0])==='OTROS/IMPREVISTOS/MULTAS/PARQUEO SUELTO');d.getRange(j.p.r+1+other,j.p.c).setNote('Conserva el presupuesto del anterior grupo mixto. Revisar antes de distribuir entre imprevistos y multas.');
 });
 t.getRange(2,5,tv.length,2).clearDataValidations().setValues(tv.map(r=>[r[4],r[5]]));h.getRange(2,1,hv.length,2).setValues(hv);
 mapeoAltium24_(ss);sincronizarAltium24_(ss);props.setProperty('ALTIUM24_VEHICULOS_SEPARADOS','1');
}
function aclararFamilia24_(ss){
 const props=PropertiesService.getDocumentProperties();if(props.getProperty('ALTIUM24_NOMBRES_FAMILIA'))return;
 const d=ss.getSheetByName('Datos'),t=hojaGastosAltium25_(ss),h=ss.getSheetByName('Historico_presupuesto');
 const names=[['zoraida','Cuidado de Alejo — Zoraida'],['Aldemar','Onces de Mafe — Aldemar'],['Dani','Transporte y gastos personales de Dani'],['Mafe extra','Gastos adicionales de Mafe'],['Extras alejo','Gastos adicionales de Alejo']];
 const state=estadoAltium24_(ss),slot=state.slots.findIndex(s=>claveAltium24_(s.cat)==='FAMILIA Y DEPENDIENTES');if(slot<0)throw new Error('Falta categoria familiar.');
 const p=posicionesAltium24_()[slot],dv=d.getRange(p.r+1,p.c,20,1).getValues(),tv=t.getRange(2,5,t.getLastRow()-1,2).getValues(),hv=h.getRange(2,1,h.getLastRow()-1,2).getValues();
 const jobs=names.map(([old,name])=>{const hits=dv.map((r,i)=>({r,i})).filter(x=>claveAltium24_(x.r[0])===claveAltium24_(old));if(hits.length!==1||dv.some(r=>claveAltium24_(r[0])===claveAltium24_(name)))throw new Error('Revisar concepto familiar '+old);return {old,name,i:hits[0].i};});
 jobs.forEach(j=>{d.getRange(p.r+1+j.i,p.c).setValue(j.name);[tv,hv].forEach(rows=>rows.forEach(row=>{if(claveAltium24_(row[0])==='FAMILIA Y DEPENDIENTES'&&claveAltium24_(row[1])===claveAltium24_(j.old))row[1]=j.name;}));});
 t.getRange(2,5,tv.length,2).clearDataValidations().setValues(tv);h.getRange(2,1,hv.length,2).setValues(hv);
 d.getRange(p.r+1,p.c,20,1).setWrap(true);
 mapeoAltium24_(ss);sincronizarAltium24_(ss);props.setProperty('ALTIUM24_NOMBRES_FAMILIA','1');
}
function trasladarTransporte24_(ss){
 const props=PropertiesService.getDocumentProperties();if(props.getProperty('ALTIUM24_TRANSPORTE_PUBLICO'))return;
 const d=ss.getSheetByName('Datos'),t=hojaGastosAltium25_(ss),h=ss.getSheetByName('Historico_presupuesto'),pos=posicionesAltium24_(),state=estadoAltium24_(ss);
 const dst=state.slots.findIndex(s=>claveAltium24_(s.cat)==='TRANSPORTE PUBLICO');if(dst<0)throw new Error('Falta TRANSPORTE PUBLICO.');
 const hv=h.getRange(2,1,h.getLastRow()-1,12).getValues(),p=pos[dst];
 const changes=[['CARRO','Buses','Buses'],['CARRO','Taxis','Taxi'],['MOTO','didi picap','Picap']];
 const jobs=changes.map(([cat,old,name])=>{
  const src=state.slots.findIndex(s=>claveAltium24_(s.cat)===claveAltium24_(cat));if(src<0)throw new Error('Falta origen '+cat);
  const find=(q,n)=>Array.from({length:20},(_,i)=>q.r+1+i).filter(r=>claveAltium24_(d.getRange(r,q.c).getValue())===claveAltium24_(n));
  const sr=find(pos[src],old),dr=find(p,name);
  const hs=hv.map((v,i)=>({v,r:i+2})).filter(x=>claveAltium24_(x.v[0])===claveAltium24_(cat)&&claveAltium24_(x.v[1])===claveAltium24_(old));
  const hd=hv.map((v,i)=>({v,r:i+2})).filter(x=>claveAltium24_(x.v[0])==='TRANSPORTE PUBLICO'&&claveAltium24_(x.v[1])===claveAltium24_(name));
  if(sr.length!==1||dr.length!==1||hs.length!==1||hd.length!==1)throw new Error('Revisar duplicados de '+old);
  const sv=d.getRange(sr[0],pos[src].c,1,4).getValues()[0],dv=d.getRange(dr[0],p.c,1,4).getValues()[0];
  if([...hs[0].v.slice(3,10),...hd[0].v.slice(3,10),sv[2],dv[2]].some(v=>v!==''&&v!==null&&typeof v!=='number'))throw new Error('Monto no numerico en '+old);
  return {cat,old,name,src,sr:sr[0],dr:dr[0],hs:hs[0],hd:hd[0],sv,dv};
 });
 const tv=t.getRange(2,5,t.getLastRow()-1,2).getValues();
 jobs.forEach(j=>{
  const vals=j.dv.slice();vals[2]=Number(j.sv[2]||0)+Number(vals[2]||0);if(!vals[1])vals[1]=j.sv[1];if(!vals[3])vals[3]=j.sv[3];
  d.getRange(j.dr,p.c,1,4).setValues([vals]);d.getRange(j.sr,pos[j.src].c,1,4).clearContent();
  h.getRange(j.hd.r,4,1,7).setValues([j.hd.v.slice(3,10).map((v,i)=>v===''&&j.hs.v[i+3]===''?'':Number(v||0)+Number(j.hs.v[i+3]||0))]);
  h.getRange(j.hs.r,1,1,12).clearContent();h.getRange(j.hs.r,11,1,2).setValues([[j.src+1,'Reserva']]);
  tv.forEach(row=>{if(claveAltium24_(row[0])===claveAltium24_(j.cat)&&claveAltium24_(row[1])===claveAltium24_(j.old)){row[0]='TRANSPORTE PUBLICO';row[1]=j.name;}});
 });
 t.getRange(2,5,tv.length,2).clearDataValidations().setValues(tv);
 mapeoAltium24_(ss);sincronizarAltium24_(ss);props.setProperty('ALTIUM24_TRANSPORTE_PUBLICO','1');
}
function trasladarFondosAhorros24_(ss){
 const props=PropertiesService.getDocumentProperties();if(props.getProperty('ALTIUM24_FONDOS_AHORROS'))return;
 const d=ss.getSheetByName('Datos'),t=hojaGastosAltium25_(ss),h=ss.getSheetByName('Historico_presupuesto');
 const pos=posicionesAltium24_(),state=estadoAltium24_(ss),dst=state.slots.findIndex(s=>claveAltium24_(s.cat)==='AHORROS');
 if(dst<0)throw new Error('Falta categoria AHORROS.');
 const p=pos[dst],free=[];for(let r=p.r+1;r<=p.r+20;r++)if(!d.getRange(r,p.c,1,4).getValues()[0].some(v=>v!==''))free.push(r);
 const hv=h.getRange(2,1,h.getLastRow()-1,12).getValues(),hf=[];
 hv.forEach((row,i)=>{if(Number(row[10])===dst+1&&!row[1]&&!row.slice(3,10).some(v=>v!==''&&v!==null))hf.push(i+2);});
 const changes=[['fondo amigos (ahorro)','Fondo amigos'],['fondo de tranquilidad','Fondo de emergencia']];
 const jobs=changes.map(([old,name])=>{
  const hits=[];state.slots.forEach((s,i)=>{if(claveAltium24_(s.cat)==='CREDITOS')for(let r=pos[i].r+1;r<=pos[i].r+20;r++)if(claveAltium24_(d.getRange(r,pos[i].c).getValue())===claveAltium24_(old))hits.push({r,c:pos[i].c,slot:i+1});});
  if(hits.length!==1)throw new Error('Origen ambiguo: '+old);
  const history=hv.map((row,i)=>({row,i})).filter(x=>claveAltium24_(x.row[0])==='CREDITOS'&&claveAltium24_(x.row[1])===claveAltium24_(old));
  if(history.length!==1||state.slots[dst].items.some(x=>claveAltium24_(x)===claveAltium24_(name)))throw new Error('Revisar historico o destino: '+name);
  return {...hits[0],old,name,history:history[0].i+2};
 });
 if(free.length<2||hf.length<2)throw new Error('Faltan dos espacios libres para ahorros.');
 const tv=t.getRange(2,5,t.getLastRow()-1,2).getValues();
 jobs.forEach((j,i)=>{
  const vals=d.getRange(j.r,j.c,1,4).getValues();vals[0][0]=j.name;d.getRange(free[i],p.c,1,4).setValues(vals);d.getRange(j.r,j.c,1,4).clearContent();
  h.getRange(j.history,1,1,12).copyTo(h.getRange(hf[i],1,1,12));h.getRange(hf[i],1,1,2).setValues([['AHORROS',j.name]]);h.getRange(hf[i],11,1,2).setValues([[dst+1,'Concepto']]);
  h.getRange(j.history,1,1,12).clearContent();h.getRange(j.history,11,1,2).setValues([[j.slot,'Reserva']]);
  tv.forEach(row=>{if(claveAltium24_(row[0])==='CREDITOS'&&claveAltium24_(row[1])===claveAltium24_(j.old)){row[0]='AHORROS';row[1]=j.name;}});
 });
 t.getRange(2,5,tv.length,2).clearDataValidations().setValues(tv);
 mapeoAltium24_(ss);sincronizarAltium24_(ss);
 props.setProperty('ALTIUM24_FONDOS_AHORROS','1');
}
function separarIngresos24_(ss){
 if(ss.getSheetByName('Gastos')&&ss.getSheetByName('Ingresos'))return;
 const p=PropertiesService.getDocumentProperties();if(p.getProperty('ALTIUM24_SEPARACION_INGRESOS'))return;
 const t=hojaGastosAltium25_(ss);
 if(claveAltium24_(t.getRange('K1').getValue())!=='MES')throw new Error('Revisar inicio de ingresos antes de insertar separador.');
 t.insertColumnBefore(11);
 t.getRange(1,11,t.getMaxRows(),1).clearContent().clearDataValidations().clearFormat().setBackground('#ffffff');
 t.setColumnWidth(11,30);
 p.setProperty('ALTIUM24_SEPARACION_INGRESOS','1');
}
function moverControlAJ24_(ss){
 if(ss.getSheetByName('Gastos')&&ss.getSheetByName('Ingresos'))return;
 const p=PropertiesService.getDocumentProperties();if(p.getProperty('ALTIUM24_CONTROL_J'))return;
 const t=hojaGastosAltium25_(ss);
 if(claveAltium24_(t.getRange('J1').getValue())==='ACCION DE CONTROL (OPCIONAL)'){p.setProperty('ALTIUM24_CONTROL_J','1');return;}
 if(claveAltium24_(t.getRange('Q1').getValue())!=='ACCION DE CONTROL (OPCIONAL)'||claveAltium24_(t.getRange('J1').getValue())!=='MES')throw new Error('Revisar columnas antes de mover control.');
 t.moveColumns(t.getRange('Q:Q'),10);
 p.setProperty('ALTIUM24_CONTROL_J','1');
}
function prepararAltium24(){const ss=SpreadsheetApp.getActiveSpreadsheet();if(!PropertiesService.getDocumentProperties().getProperty(ALTIUM24_ESTADO))ampliarDatos24_(ss);else sincronizarAltium24_(ss);}
function bloquesAltium24_(ss){
 const v=ss.getSheetByName('Datos').getDataRange().getValues(),blocks=[];
 for(let r=0;r<v.length;r++)for(let c=0;c+1<v[r].length;c++){
  if(!v[r][c]||['PRIORIDAD','MONTO','ACCION DE CONTROL'].includes(claveAltium24_(v[r][c])))continue;
  const monto=claveAltium24_(v[r][c+1])==='MONTO'?1:(claveAltium24_(v[r][c+1])==='PRIORIDAD'&&claveAltium24_(v[r][c+2])==='MONTO'?2:0);if(!monto)continue;
  let end=r+1;while(end<v.length&&claveAltium24_(v[end][c])!=='TOTAL')end++;
  if(end===v.length)throw new Error('Falta TOTAL en Datos: '+v[r][c]);
  blocks.push({cat:String(v[r][c]).trim(),col:c+1,montoCol:c+monto+1,start:r+2,end:end,rows:v.slice(r+1,end).map(row=>[row[c],row[c+monto]])});
 }return blocks;
}
function ampliarDatos24_(ss){
 const d=ss.getSheetByName('Datos'),h=ss.getSheetByName('Historico_presupuesto'),original=bloquesAltium24_(ss);
 if(original.length!==9||original.some(b=>b.rows.filter(x=>String(x[0]||'').trim()).length>20))throw new Error('La ampliacion espera 9 categorias originales con hasta 20 conceptos.');
 const ab=h.getRange(2,1,Math.max(1,h.getLastRow()-1),2);ab.setValues(ab.getValues());
 if(d.getMaxRows()<70)d.insertRowsAfter(d.getMaxRows(),70-d.getMaxRows());
 const matrix=Array.from({length:69},()=>Array(24).fill(''));
 posicionesAltium24_().forEach((p,i)=>{
  const old=original[i],items=old?old.rows.filter(x=>String(x[0]||'').trim()):[];
  matrix[p.r-1][p.c-1]=old?old.cat:'';matrix[p.r-1][p.c]='Monto';
  items.forEach((row,j)=>{matrix[p.r+j][p.c-1]=row[0];matrix[p.r+j][p.c]=row[1];});
  matrix[p.r+20][p.c-1]='TOTAL';
  const col=String.fromCharCode(66+p.c);matrix[p.r+20][p.c]='=SUM('+col+(p.r+1)+':'+col+(p.r+20)+')';
 });
 d.getRange('A1:X69').clearDataValidations().setBackground('#ffffff').setFontColor('#1f2937').setFontWeight('normal').setValues(matrix);
 const hdr=posicionesAltium24_().map(p=>d.getRange(p.r,p.c,1,2).getA1Notation());
 const input=posicionesAltium24_().map(p=>d.getRange(p.r+1,p.c,20,2).getA1Notation());
 const totals=posicionesAltium24_().map(p=>d.getRange(p.r+21,p.c,1,2).getA1Notation());
 d.getRangeList(hdr).setBackground('#185b4a').setFontColor('#ffffff').setFontWeight('bold');
 d.getRangeList(input).setBackground('#fff8df');
 d.getRangeList(totals).setBackground('#e2eee8').setFontWeight('bold');
 posicionesAltium24_().forEach(p=>d.getRange(p.r+1,p.c+1,21,1).setNumberFormat('"$"#,##0'));
 [1,5,9,13,17].forEach(c=>{d.setColumnWidth(c,220);d.setColumnWidth(c+1,115);});
 [4,8,12,16].forEach(c=>d.setColumnWidth(c,20));d.setFrozenRows(0);
 const named=ss.getNamedRanges();original.forEach((b,i)=>{const n=named.find(x=>claveAltium24_(x.getName())===claveAltium24_(b.cat)),p=posicionesAltium24_()[i];if(n)n.setRange(d.getRange(p.r+1,p.c,20,1));});
 d.getRange('A1').setNote('Edita los nombres de categoria en los encabezados verdes. Cada bloque tiene 20 subcategorias. Los seis bloques vacios estan disponibles para categorias nuevas. Mueve siempre concepto y monto juntos al ordenar.');
 PropertiesService.getDocumentProperties().setProperty(ALTIUM24_ESTADO,JSON.stringify({slots:original.map(b=>({cat:b.cat,items:b.rows.filter(x=>String(x[0]||'').trim()).map(x=>String(x[0]).trim())}))}));
 sincronizarAltium24_(ss);
}
function estadoAltium24_(ss){
 const v=ss.getSheetByName('Datos').getRange('A1:X69').getValues();
 return{slots:posicionesAltium24_().map(p=>({cat:String(v[p.r-1][p.c-1]||'').trim(),items:v.slice(p.r,p.r+20).map(row=>String(row[p.c-1]||'').trim()).filter(Boolean)}))};
}
function sincronizarAltium24_(ss,edited){
 const props=PropertiesService.getDocumentProperties(),old=JSON.parse(props.getProperty(ALTIUM24_ESTADO)||'{"slots":[]}'),current=estadoAltium24_(ss),cats=current.slots.map(s=>claveAltium24_(s.cat)).filter(Boolean);
 if(new Set(cats).size!==cats.length){ss.toast('Hay categorias repetidas. Corrige los encabezados en Datos.','Altium 24',10);return;}
 const h=ss.getSheetByName('Historico_presupuesto'),t=hojaGastosAltium25_(ss),hv=h.getRange(2,1,Math.max(1,h.getLastRow()-1),2).getValues(),tv=t.getRange(2,5,Math.max(1,t.getLastRow()-1),2).getValues();let hc=false,tc=false;
 current.slots.forEach((slot,i)=>{
  const prev=old.slots[i];if(!prev||!prev.cat||!slot.cat)return;
  if(prev.cat!==slot.cat){hv.forEach(row=>{if(claveAltium24_(row[0])===claveAltium24_(prev.cat)){row[0]=slot.cat;hc=true;}});tv.forEach(row=>{if(claveAltium24_(row[0])===claveAltium24_(prev.cat)){row[0]=slot.cat;tc=true;}});}
  const removed=prev.items.filter(x=>!slot.items.some(y=>claveAltium24_(x)===claveAltium24_(y))),added=slot.items.filter(x=>!prev.items.some(y=>claveAltium24_(x)===claveAltium24_(y))),p=posicionesAltium24_()[i];
  if(edited&&edited.getSheet().getName()==='Datos'&&edited.getNumRows()===1&&edited.getNumColumns()===1&&edited.getColumn()===p.c&&edited.getRow()>p.r&&edited.getRow()<=p.r+20&&removed.length===1&&added.length===1){
   hv.forEach(row=>{if(claveAltium24_(row[0])===claveAltium24_(slot.cat)&&claveAltium24_(row[1])===claveAltium24_(removed[0])){row[1]=added[0];hc=true;}});
   tv.forEach(row=>{if(claveAltium24_(row[0])===claveAltium24_(slot.cat)&&claveAltium24_(row[1])===claveAltium24_(removed[0])){row[1]=added[0];tc=true;}});
  }
 });
 if(hc)h.getRange(2,1,hv.length,2).setValues(hv);if(tc)t.getRange(2,5,tv.length,2).clearDataValidations().setValues(tv);
 if(!old.layout||(edited&&edited.getSheet().getName()==='Mapeo'))mapeoAltium24_(ss);historicoAltium24_(ss);SpreadsheetApp.flush();listasAltium24_(ss);current.layout=1;
 props.setProperty(ALTIUM24_ESTADO,JSON.stringify(current));
}
function mapeoAltium24_(ss){
 const m=ss.getSheetByName('Mapeo'),d=ss.getSheetByName('Datos'),pos=posicionesAltium24_();
 if(m.getMaxColumns()<15)m.insertColumnsAfter(m.getMaxColumns(),15-m.getMaxColumns());
 if(m.getMaxRows()<21)m.insertRowsAfter(m.getMaxRows(),21-m.getMaxRows());
 m.getRange(1,1,Math.max(21,m.getLastRow()),15).clearContent();
 m.getRange(1,1,21,15).setFormulas(Array.from({length:21},(_,r)=>pos.map(p=>{const a=String.fromCharCode(64+p.c)+(p.r+r);return '=IF(Datos!'+a+'="";"";Datos!'+a+')';})));
 m.getRange(1,1,1,15).setBackground('#185b4a').setFontColor('#ffffff').setFontWeight('bold');m.setFrozenRows(1);
 m.getRange('A1').setNote('Vista automatica: edita categorias y subcategorias en Datos.');
 d.getRange('AA1:AA15').setFormulas(pos.map(p=>{const a=String.fromCharCode(64+p.c)+p.r;return ['=IF('+a+'="";"";'+a+')'];}));
}
function asegurarTotalesAltium24_(ss){
 const props=PropertiesService.getDocumentProperties();if(props.getProperty('ALTIUM24_TOTALES_VALIDOS_V3'))return;
 const d=ss.getSheetByName('Datos');
 posicionesAltium24_().forEach(p=>{
  const c=String.fromCharCode(64+p.c),m=String.fromCharCode(66+p.c);
  d.getRange(p.r+21,p.c+2).setFormula('=IF('+c+p.r+'="";0;SUMIF('+c+(p.r+1)+':'+c+(p.r+20)+';"<>";'+m+(p.r+1)+':'+m+(p.r+20)+'))');
 });
 props.setProperty('ALTIUM24_TOTALES_VALIDOS_V3','1');
}
function ampliarHistoricoAltium24_(ss){
 const props=PropertiesService.getDocumentProperties();if(props.getProperty('ALTIUM24_HISTORICO_15X20'))return;
 const h=ss.getSheetByName('Historico_presupuesto'),d=ss.getSheetByName('Datos'),state=estadoAltium24_(ss),used=h.getDataRange(),raw=used.getValues(),formulas=used.getFormulas();
 const previous=raw.slice(1).map((row,i)=>({row:row.slice(0,10).map((v,j)=>j>=3&&formulas[i+1][j]?formulas[i+1][j]:v),used:false})).filter(x=>x.row.some(v=>v!==''&&v!==null));
 const rows=[];
 state.slots.forEach((slot,i)=>{
  slot.items.forEach(item=>{
   const found=previous.find(x=>!x.used&&claveAltium24_(x.row[0])===claveAltium24_(slot.cat)&&claveAltium24_(x.row[1])===claveAltium24_(item));
   const row=found?found.row.slice():[slot.cat,item,'','','','','','','',''];if(found)found.used=true;
   while(row.length<10)row.push('');rows.push([...row,i+1,'Concepto']);
  });
  for(let j=slot.items.length;j<20;j++)rows.push(['','','','','','','','','','',i+1,'Reserva']);
 });
 // Conserva aparte conceptos anteriores que ya no figuran en el catalogo.
 previous.filter(x=>!x.used).forEach(x=>{const row=x.row.slice();while(row.length<10)row.push('');rows.push([...row,'','Anterior']);});
 if(h.getMaxRows()<rows.length+1)h.insertRowsAfter(h.getMaxRows(),rows.length+1-h.getMaxRows());
 if(h.getMaxColumns()<12)h.insertColumnsAfter(h.getMaxColumns(),12-h.getMaxColumns());
 h.getRange(2,1,Math.max(rows.length,raw.length-1),12).clearContent().clearDataValidations();
 h.getRange(2,1,rows.length,12).setValues(rows);
 h.getRange('K1:L1').setValues([['Bloque Datos','Estado']]);h.hideColumns(11,2);
 h.getRange(2,1,rows.length,10).setBackground('#ffffff').setFontColor('#1f2937').setFontWeight('normal');
 // La tabla nativa conserva el formato monetario de sus columnas.
 h.getRange(2,1,rows.length,2).setWrap(true);
 h.getRangeList(Array.from({length:15},(_,i)=>'A'+(2+i*20)+':J'+(2+i*20))).setBackground('#e2eee8').setFontWeight('bold');
 posicionesAltium24_().forEach((p,i)=>h.getRange(2+i*20,1).setNote('20 espacios para la categoria de Datos!'+String.fromCharCode(64+p.c)+p.r+'. Completa categorias y conceptos desde Datos. Los meses anteriores se conservan.'));
 h.setFrozenRows(1);props.setProperty('ALTIUM24_HISTORICO_15X20','1');
}
function historicoAltium24_(ss){
 asegurarTotalesAltium24_(ss);ampliarHistoricoAltium24_(ss);
 const d=ss.getSheetByName('Datos'),h=ss.getSheetByName('Historico_presupuesto'),blocks=bloquesAltium24_(ss),pos=posicionesAltium24_();
 d.getRange('AA19').setFormula('='+pos.map(p=>String.fromCharCode(66+p.c)+(p.r+21)).join('+'));
 const last=Math.max(2,h.getLastRow()),values=h.getRange(2,1,last-1,12).getValues();
 const known=new Set(values.filter(r=>r[1]!==''&&r[1]!==null).map(r=>claveAltium24_(r[0])+'|'+claveAltium24_(r[1])));
 blocks.forEach(b=>b.rows.forEach(row=>{
  if(row[0]==null||String(row[0]).trim()==='')return;
  const key=claveAltium24_(b.cat)+'|'+claveAltium24_(row[0]);if(known.has(key))return;
  const slot=pos.findIndex(p=>p.c===b.col&&p.r+1===b.start)+1;
  const free=values.findIndex(r=>Number(r[10])===slot&&(r[1]===''||r[1]===null));
  if(free>=0){values[free][0]=b.cat;values[free][1]=String(row[0]);values[free][11]='Concepto';}
  else values.push([b.cat,String(row[0]),'','','','','','','','',slot,'Concepto']);
  known.add(key);
 }));
 if(values.length+1>h.getMaxRows())h.insertRowsAfter(h.getMaxRows(),values.length+1-h.getMaxRows());
 // Solo actualiza identidades y propuesta; D:J no se reescriben al sincronizar.
 const abc=values.map((row,i)=>{
  if(row[1]===''||row[1]===null){
   const slot=Number(row[10]),p=pos[slot-1];
   if(!p)return ['','',''];
   const a=String.fromCharCode(64+p.c)+p.r;
   row[11]='Reserva';return ['=IF(Datos!'+a+'="";"";Datos!'+a+')','',''];
  }
  const b=blocks.find(x=>claveAltium24_(x.cat)===claveAltium24_(row[0]));
  if(!b)return [row[0],row[1],'=0'];
  const names=String.fromCharCode(64+b.col)+b.start+':'+String.fromCharCode(64+b.col)+b.end,amounts=String.fromCharCode(64+b.montoCol)+b.start+':'+String.fromCharCode(64+b.montoCol)+b.end;
  return [row[0],row[1],'=SUMIF(Datos!'+names+';$B'+(i+2)+';Datos!'+amounts+')'];
 });
 h.getRange(2,1,abc.length,3).clearDataValidations().setValues(abc);
 h.getRange(2,11,values.length,2).setValues(values.map(row=>[row[10],row[11]]));
}
function listasAltium24_(ss,first,count){
 const t=hojaGastosAltium25_(ss),slots=estadoAltium24_(ss).slots,cats=[],rules={};
 slots.forEach(slot=>{const cat=slot.cat;if(!cat)return;cats.push(cat);const items=[...new Set(slot.items)];rules[claveAltium24_(cat)]=items.length?SpreadsheetApp.newDataValidation().requireValueInList(items,true).setAllowInvalid(false).build():null;});
 const catRule=cats.length?SpreadsheetApp.newDataValidation().requireValueInList([...new Set(cats)],true).setAllowInvalid(false).build():null,row=Math.max(2,first||2),n=Math.min(count||t.getMaxRows()-1,t.getMaxRows()-row+1);if(n<=0)return;
 t.getRange(row,5,n,2).setDataValidations(t.getRange(row,5,n,1).getDisplayValues().map(r=>[catRule,rules[claveAltium24_(r[0])]||null]));
}




function eliminarMesDuplicadoAltium24_(ss){
 if(ss.getSheetByName('Gastos')&&ss.getSheetByName('Ingresos'))return;
 const t=hojaGastosAltium25_(ss),props=PropertiesService.getDocumentProperties();
 if(props.getProperty('ALTIUM24_N_ELIMINADA'))return;
 if(t.getRange('N1').getValue()!==''||claveAltium24_(t.getRange('O1').getValue())!=='CATEGORIA'||claveAltium24_(t.getRange('P1').getValue())!=='HORAS')throw new Error('La distribucion de columnas cambio; no se elimino ninguna columna.');
 t.deleteColumn(14);t.showColumns(14,3);t.getRange('J1').setValue('MES');
 props.setProperty('ALTIUM24_N_ELIMINADA','1');
}

function repararReferenciasMesAltium24_(ss){
 if(ss.getSheetByName('Gastos')&&ss.getSheetByName('Ingresos'))return;
 const props=PropertiesService.getDocumentProperties();if(props.getProperty('ALTIUM24_REFERENCIAS_MES_J'))return;
 const h=ss.getSheetByName('Ingresos');
 if(h)['D2:O5','D10:O18'].forEach(a=>{const range=h.getRange(a),formulas=range.getFormulas();if(formulas.some(row=>row.some(f=>f.includes('#REF!'))))range.setFormulas(formulas.map(row=>row.map(f=>f.replace(/#REF!/g,'Transaccional!$J:$J'))));});
 hojaGastosAltium25_(ss).getRange('J1').setValue('MES');
 props.setProperty('ALTIUM24_REFERENCIAS_MES_J','1');
}

function configurarPrioridadesAltium24_(ss){
 const props=PropertiesService.getDocumentProperties();if(props.getProperty('ALTIUM24_PRIORIDADES'))return;
 const d=ss.getSheetByName('Datos'),t=hojaGastosAltium25_(ss);
 const opciones=['Básicos','Calidad de vida','Estilo de vida','Caprichosos'];
 const regla=SpreadsheetApp.newDataValidation().requireValueInList(opciones,true).setAllowInvalid(false).build();
 // Libera O19 para la prioridad del quinto bloque y conserva el total a la derecha.
 d.getRange('O19:Q21').breakApart().clearContent();
 d.getRange('AA19:AC21').merge().setFontSize(24).setFontWeight('bold').setNumberFormat('"$"#,##0');
 d.getRange('AA18').setValue('PRESUPUESTO TOTAL').setFontWeight('bold');
 d.getRange('AA19').setFormula('='+posicionesAltium24_().map(p=>String.fromCharCode(66+p.c)+(p.r+21)).join('+'));
 posicionesAltium24_().forEach(p=>{
  d.getRange(p.r,p.c+1).setValue('Prioridad').setBackground('#185b4a').setFontColor('#ffffff').setFontSize(11).setFontWeight('bold');
  d.getRange(p.r+1,p.c+1,20,1).setDataValidation(regla).setNumberFormat('@').setFontSize(11).setFontWeight('normal').setBackground('#fff8df');
 });
 [3,7,11,15,19].forEach(c=>d.setColumnWidth(c,155));
 t.getRange('I1').setValue('Prioridad (opcional)').setBackground('#f4cccc').setFontWeight('bold').setWrap(true).setNote('Opcional. Si eliges una prioridad aqui, se usa para este movimiento. Si queda vacia, Altium usa la prioridad de la subcategoria en Datos.');
 t.getRange(2,9,t.getMaxRows()-1,1).setDataValidation(regla);t.setColumnWidth(9,180);
 props.setProperty('ALTIUM24_PRIORIDADES','1');
}

function proponerPrioridadesIniciales24_(ss){
 const props=PropertiesService.getDocumentProperties();if(props.getProperty('ALTIUM24_PROPUESTA_PRIORIDADES'))return;
 const propuesta={"VIVIENDA|IMPUESTOS (PREDIAL, VALORIZACION)": "Básicos", "VIVIENDA|ADMINISTRACION – VIGILANCIA": "Básicos", "VIVIENDA|SEGURO TODO RIESGO": "Básicos", "VIVIENDA|ALIMENTACION DEL HOGAR": "Básicos", "VIVIENDA|SUPLEMENTOS NUTRICIONALES": "Calidad de vida", "VIVIENDA|SERVICIOS PUBLICOS": "Básicos", "VIVIENDA|TRIPLEPLAY – INTERNET – NETFLIX": "Calidad de vida", "VIVIENDA|EMPLEADA SERVICIO DOMESTICO": "Calidad de vida", "VIVIENDA|OTROS": "Calidad de vida", "SALUD|SALUD": "Básicos", "SALUD|FONDO DE PENSIONES": "Básicos", "SALUD|PARAFISCALES (ARL, ICBF)": "Básicos", "SALUD|MEDICINA PREPAGADA": "Calidad de vida", "SALUD|MEDICAMENTOS": "Básicos", "SALUD|GIMNASIO": "Calidad de vida", "SALUD|NUTRICION ESPECIAL": "Calidad de vida", "SALUD|COPAGOS": "Básicos", "SALUD|OTRO": "Básicos", "EDUCACION|PROPIA": "Calidad de vida", "EDUCACION|PERSONAS A CARGO": "Básicos", "EDUCACION|CURSOS/CONFERENCIAS": "Calidad de vida", "EDUCACION|OTRO": "Calidad de vida", "CREDITOS|CADENA JARBY": "Básicos", "CREDITOS|CADENA YOSA": "Básicos", "CREDITOS|FONDO AMIGOS": "Básicos", "CREDITOS|FONDO DE TRANQUILIDAD": "Básicos", "CREDITOS|CREDITO EDUCATIVO": "Básicos", "CREDITOS|CREDITO POR LIBRANZA": "Básicos", "CREDITOS|CODEMA": "Básicos", "CREDITOS|DEUDA A AMIGOS": "Básicos", "CREDITOS|DEUDA A FAMILIARES": "Básicos", "CREDITOS|DEUDAS DE IMPUESTOS": "Básicos", "CREDITOS|MULTAS DE TRANSITO": "Básicos", "CREDITOS|OTRAS": "Básicos", "IMPUESTOS|PAGO RENTA": "Básicos", "IMPUESTOS|IVA": "Básicos", "IMPUESTOS|RETEFUENTE": "Básicos", "IMPUESTOS|OTRO": "Básicos", "HIJOS|COLEGIO MAFE": "Básicos", "HIJOS|TRANSPORTE": "Básicos", "HIJOS|MESADA MAFE": "Básicos", "HIJOS|CUADERNOS/LIBROS": "Básicos", "HIJOS|VESTURIO/CALSADO": "Básicos", "HIJOS|ZORAIDA": "Básicos", "HIJOS|MAFE EXTRA": "Calidad de vida", "HIJOS|ALDEMAR": "Básicos", "HIJOS|DANI": "Básicos", "HIJOS|EXTRAS ALEJO": "Calidad de vida", "CARRO|MANTENIMIENTO CARRO": "Básicos", "CARRO|ASEO CARRO": "Calidad de vida", "CARRO|IMPUESTO RODAMIENTO CARRO": "Básicos", "CARRO|PARQUEADERO CARRO": "Básicos", "CARRO|SOAT CARRO": "Básicos", "CARRO|COMBUSTIBLE CARRO": "Básicos", "CARRO|OTROS/IMPREVISTOS/MULTAS/PARQUEO SUELTO": "Básicos", "CARRO|TECNO CARRO": "Básicos", "CARRO|BUSES": "Básicos", "CARRO|TAXIS": "Calidad de vida", "CARRO|PARQUEO DIARIO": "Básicos", "MOTO|MANTENIMIENTO MOTO": "Básicos", "MOTO|ASEO MOTO": "Calidad de vida", "MOTO|IMPUESTO RODAMIENTO MOTO": "Básicos", "MOTO|PARQUEADERO MOTO": "Básicos", "MOTO|SOAT MOTO": "Básicos", "MOTO|COMBUSTIBLE MOTO": "Básicos", "MOTO|OTROS/IMPREVISTOS/MULTAS/PARQUEO SUELTO": "Básicos", "MOTO|TECNOMECANICA MOTO": "Básicos", "MOTO|DIDI PICAP": "Calidad de vida", "MOTO|PARQUEO DIARIO": "Básicos", "GUSTOS|VESTUARIO/CALZADO": "Calidad de vida", "GUSTOS|PELUQUERIA/MAQUILLAJE": "Calidad de vida", "GUSTOS|SOCIAL/RUMBA/DIVERSION": "Estilo de vida", "GUSTOS|RESTAURANTE": "Estilo de vida", "GUSTOS|GASTOS HORMIGA": "Caprichosos", "GUSTOS|REGALOS": "Estilo de vida", "GUSTOS|HOBBY/DEPORTES/LIBROS": "Calidad de vida", "GUSTOS|SUSCRIPCION REVISTAS/PERIODICOS": "Estilo de vida", "GUSTOS|VACACIONES FAMILIARES": "Estilo de vida", "GUSTOS|ENTRETENIMIENTO (CINE-TEATRO)": "Estilo de vida", "GUSTOS|PASEOS": "Estilo de vida", "GUSTOS|LUJOS": "Caprichosos"};
 const d=ss.getSheetByName('Datos');
 posicionesAltium24_().forEach(p=>{
  const cat=claveAltium24_(d.getRange(p.r,p.c).getValue()),v=d.getRange(p.r+1,p.c,20,3).getValues();
  const out=v.map(row=>{const actual=String(row[1]||'').trim();if(actual||!row[0])return [row[1]];return [propuesta[cat+'|'+claveAltium24_(row[0])]||''];});
  d.getRange(p.r+1,p.c+1,20,1).setValues(out);
 });
 props.setProperty('ALTIUM24_PROPUESTA_PRIORIDADES','1');
}

function separarCategoriasAltium24_(ss){
 const props=PropertiesService.getDocumentProperties();if(props.getProperty('ALTIUM24_SEPARADORES'))return;
 const d=ss.getSheetByName('Datos');
 [13,10,7,4].forEach(c=>d.insertColumnBefore(c));
 [4,8,12,16].forEach(c=>{d.setColumnWidth(c,24);d.getRange(1,c,d.getMaxRows(),1).clearContent().clearDataValidations().clearFormat().setBackground('#ffffff');});
 props.setProperty('ALTIUM24_SEPARADORES','1');
}

function configurarControlAltium24_(ss){
 const props=PropertiesService.getDocumentProperties();if(props.getProperty('ALTIUM24_CONTROL'))return;
 const d=ss.getSheetByName('Datos'),t=hojaGastosAltium25_(ss);
 [20,16,12,8,4].forEach(c=>d.insertColumnBefore(c));
 const regla=SpreadsheetApp.newDataValidation().requireValueInList(['Mantener','Reducir','Eliminar'],true).setAllowInvalid(false).build();
 posicionesAltium24_().forEach(p=>{
  d.getRange(p.r,p.c+3).setValue('Acción de control').setBackground('#185b4a').setFontColor('#ffffff').setFontWeight('bold').setWrap(true);
  d.getRange(p.r+1,p.c+3,20,1).setDataValidation(regla).setBackground('#fff8df').setFontWeight('normal');
 });
 [4,9,14,19,24].forEach(c=>d.setColumnWidth(c,165));
 [5,10,15,20].forEach(c=>d.setColumnWidth(c,24));
 if(t.getMaxColumns()<17)t.insertColumnAfter(t.getMaxColumns());
 t.getRange('Q1').setValue('Acción de control (opcional)').setBackground('#f4cccc').setFontWeight('bold').setWrap(true).setNote('Si esta vacia, Altium usa la accion de Datos. Si eliges una opcion, se aplica a este movimiento.');
 t.getRange(2,17,t.getMaxRows()-1,1).setDataValidation(regla);t.setColumnWidth(17,205);
 props.setProperty('ALTIUM24_CONTROL','1');
}

function reordenarColumnasDatos24_(ss){
 const props=PropertiesService.getDocumentProperties();if(props.getProperty('ALTIUM24_ORDEN_PRIORIDAD_MONTO'))return;
 const d=ss.getSheetByName('Datos');
 posicionesAltium24_().slice(0,5).forEach(p=>d.moveColumns(d.getRange(1,p.c+2,d.getMaxRows(),1),p.c+1));
 props.setProperty('ALTIUM24_ORDEN_PRIORIDAD_MONTO','1');
}

function hojaGastosAltium25_(ss){return ss.getSheetByName('Gastos')||ss.getSheetByName('Transaccional');}
