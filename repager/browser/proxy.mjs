// Local forward proxy. Every request/tunnel gets one all-address DNS lookup;
// only its numeric validated result reaches net.connect (no second DNS lookup).
import http from 'node:http';
import net from 'node:net';
import dnsDefault from 'node:dns';
import utils from './adapter-utils.js';

export async function createProxy({dns=dnsDefault.promises, connect=net.connect, denyAll=false,
  maxRequests=600, maxSockets=64, maxBytes=32*1024*1024, timeoutMs=15000, lifetimeMs=90000}={}) {
  const sockets=new Set();
  const stats={requests:0,denied:0,bytes:0,dials:0};
  let closed=false;
  function track(socket) {
    if (closed || sockets.size>=maxSockets) {socket.destroy();return socket;}
    sockets.add(socket);
    socket.on('close',()=>sockets.delete(socket));
    socket.on('error',()=>{});
    socket.setTimeout(timeoutMs,()=>socket.destroy());
    socket.on('data',data=>{stats.bytes+=data.length;if(stats.bytes>maxBytes) for(const s of sockets)s.destroy();});
    const timer=setTimeout(()=>socket.destroy(),lifetimeMs);timer.unref();socket.on('close',()=>clearTimeout(timer));
    return socket;
  }
  async function pin(url) {
    if (closed || denyAll || ++stats.requests>maxRequests || stats.bytes>maxBytes) throw Error('proxy budget');
    const parsed=utils.parseHttpUrl(url);
    let timer;
    try {
      const host=await Promise.race([utils.resolveHostToPublic(parsed.hostname,{dns}),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('DNS timeout')),timeoutMs);})]);
      if(closed) throw Error('closed');
      return {parsed,host};
    } finally {clearTimeout(timer);}
  }
  const server=http.createServer({maxHeaderSize:16384},async(req,res)=>{
    let upstream;
    try {
      if (!['GET','HEAD'].includes(req.method) || req.headers.upgrade || req.headers['transfer-encoding'] || Number(req.headers['content-length']||0)!==0) throw Error('method/body');
      const {parsed,host}=await pin(req.url);
      if(parsed.protocol!=='http:') throw Error('HTTPS requires CONNECT');
      const headers={host:parsed.host,connection:'close'};
      // Small allowlist, no proxy auth, credentials, hop-by-hop or caller Host.
      for(const key of ['accept','accept-language','accept-encoding','user-agent','range','if-none-match','if-modified-since']) if(req.headers[key])headers[key]=req.headers[key];
      const agent=new http.Agent({keepAlive:false,maxSockets:1});
      agent.createConnection=()=>{stats.dials++;return track(connect({host,port:80,family:net.isIP(host)}));};
      upstream=http.request({hostname:host,port:80,method:req.method,path:parsed.pathname+parsed.search,headers,agent},response=>{
        const responseHeaders={...response.headers};
        delete responseHeaders['proxy-authenticate'];delete responseHeaders['set-cookie'];
        res.writeHead(response.statusCode,responseHeaders);
        response.on('error',()=>res.destroy());response.pipe(res);
      });
      upstream.setTimeout(timeoutMs,()=>upstream.destroy());
      upstream.on('error',()=>{if(!res.headersSent)res.writeHead(502);res.end();});
      res.on('close',()=>{upstream.destroy();agent.destroy();});upstream.end();
    } catch {stats.denied++;if(!res.headersSent)res.writeHead(403);res.end();upstream?.destroy();}
  });
  server.on('connection',track);
  server.on('upgrade',(req,socket)=>{stats.denied++;socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n');});
  server.on('connect',async(req,client,head)=>{
    try {
      if(!/^(\[[^\]]+\]|[^:]+):443$/.test(req.url) || head.length)throw Error('CONNECT authority');
      const {host}=await pin(`https://${req.url}/`);
      stats.dials++;
      const upstream=track(connect({host,port:443,family:net.isIP(host)}));
      upstream.once('connect',()=>{
        if(client.destroyed){upstream.destroy();return;}
        client.write('HTTP/1.1 200 Connection Established\r\n\r\n');
        upstream.pipe(client);client.pipe(upstream);
      });
      upstream.on('error',()=>client.destroy());
      client.on('error',()=>upstream.destroy());client.on('close',()=>upstream.destroy());upstream.on('close',()=>client.destroy());
    } catch {stats.denied++;client.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n');}
  });
  server.headersTimeout=timeoutMs;server.requestTimeout=timeoutMs;server.keepAliveTimeout=1000;
  server.on('clientError',(_,socket)=>socket.destroy());
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  return {port:server.address().port,stats,async close(){closed=true;for(const s of sockets)s.destroy();await new Promise(resolve=>server.close(resolve));}};
}
