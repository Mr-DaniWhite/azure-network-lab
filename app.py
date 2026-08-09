import argparse
import ipaddress
import json
from pathlib import Path


STATE_FILE = Path("data/state.json")


DEFAULT_STATE = {
    "resource_groups": {},
    "vnets": {},
    "peerings": {},
    "nsgs": {},
    "route_tables": {},
    "vpn_gateways": {},
    "local_network_gateways": {},
    "vpn_connections": {},
    "bgp_peers": {},
    "route_servers": {},
    "nvas": {},
    "expressroute_circuits": {},
    "virtual_wans": {},
}


# ============================================================
# STATE
# ============================================================

def load_state():

    if not STATE_FILE.exists():
        return DEFAULT_STATE.copy()

    if STATE_FILE.stat().st_size == 0:
        return DEFAULT_STATE.copy()

    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            state = json.load(f)

    except json.JSONDecodeError:
        print("⚠ Invalid state.json. Creating new state.")
        return DEFAULT_STATE.copy()

    for key in DEFAULT_STATE:
        state.setdefault(key, {})

    for vnet in state["vnets"].values():
        vnet.setdefault("subnets", {})

        for subnet in vnet["subnets"].values():
            subnet.setdefault("nsg", None)
            subnet.setdefault("route_table", None)

    for nsg in state["nsgs"].values():
        nsg.setdefault("rules", {})

    for rt in state["route_tables"].values():
        rt.setdefault("routes", {})

    return state


def save_state(state):

    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            state,
            f,
            indent=2
        )


# ============================================================
# RESOURCE GROUP
# ============================================================

def create_group(args, state):

    if args.name in state["resource_groups"]:
        print(f"✗ Resource group '{args.name}' already exists")
        return

    state["resource_groups"][args.name] = {
        "location": args.location
    }

    save_state(state)

    print()
    print("✓ Resource group created")
    print(f"  Name:     {args.name}")
    print(f"  Location: {args.location}")


def list_groups(state):

    print()
    print("NAME          LOCATION")
    print("-" * 40)

    for name, group in state["resource_groups"].items():
        print(
            f"{name:<14}"
            f"{group['location']}"
        )


# ============================================================
# VNET
# ============================================================

def create_vnet(args, state):

    if args.resource_group not in state["resource_groups"]:
        print(
            f"✗ Resource group "
            f"'{args.resource_group}' not found"
        )
        return

    if args.name in state["vnets"]:
        print(
            f"✗ VNet "
            f"'{args.name}' already exists"
        )
        return

    location = state[
        "resource_groups"
    ][args.resource_group]["location"]

    state["vnets"][args.name] = {
        "resource_group": args.resource_group,
        "location": location,
        "address_prefix": args.address_prefix,
        "subnets": {},
    }

    save_state(state)

    print()
    print("✓ VNet created")
    print(f"  Name:          {args.name}")
    print(f"  Resource Group:{args.resource_group}")
    print(f"  Region:        {location}")
    print(f"  Address Space: {args.address_prefix}")


def list_vnets(state):

    print()
    print("NAME          REGION          ADDRESS SPACE")
    print("-" * 60)

    for name, vnet in state["vnets"].items():
        print(
            f"{name:<14}"
            f"{vnet['location']:<16}"
            f"{vnet['address_prefix']}"
        )


def show_vnet(args, state):

    if args.name not in state["vnets"]:
        print(
            f"✗ VNet "
            f"'{args.name}' not found"
        )
        return

    vnet = state["vnets"][args.name]

    print()
    print("VIRTUAL NETWORK")
    print("-" * 70)
    print(f"Name:           {args.name}")
    print(f"Region:         {vnet['location']}")
    print(f"Address Space:  {vnet['address_prefix']}")

    print()
    print("SUBNETS")
    print("-" * 70)

    if not vnet["subnets"]:
        print("No subnets")
        return

    for name, subnet in vnet["subnets"].items():
        print(
            f"{name:<16}"
            f"{subnet['address_prefix']:<20}"
            f"NSG={subnet.get('nsg') or 'None':<16}"
            f"RT={subnet.get('route_table') or 'None'}"
        )


# ============================================================
# SUBNET
# ============================================================

def create_subnet(args, state):

    if args.resource_group not in state["resource_groups"]:
        print(
            f"✗ Resource group "
            f"'{args.resource_group}' not found"
        )
        return

    if args.vnet not in state["vnets"]:
        print(
            f"✗ VNet "
            f"'{args.vnet}' not found"
        )
        return

    vnet = state["vnets"][args.vnet]

    vnet.setdefault("subnets", {})

    if args.name in vnet["subnets"]:
        print(
            f"✗ Subnet "
            f"'{args.name}' already exists"
        )
        return

    vnet["subnets"][args.name] = {
        "address_prefix": args.address_prefix,
        "nsg": None,
        "route_table": None,
    }

    save_state(state)

    print()
    print("✓ Subnet created")
    print(f"  Name:          {args.name}")
    print(f"  VNet:          {args.vnet}")
    print(f"  Address Space: {args.address_prefix}")


def list_subnets(args, state):

    if args.vnet not in state["vnets"]:
        print(
            f"✗ VNet "
            f"'{args.vnet}' not found"
        )
        return

    vnet = state["vnets"][args.vnet]

    print()
    print(
        "SUBNET        ADDRESS SPACE      "
        "NSG             ROUTE TABLE"
    )
    print("-" * 90)

    for name, subnet in vnet["subnets"].items():

        print(
            f"{name:<14}"
            f"{subnet['address_prefix']:<19}"
            f"{str(subnet.get('nsg') or 'None'):<16}"
            f"{subnet.get('route_table') or 'None'}"
        )


def associate_nsg(args, state):

    if args.vnet not in state["vnets"]:
        print("✗ VNet not found")
        return

    if args.nsg not in state["nsgs"]:
        print("✗ NSG not found")
        return

    vnet = state["vnets"][args.vnet]

    if args.subnet not in vnet["subnets"]:
        print("✗ Subnet not found")
        return

    vnet["subnets"][args.subnet]["nsg"] = args.nsg

    save_state(state)

    print()
    print("✓ NSG associated")
    print(f"  VNet:   {args.vnet}")
    print(f"  Subnet: {args.subnet}")
    print(f"  NSG:    {args.nsg}")


# ============================================================
# PEERING
# ============================================================

def create_peering(args, state):

    if args.source_vnet not in state["vnets"]:
        print("✗ Source VNet not found")
        return

    if args.remote_vnet not in state["vnets"]:
        print("✗ Remote VNet not found")
        return

    if args.source_vnet == args.remote_vnet:
        print("✗ A VNet cannot peer with itself")
        return

    peering_id = (
        f"{args.source_vnet}"
        f"->{args.remote_vnet}"
    )

    if peering_id in state["peerings"]:
        print("✗ Peering already exists")
        return

    state["peerings"][peering_id] = {
        "source_vnet": args.source_vnet,
        "remote_vnet": args.remote_vnet,
        "state": "Connected",
    }

    save_state(state)

    print()
    print("✓ VNet peering created")
    print(f"  Source: {args.source_vnet}")
    print(f"  Remote: {args.remote_vnet}")
    print("  State:  Connected")


def list_peerings(state):

    print()
    print("SOURCE VNET     REMOTE VNET     STATE")
    print("-" * 60)

    for peering in state["peerings"].values():
        print(
            f"{peering['source_vnet']:<16}"
            f"{peering['remote_vnet']:<16}"
            f"{peering['state']}"
        )


# ============================================================
# NSG
# ============================================================

def create_nsg(args, state):

    if args.resource_group not in state["resource_groups"]:
        print("✗ Resource group not found")
        return

    if args.name in state["nsgs"]:
        print("✗ NSG already exists")
        return

    location = state[
        "resource_groups"
    ][args.resource_group]["location"]

    state["nsgs"][args.name] = {
        "resource_group": args.resource_group,
        "location": location,
        "rules": {},
    }

    save_state(state)

    print()
    print("✓ NSG created")
    print(f"  Name:     {args.name}")
    print(f"  Location: {location}")


def list_nsgs(state):

    print()
    print("NAME          RESOURCE GROUP     REGION")
    print("-" * 65)

    for name, nsg in state["nsgs"].items():
        print(
            f"{name:<14}"
            f"{nsg['resource_group']:<20}"
            f"{nsg['location']}"
        )


def create_nsg_rule(args, state):

    if args.nsg not in state["nsgs"]:
        print("✗ NSG not found")
        return

    nsg = state["nsgs"][args.nsg]

    for rule in nsg["rules"].values():
        if rule["priority"] == args.priority:
            print(
                f"✗ Priority "
                f"{args.priority} already exists"
            )
            return

    nsg["rules"][args.name] = {
        "priority": args.priority,
        "direction": args.direction,
        "access": args.access,
        "protocol": args.protocol,
        "source_prefix": args.source_prefix,
        "destination_port": args.destination_port,
    }

    save_state(state)

    print()
    print("✓ NSG rule created")
    print(f"  Name:      {args.name}")
    print(f"  Priority:  {args.priority}")
    print(f"  Direction: {args.direction}")
    print(f"  Access:    {args.access}")
    print(f"  Protocol:  {args.protocol}")


def list_nsg_rules(args, state):

    if args.nsg not in state["nsgs"]:
        print("✗ NSG not found")
        return

    rules = state[
        "nsgs"
    ][args.nsg]["rules"]

    print()
    print(
        "NAME          PRIORITY  "
        "DIRECTION  ACCESS  PROTOCOL"
    )
    print("-" * 80)

    for name, rule in sorted(
        rules.items(),
        key=lambda x: x[1]["priority"]
    ):
        print(
            f"{name:<14}"
            f"{rule['priority']:<10}"
            f"{rule['direction']:<11}"
            f"{rule['access']:<8}"
            f"{rule['protocol']}"
        )


# ============================================================
# ROUTE TABLES
# ============================================================

def create_route_table(args, state):

    if args.resource_group not in state["resource_groups"]:
        print("✗ Resource group not found")
        return

    if args.name in state["route_tables"]:
        print("✗ Route table already exists")
        return

    location = state[
        "resource_groups"
    ][args.resource_group]["location"]

    state["route_tables"][args.name] = {
        "resource_group": args.resource_group,
        "location": location,
        "routes": {},
    }

    save_state(state)

    print()
    print("✓ Route table created")
    print(f"  Name:     {args.name}")
    print(f"  Location: {location}")


def list_route_tables(state):

    print()
    print("NAME          RESOURCE GROUP     REGION")
    print("-" * 65)

    for name, rt in state["route_tables"].items():
        print(
            f"{name:<14}"
            f"{rt['resource_group']:<20}"
            f"{rt['location']}"
        )


def create_route(args, state):

    if args.route_table not in state["route_tables"]:
        print("✗ Route table not found")
        return

    try:
        ipaddress.ip_network(
            args.address_prefix,
            strict=False
        )
    except ValueError:
        print("✗ Invalid CIDR")
        return

    rt = state[
        "route_tables"
    ][args.route_table]

    if args.name in rt["routes"]:
        print("✗ Route already exists")
        return

    rt["routes"][args.name] = {
        "address_prefix": args.address_prefix,
        "next_hop_type": args.next_hop_type,
        "next_hop_ip": args.next_hop_ip,
    }

    save_state(state)

    print()
    print("✓ Route created")
    print(f"  Name:       {args.name}")
    print(f"  Prefix:     {args.address_prefix}")
    print(f"  Next hop:   {args.next_hop_type}")


def list_routes(args, state):

    if args.route_table not in state["route_tables"]:
        print("✗ Route table not found")
        return

    routes = state[
        "route_tables"
    ][args.route_table]["routes"]

    print()
    print(
        "NAME          ADDRESS PREFIX       NEXT HOP"
    )
    print("-" * 75)

    for name, route in routes.items():

        next_hop = route["next_hop_type"]

        if route.get("next_hop_ip"):
            next_hop += (
                f" ({route['next_hop_ip']})"
            )

        print(
            f"{name:<14}"
            f"{route['address_prefix']:<21}"
            f"{next_hop}"
        )


def associate_route_table(args, state):

    if args.vnet not in state["vnets"]:
        print("✗ VNet not found")
        return

    if args.route_table not in state["route_tables"]:
        print("✗ Route table not found")
        return

    vnet = state["vnets"][args.vnet]

    if args.subnet not in vnet["subnets"]:
        print("✗ Subnet not found")
        return

    vnet["subnets"][
        args.subnet
    ]["route_table"] = args.route_table

    save_state(state)

    print()
    print("✓ Route table associated")
    print(f"  VNet:        {args.vnet}")
    print(f"  Subnet:      {args.subnet}")
    print(f"  Route table: {args.route_table}")


# ============================================================
# HYBRID - VPN GATEWAY
# ============================================================

def create_vpn_gateway(args, state):

    if args.vnet not in state["vnets"]:
        print("✗ VNet not found")
        return

    if args.name in state["vpn_gateways"]:
        print("✗ VPN Gateway already exists")
        return

    state["vpn_gateways"][args.name] = {
        "vnet": args.vnet,
        "sku": args.sku,
        "asn": args.asn,
        "state": "Succeeded",
    }

    save_state(state)

    print()
    print("✓ VPN Gateway created")
    print(f"  Name:  {args.name}")
    print(f"  VNet:  {args.vnet}")
    print(f"  SKU:   {args.sku}")
    print(f"  ASN:   {args.asn}")
    print("  State: Succeeded")
    print("  Mode:  LOCAL SIMULATION")


def list_vpn_gateways(state):

    print()
    print("NAME          VNET          SKU        ASN")
    print("-" * 60)

    for name, gw in state[
        "vpn_gateways"
    ].items():

        print(
            f"{name:<14}"
            f"{gw['vnet']:<14}"
            f"{gw['sku']:<11}"
            f"{gw['asn']}"
        )


# ============================================================
# LOCAL NETWORK GATEWAY
# ============================================================

def create_local_gateway(args, state):

    if args.name in state["local_network_gateways"]:
        print("✗ Local Network Gateway already exists")
        return

    state["local_network_gateways"][args.name] = {
        "ip_address": args.ip_address,
        "address_prefixes": args.address_prefixes,
        "asn": args.asn,
        "bgp_peering_address": args.bgp_peering_address,
    }

    save_state(state)

    print()
    print("✓ Local Network Gateway created")
    print(f"  Name:          {args.name}")
    print(f"  IP:            {args.ip_address}")
    print(
        f"  Prefixes:      "
        f"{', '.join(args.address_prefixes)}"
    )
    print(f"  ASN:           {args.asn}")

    if args.bgp_peering_address:
        print(
            f"  BGP Peer IP:   "
            f"{args.bgp_peering_address}"
        )


def list_local_gateways(state):

    print()
    print("NAME          IP ADDRESS       ASN")
    print("-" * 55)

    for name, lng in state[
        "local_network_gateways"
    ].items():

        print(
            f"{name:<14}"
            f"{lng['ip_address']:<18}"
            f"{lng['asn']}"
        )


# ============================================================
# VPN CONNECTION
# ============================================================

def create_vpn_connection(args, state):

    if args.vpn_gateway not in state["vpn_gateways"]:
        print("✗ VPN Gateway not found")
        return

    if args.local_gateway not in state[
        "local_network_gateways"
    ]:
        print("✗ Local Network Gateway not found")
        return

    if args.name in state["vpn_connections"]:
        print("✗ VPN connection already exists")
        return

    state["vpn_connections"][args.name] = {
        "vpn_gateway": args.vpn_gateway,
        "local_gateway": args.local_gateway,
        "protocol": "IPsec",
        "bgp": args.bgp,
        "state": "Connected",
    }

    save_state(state)

    print()
    print("✓ VPN connection created")
    print(f"  Name:          {args.name}")
    print(f"  VPN Gateway:   {args.vpn_gateway}")
    print(f"  Local Gateway:  {args.local_gateway}")
    print("  Protocol:      IPsec")
    print(f"  BGP:           {args.bgp}")
    print("  State:         Connected")


def list_vpn_connections(state):

    print()
    print(
        "NAME          VPN GATEWAY     "
        "LOCAL GATEWAY     BGP       STATE"
    )
    print("-" * 90)

    for name, conn in state[
        "vpn_connections"
    ].items():

        print(
            f"{name:<14}"
            f"{conn['vpn_gateway']:<16}"
            f"{conn['local_gateway']:<18}"
            f"{str(conn['bgp']):<10}"
            f"{conn['state']}"
        )


# ============================================================
# BGP
# ============================================================

def create_bgp_peer(args, state):

    if args.name in state["bgp_peers"]:
        print("✗ BGP peer already exists")
        return

    state["bgp_peers"][args.name] = {
        "local_device": args.local_device,
        "local_asn": args.local_asn,
        "local_ip": args.local_ip,
        "remote_device": args.remote_device,
        "remote_asn": args.remote_asn,
        "remote_ip": args.remote_ip,
        "state": "Established",
        "advertised_routes": [],
        "learned_routes": [],
    }

    save_state(state)

    print()
    print("✓ BGP peer created")
    print(f"  Name:        {args.name}")
    print(f"  Local ASN:   {args.local_asn}")
    print(f"  Local IP:    {args.local_ip}")
    print(f"  Remote ASN:  {args.remote_asn}")
    print(f"  Remote IP:   {args.remote_ip}")
    print("  State:       Established")


def list_bgp_peers(state):

    print()
    print(
        "NAME          LOCAL ASN   "
        "REMOTE ASN   STATE"
    )
    print("-" * 65)

    for name, peer in state[
        "bgp_peers"
    ].items():

        print(
            f"{name:<14}"
            f"{peer['local_asn']:<12}"
            f"{peer['remote_asn']:<13}"
            f"{peer['state']}"
        )


def bgp_advertise(args, state):

    if args.peer not in state["bgp_peers"]:
        print("✗ BGP peer not found")
        return

    try:
        ipaddress.ip_network(
            args.prefix,
            strict=False
        )
    except ValueError:
        print("✗ Invalid prefix")
        return

    peer = state["bgp_peers"][args.peer]

    if args.prefix not in peer["advertised_routes"]:
        peer["advertised_routes"].append(
            args.prefix
        )

    save_state(state)

    print()
    print("✓ BGP route advertised")
    print(f"  Peer:   {args.peer}")
    print(f"  Prefix: {args.prefix}")


def bgp_learn(args, state):

    if args.peer not in state["bgp_peers"]:
        print("✗ BGP peer not found")
        return

    try:
        ipaddress.ip_network(
            args.prefix,
            strict=False
        )
    except ValueError:
        print("✗ Invalid prefix")
        return

    peer = state["bgp_peers"][args.peer]

    if args.prefix not in peer["learned_routes"]:
        peer["learned_routes"].append(
            args.prefix
        )

    save_state(state)

    print()
    print("✓ BGP route learned")
    print(f"  Peer:   {args.peer}")
    print(f"  Prefix: {args.prefix}")


# ============================================================
# ROUTE SERVER
# ============================================================

def create_route_server(args, state):

    if args.vnet not in state["vnets"]:
        print("✗ VNet not found")
        return

    if args.name in state["route_servers"]:
        print("✗ Route Server already exists")
        return

    state["route_servers"][args.name] = {
        "vnet": args.vnet,
        "subnet": args.subnet,
        "asn": args.asn,
        "state": "Running",
        "peers": [],
    }

    save_state(state)

    print()
    print("✓ Azure Route Server created")
    print(f"  Name:    {args.name}")
    print(f"  VNet:    {args.vnet}")
    print(f"  Subnet:  {args.subnet}")
    print(f"  ASN:     {args.asn}")
    print("  State:   Running")


def list_route_servers(state):

    print()
    print("NAME          VNET          ASN       STATE")
    print("-" * 65)

    for name, rs in state[
        "route_servers"
    ].items():

        print(
            f"{name:<14}"
            f"{rs['vnet']:<14}"
            f"{rs['asn']:<10}"
            f"{rs['state']}"
        )


def route_server_peer(args, state):

    if args.route_server not in state["route_servers"]:
        print("✗ Route Server not found")
        return

    rs = state[
        "route_servers"
    ][args.route_server]

    if args.peer not in rs["peers"]:
        rs["peers"].append(
            args.peer
        )

    save_state(state)

    print()
    print("✓ Route Server peer added")
    print(f"  Route Server: {args.route_server}")
    print(f"  Peer:         {args.peer}")


# ============================================================
# NVA
# ============================================================

def create_nva(args, state):

    if args.vnet not in state["vnets"]:
        print("✗ VNet not found")
        return

    if args.name in state["nvas"]:
        print("✗ NVA already exists")
        return

    state["nvas"][args.name] = {
        "vnet": args.vnet,
        "subnet": args.subnet,
        "ip_address": args.ip_address,
        "asn": args.asn,
        "state": "Running",
    }

    save_state(state)

    print()
    print("✓ NVA created")
    print(f"  Name:       {args.name}")
    print(f"  VNet:       {args.vnet}")
    print(f"  Subnet:     {args.subnet}")
    print(f"  IP:         {args.ip_address}")
    print(f"  ASN:        {args.asn}")
    print("  State:      Running")


def list_nvas(state):

    print()
    print("NAME          VNET          IP              ASN")
    print("-" * 70)

    for name, nva in state[
        "nvas"
    ].items():

        print(
            f"{name:<14}"
            f"{nva['vnet']:<14}"
            f"{nva['ip_address']:<16}"
            f"{nva['asn']}"
        )


# ============================================================
# EXPRESSROUTE
# ============================================================

def create_expressroute(args, state):

    if args.name in state[
        "expressroute_circuits"
    ]:
        print("✗ ExpressRoute circuit already exists")
        return

    state[
        "expressroute_circuits"
    ][args.name] = {
        "provider": args.provider,
        "location": args.location,
        "bandwidth": args.bandwidth,
        "asn": args.asn,
        "state": "Provisioned",
        "peering": None,
    }

    save_state(state)

    print()
    print("✓ ExpressRoute circuit created")
    print(f"  Name:      {args.name}")
    print(f"  Provider:  {args.provider}")
    print(f"  Location:  {args.location}")
    print(f"  Bandwidth: {args.bandwidth}")
    print(f"  ASN:       {args.asn}")
    print("  State:     Provisioned")


def expressroute_peer(args, state):

    if args.circuit not in state[
        "expressroute_circuits"
    ]:
        print("✗ ExpressRoute circuit not found")
        return

    circuit = state[
        "expressroute_circuits"
    ][args.circuit]

    circuit["peering"] = {
        "type": args.peering_type,
        "vlan": args.vlan,
        "peer_asn": args.peer_asn,
        "peer_ip": args.peer_ip,
    }

    save_state(state)

    print()
    print("✓ ExpressRoute peering configured")
    print(f"  Circuit:   {args.circuit}")
    print(f"  Type:      {args.peering_type}")
    print(f"  VLAN:      {args.vlan}")
    print(f"  Peer ASN:  {args.peer_asn}")
    print(f"  Peer IP:   {args.peer_ip}")


def list_expressroute(state):

    print()
    print(
        "NAME          PROVIDER       "
        "BANDWIDTH      ASN       STATE"
    )
    print("-" * 90)

    for name, circuit in state[
        "expressroute_circuits"
    ].items():

        print(
            f"{name:<14}"
            f"{circuit['provider']:<15}"
            f"{circuit['bandwidth']:<15}"
            f"{circuit['asn']:<10}"
            f"{circuit['state']}"
        )


# ============================================================
# VIRTUAL WAN
# ============================================================

def create_virtual_wan(args, state):

    if args.name in state["virtual_wans"]:
        print("✗ Virtual WAN already exists")
        return

    state["virtual_wans"][args.name] = {
        "type": args.type,
        "hubs": [],
        "connections": [],
        "state": "Succeeded",
    }

    save_state(state)

    print()
    print("✓ Virtual WAN created")
    print(f"  Name:  {args.name}")
    print(f"  Type:  {args.type}")
    print("  State: Succeeded")


def virtual_wan_hub(args, state):

    if args.wan not in state["virtual_wans"]:
        print("✗ Virtual WAN not found")
        return

    if args.vnet not in state["vnets"]:
        print("✗ VNet not found")
        return

    wan = state[
        "virtual_wans"
    ][args.wan]

    hub = {
        "name": args.name,
        "vnet": args.vnet,
        "location": args.location,
    }

    wan["hubs"].append(hub)

    save_state(state)

    print()
    print("✓ Virtual WAN hub created")
    print(f"  WAN:       {args.wan}")
    print(f"  Hub:       {args.name}")
    print(f"  VNet:      {args.vnet}")
    print(f"  Location:  {args.location}")


def list_virtual_wans(state):

    print()
    print("NAME          TYPE          HUBS       STATE")
    print("-" * 65)

    for name, wan in state[
        "virtual_wans"
    ].items():

        print(
            f"{name:<14}"
            f"{wan['type']:<14}"
            f"{len(wan['hubs']):<11}"
            f"{wan['state']}"
        )


# ============================================================
# ROUTE DISCOVERY HELPERS
# ============================================================

def find_subnet_for_ip(ip, state):

    for vnet_name, vnet in state["vnets"].items():

        for subnet_name, subnet in vnet[
            "subnets"
        ].items():

            try:
                network = ipaddress.ip_network(
                    subnet["address_prefix"],
                    strict=False
                )
            except ValueError:
                continue

            if ip in network:
                return (
                    vnet_name,
                    subnet_name,
                    subnet
                )

    return None, None, None


def find_vnet_for_ip(ip, state):

    for vnet_name, vnet in state["vnets"].items():

        try:
            network = ipaddress.ip_network(
                vnet["address_prefix"],
                strict=False
            )
        except ValueError:
            continue

        if ip in network:
            return vnet_name

    return None


# ============================================================
# HYBRID ROUTE SIMULATION
# ============================================================

def simulate_route(args, state):

    try:
        source = ipaddress.ip_address(
            args.source
        )

        destination = ipaddress.ip_address(
            args.destination
        )

    except ValueError as exc:
        print(
            f"✗ Invalid IP: {exc}"
        )
        return

    print()
    print("=" * 72)
    print("AZURE HYBRID NETWORK ROUTE SIMULATION")
    print("=" * 72)

    print(f"Source:       {source}")
    print(f"Destination:  {destination}")

    (
        source_vnet,
        source_subnet,
        source_subnet_data
    ) = find_subnet_for_ip(
        source,
        state
    )

    if not source_vnet:

        print()
        print(
            "✗ Source IP does not belong "
            "to a simulated Azure subnet"
        )

        return

    destination_vnet = find_vnet_for_ip(
        destination,
        state
    )

    (
        destination_subnet_vnet,
        destination_subnet,
        destination_subnet_data
    ) = find_subnet_for_ip(
        destination,
        state
    )

    if destination_subnet_vnet:
        destination_vnet = destination_subnet_vnet

    print()
    print(
        f"Source VNet:       {source_vnet}"
    )

    print(
        f"Source Subnet:     {source_subnet}"
    )

    if destination_vnet:
        print(
            f"Destination VNet:  "
            f"{destination_vnet}"
        )

    else:
        print(
            "Destination:       HYBRID / EXTERNAL"
        )

    # --------------------------------------------------------
    # SAME SUBNET
    # --------------------------------------------------------

    source_network = ipaddress.ip_network(
        source_subnet_data["address_prefix"],
        strict=False
    )

    if destination in source_network:

        print()
        print("RESULT")
        print("-" * 72)
        print("✓ Same subnet")
        print("Next Hop:   DIRECT")
        print("Route:      SYSTEM")
        return

    # --------------------------------------------------------
    # UDR
    # --------------------------------------------------------

    route_table_name = source_subnet_data.get(
        "route_table"
    )

    route_table = None

    if route_table_name:

        route_table = state[
            "route_tables"
        ].get(route_table_name)

    matches = []

    if route_table:

        for name, route in route_table[
            "routes"
        ].items():

            try:
                network = ipaddress.ip_network(
                    route["address_prefix"],
                    strict=False
                )
            except ValueError:
                continue

            if destination in network:

                matches.append(
                    (
                        network.prefixlen,
                        name,
                        route
                    )
                )

    if matches:

        matches.sort(
            key=lambda x: x[0],
            reverse=True
        )

        (
            prefix_len,
            route_name,
            route
        ) = matches[0]

        print()
        print("RESULT")
        print("-" * 72)

        print("✓ USER DEFINED ROUTE")

        print(
            f"Route:       {route_name}"
        )

        print(
            f"Prefix:      {route['address_prefix']}"
        )

        print(
            f"Prefix Len:  /{prefix_len}"
        )

        print(
            f"Next Hop:    {route['next_hop_type']}"
        )

        if route.get("next_hop_ip"):
            print(
                f"Next Hop IP: {route['next_hop_ip']}"
            )

        # If NVA next-hop
        if (
            route["next_hop_type"]
            == "virtual-appliance"
        ):

            for nva_name, nva in state[
                "nvas"
            ].items():

                if (
                    route.get("next_hop_ip")
                    == nva["ip_address"]
                ):

                    print()
                    print(
                        f"✓ NVA matched: "
                        f"{nva_name}"
                    )

                    print(
                        f"  ASN: "
                        f"{nva['asn']}"
                    )

        return

    # --------------------------------------------------------
    # SAME VNET
    # --------------------------------------------------------

    if (
        destination_vnet
        and destination_vnet == source_vnet
    ):

        print()
        print("RESULT")
        print("-" * 72)

        print(
            "✓ SYSTEM ROUTE"
        )

        print(
            "Next Hop: VIRTUAL NETWORK"
        )

        return

    # --------------------------------------------------------
    # PEERING
    # --------------------------------------------------------

    if destination_vnet:

        for peering in state[
            "peerings"
        ].values():

            direct = (
                peering["source_vnet"]
                == source_vnet
                and
                peering["remote_vnet"]
                == destination_vnet
            )

            reverse = (
                peering["source_vnet"]
                == destination_vnet
                and
                peering["remote_vnet"]
                == source_vnet
            )

            if direct or reverse:

                print()
                print("RESULT")
                print("-" * 72)

                print(
                    "✓ VNET PEERING"
                )

                print(
                    "Next Hop: "
                    "VIRTUAL NETWORK PEERING"
                )

                return

    # --------------------------------------------------------
    # VPN
    # --------------------------------------------------------

    for connection in state[
        "vpn_connections"
    ].values():

        if connection["state"] != "Connected":
            continue

        local_gateway = state[
            "local_network_gateways"
        ].get(
            connection["local_gateway"]
        )

        if not local_gateway:
            continue

        for prefix in local_gateway[
            "address_prefixes"
        ]:

            network = ipaddress.ip_network(
                prefix,
                strict=False
            )

            if destination in network:

                print()
                print("RESULT")
                print("-" * 72)

                print(
                    "✓ HYBRID ROUTE"
                )

                print(
                    "Transport: IPsec VPN"
                )

                print(
                    f"VPN Gateway: "
                    f"{connection['vpn_gateway']}"
                )

                print(
                    f"Local Network: "
                    f"{connection['local_gateway']}"
                )

                if connection["bgp"]:

                    print(
                        "Routing: BGP"
                    )

                else:

                    print(
                        "Routing: STATIC"
                    )

                print(
                    f"Destination Prefix: "
                    f"{prefix}"
                )

                return

    # --------------------------------------------------------
    # EXPRESSROUTE
    # --------------------------------------------------------

    for circuit in state[
        "expressroute_circuits"
    ].values():

        if circuit["state"] != "Provisioned":
            continue

        peering = circuit.get(
            "peering"
        )

        if not peering:
            continue

        print()
        print("RESULT")
        print("-" * 72)

        print(
            "✓ EXPRESSROUTE AVAILABLE"
        )

        print(
            f"Provider: "
            f"{circuit['provider']}"
        )

        print(
            f"Bandwidth: "
            f"{circuit['bandwidth']}"
        )

        print(
            f"ASN: "
            f"{circuit['asn']}"
        )

        print(
            f"Peering: "
            f"{peering['type']}"
        )

        print(
            "Transport: PRIVATE CIRCUIT"
        )

        return

    # --------------------------------------------------------
    # BGP LEARNED ROUTE
    # --------------------------------------------------------

    for peer in state[
        "bgp_peers"
    ].values():

        if peer["state"] != "Established":
            continue

        for prefix in peer[
            "learned_routes"
        ]:

            network = ipaddress.ip_network(
                prefix,
                strict=False
            )

            if destination in network:

                print()
                print("RESULT")
                print("-" * 72)

                print(
                    "✓ BGP LEARNED ROUTE"
                )

                print(
                    f"Prefix: "
                    f"{prefix}"
                )

                print(
                    f"Peer ASN: "
                    f"{peer['remote_asn']}"
                )

                print(
                    f"Peer IP: "
                    f"{peer['remote_ip']}"
                )

                print(
                    "State: Established"
                )

                return

    # --------------------------------------------------------
    # DEFAULT
    # --------------------------------------------------------

    print()
    print("RESULT")
    print("-" * 72)

    print(
        "✗ No simulated route found"
    )


# ============================================================
# CLI
# ============================================================

def build_parser():

    parser = argparse.ArgumentParser(
        prog="azsim",
        description="Azure Network Simulator"
    )

    sub = parser.add_subparsers(
        dest="resource"
    )

    # ========================================================
    # GROUP
    # ========================================================

    group = sub.add_parser("group")

    group_sub = group.add_subparsers(
        dest="action"
    )

    group_create = group_sub.add_parser("create")

    group_create.add_argument(
        "--name",
        required=True
    )

    group_create.add_argument(
        "--location",
        required=True
    )

    group_sub.add_parser("list")

    # ========================================================
    # VNET
    # ========================================================

    vnet = sub.add_parser("vnet")

    vnet_sub = vnet.add_subparsers(
        dest="action"
    )

    vnet_create = vnet_sub.add_parser("create")

    vnet_create.add_argument(
        "--resource-group",
        required=True
    )

    vnet_create.add_argument(
        "--name",
        required=True
    )

    vnet_create.add_argument(
        "--address-prefix",
        required=True
    )

    vnet_sub.add_parser("list")

    vnet_show = vnet_sub.add_parser("show")

    vnet_show.add_argument(
        "--name",
        required=True
    )

    # ========================================================
    # SUBNET
    # ========================================================

    subnet = sub.add_parser("subnet")

    subnet_sub = subnet.add_subparsers(
        dest="action"
    )

    subnet_create = subnet_sub.add_parser("create")

    subnet_create.add_argument(
        "--resource-group",
        required=True
    )

    subnet_create.add_argument(
        "--vnet",
        required=True
    )

    subnet_create.add_argument(
        "--name",
        required=True
    )

    subnet_create.add_argument(
        "--address-prefix",
        required=True
    )

    subnet_list = subnet_sub.add_parser("list")

    subnet_list.add_argument(
        "--vnet",
        required=True
    )

    subnet_nsg = subnet_sub.add_parser(
        "associate-nsg"
    )

    subnet_nsg.add_argument(
        "--vnet",
        required=True
    )

    subnet_nsg.add_argument(
        "--subnet",
        required=True
    )

    subnet_nsg.add_argument(
        "--nsg",
        required=True
    )

    # ========================================================
    # PEERING
    # ========================================================

    peering = sub.add_parser("peering")

    peering_sub = peering.add_subparsers(
        dest="action"
    )

    peering_create = peering_sub.add_parser(
        "create"
    )

    peering_create.add_argument(
        "--source-vnet",
        required=True
    )

    peering_create.add_argument(
        "--remote-vnet",
        required=True
    )

    peering_sub.add_parser("list")

    # ========================================================
    # NSG
    # ========================================================

    nsg = sub.add_parser("nsg")

    nsg_sub = nsg.add_subparsers(
        dest="action"
    )

    nsg_create = nsg_sub.add_parser("create")

    nsg_create.add_argument(
        "--resource-group",
        required=True
    )

    nsg_create.add_argument(
        "--name",
        required=True
    )

    nsg_sub.add_parser("list")

    nsg_rule = nsg_sub.add_parser(
        "rule"
    )

    nsg_rule_sub = nsg_rule.add_subparsers(
        dest="rule_action"
    )

    nsg_rule_create = nsg_rule_sub.add_parser(
        "create"
    )

    nsg_rule_create.add_argument(
        "--nsg",
        required=True
    )

    nsg_rule_create.add_argument(
        "--name",
        required=True
    )

    nsg_rule_create.add_argument(
        "--priority",
        type=int,
        required=True
    )

    nsg_rule_create.add_argument(
        "--direction",
        choices=[
            "inbound",
            "outbound"
        ],
        required=True
    )

    nsg_rule_create.add_argument(
        "--access",
        choices=[
            "allow",
            "deny"
        ],
        required=True
    )

    nsg_rule_create.add_argument(
        "--protocol",
        choices=[
            "tcp",
            "udp",
            "any"
        ],
        required=True
    )

    nsg_rule_create.add_argument(
        "--source-prefix",
        required=True
    )

    nsg_rule_create.add_argument(
        "--destination-port",
        required=True
    )

    nsg_rule_list = nsg_rule_sub.add_parser(
        "list"
    )

    nsg_rule_list.add_argument(
        "--nsg",
        required=True
    )

    # ========================================================
    # ROUTE
    # ========================================================

    route = sub.add_parser("route")

    route_sub = route.add_subparsers(
        dest="action"
    )

    route_table_create = route_sub.add_parser(
        "table-create"
    )

    route_table_create.add_argument(
        "--resource-group",
        required=True
    )

    route_table_create.add_argument(
        "--name",
        required=True
    )

    route_sub.add_parser(
        "table-list"
    )

    route_create = route_sub.add_parser(
        "create"
    )

    route_create.add_argument(
        "--route-table",
        required=True
    )

    route_create.add_argument(
        "--name",
        required=True
    )

    route_create.add_argument(
        "--address-prefix",
        required=True
    )

    route_create.add_argument(
        "--next-hop-type",
        choices=[
            "virtual-network",
            "virtual-appliance",
            "internet",
            "none"
        ],
        required=True
    )

    route_create.add_argument(
        "--next-hop-ip"
    )

    route_list = route_sub.add_parser(
        "list"
    )

    route_list.add_argument(
        "--route-table",
        required=True
    )

    route_associate = route_sub.add_parser(
        "associate"
    )

    route_associate.add_argument(
        "--vnet",
        required=True
    )

    route_associate.add_argument(
        "--subnet",
        required=True
    )

    route_associate.add_argument(
        "--route-table",
        required=True
    )

    route_simulate = route_sub.add_parser(
        "simulate"
    )

    route_simulate.add_argument(
        "--source",
        required=True
    )

    route_simulate.add_argument(
        "--destination",
        required=True
    )

    # ========================================================
    # VPN
    # ========================================================

    vpn = sub.add_parser("vpn")

    vpn_sub = vpn.add_subparsers(
        dest="action"
    )

    vpn_gateway_create = vpn_sub.add_parser(
        "gateway-create"
    )

    vpn_gateway_create.add_argument(
        "--name",
        required=True
    )

    vpn_gateway_create.add_argument(
        "--vnet",
        required=True
    )

    vpn_gateway_create.add_argument(
        "--sku",
        default="VpnGw1"
    )

    vpn_gateway_create.add_argument(
        "--asn",
        type=int,
        default=65515
    )

    vpn_sub.add_parser(
        "gateway-list"
    )

    vpn_local_create = vpn_sub.add_parser(
        "local-create"
    )

    vpn_local_create.add_argument(
        "--name",
        required=True
    )

    vpn_local_create.add_argument(
        "--ip-address",
        required=True
    )

    vpn_local_create.add_argument(
        "--address-prefixes",
        nargs="+",
        required=True
    )

    vpn_local_create.add_argument(
        "--asn",
        type=int,
        default=65010
    )

    vpn_local_create.add_argument(
        "--bgp-peering-address"
    )

    vpn_sub.add_parser(
        "local-list"
    )

    vpn_connection_create = vpn_sub.add_parser(
        "connection-create"
    )

    vpn_connection_create.add_argument(
        "--name",
        required=True
    )

    vpn_connection_create.add_argument(
        "--vpn-gateway",
        required=True
    )

    vpn_connection_create.add_argument(
        "--local-gateway",
        required=True
    )

    vpn_connection_create.add_argument(
        "--bgp",
        action="store_true"
    )

    vpn_sub.add_parser(
        "connection-list"
    )

    # ========================================================
    # BGP
    # ========================================================

    bgp = sub.add_parser("bgp")

    bgp_sub = bgp.add_subparsers(
        dest="action"
    )

    bgp_create = bgp_sub.add_parser(
        "peer-create"
    )

    bgp_create.add_argument(
        "--name",
        required=True
    )

    bgp_create.add_argument(
        "--local-device",
        required=True
    )

    bgp_create.add_argument(
        "--local-asn",
        type=int,
        required=True
    )

    bgp_create.add_argument(
        "--local-ip",
        required=True
    )

    bgp_create.add_argument(
        "--remote-device",
        required=True
    )

    bgp_create.add_argument(
        "--remote-asn",
        type=int,
        required=True
    )

    bgp_create.add_argument(
        "--remote-ip",
        required=True
    )

    bgp_sub.add_parser(
        "peer-list"
    )

    bgp_adv = bgp_sub.add_parser(
        "advertise"
    )

    bgp_adv.add_argument(
        "--peer",
        required=True
    )

    bgp_adv.add_argument(
        "--prefix",
        required=True
    )

    bgp_learn_parser = bgp_sub.add_parser(
        "learn"
    )

    bgp_learn_parser.add_argument(
        "--peer",
        required=True
    )

    bgp_learn_parser.add_argument(
        "--prefix",
        required=True
    )

    # ========================================================
    # ROUTE SERVER
    # ========================================================

    route_server = sub.add_parser(
        "route-server"
    )

    rs_sub = route_server.add_subparsers(
        dest="action"
    )

    rs_create = rs_sub.add_parser(
        "create"
    )

    rs_create.add_argument(
        "--name",
        required=True
    )

    rs_create.add_argument(
        "--vnet",
        required=True
    )

    rs_create.add_argument(
        "--subnet",
        required=True
    )

    rs_create.add_argument(
        "--asn",
        type=int,
        default=65515
    )

    rs_sub.add_parser(
        "list"
    )

    rs_peer = rs_sub.add_parser(
        "peer"
    )

    rs_peer.add_argument(
        "--route-server",
        required=True
    )

    rs_peer.add_argument(
        "--peer",
        required=True
    )

    # ========================================================
    # NVA
    # ========================================================

    nva = sub.add_parser("nva")

    nva_sub = nva.add_subparsers(
        dest="action"
    )

    nva_create = nva_sub.add_parser(
        "create"
    )

    nva_create.add_argument(
        "--name",
        required=True
    )

    nva_create.add_argument(
        "--vnet",
        required=True
    )

    nva_create.add_argument(
        "--subnet",
        required=True
    )

    nva_create.add_argument(
        "--ip-address",
        required=True
    )

    nva_create.add_argument(
        "--asn",
        type=int,
        default=65050
    )

    nva_sub.add_parser(
        "list"
    )

    # ========================================================
    # EXPRESSROUTE
    # ========================================================

    expressroute = sub.add_parser(
        "expressroute"
    )

    er_sub = expressroute.add_subparsers(
        dest="action"
    )

    er_create = er_sub.add_parser(
        "create"
    )

    er_create.add_argument(
        "--name",
        required=True
    )

    er_create.add_argument(
        "--provider",
        required=True
    )

    er_create.add_argument(
        "--location",
        required=True
    )

    er_create.add_argument(
        "--bandwidth",
        required=True
    )

    er_create.add_argument(
        "--asn",
        type=int,
        default=65010
    )

    er_peer = er_sub.add_parser(
        "peer"
    )

    er_peer.add_argument(
        "--circuit",
        required=True
    )

    er_peer.add_argument(
        "--peering-type",
        choices=[
            "private",
            "microsoft"
        ],
        default="private"
    )

    er_peer.add_argument(
        "--vlan",
        type=int,
        required=True
    )

    er_peer.add_argument(
        "--peer-asn",
        type=int,
        required=True
    )

    er_peer.add_argument(
        "--peer-ip",
        required=True
    )

    er_sub.add_parser(
        "list"
    )

    # ========================================================
    # VIRTUAL WAN
    # ========================================================

    wan = sub.add_parser(
        "wan"
    )

    wan_sub = wan.add_subparsers(
        dest="action"
    )

    wan_create = wan_sub.add_parser(
        "create"
    )

    wan_create.add_argument(
        "--name",
        required=True
    )

    wan_create.add_argument(
        "--type",
        choices=[
            "Standard",
            "Basic"
        ],
        default="Standard"
    )

    wan_hub = wan_sub.add_parser(
        "hub-create"
    )

    wan_hub.add_argument(
        "--wan",
        required=True
    )

    wan_hub.add_argument(
        "--name",
        required=True
    )

    wan_hub.add_argument(
        "--vnet",
        required=True
    )

    wan_hub.add_argument(
        "--location",
        required=True
    )

    wan_sub.add_parser(
        "list"
    )

    return parser


# ============================================================
# MAIN
# ============================================================

def main():

    parser = build_parser()

    args = parser.parse_args()

    state = load_state()

    # --------------------------------------------------------
    # GROUP
    # --------------------------------------------------------

    if args.resource == "group":

        if args.action == "create":
            create_group(args, state)

        elif args.action == "list":
            list_groups(state)

        else:
            parser.print_help()

    # --------------------------------------------------------
    # VNET
    # --------------------------------------------------------

    elif args.resource == "vnet":

        if args.action == "create":
            create_vnet(args, state)

        elif args.action == "list":
            list_vnets(state)

        elif args.action == "show":
            show_vnet(args, state)

        else:
            parser.print_help()

    # --------------------------------------------------------
    # SUBNET
    # --------------------------------------------------------

    elif args.resource == "subnet":

        if args.action == "create":
            create_subnet(args, state)

        elif args.action == "list":
            list_subnets(args, state)

        elif args.action == "associate-nsg":
            associate_nsg(args, state)

        else:
            parser.print_help()

    # --------------------------------------------------------
    # PEERING
    # --------------------------------------------------------

    elif args.resource == "peering":

        if args.action == "create":
            create_peering(args, state)

        elif args.action == "list":
            list_peerings(state)

        else:
            parser.print_help()

    # --------------------------------------------------------
    # NSG
    # --------------------------------------------------------

    elif args.resource == "nsg":

        if args.action == "create":
            create_nsg(args, state)

        elif args.action == "list":
            list_nsgs(state)

        elif (
            args.action == "rule"
            and args.rule_action == "create"
        ):
            create_nsg_rule(args, state)

        elif (
            args.action == "rule"
            and args.rule_action == "list"
        ):
            list_nsg_rules(args, state)

        else:
            parser.print_help()

    # --------------------------------------------------------
    # ROUTE
    # --------------------------------------------------------

    elif args.resource == "route":

        if args.action == "table-create":
            create_route_table(args, state)

        elif args.action == "table-list":
            list_route_tables(state)

        elif args.action == "create":
            create_route(args, state)

        elif args.action == "list":
            list_routes(args, state)

        elif args.action == "associate":
            associate_route_table(args, state)

        elif args.action == "simulate":
            simulate_route(args, state)

        else:
            parser.print_help()

    # --------------------------------------------------------
    # VPN
    # --------------------------------------------------------

    elif args.resource == "vpn":

        if args.action == "gateway-create":
            create_vpn_gateway(args, state)

        elif args.action == "gateway-list":
            list_vpn_gateways(state)

        elif args.action == "local-create":
            create_local_gateway(args, state)

        elif args.action == "local-list":
            list_local_gateways(state)

        elif args.action == "connection-create":
            create_vpn_connection(args, state)

        elif args.action == "connection-list":
            list_vpn_connections(state)

        else:
            parser.print_help()

    # --------------------------------------------------------
    # BGP
    # --------------------------------------------------------

    elif args.resource == "bgp":

        if args.action == "peer-create":
            create_bgp_peer(args, state)

        elif args.action == "peer-list":
            list_bgp_peers(state)

        elif args.action == "advertise":
            bgp_advertise(args, state)

        elif args.action == "learn":
            bgp_learn(args, state)

        else:
            parser.print_help()

    # --------------------------------------------------------
    # ROUTE SERVER
    # --------------------------------------------------------

    elif args.resource == "route-server":

        if args.action == "create":
            create_route_server(args, state)

        elif args.action == "list":
            list_route_servers(state)

        elif args.action == "peer":
            route_server_peer(args, state)

        else:
            parser.print_help()

    # --------------------------------------------------------
    # NVA
    # --------------------------------------------------------

    elif args.resource == "nva":

        if args.action == "create":
            create_nva(args, state)

        elif args.action == "list":
            list_nvas(state)

        else:
            parser.print_help()

    # --------------------------------------------------------
    # EXPRESSROUTE
    # --------------------------------------------------------

    elif args.resource == "expressroute":

        if args.action == "create":
            create_expressroute(args, state)

        elif args.action == "peer":
            expressroute_peer(args, state)

        elif args.action == "list":
            list_expressroute(state)

        else:
            parser.print_help()

    # --------------------------------------------------------
    # VIRTUAL WAN
    # --------------------------------------------------------

    elif args.resource == "wan":

        if args.action == "create":
            create_virtual_wan(args, state)

        elif args.action == "hub-create":
            virtual_wan_hub(args, state)

        elif args.action == "list":
            list_virtual_wans(state)

        else:
            parser.print_help()

    else:

        parser.print_help()


if __name__ == "__main__":
    main()