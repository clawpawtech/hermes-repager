'use strict';
// Independent implementation. Public unicast only, conservatively excludes
// IPv6 transition mechanisms and whole special-purpose allocations.
const ipaddr = require('ipaddr.js');
const net = require('node:net');
const MAX_INPUT_LENGTH = 2048;
const MAX_HTML_BYTES = 128 * 1024;
function isPublicIp(value) {
  if (!net.isIP(value)) return false;
  const ip = ipaddr.parse(value);
  if (ip.range() !== 'unicast') return false;
  if (ip.kind() === 'ipv4') return !ip.match(ipaddr.parse('192.0.0.0'),24);
  return ip.match(ipaddr.parse('2000::'),3) &&
    !ip.match(ipaddr.parse('2001::'),23) && !ip.match(ipaddr.parse('2002::'),16) &&
    !ip.match(ipaddr.parse('3fff::'),20);
}
function parseHttpUrl(value) {
  if (typeof value !== 'string' || !value || Buffer.byteLength(value)>MAX_INPUT_LENGTH || /[\x00-\x20\x7f\\]/.test(value) || /%(?:0[0-9a-f]|1[0-9a-f]|7f)/i.test(value)) throw Error('unsafe URL');
  const match = /^(https?):\/\/([^/?#]+)(?:[/?#]|$)/i.exec(value);
  if (!match || /[@%]/.test(match[2])) throw Error('unsafe URL authority');
  const url = new URL(value);
  const host = url.hostname.replace(/^\[|\]$/g,'');
  const authority = /^(\[[^\]]+\]|[^:]+)(?::(\d+))?$/.exec(match[2]);
  if (!authority || (authority[2] && authority[2] !== (url.protocol==='https:'?'443':'80'))) throw Error('nonstandard port');
  const rawHost = authority[1].replace(/^\[|\]$/g,'');
  // WHATWG accepts octal, hex and short IPv4. Reject rather than normalize.
  if (net.isIP(host)===4 && rawHost!==host) throw Error('noncanonical IPv4');
  if (net.isIP(host)) {if (!isPublicIp(host)) throw Error('nonpublic IP');}
  else if (!/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{0,62}$/i.test(host)) throw Error('invalid hostname');
  return url;
}
function isValidHttpUrl(value) {try {parseHttpUrl(value);return true;}catch{return false;}}
async function resolveHostToPublic(hostname, {dns=require('node:dns').promises}={}) {
  const host=hostname.replace(/^\[|\]$/g,'');
  if (net.isIP(host)) {if (!isPublicIp(host)) throw Error('nonpublic IP');return host;}
  const records=await dns.lookup(host,{all:true,verbatim:true});
  if (!records.length || records.some(record=>!isPublicIp(record.address))) throw Error('nonpublic DNS answer');
  return records[0].address;
}
function normalizeHexColor(value) {
  if (typeof value!=='string') return null;
  const s=value.trim().toLowerCase();
  if (/^#[0-9a-f]{6}$/.test(s)) return s;
  const m=/^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)$/.exec(s);
  if (!m || (m[4]!==undefined && Number(m[4])!==1)) return null;
  const rgb=m.slice(1,4).map(Number);
  if (rgb.some(v=>v>255)) return null;
  return '#'+rgb.map(v=>v.toString(16).padStart(2,'0')).join('');
}
function normalizePalette(colors) {return [...new Set(colors.map(normalizeHexColor).filter(Boolean))].slice(0,16);}
module.exports={MAX_INPUT_LENGTH,MAX_HTML_BYTES,isPublicIp,parseHttpUrl,isValidHttpUrl,resolveHostToPublic,normalizeHexColor,normalizePalette};