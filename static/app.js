const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
let state={};

async function api(url,opt={}){
  const r=await fetch(url,opt);
  const d=await r.json();
  if(!r.ok) throw Error(d.detail||"Request failed");
  return d;
}
function toast(msg,good=true){
  const t=$("toast");t.textContent=msg;t.className="toast show";
  setTimeout(()=>t.className="toast",3500);
}
function openView(name){
  document.querySelectorAll(".view").forEach(v=>v.classList.remove("active"));
  document.querySelectorAll(".nav").forEach(v=>v.classList.remove("active"));
  $(name).classList.add("active");
  const b=document.querySelector(`[data-view="${name}"]`);if(b)b.classList.add("active");
  if(name==="resources")renderResources();
  if(name==="topology")renderTopology();
}
document.querySelectorAll(".nav").forEach(b=>b.onclick=()=>openView(b.dataset.view));

function arr(key){const v=state[key];return Array.isArray(v)?v:Object.values(v||{});}
function count(...keys){for(const k of keys){if(k in state){const v=state[k];return Array.isArray(v)?v.length:Object.keys(v||{}).length}}return 0;}

function resourceEntries(key){
  const value=state[key];
  if(Array.isArray(value)) return value.map((v,i)=>[String(v?.name||v?.id||i),v]);
  return Object.entries(value||{});
}
function statusState(value, expected=[]){
  const s=String(value??"").toLowerCase();
  if(!s) return {kind:"good",label:"Healthy"};
  if(expected.some(x=>s===String(x).toLowerCase())) return {kind:"good",label:value};
  if(["failed","error","down","disconnected","degraded","unavailable"].some(x=>s.includes(x))) return {kind:"bad",label:value};
  if(["provisioning","pending","updating","creating","unknown"].some(x=>s.includes(x))) return {kind:"warn",label:value};
  return {kind:"good",label:value};
}
function healthResource(name, type, status, detail){
  const st=statusState(status,["Succeeded","Established","Connected","Provisioned","Active","Healthy"]);
  return {name,type,status:st.label,kind:st.kind,detail};
}
function buildHealthGroups(){
  const groups=[{title:"Azure network",items:[]},{title:"Routing",items:[]},{title:"Hybrid connectivity",items:[]},{title:"Advertised routes",items:[]}];
  resourceEntries("vnets").forEach(([name,v])=>groups[0].items.push(healthResource(name,"VNet","Healthy",v.address_prefix||"")));
  resourceEntries("route_servers").forEach(([name,v])=>groups[1].items.push(healthResource(name,"Route Server",v.state||"Succeeded",`ASN ${v.asn??"-"}`)));
  resourceEntries("nvas").forEach(([name,v])=>groups[1].items.push(healthResource(name,"NVA",v.state||"Healthy",`${v.private_ip||v.ip||"-"} · AS${v.asn??"-"}`)));
  resourceEntries("bgp_peers").forEach(([name,v])=>groups[1].items.push(healthResource(name,"BGP peer",v.state||"Established",`AS${v.local_asn??"-"} → AS${v.remote_asn??"-"}`)));
  resourceEntries("vpn_gateways").forEach(([name,v])=>groups[2].items.push(healthResource(name,"VPN Gateway",v.state||"Succeeded",`ASN ${v.asn??"-"}`)));
  resourceEntries("vpn_connections").forEach(([name,v])=>groups[2].items.push(healthResource(name,"VPN connection",v.state||"Connected",v.bgp?"IPsec · BGP":"IPsec")));
  resourceEntries("expressroute_circuits").forEach(([name,v])=>groups[2].items.push(healthResource(name,"ExpressRoute",v.state||"Provisioned",`${v.bandwidth||"-"} · ${v.location||""}`)));
  resourceEntries("expressroute_peerings").forEach(([name,v])=>groups[2].items.push(healthResource(name,"ER peering",v.state||"Established",`ASN ${v.peer_asn??"-"} · ${v.peer_ip||"-"}`)));
  resourceEntries("nva_routes").forEach(([i,v])=>groups[3].items.push(healthResource(v.prefix||String(i),"NVA route","Advertised",`NVA ${v.nva||"-"} · next hop ${v.next_hop||"-"}`)));
  resourceEntries("expressroute_routes").forEach(([i,v])=>groups[3].items.push(healthResource(v.prefix||String(i),"ER route","Advertised",`ER ${v.circuit||"-"} · ${v.peering_type||"-"}`)));
  resourceEntries("bgp_routes").forEach(([i,v])=>groups[3].items.push(healthResource(v.prefix||String(i),"BGP route","Advertised",`Peer ${v.peer||v.bgp_peer||"-"}`)));
  return groups.filter(g=>g.items.length);
}
function renderHealth(){
  const groups=buildHealthGroups();
  const items=groups.flatMap(g=>g.items);
  const bad=items.filter(x=>x.kind==="bad").length;
  const warn=items.filter(x=>x.kind==="warn").length;
  const summary=bad?{cls:"bad",text:`● ${bad} ISSUE${bad===1?"":"S"}`} : warn?{cls:"warn",text:`● ${warn} CHECK${warn===1?"":"S"}`} : {cls:"good",text:"● ALL SYSTEMS OPERATIONAL"};
  const hs=$("healthSummary"); if(hs){hs.className=`health-summary ${summary.cls}`;hs.textContent=summary.text}
  const root=$("healthMonitor"); if(!root)return;
  root.innerHTML=groups.map(g=>`<div class="health-group"><div class="health-group-title">${esc(g.title)}</div>${g.items.map(x=>`<div class="health-row"><span class="status-dot ${x.kind}"></span><div class="health-main"><strong>${esc(x.name)}</strong><small>${esc(x.type)}${x.detail?` · ${esc(x.detail)}`:""}</small></div><span class="health-state ${x.kind}">${esc(x.status)}</span></div>`).join("")}</div>`).join("");
}

function renderCards(){
  const data=[
    ["Resource Groups",count("resource_groups","groups")],
    ["VNets",count("vnets")],
    ["Subnets",Object.values(state.vnets||{}).reduce((n,v)=>n+Object.keys(v.subnets||{}).length,0)],
    ["VPN Gateways",count("vpn_gateways")],
    ["BGP Peers",count("bgp_peers")],
    ["ExpressRoute",count("expressroute_circuits")]
  ];
  $("cards").innerHTML=data.map(x=>`<div class="card"><div class="label">${x[0]}</div><div class="num">${x[1]}</div></div>`).join("");
}

function topologyModel(){
  const nodes=new Map(), edges=[];
  const add=(id,type,title,subtitle,extra={})=>{if(!nodes.has(id))nodes.set(id,{id,type,title,subtitle,...extra});return nodes.get(id)};
  const vnets=state.vnets||{};
  const rs=state.route_servers||{};
  const nvas=state.nvas||{};
  const vpns=state.vpn_gateways||{};
  const locals=state.local_gateways||{};
  const er=state.expressroute_circuits||{};

  Object.entries(vnets).forEach(([name,v])=>add(`vnet:${name}`,"vnet",name,v.address_prefix||"",{subnets:Object.values(v.subnets||{})}));
  Object.entries(rs).forEach(([name,v])=>add(`rs:${name}`,"route-server",name,`ASN ${v.asn??"-"}`,{vnet:v.vnet,subnet:v.subnet}));
  Object.entries(nvas).forEach(([name,v])=>add(`nva:${name}`,"nva",name,`${v.private_ip||v.ip||"-"} · AS${v.asn??"-"}`,{vnet:v.vnet,subnet:v.subnet}));
  Object.entries(vpns).forEach(([name,v])=>add(`vpn:${name}`,"vpn",name,`ASN ${v.asn??"-"}`,{vnet:v.vnet}));
  Object.entries(locals).forEach(([name,v])=>add(`local:${name}`,"external",name,`${v.ip_address||"-"} · AS${v.asn??"-"}`));
  Object.entries(er).forEach(([name,v])=>add(`er:${name}`,"expressroute",name,`${v.bandwidth||"-"} · ${v.location||""}`));

  // Real VNet peering relationships.
  arr("peerings").forEach(p=>{
    if(vnets[p.source_vnet]&&vnets[p.remote_vnet]) edges.push({a:`vnet:${p.source_vnet}`,b:`vnet:${p.remote_vnet}`,label:"VNet peering",kind:"peering"});
  });
  // Resource placement and BGP relationships.
  Object.entries(rs).forEach(([name,v])=>{if(vnets[v.vnet])edges.push({a:`vnet:${v.vnet}`,b:`rs:${name}`,label:v.subnet?`Route Server · ${v.subnet}`:"Route Server",kind:"placement"})});
  Object.entries(nvas).forEach(([name,v])=>{
    if(vnets[v.vnet])edges.push({a:`vnet:${v.vnet}`,b:`nva:${name}`,label:v.subnet?`NVA · ${v.subnet}`:"NVA",kind:"placement"});
    if(v.route_server && rs[v.route_server])edges.push({a:`rs:${v.route_server}`,b:`nva:${name}`,label:"BGP peer",kind:"bgp"});
  });
  Object.entries(vpns).forEach(([name,v])=>{if(vnets[v.vnet])edges.push({a:`vnet:${v.vnet}`,b:`vpn:${name}`,label:"VPN Gateway",kind:"vpn"})});
  Object.entries(state.vpn_connections||{}).forEach((c)=>{
    const v=`vpn:${c.vpn_gateway}`,l=`local:${c.local_gateway}`;
    if(nodes.has(v)&&nodes.has(l))edges.push({a:v,b:l,label:c.bgp?"IPsec · BGP":"IPsec",kind:"vpn"});
  });
  // BGP peers connect the named local/remote devices when they exist.
  Object.values(state.bgp_peers||{}).forEach(p=>{
    const local=resolveDeviceId(p.local_device,nodes), remote=resolveDeviceId(p.remote_device,nodes);
    if(local&&remote)edges.push({a:local,b:remote,label:`BGP · AS${p.local_asn} ↔ AS${p.remote_asn}`,kind:"bgp"});
  });
  // ExpressRoute is related to a VNet through an active coexistence profile.
  Object.values(state.hybrid_coexistence||{}).forEach(h=>{
    if(vnets[h.vnet]&&er[h.expressroute_circuit])edges.push({a:`vnet:${h.vnet}`,b:`er:${h.expressroute_circuit}`,label:"ExpressRoute",kind:"expressroute"});
    if(vnets[h.vnet]&&vpns[h.vpn_gateway])edges.push({a:`vnet:${h.vnet}`,b:`vpn:${h.vpn_gateway}`,label:"Coexistence",kind:"vpn"});
    if(rs[h.route_server]&&nvas[h.nva])edges.push({a:`rs:${h.route_server}`,b:`nva:${h.nva}`,label:"Coexistence / BGP",kind:"bgp"});
  });
  // ER private peering terminates at an external peer. Create one node per circuit.
  Object.values(state.expressroute_peerings||{}).forEach(p=>{
    if(er[p.circuit]){
      const id=`erpeer:${p.circuit}:${p.peering_type}`;
      add(id,"external",`${p.circuit} · ${p.peering_type}`,`Peer ASN ${p.peer_asn??"-"} · ${p.peer_ip||"-"}`);
      edges.push({a:`er:${p.circuit}`,b:id,label:"Private peering",kind:"expressroute"});
    }
  });
  // Advertised route targets are shown as route/prefix nodes instead of pretending they are devices.
  Object.values(state.nva_routes||[]).forEach(r=>{
    const id=`prefix:nva:${r.nva}:${r.prefix}`;add(id,"route",r.prefix,`NVA ${r.nva} · next hop ${r.next_hop||"-"}`);
    if(nodes.has(`nva:${r.nva}`))edges.push({a:`nva:${r.nva}`,b:id,label:"Advertised route",kind:"route"});
  });
  Object.values(state.expressroute_routes||[]).forEach(r=>{
    const id=`prefix:er:${r.circuit}:${r.prefix}`;add(id,"route",r.prefix,`ER ${r.circuit} · ${r.peering_type||"-"}`);
    if(nodes.has(`er:${r.circuit}`))edges.push({a:`er:${r.circuit}`,b:id,label:"Advertised route",kind:"route"});
  });
  Object.values(state.bgp_routes||[]).forEach(r=>{
    const peer=r.peer||r.bgp_peer||"BGP";const id=`prefix:bgp:${peer}:${r.prefix}`;add(id,"route",r.prefix,`BGP peer ${peer}`);
    const peerObj=state.bgp_peers?.[peer];
    if(peerObj){const d=resolveDeviceId(peerObj.local_device,nodes);if(d)edges.push({a:d,b:id,label:"BGP route",kind:"route"})}
  });
  return {nodes:[...nodes.values()],edges:dedupeEdges(edges)};
}
function resolveDeviceId(name,nodes){
  if(!name)return null;
  const candidates=[`vnet:${name}`,`vpn:${name}`,`nva:${name}`,`rs:${name}`,`er:${name}`,`local:${name}`];
  return candidates.find(x=>nodes.has(x))||null;
}
function dedupeEdges(edges){const seen=new Set();return edges.filter(e=>{const k=[e.a,e.b,e.label].sort().join("|");if(seen.has(k))return false;seen.add(k);return true})}
function nodeIcon(type){return ({vnet:"▦", "route-server":"◈",nva:"⬢",vpn:"🔐",expressroute:"⚡",external:"◎",route:"↗"}[type]||"•")}
function nodeClass(type){return `topo-node topo-${type}`}

function topologyStorageKey(id){return `azure-network-lab.topology.${id}`}
function loadTopologyPositions(model,compact=false){
  const groups={vnet:[],"route-server":[],nva:[],vpn:[],expressroute:[],external:[],route:[]};
  model.nodes.forEach(n=>{if(groups[n.type])groups[n.type].push(n)});
  const cols=[groups.vnet,groups["route-server"].concat(groups.nva),groups.vpn.concat(groups.expressroute),groups.external.concat(groups.route)];
  const width=compact?1050:1450;
  const colX=[40,Math.round(width*.31),Math.round(width*.59),Math.round(width*.80)];
  const positions=new Map();
  cols.forEach((items,ci)=>items.forEach((n,i)=>{
    let p;
    try{p=JSON.parse(localStorage.getItem(topologyStorageKey(n.id))||"null")}catch(_){p=null}
    positions.set(n.id,{x:Number.isFinite(p?.x)?p.x:colX[ci],y:Number.isFinite(p?.y)?p.y:35+i*150,w:250,h:110});
  }));
  const maxY=Math.max(360,...[...positions.values()].map(p=>p.y+p.h));
  return {positions,width,height:Math.max(520,maxY+80)};
}
function edgeGeometry(a,b){
  const ax=a.x+a.w/2, ay=a.y+a.h/2, bx=b.x+b.w/2, by=b.y+b.h/2;
  const dx=bx-ax, dy=by-ay;
  if(Math.abs(dx)<.001 && Math.abs(dy)<.001)return {x1:ax,y1:ay,x2:bx,y2:by,lx:ax,ly:ay};
  const tx=(a.w/2)/Math.max(Math.abs(dx),.001), ty=(a.h/2)/Math.max(Math.abs(dy),.001);
  const t1=Math.min(tx,ty);
  const ux=(b.w/2)/Math.max(Math.abs(dx),.001), uy=(b.h/2)/Math.max(Math.abs(dy),.001);
  const t2=Math.min(ux,uy);
  const x1=ax+dx*t1, y1=ay+dy*t1, x2=bx-dx*t2, y2=by-dy*t2;
  return {x1,y1,x2,y2,lx:(x1+x2)/2,ly:(y1+y2)/2};
}
function topologyMarkup(compact=false){
  const model=topologyModel();
  if(!model.nodes.length)return `<div class="topology-empty"><div><strong>Blank lab</strong><p>Create resources from Build Lab.</p></div></div>`;
  const {positions,width,height}=loadTopologyPositions(model,compact);
  const svg=[];
  model.edges.forEach((e,i)=>{
    const a=positions.get(e.a),b=positions.get(e.b);if(!a||!b)return;
    const g=edgeGeometry(a,b);
    const labelW=Math.max(88,Math.min(180,(e.label||'').length*6.2+22));
    svg.push(`<line class="edge edge-${e.kind}" data-a="${esc(e.a)}" data-b="${esc(e.b)}" x1="${g.x1}" y1="${g.y1}" x2="${g.x2}" y2="${g.y2}" marker-end="url(#arrow-${e.kind})"></line>`);
    svg.push(`<g class="edge-label" data-a="${esc(e.a)}" data-b="${esc(e.b)}"><rect x="${g.lx-labelW/2}" y="${g.ly-10}" width="${labelW}" height="20" rx="4"></rect><text x="${g.lx}" y="${g.ly+4}">${esc(e.label)}</text></g>`);
  });
  const nodes=model.nodes.map(n=>{
    const p=positions.get(n.id);if(!p)return "";
    const subnets=n.type==="vnet"?(n.subnets||[]).map(s=>`<span class="subnet-chip">${esc(s.name||"")} · ${esc(s.address_prefix||"")}</span>`).join(""):"";
    return `<div class="${nodeClass(n.type)} topo-draggable" data-node="${esc(n.id)}" title="Drag to reposition · double-click to reset" style="left:${p.x}px;top:${p.y}px;width:${p.w}px;min-height:${p.h}px"><div class="topo-title"><span class="topo-icon">${nodeIcon(n.type)}</span><strong>${esc(n.title)}</strong></div><small>${esc(n.subtitle)}</small>${subnets?`<div class="subnet-list">${subnets}</div>`:""}${n.subnet&&n.type!=="route-server"?`<div class="topo-meta">Subnet: ${esc(n.subnet)}</div>`:""}${n.vnet&&n.type!=="vnet"?`<div class="topo-meta">VNet: ${esc(n.vnet)}</div>`:""}</div>`;
  }).join("");
  return `<div class="topology-graph" style="width:${width}px;height:${height}px"><svg class="topology-svg" viewBox="0 0 ${width} ${height}" aria-hidden="true"><defs>
    ${["peering","placement","bgp","vpn","expressroute","route"].map(k=>`<marker id="arrow-${k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" class="marker-${k}"></path></marker>`).join("")}
  </defs>${svg.join("")}</svg>${nodes}</div>`;
}
function updateTopologyEdges(graph){
  const nodes=new Map([...graph.querySelectorAll(".topo-node")].map(n=>[n.dataset.node,{x:parseFloat(n.style.left)||0,y:parseFloat(n.style.top)||0,w:n.offsetWidth,h:n.offsetHeight}]));
  graph.querySelectorAll(".edge").forEach(line=>{
    const a=nodes.get(line.dataset.a),b=nodes.get(line.dataset.b);if(!a||!b)return;
    const g=edgeGeometry(a,b);line.setAttribute("x1",g.x1);line.setAttribute("y1",g.y1);line.setAttribute("x2",g.x2);line.setAttribute("y2",g.y2);
  });
  graph.querySelectorAll(".edge-label").forEach(label=>{
    const a=nodes.get(label.dataset.a),b=nodes.get(label.dataset.b);if(!a||!b)return;
    const g=edgeGeometry(a,b);const rect=label.querySelector("rect"),text=label.querySelector("text");
    const w=parseFloat(rect.getAttribute("width"))||110;
    rect.setAttribute("x",g.lx-w/2);rect.setAttribute("y",g.ly-10);text.setAttribute("x",g.lx);text.setAttribute("y",g.ly+4);
  });
}
function bindTopologyDrag(root){
  const graph=root.querySelector(".topology-graph");if(!graph)return;
  if(root.closest(".mini-topology"))return;
  let drag=null;
  graph.querySelectorAll(".topo-draggable").forEach(node=>{
    node.addEventListener("dblclick",()=>{localStorage.removeItem(topologyStorageKey(node.dataset.node));renderTopology()});
    node.addEventListener("pointerdown",e=>{
      if(e.button!==0)return;
      e.preventDefault();node.setPointerCapture?.(e.pointerId);
      const startX=e.clientX,startY=e.clientY,startLeft=parseFloat(node.style.left)||0,startTop=parseFloat(node.style.top)||0;
      drag={node,startX,startY,startLeft,startTop};node.classList.add("dragging");
    });
    node.addEventListener("pointermove",e=>{
      if(!drag||drag.node!==node)return;
      const scale=graph.clientWidth/parseFloat(graph.style.width||graph.clientWidth);
      const nx=Math.max(10,drag.startLeft+(e.clientX-drag.startX)/Math.max(scale,.1));
      const ny=Math.max(10,drag.startTop+(e.clientY-drag.startY)/Math.max(scale,.1));
      node.style.left=`${nx}px`;node.style.top=`${ny}px`;updateTopologyEdges(graph);
    });
    node.addEventListener("pointerup",()=>{
      if(!drag||drag.node!==node)return;
      const x=parseFloat(node.style.left)||0,y=parseFloat(node.style.top)||0;
      localStorage.setItem(topologyStorageKey(node.dataset.node),JSON.stringify({x,y}));
      node.classList.remove("dragging");drag=null;
    });
    node.addEventListener("pointercancel",()=>{node.classList.remove("dragging");drag=null});
  });
}
function renderTopology(){
  const full=topologyMarkup(false);$("topologyCanvas").innerHTML=full;bindTopologyDrag($("topologyCanvas"));
  const fullGraph=$("topologyCanvas").querySelector(".topology-graph");if(fullGraph)updateTopologyEdges(fullGraph);
  const mini=topologyMarkup(true);$("miniTopology").innerHTML=`<div class="mini-scroll">${mini}</div>`;
}

function renderResources(){
  const targets=["vnet","vpn","bgp","expressroute","routes","route-server","nva","route-server-peers","nva-routes","coexistence"];
  $("resourceTables").innerHTML=targets.map(t=>`<article class="panel resource-block"><div class="panel-head"><h2>${t}</h2><button class="ghost" onclick="loadShow('${t}', 'res-${t}')">Refresh</button></div><pre id="res-${t}">Click Refresh</pre></article>`).join("");
}
async function loadShow(t,target="showOutput"){try{$(target).textContent=(await api("/api/show/"+t)).output}catch(e){$(target).textContent="[FAIL] "+e.message}}

function formSpec(type){
 const specs={
  group:["Resource Group",[["name","Name","rg-weu"],["location","Location","westeurope"]]],
  vnet:["Virtual Network",[["resource-group","Resource Group","rg-weu"],["name","Name","vnet-weu"],["address-prefix","Address Prefix","10.10.0.0/16"]]],
  subnet:["Subnet",[["resource-group","Resource Group","rg-weu"],["vnet","VNet","vnet-weu"],["name","Name","web"],["address-prefix","Address Prefix","10.10.1.0/24"]]],
  peering:["VNet Peering",[["source-vnet","Source VNet","vnet-weu"],["remote-vnet","Remote VNet","vnet-neu"]]],
  nsg:["Network Security Group",[["resource-group","Resource Group","rg-weu"],["name","Name","nsg-web"]]],
  "nsg-rule":["NSG Rule",[["nsg","NSG","nsg-web"],["name","Name","allow-https"],["priority","Priority","100"],["direction","Direction","inbound"],["access","Access","allow"],["protocol","Protocol","tcp"],["source-prefix","Source Prefix","Internet"],["destination-port","Destination Port","443"]]],
  "route-table":["Route Table",[["resource-group","Resource Group","rg1"],["name","Name","rt1"]]],
  route:["UDR Route",[["route-table","Route Table","rt1"],["name","Name","r1"],["address-prefix","Address Prefix","10.1.0.0/24"],["next-hop-type","Next Hop Type","VirtualAppliance"],["next-hop-ip","Next Hop IP","10.0.0.4"]]],
  "vpn-gateway":["VPN Gateway",[["name","Name","vpn-gw-weu"],["vnet","VNet","vnet-weu"],["sku","SKU","VpnGw1"],["asn","ASN","65515"]]],
  "local-gateway":["Local Network Gateway",[["name","Name","onprem-weu"],["ip-address","Public IP","203.0.113.10"],["address-prefixes","Address Prefixes","10.100.0.0/16"],["asn","ASN","65010"],["bgp-peering-address","BGP Peer IP","10.100.255.1"]]],
  "vpn-connection":["VPN Connection",[["name","Name","vpn-onprem-weu"],["vpn-gateway","VPN Gateway","vpn-gw-weu"],["local-gateway","Local Gateway","onprem-weu"]]],
  "bgp-peer":["BGP Peer",[["name","Name","bgp-onprem"],["local-device","Local Device","vpn-gw-weu"],["local-asn","Local ASN","65515"],["local-ip","Local IP","10.100.255.2"],["remote-device","Remote Device","onprem-router"],["remote-asn","Remote ASN","65010"],["remote-ip","Remote IP","10.100.255.1"]]],
  "bgp-route":["Advertise BGP Route",[["peer","Peer","bgp-onprem"],["prefix","Prefix","10.100.0.0/16"]]],
  "bgp-learn":["Learn BGP Route",[["peer","Peer","bgp-onprem"],["prefix","Prefix","10.100.0.0/16"]]],
  "route-server":["Azure Route Server",[["name","Name","ars-weu"],["vnet","VNet","vnet-weu"],["subnet","Subnet","RouteServerSubnet"],["asn","ASN","65515"]]],
  "rs-peer":["Route Server BGP Peer",[["name","Name","ars-nva"],["route-server","Route Server","ars-weu"],["nva","NVA","nva-weu"],["route-server-ip","Route Server IP","10.10.10.5"]]],
  nva:["Network Virtual Appliance",[["name","Name","nva-weu"],["vnet","VNet","vnet-weu"],["subnet","Subnet","nva"],["private-ip","Private IP","10.10.10.4"],["asn","ASN","65050"]]],
  "nva-route":["Advertise NVA Route",[["nva","NVA","nva-weu"],["prefix","Prefix","10.200.0.0/16"]]],
  hybrid:["VPN + ExpressRoute Coexistence",[["name","Name","coexist-weu"],["vnet","VNet","vnet-weu"],["vpn-gateway","VPN Gateway","vpn-gw-weu"],["circuit","ExpressRoute","er-weu"],["route-server","Route Server","ars-weu"],["nva","NVA","nva-weu"]]],
  expressroute:["ExpressRoute Circuit",[["name","Name","er-weu"],["provider","Provider","Contoso"],["location","Location","Amsterdam"],["bandwidth","Bandwidth","1Gbps"],["asn","ASN","65010"]]],
  "er-peer":["ExpressRoute Peering",[["circuit","Circuit","er-weu"],["peering-type","Peering Type","private"],["vlan","VLAN","100"],["peer-asn","Peer ASN","65010"],["peer-ip","Peer IP","192.0.2.2"]]],
  "er-route":["Advertise ExpressRoute Route",[["circuit","Circuit","er-weu"],["peering-type","Peering Type","private"],["prefix","Prefix","10.100.0.0/16"]]],
  wan:["Virtual WAN",[["name","Name","vwan-global"],["type","Type","Standard"]]],
  "wan-hub":["Virtual WAN Hub",[["wan","WAN","vwan-global"],["name","Name","hub-weu"],["vnet","VNet","vnet-weu"],["location","Location","westeurope"]]]
 };
 return specs[type];
}
function openForm(type){
 const spec=formSpec(type);if(!spec)return;const [title,fields]=spec;
 const actionMap={"nsg-rule":["nsg","rule","create"],"route-table":["route","table-create"],route:["route","create"],"vpn-gateway":["vpn","gateway-create"],"local-gateway":["vpn","local-create"],"vpn-connection":["vpn","connection-create"],"bgp-peer":["bgp","peer-create"],"bgp-route":["bgp","advertise"],"bgp-learn":["bgp","learn"],"route-server":["route-server","create"],"rs-peer":["route-server","peer-create"],nva:["nva","create"],"nva-route":["nva","advertise"],hybrid:["hybrid","create"],expressroute:["expressroute","create"],"er-peer":["expressroute","peer"],"er-route":["expressroute","advertise"],wan:["wan","create"],"wan-hub":["wan","hub-create"]};
 const action=actionMap[type]||[type,"create"];
 $("formPanel").classList.remove("hidden");
 $("formPanel").innerHTML=`<div class="panel-head"><div><small>CREATE RESOURCE</small><h2>${title}</h2></div><button class="ghost" onclick="closeForm()">Close</button></div><form id="resourceForm"><div class="form-grid">${fields.map(f=>`<label>${f[1]}<input name="${esc(f[0])}" value="${esc(f[2])}" required></label>`).join("")}</div>${type==="vpn-connection"?'<label style="display:block;margin-top:12px"><input style="width:auto" type="checkbox" name="bgp"> Enable BGP</label>':''}<div class="form-actions"><button>Create</button></div></form><pre id="formOutput">Ready.</pre>`;
 $("resourceForm").onsubmit=async e=>{e.preventDefault();const fd=new FormData(e.target);const args=[...action];for(const f of fields){const v=fd.get(f[0]);if(v!==null&&v!=="")args.push("--"+f[0],v)}if(type==="vpn-connection"&&fd.get("bgp"))args.push("--bgp");try{const r=await api("/api/cli",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({args})});$("formOutput").textContent=r.output;toast("Resource created");await loadAll()}catch(err){$("formOutput").textContent="[FAIL] "+err.message;toast(err.message,false)}};
 $("formPanel").scrollIntoView({behavior:"smooth"});
}
function closeForm(){$("formPanel").classList.add("hidden")}
async function simulate(path,target){
 const source=$(target==="qout"?"qs":"rs").value,destination=$(target==="qout"?"qd":"rd").value;
 try{$(target).textContent="Running...";$(target).textContent=(await api(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({source,destination})})).output}catch(e){$(target).textContent="[FAIL] "+e.message}
}
async function deployTemplate(kind){
 try{
  if(kind==="core"){
   await create(["group","create","--name","rg-weu","--location","westeurope"]);await create(["vnet","create","--resource-group","rg-weu","--name","vnet-weu","--address-prefix","10.10.0.0/16"]);await create(["subnet","create","--resource-group","rg-weu","--vnet","vnet-weu","--name","web","--address-prefix","10.10.1.0/24"]);await create(["subnet","create","--resource-group","rg-weu","--vnet","vnet-weu","--name","app","--address-prefix","10.10.2.0/24"]);
  }else if(kind==="hybrid"){
   await deployTemplate("core");await create(["vpn","gateway-create","--name","vpn-gw-weu","--vnet","vnet-weu","--sku","VpnGw1","--asn","65515"]);await create(["vpn","local-create","--name","onprem-weu","--ip-address","203.0.113.10","--address-prefixes","10.100.0.0/16","--asn","65010","--bgp-peering-address","10.100.255.1"]);await create(["vpn","connection-create","--name","vpn-onprem-weu","--vpn-gateway","vpn-gw-weu","--local-gateway","onprem-weu","--bgp"]);await create(["bgp","peer-create","--name","bgp-onprem","--local-device","vpn-gw-weu","--local-asn","65515","--local-ip","10.100.255.2","--remote-device","onprem-router","--remote-asn","65010","--remote-ip","10.100.255.1"]);await create(["bgp","advertise","--peer","bgp-onprem","--prefix","10.100.0.0/16"]);
  }else if(kind==="advanced"){
   await deployTemplate("hybrid");await create(["subnet","create","--resource-group","rg-weu","--vnet","vnet-weu","--name","nva","--address-prefix","10.10.10.0/24"]);await create(["route-server","create","--name","ars-weu","--vnet","vnet-weu","--subnet","nva","--asn","65515"]);await create(["nva","create","--name","nva-weu","--vnet","vnet-weu","--subnet","nva","--private-ip","10.10.10.4","--asn","65050"]);await create(["route-server","peer-create","--name","ars-nva","--route-server","ars-weu","--nva","nva-weu","--route-server-ip","10.10.10.5"]);await create(["nva","advertise","--nva","nva-weu","--prefix","10.200.0.0/16"]);await create(["expressroute","create","--name","er-weu","--provider","Contoso","--location","Amsterdam","--bandwidth","1Gbps","--asn","65010"]);await create(["expressroute","peer","--circuit","er-weu","--peering-type","private","--vlan","100","--peer-asn","65010","--peer-ip","192.0.2.2"]);await create(["expressroute","advertise","--circuit","er-weu","--peering-type","private","--prefix","10.100.0.0/16"]);await create(["hybrid","create","--name","coexist-weu","--vnet","vnet-weu","--vpn-gateway","vpn-gw-weu","--circuit","er-weu","--route-server","ars-weu","--nva","nva-weu"]);
  }
  toast("Template deployment finished");await loadAll();openView("topology");
 }catch(e){toast(e.message,false)}
}
async function create(args){return api("/api/cli",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({args})})}
async function resetLab(){
 if(!confirm("Reset the simulated lab to a blank state? A JSON backup will be created first."))return;
 try{const r=await api("/api/reset",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({confirm:true})});toast(r.output);await loadAll();openView("dashboard")}catch(e){toast(e.message,false)}
}
async function loadState(){state=await api("/api/state");renderCards();renderHealth();renderTopology()}
async function loadAll(){try{await loadState();await loadShow($("showTarget")?.value||"vnet")}catch(e){toast(e.message,false)}}
window.addEventListener("resize",()=>{if($("topology")?.classList.contains("active"))renderTopology()});
loadAll();
