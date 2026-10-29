import {createServer} from 'node:http';
import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
const root=resolve('dist'),out=resolve(process.env.DATA_DIR||'/data','frames');await mkdir(out,{recursive:true});
const receipt=JSON.parse(await readFile(resolve(root,'build-receipt.json'),'utf8'));
const json=(res,status,value)=>{res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(value));};
createServer(async(req,res)=>{try{
 const url=new URL(req.url,'http://localhost');
 if(url.pathname==='/health')return json(res,200,{status:'ok',stateless:true,output:'/data/frames',recipe:receipt.recipe,versions:receipt.versions});
 if(url.pathname==='/api/frames'&&req.method==='GET')return json(res,200,{files:(await readdir(out)).filter(x=>x.endsWith('.json'))});
 if(url.pathname==='/api/frames'&&req.method==='POST'){
  if(req.headers.origin&&!['http://localhost:8872','http://127.0.0.1:8872'].includes(req.headers.origin))return json(res,403,{error:'origin'});
  let size=0;const chunks=[];for await(const chunk of req){size+=chunk.length;if(size>8*1024*1024)return json(res,413,{error:'frame too large'});chunks.push(chunk);}
  const body=JSON.parse(Buffer.concat(chunks).toString('utf8'));
  if(!Number.isInteger(body.frame)||body.frame<0||body.frame>1000||typeof body.png!=='string'||!body.png.startsWith('data:image/png;base64,'))return json(res,400,{error:'invalid frame'});
  const bytes=Buffer.from(body.png.slice(22),'base64');if(bytes.subarray(0,8).toString('hex')!=='89504e470d0a1a0a')return json(res,400,{error:'invalid PNG'});
  const id=`frame-${body.frame}-${randomUUID()}`;const metadata={id,frame:body.frame,bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex'),createdAt:new Date().toISOString(),engine:receipt,geometry:body.geometry||[],scope:'Actual Motion Canvas Stage canvas PNG supplied by local browser; no video encoding claim'};
  await writeFile(resolve(out,id+'.png'),bytes,{flag:'wx'});await writeFile(resolve(out,id+'.json'),JSON.stringify(metadata,null,2),{flag:'wx'});
  return json(res,201,{...metadata,url:'/frames/'+id+'.png'});
 }
 let file;if(url.pathname.startsWith('/frames/')){const name=url.pathname.slice(8);if(!/^frame-\d+-[a-f0-9-]+\.(png|json)$/.test(name))return json(res,404,{error:'missing'});file=resolve(out,name);}else{file=resolve(root,'.'+(url.pathname==='/'?'/index.html':decodeURIComponent(url.pathname)));if(!file.startsWith(root+'/'))return json(res,404,{error:'missing'});}
 const bytes=await readFile(file);res.writeHead(200,{'Content-Type':({'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json','.png':'image/png'})[extname(file)]||'application/octet-stream','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(bytes);
}catch(error){json(res,error.code==='ENOENT'?404:500,{error:error.code==='ENOENT'?'missing':error.message});}}).listen(Number(process.env.PORT||8862),'0.0.0.0');
