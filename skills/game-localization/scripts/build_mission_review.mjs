#!/usr/bin/env node
// Export only: no game writes or automatic import of reviewer changes.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL, fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';

const args=process.argv.slice(2);
if (args.includes('--help') || args.length<2) {
  console.log('Usage: node build_mission_review.mjs input.json output.xlsx [--node-modules DIR] [--preview preview.png]');
  process.exit(args.includes('--help') ? 0 : 2);
}
const [inputPath,outputPath,...opts]=args;
const options={};
for(let i=0;i<opts.length;i+=2){
  if(!['--node-modules','--preview'].includes(opts[i]) || !opts[i+1]) throw Error('Unknown or incomplete option: '+opts[i]);
  options[opts[i]]=opts[i+1];
}
const output=path.resolve(outputPath), mappingPath=output+'.mapping.json';
for(const p of [output,mappingPath,options['--preview']].filter(Boolean)){
  try{await fs.access(p);throw Error('Output already exists: '+p);}catch(e){if(e.code!=='ENOENT')throw e;}
}
if(path.resolve(inputPath)===output)throw Error('Input and output must differ');
const data=JSON.parse(await fs.readFile(inputPath,'utf8'));
if(!Array.isArray(data.missions) || !data.missions.length)throw Error('missions must be a nonempty array');
const ids=new Set();
const text=(v,name)=>{if(typeof v!=='string')throw Error(name+' must be a string');return v;};
text(data.baseline,'baseline');
for(const m of data.missions){
  for(const k of ['id','stage','client'])text(m[k],k);
  for(const k of ['advance','reward'])if(m[k]!==null && !(Number.isSafeInteger(m[k])&&m[k]>=0))throw Error(k+' must be a nonnegative integer or null');
  if(!Array.isArray(m.entries)||!m.entries.length)throw Error('Each mission needs entries');
  for(const e of m.entries){
    for(const k of ['uid','category','number','speaker','content'])text(e[k],k);
    if(!e.uid||ids.has(e.uid))throw Error('Missing or duplicate technical UID: '+e.uid);
    ids.add(e.uid);
    if(e.source!==null)text(e.source,'source');
  }
}
let artifact;
if(options['--node-modules']){
  const require=createRequire(path.join(path.resolve(options['--node-modules']),'../_review_resolver.cjs'));
  artifact=await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
}else artifact=await import('@oai/artifact-tool');
const {Workbook,SpreadsheetFile}=artifact;
const here=path.dirname(fileURLToPath(import.meta.url));
const style=JSON.parse(await fs.readFile(path.join(here,'../references/mission-review-format.json'),'utf8'));
const wb=Workbook.create(),s=wb.worksheets.add(style.sheet_name);
const count=data.missions.reduce((n,m)=>n+m.entries.length,0),last=count+1;
const all=s.getRange(`A1:P${last}`);
all.format.font={name:style.font_name,size:style.font_size,color:'#000000'};
all.format.verticalAlignment='center';all.format.horizontalAlignment='center';all.format.wrapText=true;
all.setNumberFormat('@');
for(let c=0;c<16;c++)s.getRangeByIndexes(0,c,last,1).format.columnWidth=style.column_widths[c];
s.getRange('A1:I1').values=[style.headers.slice(0,9)];
s.getRange('A1:I1').format.fill=style.header_fill;
s.getRange('A1:I1').format.font={name:style.font_name,size:style.font_size,bold:true,color:style.header_color};
s.getRange('A1:I1').format.borders={preset:'all',style:'thin',color:style.border_color};
s.mergeCells('J1:P1');s.getRange('J1').values=[[data.source_header??style.headers[9]]];
s.getRange('J1:P1').format.fill=style.source_header_fill;
s.getRange('J1:P1').format.font={name:style.font_name,size:style.font_size,color:style.source_header_color};
s.getRange('J1:P1').format.borders={preset:'outside',style:'thin',color:'#7F7F7F'};
s.getRange('A1:P1').format.rowHeight=style.header_height;
s.freezePanes.freezeRows(style.freeze_rows);
const literal=v=>typeof v==='string'&&v.startsWith('=')?"'"+v:v;
const hash=v=>createHash('sha256').update(v).digest('hex');
function lineCount(v,width){
  return v.split('\n').reduce((n,line)=>n+Math.max(1,Math.ceil([...line].reduce((x,c)=>x+(c.charCodeAt(0)>255?2:1),0)/width)),0);
}
const mapping={profile:style.profile,baseline:data.baseline,source_header:data.source_header??style.headers[9],entries:[]};
let row=2;
for(const [mi,m] of data.missions.entries()){
  const start=row,end=row+m.entries.length-1,block=s.getRange(`A${start}:I${end}`);
  block.format.fill=style.mission_fills[mi%2];
  block.format.borders={preset:'all',style:'thin',color:style.border_color};
  const meta=[m.id,m.stage,m.client,m.advance,m.reward];
  for(let c=0;c<5;c++){
    if(end>start)s.getRangeByIndexes(start-1,c,end-start+1,1).merge();
    s.getCell(start-1,c).values=[[literal(meta[c])]];
  }
  s.getRange(`D${start}:E${end}`).setNumberFormat('0');
  for(const e of m.entries){
    s.getRange(`F${row}:I${row}`).values=[[e.category,e.number,e.speaker,e.content].map(literal)];
    s.getRange(`I${row}`).format.horizontalAlignment='left';
    s.mergeCells(`J${row}:P${row}`);s.getRange(`J${row}`).values=[[literal(e.source??'')]];
    s.getRange(`J${row}:P${row}`).format.horizontalAlignment='left';
    s.getRange(`J${row}:P${row}`).format.borders={left:{style:'thin',color:style.border_color}};
    const lines=Math.max(lineCount(e.content,66),lineCount(e.source??'',56));
    // Allow one extra wrap for mixed Latin/CJK word breaking and font fallback.
    s.getRange(`A${row}:P${row}`).format.rowHeight=Math.max(style.body_min_height,(lines+(lines>1?1:0))*15+8);
    mapping.entries.push({uid:e.uid,row,mission:m.id,category:e.category,number:e.number,speaker:e.speaker,original_content:e.content,source:e.source,source_sha256:e.source===null?null:hash(e.source),locator:e.locator??null});
    row++;
  }
}
console.log((await wb.inspect({kind:'table',range:`${style.sheet_name}!F1:J${Math.min(last,5)}`,tableMaxRows:5,tableMaxCols:5,maxChars:1700})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:10},summary:'formula error scan'})).ndjson);
if(options['--preview']){
  const blob=await wb.render({sheetName:style.sheet_name,range:`A1:P${last}`,scale:1});
  await fs.mkdir(path.dirname(path.resolve(options['--preview'])),{recursive:true});
  await fs.writeFile(options['--preview'],new Uint8Array(await blob.arrayBuffer()),{flag:'wx'});
}
await fs.mkdir(path.dirname(output),{recursive:true});
const xlsx=await SpreadsheetFile.exportXlsx(wb);
// Export to a fresh directory, then commit without overwriting an existing file.
const tmp=await fs.mkdtemp(path.join(path.dirname(output),'.review-export-'));
try {
  const staged=path.join(tmp,'review.xlsx');await xlsx.save(staged);
  await fs.link(staged,output);
} finally {await fs.rm(tmp,{recursive:true,force:true});}
mapping.workbook_sha256=hash(await fs.readFile(output));
await fs.writeFile(mappingPath,JSON.stringify(mapping,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({output,rows:count,missions:data.missions.length,mapping:mappingPath}));
