import argparse
import ipaddress
import json
from pathlib import Path


STATE_FILE = Path("data/state.json")


def default_state():
    return {
        "groups": {},
        "vnets": {},
        "peerings": [],
        "nsgs": {},
        "route_tables": {},
        "vpn_gateways": {},
        "local_gateways": {},
        "vpn_connections": {},
        "bgp_peers": {},
        "bgp_routes": [],
        "expressroute_circuits": {},
        "expressroute_peerings": {},
        "expressroute_routes": [],
        "route_servers": {},
        "nvas": {},
        "route_server_peers": {},
        "hybrid_coexistence": {},
        "nva_routes": [],
    }


def load_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not STATE_FILE.exists() or STATE_FILE.stat().st_size == 0:
        state = default_state()
        save_state(state)
        return state

    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        state = default_state()
        save_state(state)
        return state

    base = default_state()
    for key, value in base.items():
        state.setdefault(key, value)

    # Normalize legacy state files: older versions used the resource name
    # as the dictionary key but did not store a "name" field.
    for name, vnet in state["vnets"].items():
        vnet.setdefault("name", name)
        vnet.setdefault("subnets", {})
        for subnet_name, subnet in vnet["subnets"].items():
            subnet.setdefault("name", subnet_name)
            subnet.setdefault("nsg", None)
            subnet.setdefault("route_table", None)

    for name, item in state["vpn_gateways"].items():
        item.setdefault("name", name)
    for name, item in state["local_gateways"].items():
        item.setdefault("name", name)
    for name, item in state["vpn_connections"].items():
        item.setdefault("name", name)
    for name, item in state["bgp_peers"].items():
        item.setdefault("name", name)
    for name, item in state["nsgs"].items():
        item.setdefault("name", name)
        for rule_name, rule in item.get("rules", {}).items():
            rule.setdefault("name", rule_name)
    for name, item in state["route_tables"].items():
        item.setdefault("name", name)
        for route_name, route in item.get("routes", {}).items():
            route.setdefault("name", route_name)
    for name, item in state["expressroute_circuits"].items():
        item.setdefault("name", name)
    for name, item in state["expressroute_peerings"].items():
        item.setdefault("name", name)

    for name, item in state["route_servers"].items():
        item.setdefault("name", name)
        item.setdefault("state", "Succeeded")
        item.setdefault("peerings", {})
    for name, item in state["nvas"].items():
        item.setdefault("name", name)
        item.setdefault("state", "Succeeded")
        item.setdefault("route_server", None)
    for name, item in state["route_server_peers"].items():
        item.setdefault("name", name)
        item.setdefault("state", "Established")

    # Normalize legacy VNet peerings. Older versions may store peerings as:
    #   [{"source_vnet": "...", "remote_vnet": "..."}]
    # or as a dict keyed by a peer name, and some early versions stored
    # a simple string as the value. Convert all supported forms to a list
    # of dictionaries without changing the on-disk state file.
    raw_peerings = state.get("peerings", [])
    normalized_peerings = []

    if isinstance(raw_peerings, dict):
        for peer_name, value in raw_peerings.items():
            if isinstance(value, dict):
                peer = dict(value)
                peer.setdefault("name", str(peer_name))
            elif isinstance(value, str):
                peer = {
                    "name": str(peer_name),
                    "state": value,
                }
            else:
                peer = {"name": str(peer_name)}
            normalized_peerings.append(peer)
    elif isinstance(raw_peerings, list):
        for index, value in enumerate(raw_peerings):
            if isinstance(value, dict):
                peer = dict(value)
                peer.setdefault(
                    "name",
                    f"{peer.get('source_vnet', '?')}-to-{peer.get('remote_vnet', '?')}",
                )
                normalized_peerings.append(peer)
            elif isinstance(value, str):
                normalized_peerings.append({
                    "name": value,
                    "state": "Unknown",
                })
            else:
                normalized_peerings.append({
                    "name": f"peering-{index + 1}",
                    "state": "Unknown",
                })
    else:
        normalized_peerings = []

    state["peerings"] = normalized_peerings

    return state


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def ok(message):
    print(f"\n[OK] {message}")


def fail(message):
    print(f"\n[FAIL] {message}")


def find_vnet(state, name):
    return state["vnets"].get(name)


def find_subnet(state, vnet_name, subnet_name):
    vnet = find_vnet(state, vnet_name)
    if not vnet:
        return None
    return vnet.get("subnets", {}).get(subnet_name)


def prefix_contains(prefix, ip):
    try:
        return ipaddress.ip_address(ip) in ipaddress.ip_network(prefix, strict=False)
    except ValueError:
        return False


def prefix_matches_ip(prefix, ip):
    return prefix_contains(prefix, ip)


# ---------------------------------------------------------------------------
# GROUP
# ---------------------------------------------------------------------------

def group_create(args, state):
    if args.name in state["groups"]:
        fail(f"Resource Group already exists: {args.name}")
        return

    state["groups"][args.name] = {
        "name": args.name,
        "location": args.location,
    }
    save_state(state)

    ok("Resource Group created")
    print(f"Name:      {args.name}")
    print(f"Location:  {args.location}")


def group_list(args, state):
    print("\n## NAME                 LOCATION")
    print("-" * 45)

    for group in state["groups"].values():
        print(f"{group['name']:<22} {group['location']}")


# ---------------------------------------------------------------------------
# VNET
# ---------------------------------------------------------------------------

def vnet_create(args, state):
    if args.name in state["vnets"]:
        fail(f"VNet already exists: {args.name}")
        return

    if args.resource_group not in state["groups"]:
        fail(f"Resource Group not found: {args.resource_group}")
        return

    try:
        ipaddress.ip_network(args.address_prefix, strict=False)
    except ValueError:
        fail(f"Invalid address prefix: {args.address_prefix}")
        return

    state["vnets"][args.name] = {
        "name": args.name,
        "resource_group": args.resource_group,
        "address_prefix": args.address_prefix,
        "subnets": {},
    }
    save_state(state)

    ok("VNet created")
    print(f"Name:      {args.name}")
    print(f"Address:   {args.address_prefix}")
    print(f"RG:        {args.resource_group}")


def vnet_list(args, state):
    print("\n## NAME                 ADDRESS             RESOURCE GROUP")
    print("-" * 70)

    for vnet in state["vnets"].values():
        print(
            f"{vnet['name']:<22}"
            f"{vnet['address_prefix']:<20}"
            f"{vnet['resource_group']}"
        )


def vnet_show(args, state):
    vnet = find_vnet(state, args.name)

    if not vnet:
        fail(f"VNet not found: {args.name}")
        return

    print("\nVIRTUAL NETWORK")
    print("-" * 65)
    print(f"Name:           {vnet['name']}")
    print(f"Address Space:  {vnet['address_prefix']}")
    print(f"Resource Group: {vnet['resource_group']}")

    print("\nSUBNETS")
    print("-" * 65)

    for subnet in vnet.get("subnets", {}).values():
        print(f"{subnet['name']:<20} {subnet['address_prefix']}")


# ---------------------------------------------------------------------------
# SUBNET
# ---------------------------------------------------------------------------

def create_subnet(args, state):
    vnet = find_vnet(state, args.vnet)

    if not vnet:
        fail(f"VNet not found: {args.vnet}")
        return

    vnet.setdefault("subnets", {})

    if args.name in vnet["subnets"]:
        fail(f"Subnet already exists: {args.name}")
        return

    try:
        subnet_network = ipaddress.ip_network(args.address_prefix, strict=False)
        vnet_network = ipaddress.ip_network(vnet["address_prefix"], strict=False)
    except ValueError:
        fail("Invalid CIDR")
        return

    if not subnet_network.subnet_of(vnet_network):
        fail(
            f"Subnet {args.address_prefix} is not inside "
            f"VNet {vnet['address_prefix']}"
        )
        return

    vnet["subnets"][args.name] = {
        "name": args.name,
        "address_prefix": args.address_prefix,
        "nsg": None,
        "route_table": None,
    }

    save_state(state)

    ok("Subnet created")
    print(f"VNet:      {args.vnet}")
    print(f"Name:      {args.name}")
    print(f"Prefix:    {args.address_prefix}")


def subnet_list(args, state):
    vnet = find_vnet(state, args.vnet)

    if not vnet:
        fail(f"VNet not found: {args.vnet}")
        return

    print("\n## NAME                 PREFIX")
    print("-" * 50)

    for subnet in vnet.get("subnets", {}).values():
        print(f"{subnet['name']:<22} {subnet['address_prefix']}")


def subnet_associate_nsg(args, state):
    subnet = find_subnet(state, args.vnet, args.subnet)

    if not subnet:
        fail("Subnet not found")
        return

    if args.nsg not in state["nsgs"]:
        fail(f"NSG not found: {args.nsg}")
        return

    subnet["nsg"] = args.nsg
    save_state(state)

    ok("NSG associated")
    print(f"VNet:    {args.vnet}")
    print(f"Subnet:  {args.subnet}")
    print(f"NSG:     {args.nsg}")


# ---------------------------------------------------------------------------
# PEERING
# ---------------------------------------------------------------------------

def peering_create(args, state):
    if args.source_vnet not in state["vnets"]:
        fail(f"VNet not found: {args.source_vnet}")
        return

    if args.remote_vnet not in state["vnets"]:
        fail(f"VNet not found: {args.remote_vnet}")
        return

    for peer in state["peerings"]:
        if (
            peer["source_vnet"] == args.source_vnet
            and peer["remote_vnet"] == args.remote_vnet
        ):
            fail("Peering already exists")
            return

    state["peerings"].append(
        {
            "source_vnet": args.source_vnet,
            "remote_vnet": args.remote_vnet,
            "state": "Connected",
        }
    )
    save_state(state)

    ok("VNet Peering created")
    print(f"Source:  {args.source_vnet}")
    print(f"Remote:  {args.remote_vnet}")
    print("State:   Connected")


def peering_list(args, state):
    print("\n## SOURCE                 REMOTE                 STATE")
    print("-" * 70)

    for peer in state["peerings"]:
        print(
            f"{peer['source_vnet']:<24}"
            f"{peer['remote_vnet']:<24}"
            f"{peer['state']}"
        )


def are_peered(state, vnet_a, vnet_b):
    for peer in state["peerings"]:
        if (
            peer["source_vnet"] == vnet_a
            and peer["remote_vnet"] == vnet_b
        ) or (
            peer["source_vnet"] == vnet_b
            and peer["remote_vnet"] == vnet_a
        ):
            return True
    return False


# ---------------------------------------------------------------------------
# NSG
# ---------------------------------------------------------------------------

def nsg_create(args, state):
    if args.name in state["nsgs"]:
        fail(f"NSG already exists: {args.name}")
        return

    if args.resource_group not in state["groups"]:
        fail(f"Resource Group not found: {args.resource_group}")
        return

    state["nsgs"][args.name] = {
        "name": args.name,
        "resource_group": args.resource_group,
        "rules": {},
    }
    save_state(state)

    ok("NSG created")
    print(f"Name:  {args.name}")


def nsg_list(args, state):
    print("\n## NAME                 RESOURCE GROUP")
    print("-" * 55)

    for nsg in state["nsgs"].values():
        print(f"{nsg['name']:<22} {nsg['resource_group']}")


def nsg_rule_create(args, state):
    nsg = state["nsgs"].get(args.nsg)

    if not nsg:
        fail(f"NSG not found: {args.nsg}")
        return

    if args.name in nsg["rules"]:
        fail(f"Rule already exists: {args.name}")
        return

    nsg["rules"][args.name] = {
        "name": args.name,
        "priority": args.priority,
        "direction": args.direction,
        "access": args.access,
        "protocol": args.protocol,
        "source_prefix": args.source_prefix,
        "destination_port": args.destination_port,
    }
    save_state(state)

    ok("NSG rule created")
    print(f"NSG:       {args.nsg}")
    print(f"Name:      {args.name}")
    print(f"Priority:  {args.priority}")
    print(f"Access:    {args.access}")


def nsg_rule_list(args, state):
    nsg = state["nsgs"].get(args.nsg)

    if not nsg:
        fail(f"NSG not found: {args.nsg}")
        return

    print("\n## NAME                 PRIORITY   DIRECTION   ACCESS")
    print("-" * 70)

    for rule in nsg["rules"].values():
        print(
            f"{rule['name']:<22}"
            f"{rule['priority']:<11}"
            f"{rule['direction']:<12}"
            f"{rule['access']}"
        )


# ---------------------------------------------------------------------------
# ROUTING
# ---------------------------------------------------------------------------

def route_table_create(args, state):
    if args.name in state["route_tables"]:
        fail(f"Route table already exists: {args.name}")
        return

    if args.resource_group not in state["groups"]:
        fail(f"Resource Group not found: {args.resource_group}")
        return

    state["route_tables"][args.name] = {
        "name": args.name,
        "resource_group": args.resource_group,
        "routes": {},
    }
    save_state(state)

    ok("Route Table created")
    print(f"Name:  {args.name}")


def route_table_list(args, state):
    print("\n## NAME                 RESOURCE GROUP")
    print("-" * 55)

    for table in state["route_tables"].values():
        print(f"{table['name']:<22} {table['resource_group']}")


def route_create(args, state):
    table = state["route_tables"].get(args.route_table)

    if not table:
        fail(f"Route table not found: {args.route_table}")
        return

    if args.name in table["routes"]:
        fail(f"Route already exists: {args.name}")
        return

    table["routes"][args.name] = {
        "name": args.name,
        "address_prefix": args.address_prefix,
        "next_hop_type": args.next_hop_type,
        "next_hop_ip": args.next_hop_ip,
    }
    save_state(state)

    ok("Route created")
    print(f"Route Table:       {args.route_table}")
    print(f"Name:              {args.name}")
    print(f"Address Prefix:    {args.address_prefix}")
    print(f"Next Hop Type:     {args.next_hop_type}")
    print(f"Next Hop IP:       {args.next_hop_ip or '-'}")


def route_list(args, state):
    table = state["route_tables"].get(args.route_table)

    if not table:
        fail(f"Route table not found: {args.route_table}")
        return

    print("\n## NAME                 PREFIX              NEXT HOP")
    print("-" * 75)

    for route in table["routes"].values():
        print(
            f"{route['name']:<22}"
            f"{route['address_prefix']:<20}"
            f"{route['next_hop_type']}"
        )


def route_associate(args, state):
    subnet = find_subnet(state, args.vnet, args.subnet)

    if not subnet:
        fail("Subnet not found")
        return

    if args.route_table not in state["route_tables"]:
        fail(f"Route table not found: {args.route_table}")
        return

    subnet["route_table"] = args.route_table
    save_state(state)

    ok("Route table associated")
    print(f"VNet:         {args.vnet}")
    print(f"Subnet:       {args.subnet}")
    print(f"Route Table:  {args.route_table}")


def find_route_table_route(state, source_vnet, source_subnet, destination):
    subnet = find_subnet(state, source_vnet, source_subnet)

    if not subnet or not subnet.get("route_table"):
        return None

    table = state["route_tables"].get(subnet["route_table"])
    if not table:
        return None

    candidates = []

    for route in table["routes"].values():
        if prefix_matches_ip(route["address_prefix"], destination):
            network = ipaddress.ip_network(route["address_prefix"], strict=False)
            candidates.append((network.prefixlen, route))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


# ---------------------------------------------------------------------------
# VPN
# ---------------------------------------------------------------------------

def vpn_gateway_create(args, state):
    if args.name in state["vpn_gateways"]:
        fail(f"VPN Gateway already exists: {args.name}")
        return

    if args.vnet not in state["vnets"]:
        fail(f"VNet not found: {args.vnet}")
        return

    state["vpn_gateways"][args.name] = {
        "name": args.name,
        "vnet": args.vnet,
        "sku": args.sku,
        "asn": args.asn,
        "state": "Succeeded",
    }
    save_state(state)

    ok("VPN Gateway created")
    print(f"Name:  {args.name}")
    print(f"VNet:  {args.vnet}")
    print(f"SKU:   {args.sku}")
    print(f"ASN:   {args.asn}")
    print("State: Succeeded")
    print("Mode:  LOCAL SIMULATION")


def vpn_gateway_list(args, state):
    print("\n## NAME                 VNET                 ASN")
    print("-" * 60)

    for gw in state["vpn_gateways"].values():
        print(f"{gw['name']:<22}{gw['vnet']:<21}{gw['asn']}")


def vpn_local_create(args, state):
    if args.name in state["local_gateways"]:
        fail(f"Local Network Gateway already exists: {args.name}")
        return

    state["local_gateways"][args.name] = {
        "name": args.name,
        "ip_address": args.ip_address,
        "address_prefixes": args.address_prefixes,
        "asn": args.asn,
        "bgp_peering_address": args.bgp_peering_address,
    }
    save_state(state)

    ok("Local Network Gateway created")
    print(f"Name:          {args.name}")
    print(f"IP:            {args.ip_address}")
    print(f"Prefixes:      {args.address_prefixes}")
    print(f"ASN:           {args.asn}")
    print(f"BGP Peer IP:   {args.bgp_peering_address}")


def vpn_local_list(args, state):
    print("\n## NAME                 IP                  ASN")
    print("-" * 65)

    for gw in state["local_gateways"].values():
        print(
            f"{gw['name']:<22}"
            f"{gw['ip_address']:<20}"
            f"{gw['asn']}"
        )


def vpn_connection_create(args, state):
    if args.name in state["vpn_connections"]:
        fail(f"VPN connection already exists: {args.name}")
        return

    if args.vpn_gateway not in state["vpn_gateways"]:
        fail(f"VPN Gateway not found: {args.vpn_gateway}")
        return

    if args.local_gateway not in state["local_gateways"]:
        fail(f"Local Network Gateway not found: {args.local_gateway}")
        return

    state["vpn_connections"][args.name] = {
        "name": args.name,
        "vpn_gateway": args.vpn_gateway,
        "local_gateway": args.local_gateway,
        "protocol": "IPsec",
        "bgp": bool(args.bgp),
        "state": "Connected",
    }
    save_state(state)

    ok("VPN connection created")
    print(f"Name:          {args.name}")
    print(f"VPN Gateway:   {args.vpn_gateway}")
    print(f"Local Gateway:  {args.local_gateway}")
    print("Protocol:      IPsec")
    print(f"BGP:           {bool(args.bgp)}")
    print("State:         Connected")


def vpn_connection_list(args, state):
    print("\n## NAME                 VPN GATEWAY            LOCAL GATEWAY")
    print("-" * 80)

    for conn in state["vpn_connections"].values():
        print(
            f"{conn['name']:<22}"
            f"{conn['vpn_gateway']:<23}"
            f"{conn['local_gateway']}"
        )


# ---------------------------------------------------------------------------
# BGP
# ---------------------------------------------------------------------------

def bgp_peer_create(args, state):
    if args.name in state["bgp_peers"]:
        fail(f"BGP peer already exists: {args.name}")
        return

    state["bgp_peers"][args.name] = {
        "name": args.name,
        "local_device": args.local_device,
        "local_asn": args.local_asn,
        "local_ip": args.local_ip,
        "remote_device": args.remote_device,
        "remote_asn": args.remote_asn,
        "remote_ip": args.remote_ip,
        "state": "Established",
    }
    save_state(state)

    ok("BGP peer created")
    print(f"Name:        {args.name}")
    print(f"Local ASN:   {args.local_asn}")
    print(f"Local IP:    {args.local_ip}")
    print(f"Remote ASN:  {args.remote_asn}")
    print(f"Remote IP:   {args.remote_ip}")
    print("State:       Established")


def bgp_peer_list(args, state):
    print("\n## NAME          LOCAL ASN   REMOTE ASN   STATE")
    print("-" * 55)

    for peer in state["bgp_peers"].values():
        print(
            f"{peer['name']:<15}"
            f"{peer['local_asn']:<12}"
            f"{peer['remote_asn']:<13}"
            f"{peer['state']}"
        )


def bgp_advertise(args, state):
    if args.peer not in state["bgp_peers"]:
        fail(f"BGP peer not found: {args.peer}")
        return

    route = {
        "peer": args.peer,
        "prefix": args.prefix,
        "direction": "advertised",
    }

    if route not in state["bgp_routes"]:
        state["bgp_routes"].append(route)

    save_state(state)

    ok("BGP route advertised")
    print(f"Peer:   {args.peer}")
    print(f"Prefix: {args.prefix}")


def bgp_learn(args, state):
    if args.peer not in state["bgp_peers"]:
        fail(f"BGP peer not found: {args.peer}")
        return

    route = {
        "peer": args.peer,
        "prefix": args.prefix,
        "direction": "learned",
    }

    if route not in state["bgp_routes"]:
        state["bgp_routes"].append(route)

    save_state(state)

    ok("BGP route learned")
    print(f"Peer:   {args.peer}")
    print(f"Prefix: {args.prefix}")


def bgp_route_exists(state, prefix):
    for route in state["bgp_routes"]:
        if route["prefix"] == prefix and route["direction"] in (
            "advertised",
            "learned",
        ):
            return True
    return False


# ---------------------------------------------------------------------------
# EXPRESSROUTE
# ---------------------------------------------------------------------------

def expressroute_create(args, state):
    if args.name in state["expressroute_circuits"]:
        fail(f"ExpressRoute circuit already exists: {args.name}")
        return

    state["expressroute_circuits"][args.name] = {
        "name": args.name,
        "provider": args.provider,
        "location": args.location,
        "bandwidth": args.bandwidth,
        "asn": args.asn,
        "state": "Provisioned",
    }

    save_state(state)

    ok("ExpressRoute circuit created")
    print(f"Name:       {args.name}")
    print(f"Provider:   {args.provider}")
    print(f"Location:   {args.location}")
    print(f"Bandwidth:  {args.bandwidth}")
    print(f"ASN:        {args.asn}")
    print("State:      Provisioned")
    print("Mode:       LOCAL SIMULATION")


def expressroute_list(args, state):
    print("\n## NAME                 PROVIDER             LOCATION")
    print("-" * 75)

    for circuit in state["expressroute_circuits"].values():
        print(
            f"{circuit['name']:<22}"
            f"{circuit['provider']:<21}"
            f"{circuit['location']}"
        )


def expressroute_peer(args, state):
    if args.circuit not in state["expressroute_circuits"]:
        fail(f"ExpressRoute circuit not found: {args.circuit}")
        return

    key = f"{args.circuit}:{args.peering_type}"

    if key in state["expressroute_peerings"]:
        fail("ExpressRoute peering already exists")
        return

    state["expressroute_peerings"][key] = {
        "name": key,
        "circuit": args.circuit,
        "peering_type": args.peering_type,
        "vlan": args.vlan,
        "peer_asn": args.peer_asn,
        "peer_ip": args.peer_ip,
        "state": "Established",
    }

    save_state(state)

    ok("ExpressRoute peering created")
    print(f"Circuit:       {args.circuit}")
    print(f"Peering Type:  {args.peering_type}")
    print(f"VLAN:          {args.vlan}")
    print(f"Peer ASN:      {args.peer_asn}")
    print(f"Peer IP:       {args.peer_ip}")
    print("BGP State:     Established")


def expressroute_peer_list(args, state):
    print("\n## CIRCUIT              TYPE             PEER ASN     STATE")
    print("-" * 75)

    for peer in state["expressroute_peerings"].values():
        print(
            f"{peer['circuit']:<22}"
            f"{peer['peering_type']:<17}"
            f"{peer['peer_asn']:<13}"
            f"{peer['state']}"
        )


def expressroute_advertise(args, state):
    if args.circuit not in state["expressroute_circuits"]:
        fail(f"ExpressRoute circuit not found: {args.circuit}")
        return

    peer = None
    for p in state["expressroute_peerings"].values():
        if (
            p["circuit"] == args.circuit
            and p["peering_type"] == args.peering_type
        ):
            peer = p
            break

    if not peer:
        fail(
            f"No {args.peering_type} peering exists on circuit "
            f"{args.circuit}"
        )
        return

    route = {
        "circuit": args.circuit,
        "peering_type": args.peering_type,
        "prefix": args.prefix,
    }

    if route not in state["expressroute_routes"]:
        state["expressroute_routes"].append(route)

    save_state(state)

    ok("ExpressRoute route advertised")
    print(f"Circuit:  {args.circuit}")
    print(f"Peering:  {args.peering_type}")
    print(f"Prefix:   {args.prefix}")


def expressroute_route_exists(state, prefix):
    for route in state["expressroute_routes"]:
        if route["prefix"] == prefix:
            return True
    return False


# ---------------------------------------------------------------------------
# ROUTE SIMULATION
# ---------------------------------------------------------------------------

def find_source_location(state, source):
    for vnet in state["vnets"].values():
        if prefix_contains(vnet["address_prefix"], source):
            for subnet in vnet.get("subnets", {}).values():
                if prefix_contains(subnet["address_prefix"], source):
                    return vnet, subnet
            return vnet, None

    return None, None


def simulate_route(args, state):
    source_vnet_name = None
    source_subnet_name = None
    source_vnet = None
    source_subnet = None

    # Find source VNet/Subnet using dictionary keys.
    for vnet_name, vnet in state["vnets"].items():
        if prefix_contains(vnet["address_prefix"], args.source):
            source_vnet_name = vnet_name
            source_vnet = vnet

            for subnet_name, subnet in vnet.get("subnets", {}).items():
                if prefix_contains(subnet["address_prefix"], args.source):
                    source_subnet_name = subnet_name
                    source_subnet = subnet
                    break

            break

    print()
    print(f"Source:       {args.source}")
    print(f"Destination:  {args.destination}")

    if not source_vnet:
        print()
        fail("Source IP does not belong to a simulated VNet")
        return

    print(f"\nSource VNet:       {source_vnet_name}")
    print(f"Source Subnet:     {source_subnet_name or 'N/A'}")

    # Check whether destination belongs to another simulated VNet.
    destination_vnet_name = None
    destination_vnet = None
    destination_subnet_name = None

    for vnet_name, vnet in state["vnets"].items():
        if prefix_contains(vnet["address_prefix"], args.destination):
            destination_vnet_name = vnet_name
            destination_vnet = vnet

            for subnet_name, subnet in vnet.get("subnets", {}).items():
                if prefix_contains(subnet["address_prefix"], args.destination):
                    destination_subnet_name = subnet_name
                    break

            break

    if destination_vnet:
        print(f"Destination VNet:  {destination_vnet_name}")

        if source_vnet_name == destination_vnet_name:
            print("\n## RESULT")
            print("\n? SAME VNET")
            print("Transport: Virtual Network")
            return

        if are_peered(
            state,
            source_vnet_name,
            destination_vnet_name,
        ):
            print("\n## RESULT")
            print("\n? VNET PEERING")
            print("Transport: VNet Peering")
            print(f"Destination VNet: {destination_vnet_name}")
            return

        print("\n## RESULT")
        fail("No simulated route found")
        return

    print("\nDestination:       HYBRID / EXTERNAL")

    # ---------------------------------------------------------------
    # 1. User Defined Route
    # ---------------------------------------------------------------
    if source_subnet_name:
        route = find_route_table_route(
            state,
            source_vnet_name,
            source_subnet_name,
            args.destination,
        )

        if route:
            print("\n## RESULT")
            print("\n? USER DEFINED ROUTE")
            print(f"Route:            {route['name']}")
            print(f"Next Hop Type:    {route['next_hop_type']}")
            print(f"Next Hop IP:      {route['next_hop_ip'] or '-'}")
            print(f"Destination:      {route['address_prefix']}")
            return

    # ---------------------------------------------------------------
    # 2. ExpressRoute
    # ---------------------------------------------------------------
    matching_er = []

    for route in state.get("expressroute_routes", []):
        if prefix_contains(route["prefix"], args.destination):
            matching_er.append(route)

    if matching_er:
        route = max(
            matching_er,
            key=lambda x: ipaddress.ip_network(
                x["prefix"],
                strict=False,
            ).prefixlen,
        )

        circuit = state.get("expressroute_circuits", {}).get(
            route["circuit"]
        )

        print("\n## RESULT")
        print("\n? EXPRESSROUTE ROUTE")
        print("Transport: ExpressRoute")
        print(f"Circuit:   {route['circuit']}")
        print(
            f"Provider:  "
            f"{circuit['provider'] if circuit else '-'}"
        )
        print(f"Peering:   {route['peering_type']}")
        print("Routing:   BGP")
        print(f"Destination Prefix: {route['prefix']}")
        return

    # ---------------------------------------------------------------
    # 3. VPN + BGP
    # ---------------------------------------------------------------
    matching_bgp = []

    for route in state.get("bgp_routes", []):
        if prefix_contains(route["prefix"], args.destination):
            matching_bgp.append(route)

    if matching_bgp:
        route = max(
            matching_bgp,
            key=lambda x: ipaddress.ip_network(
                x["prefix"],
                strict=False,
            ).prefixlen,
        )

        peer = state.get("bgp_peers", {}).get(route["peer"])

        if peer:
            vpn_gateway = peer["local_device"]
            connection = None

            for conn in state.get("vpn_connections", {}).values():
                if (
                    conn["vpn_gateway"] == vpn_gateway
                    and conn.get("bgp") is True
                ):
                    connection = conn
                    break

            if connection:
                local_gateway = connection["local_gateway"]

                print("\n## RESULT")
                print("\n? HYBRID ROUTE")
                print("Transport: IPsec VPN")
                print(f"VPN Gateway: {vpn_gateway}")
                print(f"Local Network: {local_gateway}")
                print("Routing: BGP")
                print(f"Destination Prefix: {route['prefix']}")
                return

    print("\n## RESULT")
    fail("No simulated route found")



# ---------------------------------------------------------------------------
# AZURE ROUTE SERVER / NVA / HYBRID COEXISTENCE
# ---------------------------------------------------------------------------

def route_server_create(args, state):
    if args.name in state["route_servers"]:
        fail(f"Route Server already exists: {args.name}")
        return
    if args.vnet not in state["vnets"]:
        fail(f"VNet not found: {args.vnet}")
        return
    if args.subnet and args.subnet not in state["vnets"][args.vnet].get("subnets", {}):
        fail(f"Subnet not found: {args.vnet}/{args.subnet}")
        return
    state["route_servers"][args.name] = {
        "name": args.name, "vnet": args.vnet, "subnet": args.subnet,
        "asn": args.asn, "state": "Succeeded", "peerings": {}
    }
    save_state(state)
    ok("Azure Route Server created")
    print(f"Name:       {args.name}")
    print(f"VNet:       {args.vnet}")
    print(f"Subnet:     {args.subnet or '-'}")
    print(f"ASN:        {args.asn}")
    print("State:      Succeeded")
    print("Mode:       LOCAL SIMULATION")


def route_server_list(args, state):
    print("\n## NAME                 VNET                 ASN        STATE")
    print("-" * 75)
    for rs in state["route_servers"].values():
        print(f"{rs['name']:<22}{rs['vnet']:<21}{rs['asn']:<11}{rs.get('state','-')}")


def nva_create(args, state):
    if args.name in state["nvas"]:
        fail(f"NVA already exists: {args.name}")
        return
    vnet = state["vnets"].get(args.vnet)
    if not vnet:
        fail(f"VNet not found: {args.vnet}")
        return
    if args.subnet not in vnet.get("subnets", {}):
        fail(f"Subnet not found: {args.vnet}/{args.subnet}")
        return
    if not prefix_contains(vnet["address_prefix"], args.private_ip):
        fail(f"NVA private IP is outside VNet address space: {args.private_ip}")
        return
    state["nvas"][args.name] = {
        "name": args.name, "vnet": args.vnet, "subnet": args.subnet,
        "private_ip": args.private_ip, "asn": args.asn,
        "state": "Succeeded", "route_server": None
    }
    save_state(state)
    ok("NVA created")
    print(f"Name:        {args.name}")
    print(f"VNet:        {args.vnet}")
    print(f"Subnet:      {args.subnet}")
    print(f"Private IP:  {args.private_ip}")
    print(f"ASN:         {args.asn}")
    print("State:       Succeeded")
    print("Mode:        LOCAL SIMULATION")


def nva_list(args, state):
    print("\n## NAME                 VNET                 SUBNET       IP              ASN")
    print("-" * 90)
    for nva in state["nvas"].values():
        print(f"{nva['name']:<22}{nva['vnet']:<21}{nva['subnet']:<13}{nva['private_ip']:<16}{nva['asn']}")


def route_server_peer_create(args, state):
    rs = state["route_servers"].get(args.route_server)
    nva = state["nvas"].get(args.nva)
    if not rs:
        fail(f"Route Server not found: {args.route_server}")
        return
    if not nva:
        fail(f"NVA not found: {args.nva}")
        return
    if rs["vnet"] != nva["vnet"]:
        fail("Route Server and NVA must be in the same VNet for this simulation")
        return
    if args.name in state["route_server_peers"]:
        fail(f"Route Server peer already exists: {args.name}")
        return
    state["route_server_peers"][args.name] = {
        "name": args.name, "route_server": args.route_server, "nva": args.nva,
        "route_server_asn": rs["asn"], "route_server_ip": args.route_server_ip,
        "nva_asn": nva["asn"], "nva_ip": nva["private_ip"], "state": "Established"
    }
    rs.setdefault("peerings", {})[args.name] = args.nva
    nva["route_server"] = args.route_server
    save_state(state)
    ok("Route Server BGP peer created")
    print(f"Name:             {args.name}")
    print(f"Route Server:     {args.route_server}")
    print(f"Route Server ASN: {rs['asn']}")
    print(f"Route Server IP:  {args.route_server_ip}")
    print(f"NVA:              {args.nva}")
    print(f"NVA ASN:          {nva['asn']}")
    print(f"NVA IP:           {nva['private_ip']}")
    print("State:            Established")


def route_server_peer_list(args, state):
    print("\n## NAME                 ROUTE SERVER         NVA                  STATE")
    print("-" * 80)
    for peer in state["route_server_peers"].values():
        print(f"{peer['name']:<22}{peer['route_server']:<21}{peer['nva']:<21}{peer.get('state','-')}")


def nva_advertise(args, state):
    nva = state["nvas"].get(args.nva)
    if not nva:
        fail(f"NVA not found: {args.nva}")
        return
    if not nva.get("route_server"):
        fail(f"NVA {args.nva} is not connected to a Route Server")
        return
    route = {
        "nva": args.nva, "prefix": args.prefix, "next_hop": nva["private_ip"],
        "route_server": nva["route_server"], "direction": "advertised"
    }
    if route not in state["nva_routes"]:
        state["nva_routes"].append(route)
    save_state(state)
    ok("NVA route advertised to Route Server")
    print(f"NVA:          {args.nva}")
    print(f"Route Server: {nva['route_server']}")
    print(f"Prefix:       {args.prefix}")
    print(f"Next Hop:     {nva['private_ip']}")


def nva_route_list(args, state):
    print("\n## NVA                  PREFIX              NEXT HOP        ROUTE SERVER")
    print("-" * 85)
    for route in state["nva_routes"]:
        print(f"{route['nva']:<22}{route['prefix']:<20}{route['next_hop']:<16}{route['route_server']}")


def hybrid_coexistence_create(args, state):
    if args.name in state["hybrid_coexistence"]:
        fail(f"Hybrid coexistence profile already exists: {args.name}")
        return
    checks = [
        ("VNet", "vnets", args.vnet),
        ("VPN Gateway", "vpn_gateways", args.vpn_gateway),
        ("ExpressRoute circuit", "expressroute_circuits", args.circuit),
        ("Route Server", "route_servers", args.route_server),
        ("NVA", "nvas", args.nva),
    ]
    for label, collection, name in checks:
        if name not in state[collection]:
            fail(f"{label} not found: {name}")
            return
    state["hybrid_coexistence"][args.name] = {
        "name": args.name, "vnet": args.vnet, "vpn_gateway": args.vpn_gateway,
        "expressroute_circuit": args.circuit, "route_server": args.route_server,
        "nva": args.nva, "state": "Active"
    }
    save_state(state)
    ok("Hybrid VPN + ExpressRoute coexistence profile created")
    print(f"Name:             {args.name}")
    print(f"VNet:             {args.vnet}")
    print(f"VPN Gateway:      {args.vpn_gateway}")
    print(f"ExpressRoute:     {args.circuit}")
    print(f"Route Server:     {args.route_server}")
    print(f"NVA:              {args.nva}")
    print("State:            Active")
    print("Mode:             LOCAL SIMULATION")


def hybrid_coexistence_list(args, state):
    print("\n## NAME                 VNET                 VPN GATEWAY           EXPRESSROUTE")
    print("-" * 95)
    for item in state["hybrid_coexistence"].values():
        print(f"{item['name']:<22}{item['vnet']:<21}{item['vpn_gateway']:<21}{item['expressroute_circuit']}")


def hybrid_route_list(args, state):
    print("\n## HYBRID ROUTING SOURCES")
    print("-" * 80)
    print("ExpressRoute routes:")
    for route in state["expressroute_routes"]:
        print(f"  ER   {route['prefix']:<20} circuit={route['circuit']}")
    print("VPN/BGP routes:")
    for route in state["bgp_routes"]:
        print(f"  VPN  {route['prefix']:<20} peer={route['peer']} direction={route['direction']}")
    print("NVA/Route Server routes:")
    for route in state["nva_routes"]:
        print(f"  NVA  {route['prefix']:<20} nva={route['nva']} next-hop={route['next_hop']}")


def simulate_hybrid_route(args, state):
    source_vnet, source_subnet = find_source_location(state, args.source)
    if not source_vnet:
        fail("Source IP does not belong to a simulated VNet")
        return
    source_vnet_name = source_vnet.get("name")
    source_subnet_name = source_subnet.get("name") if source_subnet else None
    print(f"\nSource:       {args.source}")
    print(f"Destination:  {args.destination}")
    print(f"\nSource VNet:       {source_vnet_name}")
    print(f"Source Subnet:     {source_subnet_name or 'N/A'}")
    print("\nDestination:       HYBRID / EXTERNAL")

    candidates = []
    if source_subnet_name:
        udr = find_route_table_route(state, source_vnet_name, source_subnet_name, args.destination)
        if udr:
            prefix_len = ipaddress.ip_network(udr["address_prefix"], strict=False).prefixlen
            candidates.append((prefix_len, 100, "UDR", udr))
    for route in state.get("expressroute_routes", []):
        if prefix_contains(route["prefix"], args.destination):
            prefix_len = ipaddress.ip_network(route["prefix"], strict=False).prefixlen
            candidates.append((prefix_len, 90, "ExpressRoute", route))
    for route in state.get("bgp_routes", []):
        if prefix_contains(route["prefix"], args.destination):
            prefix_len = ipaddress.ip_network(route["prefix"], strict=False).prefixlen
            candidates.append((prefix_len, 80, "VPN", route))
    for route in state.get("nva_routes", []):
        if prefix_contains(route["prefix"], args.destination):
            prefix_len = ipaddress.ip_network(route["prefix"], strict=False).prefixlen
            candidates.append((prefix_len, 70, "NVA", route))

    if not candidates:
        print("\n## RESULT")
        fail("No simulated hybrid route found")
        return

    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    prefix_len, _, transport, route = candidates[0]
    print("\n## RESULT")
    if transport == "UDR":
        print("\n[OK] USER DEFINED ROUTE")
        print(f"Route:            {route['name']}")
        print(f"Next Hop Type:    {route['next_hop_type']}")
        print(f"Next Hop IP:      {route.get('next_hop_ip') or '-'}")
        print(f"Destination Prefix: {route['address_prefix']}")
    elif transport == "ExpressRoute":
        circuit = state["expressroute_circuits"].get(route["circuit"])
        print("\n[OK] EXPRESSROUTE ROUTE")
        print("Transport: ExpressRoute")
        print(f"Circuit:   {route['circuit']}")
        print(f"Provider:  {circuit.get('provider', '-') if circuit else '-'}")
        print(f"Peering:   {route['peering_type']}")
        print("Routing:   BGP")
        print(f"Destination Prefix: {route['prefix']}")
    elif transport == "VPN":
        peer = state["bgp_peers"].get(route["peer"])
        print("\n[OK] VPN / BGP ROUTE")
        print("Transport: IPsec VPN")
        print(f"BGP Peer:  {route['peer']}")
        if peer:
            print(f"VPN Gateway: {peer.get('local_device', '-')}")
        print("Routing:   BGP")
        print(f"Destination Prefix: {route['prefix']}")
    else:
        nva = state["nvas"].get(route["nva"])
        print("\n[OK] ROUTE SERVER / NVA ROUTE")
        print("Transport: Virtual network / NVA")
        print(f"Route Server: {route['route_server']}")
        print(f"NVA:          {route['nva']}")
        print(f"Next Hop:     {route['next_hop']}")
        print(f"NVA ASN:      {nva.get('asn', '-') if nva else '-'}")
        print(f"Destination Prefix: {route['prefix']}")
    print(f"Prefix Length:     /{prefix_len}")
    print("Selection Model:   Longest Prefix + simulated source preference")

# ---------------------------------------------------------------------------
# SHOW / INSPECTION
# ---------------------------------------------------------------------------

def show_running_config(args, state):
    print("\n" + "=" * 78)
    print("AZURE NETWORK SIMULATOR - RUNNING CONFIGURATION")
    print("=" * 78)

    print("\n## RESOURCE GROUPS")
    if state["groups"]:
        for name, item in state["groups"].items():
            print(f"  {name}  location={item['location']}")
    else:
        print("  (none)")

    print("\n## VIRTUAL NETWORKS")
    if state["vnets"]:
        for name, vnet in state["vnets"].items():
            print(
                f"  {name}  "
                f"{vnet['address_prefix']}  "
                f"rg={vnet['resource_group']}"
            )
            for subnet_name, subnet in vnet.get("subnets", {}).items():
                print(
                    f"    subnet {subnet_name} "
                    f"{subnet['address_prefix']} "
                    f"nsg={subnet.get('nsg') or '-'} "
                    f"route-table={subnet.get('route_table') or '-'}"
                )
    else:
        print("  (none)")

    print("\n## VNET PEERING")
    if state["peerings"]:
        for peer in state["peerings"]:
            print(
                f"  {peer['source_vnet']} -> {peer['remote_vnet']} "
                f"state={peer['state']}"
            )
    else:
        print("  (none)")

    print("\n## NETWORK SECURITY GROUPS")
    if state["nsgs"]:
        for name, nsg in state["nsgs"].items():
            print(f"  {name}  rg={nsg['resource_group']}")
            for rule_name, rule in nsg.get("rules", {}).items():
                print(
                    f"    rule {rule_name} "
                    f"priority={rule['priority']} "
                    f"{rule['direction']} "
                    f"{rule['access']} "
                    f"{rule['protocol']} "
                    f"src={rule['source_prefix']} "
                    f"dst-port={rule['destination_port']}"
                )
    else:
        print("  (none)")

    print("\n## ROUTE TABLES / UDR")
    if state["route_tables"]:
        for name, table in state["route_tables"].items():
            print(f"  {name}  rg={table['resource_group']}")
            for route_name, route in table.get("routes", {}).items():
                print(
                    f"    route {route_name} "
                    f"{route['address_prefix']} "
                    f"next-hop={route['next_hop_type']}"
                    f"{' ' + route['next_hop_ip'] if route.get('next_hop_ip') else ''}"
                )
    else:
        print("  (none)")

    print("\n## VPN")
    if state["vpn_gateways"]:
        for name, gw in state["vpn_gateways"].items():
            print(
                f"  gateway {name} "
                f"vnet={gw['vnet']} sku={gw['sku']} asn={gw['asn']} "
                f"state={gw['state']}"
            )
    else:
        print("  gateways: (none)")

    if state["local_gateways"]:
        for name, gw in state["local_gateways"].items():
            print(
                f"  local {name} "
                f"ip={gw['ip_address']} "
                f"prefixes={gw['address_prefixes']} "
                f"asn={gw['asn']} "
                f"bgp-peer={gw['bgp_peering_address']}"
            )
    else:
        print("  local gateways: (none)")

    if state["vpn_connections"]:
        for name, conn in state["vpn_connections"].items():
            print(
                f"  connection {name} "
                f"vpn-gateway={conn['vpn_gateway']} "
                f"local-gateway={conn['local_gateway']} "
                f"protocol={conn['protocol']} "
                f"bgp={conn['bgp']} "
                f"state={conn['state']}"
            )
    else:
        print("  connections: (none)")

    print("\n## BGP")
    if state["bgp_peers"]:
        for name, peer in state["bgp_peers"].items():
            print(
                f"  peer {name} "
                f"{peer['local_ip']} AS{peer['local_asn']} -> "
                f"{peer['remote_ip']} AS{peer['remote_asn']} "
                f"state={peer['state']}"
            )
    else:
        print("  peers: (none)")

    if state["bgp_routes"]:
        for route in state["bgp_routes"]:
            print(
                f"  route {route['prefix']} "
                f"peer={route['peer']} "
                f"direction={route['direction']}"
            )
    else:
        print("  routes: (none)")

    print("\n## AZURE ROUTE SERVER")
    if state["route_servers"]:
        for name, rs in state["route_servers"].items():
            print(f"  route-server {name} vnet={rs['vnet']} subnet={rs.get('subnet','-')} asn={rs['asn']} state={rs.get('state','-')}")
    else:
        print("  route servers: (none)")

    print("\n## NVA")
    if state["nvas"]:
        for name, nva in state["nvas"].items():
            print(f"  nva {name} vnet={nva['vnet']} subnet={nva['subnet']} ip={nva['private_ip']} asn={nva['asn']} route-server={nva.get('route_server') or '-'}")
    else:
        print("  nvas: (none)")

    print("\n## ROUTE SERVER BGP PEERS")
    if state["route_server_peers"]:
        for name, peer in state["route_server_peers"].items():
            print(f"  peer {name} rs={peer['route_server']} nva={peer['nva']} rs-asn={peer['route_server_asn']} nva-asn={peer['nva_asn']} state={peer.get('state','-')}")
    else:
        print("  peers: (none)")

    print("\n## NVA ROUTES")
    if state["nva_routes"]:
        for route in state["nva_routes"]:
            print(f"  route {route['prefix']} nva={route['nva']} next-hop={route['next_hop']} route-server={route['route_server']}")
    else:
        print("  routes: (none)")

    print("\n## HYBRID VPN + EXPRESSROUTE COEXISTENCE")
    if state["hybrid_coexistence"]:
        for name, item in state["hybrid_coexistence"].items():
            print(f"  profile {name} vnet={item['vnet']} vpn={item['vpn_gateway']} expressroute={item['expressroute_circuit']} route-server={item['route_server']} nva={item['nva']} state={item.get('state','-')}")
    else:
        print("  profiles: (none)")

    print("\n## EXPRESSROUTE")
    if state["expressroute_circuits"]:
        for name, circuit in state["expressroute_circuits"].items():
            print(
                f"  circuit {name} "
                f"provider={circuit['provider']} "
                f"location={circuit['location']} "
                f"bandwidth={circuit['bandwidth']} "
                f"asn={circuit['asn']} "
                f"state={circuit['state']}"
            )
    else:
        print("  circuits: (none)")

    if state["expressroute_peerings"]:
        for name, peer in state["expressroute_peerings"].items():
            print(
                f"  peering {name} "
                f"type={peer['peering_type']} "
                f"vlan={peer['vlan']} "
                f"peer-asn={peer['peer_asn']} "
                f"peer-ip={peer['peer_ip']} "
                f"state={peer['state']}"
            )
    else:
        print("  peerings: (none)")

    if state["expressroute_routes"]:
        for route in state["expressroute_routes"]:
            print(
                f"  route {route['prefix']} "
                f"circuit={route['circuit']} "
                f"peering={route['peering_type']}"
            )
    else:
        print("  routes: (none)")

    print("\n" + "=" * 78)


def show_resource(args, state):
    target = args.show_target or "running-config"

    if target in ("running-config", "all"):
        show_running_config(args, state)
        return

    if target == "group":
        print("\n## RESOURCE GROUPS")
        for name, item in state["groups"].items():
            print(f"{name:<24} {item.get('location', '-')}")
        return

    if target == "vnet":
        if args.name:
            vnet = state["vnets"].get(args.name)
            if not vnet:
                fail(f"VNet not found: {args.name}")
                return
            print("\n## VIRTUAL NETWORK")
            print(f"Name:           {args.name}")
            print(f"Address Space:  {vnet.get('address_prefix', '-')}")
            print(f"Resource Group: {vnet.get('resource_group', '-')}")
            print("\n## SUBNETS")
            for name, subnet in vnet.get("subnets", {}).items():
                print(f"{name:<22} {subnet.get('address_prefix', '-')}")
        else:
            print("\n## NAME                 ADDRESS             RESOURCE GROUP")
            print("-" * 70)
            for name, vnet in state["vnets"].items():
                print(f"{name:<22}{vnet.get('address_prefix','-'):<20}{vnet.get('resource_group','-')}")
        return

    if target == "peering":
        print("\n## SOURCE VNET          REMOTE VNET          STATE")
        print("-" * 65)
        for peer in state["peerings"]:
            print(f"{peer.get('source_vnet','-'):<22}{peer.get('remote_vnet','-'):<21}{peer.get('state','-')}")
        return

    if target == "nsg":
        print("\n## NAME                 RESOURCE GROUP")
        print("-" * 55)
        for name, nsg in state["nsgs"].items():
            print(f"{name:<22}{nsg.get('resource_group','-')}")
        return

    if target in ("routes", "route"):
        print("\n## ROUTE TABLES")
        for name, table in state["route_tables"].items():
            print(f"\n{name}  rg={table.get('resource_group','-')}")
            for route_name, route in table.get("routes", {}).items():
                nh = route.get("next_hop_type", "-")
                if route.get("next_hop_ip"):
                    nh += f" {route['next_hop_ip']}"
                print(f"  {route_name:<20}{route.get('address_prefix','-'):<20}{nh}")
        return

    if target == "vpn":
        print("\n## VPN GATEWAYS")
        for name, gw in state["vpn_gateways"].items():
            print(f"{name:<22} vnet={gw.get('vnet','-'):<18} ASN={gw.get('asn','-')} SKU={gw.get('sku','-')} state={gw.get('state','-')}")
        print("\n## LOCAL NETWORK GATEWAYS")
        for name, gw in state["local_gateways"].items():
            print(f"{name:<22} ip={gw.get('ip_address','-'):<16} ASN={gw.get('asn','-')} peer={gw.get('bgp_peering_address','-')}")
        print("\n## VPN CONNECTIONS")
        for name, conn in state["vpn_connections"].items():
            print(f"{name:<22} vpn={conn.get('vpn_gateway','-'):<18} local={conn.get('local_gateway','-'):<18} BGP={conn.get('bgp',False)} state={conn.get('state','-')}")
        return

    if target == "bgp":
        print("\n## BGP PEERS")
        print("NAME                 LOCAL ASN   REMOTE ASN   STATE")
        print("-" * 60)
        for name, peer in state["bgp_peers"].items():
            print(f"{name:<21}{peer.get('local_asn','-'):<12}{peer.get('remote_asn','-'):<13}{peer.get('state','-')}")
        print("\n## BGP ROUTES")
        for route in state["bgp_routes"]:
            print(f"{route.get('direction','-'):<12}{route.get('prefix','-'):<20}peer={route.get('peer','-')}")
        return

    if target == "route-server":
        route_server_list(args, state)
        return

    if target == "nva":
        nva_list(args, state)
        return

    if target in ("route-server-peers", "route-server-peer"):
        route_server_peer_list(args, state)
        return

    if target in ("nva-routes", "hybrid-routes"):
        hybrid_route_list(args, state)
        return

    if target == "coexistence":
        hybrid_coexistence_list(args, state)
        return

    if target == "expressroute":
        print("\n## EXPRESSROUTE CIRCUITS")
        print("NAME                 PROVIDER             LOCATION")
        print("-" * 75)
        for name, circuit in state["expressroute_circuits"].items():
            print(f"{name:<21}{circuit.get('provider','-'):<21}{circuit.get('location','-')}")
        print("\n## EXPRESSROUTE PEERINGS")
        for name, peer in state["expressroute_peerings"].items():
            print(f"{name:<21}{peer.get('peering_type','-'):<16}ASN={peer.get('peer_asn','-'):<10}state={peer.get('state','-')}")
        print("\n## ADVERTISED ROUTES")
        for route in state["expressroute_routes"]:
            print(f"{route.get('prefix','-'):<20}circuit={route.get('circuit','-'):<20}peering={route.get('peering_type','-')}")
        return

    fail(f"Unknown show target: {target}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="azsim",
        description="Local Azure Network Simulator",
    )

    resources = parser.add_subparsers(dest="resource", required=True)

    # GROUP
    group = resources.add_parser("group")
    group_cmd = group.add_subparsers(dest="command", required=True)

    p = group_cmd.add_parser("create")
    p.add_argument("--name", required=True)
    p.add_argument("--location", required=True)

    group_cmd.add_parser("list")

    # VNET
    vnet = resources.add_parser("vnet")
    vnet_cmd = vnet.add_subparsers(dest="command", required=True)

    p = vnet_cmd.add_parser("create")
    p.add_argument("--resource-group", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--address-prefix", required=True)

    vnet_cmd.add_parser("list")

    p = vnet_cmd.add_parser("show")
    p.add_argument("--name", required=True)

    # SUBNET
    subnet = resources.add_parser("subnet")
    subnet_cmd = subnet.add_subparsers(dest="command", required=True)

    p = subnet_cmd.add_parser("create")
    p.add_argument("--resource-group", required=True)
    p.add_argument("--vnet", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--address-prefix", required=True)

    p = subnet_cmd.add_parser("list")
    p.add_argument("--vnet", required=True)

    p = subnet_cmd.add_parser("associate-nsg")
    p.add_argument("--vnet", required=True)
    p.add_argument("--subnet", required=True)
    p.add_argument("--nsg", required=True)

    # PEERING
    peering = resources.add_parser("peering")
    peering_cmd = peering.add_subparsers(dest="command", required=True)

    p = peering_cmd.add_parser("create")
    p.add_argument("--source-vnet", required=True)
    p.add_argument("--remote-vnet", required=True)

    peering_cmd.add_parser("list")

    # NSG
    nsg = resources.add_parser("nsg")
    nsg_cmd = nsg.add_subparsers(dest="command", required=True)

    p = nsg_cmd.add_parser("create")
    p.add_argument("--resource-group", required=True)
    p.add_argument("--name", required=True)

    nsg_cmd.add_parser("list")

    rule = nsg_cmd.add_parser("rule")
    rule_cmd = rule.add_subparsers(dest="rule_command", required=True)

    p = rule_cmd.add_parser("create")
    p.add_argument("--nsg", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--priority", required=True, type=int)
    p.add_argument("--direction", required=True)
    p.add_argument("--access", required=True)
    p.add_argument("--protocol", required=True)
    p.add_argument("--source-prefix", required=True)
    p.add_argument("--destination-port", required=True)

    p = rule_cmd.add_parser("list")
    p.add_argument("--nsg", required=True)

    # ROUTE
    route = resources.add_parser("route")
    route_cmd = route.add_subparsers(dest="command", required=True)

    p = route_cmd.add_parser("table-create")
    p.add_argument("--resource-group", required=True)
    p.add_argument("--name", required=True)

    route_cmd.add_parser("table-list")

    p = route_cmd.add_parser("create")
    p.add_argument("--route-table", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--address-prefix", required=True)
    p.add_argument("--next-hop-type", required=True)
    p.add_argument("--next-hop-ip")

    p = route_cmd.add_parser("list")
    p.add_argument("--route-table", required=True)

    p = route_cmd.add_parser("associate")
    p.add_argument("--vnet", required=True)
    p.add_argument("--subnet", required=True)
    p.add_argument("--route-table", required=True)

    p = route_cmd.add_parser("simulate")
    p.add_argument("--source", required=True)
    p.add_argument("--destination", required=True)

    # VPN
    vpn = resources.add_parser("vpn")
    vpn_cmd = vpn.add_subparsers(dest="command", required=True)

    p = vpn_cmd.add_parser("gateway-create")
    p.add_argument("--name", required=True)
    p.add_argument("--vnet", required=True)
    p.add_argument("--sku", required=True)
    p.add_argument("--asn", required=True, type=int)

    vpn_cmd.add_parser("gateway-list")

    p = vpn_cmd.add_parser("local-create")
    p.add_argument("--name", required=True)
    p.add_argument("--ip-address", required=True)
    p.add_argument("--address-prefixes", required=True)
    p.add_argument("--asn", required=True, type=int)
    p.add_argument("--bgp-peering-address", required=True)

    vpn_cmd.add_parser("local-list")

    p = vpn_cmd.add_parser("connection-create")
    p.add_argument("--name", required=True)
    p.add_argument("--vpn-gateway", required=True)
    p.add_argument("--local-gateway", required=True)
    p.add_argument("--bgp", action="store_true")

    vpn_cmd.add_parser("connection-list")

    # BGP
    bgp = resources.add_parser("bgp")
    bgp_cmd = bgp.add_subparsers(dest="command", required=True)

    p = bgp_cmd.add_parser("peer-create")
    p.add_argument("--name", required=True)
    p.add_argument("--local-device", required=True)
    p.add_argument("--local-asn", required=True, type=int)
    p.add_argument("--local-ip", required=True)
    p.add_argument("--remote-device", required=True)
    p.add_argument("--remote-asn", required=True, type=int)
    p.add_argument("--remote-ip", required=True)

    bgp_cmd.add_parser("peer-list")

    p = bgp_cmd.add_parser("advertise")
    p.add_argument("--peer", required=True)
    p.add_argument("--prefix", required=True)

    p = bgp_cmd.add_parser("learn")
    p.add_argument("--peer", required=True)
    p.add_argument("--prefix", required=True)

    # EXPRESSROUTE
    er = resources.add_parser("expressroute")
    er_cmd = er.add_subparsers(dest="command", required=True)

    p = er_cmd.add_parser("create")
    p.add_argument("--name", required=True)
    p.add_argument("--provider", required=True)
    p.add_argument("--location", required=True)
    p.add_argument("--bandwidth", required=True)
    p.add_argument("--asn", required=True, type=int)

    er_cmd.add_parser("list")

    p = er_cmd.add_parser("peer")
    p.add_argument("--circuit", required=True)
    p.add_argument(
        "--peering-type",
        required=True,
        choices=["private", "microsoft", "public"],
    )
    p.add_argument("--vlan", required=True, type=int)
    p.add_argument("--peer-asn", required=True, type=int)
    p.add_argument("--peer-ip", required=True)

    er_cmd.add_parser("peer-list")

    p = er_cmd.add_parser("advertise")
    p.add_argument("--circuit", required=True)
    p.add_argument(
        "--peering-type",
        required=True,
        choices=["private", "microsoft", "public"],
    )
    p.add_argument("--prefix", required=True)

    # ROUTE SERVER
    rs = resources.add_parser("route-server", help="Azure Route Server simulation")
    rs_cmd = rs.add_subparsers(dest="command", required=True)
    p = rs_cmd.add_parser("create")
    p.add_argument("--name", required=True)
    p.add_argument("--vnet", required=True)
    p.add_argument("--subnet")
    p.add_argument("--asn", required=True, type=int)
    rs_cmd.add_parser("list")
    p = rs_cmd.add_parser("peer-create")
    p.add_argument("--name", required=True)
    p.add_argument("--route-server", required=True)
    p.add_argument("--nva", required=True)
    p.add_argument("--route-server-ip", required=True)
    rs_cmd.add_parser("peer-list")

    # NVA
    nva = resources.add_parser("nva", help="Network Virtual Appliance simulation")
    nva_cmd = nva.add_subparsers(dest="command", required=True)
    p = nva_cmd.add_parser("create")
    p.add_argument("--name", required=True)
    p.add_argument("--vnet", required=True)
    p.add_argument("--subnet", required=True)
    p.add_argument("--private-ip", required=True)
    p.add_argument("--asn", required=True, type=int)
    nva_cmd.add_parser("list")
    p = nva_cmd.add_parser("advertise")
    p.add_argument("--nva", required=True)
    p.add_argument("--prefix", required=True)
    nva_cmd.add_parser("route-list")

    # HYBRID COEXISTENCE
    hybrid = resources.add_parser("hybrid", help="VPN + ExpressRoute + Route Server + NVA coexistence")
    hybrid_cmd = hybrid.add_subparsers(dest="command", required=True)
    p = hybrid_cmd.add_parser("create")
    p.add_argument("--name", required=True)
    p.add_argument("--vnet", required=True)
    p.add_argument("--vpn-gateway", required=True)
    p.add_argument("--circuit", required=True)
    p.add_argument("--route-server", required=True)
    p.add_argument("--nva", required=True)
    hybrid_cmd.add_parser("list")
    p = hybrid_cmd.add_parser("route-simulate")
    p.add_argument("--source", required=True)
    p.add_argument("--destination", required=True)
    hybrid_cmd.add_parser("route-list")

    # SHOW
    show = resources.add_parser(
        "show",
        help="Inspect the current simulated configuration",
    )
    show_cmd = show.add_subparsers(
        dest="show_target",
        required=False,
    )

    for target in (
        "running-config",
        "all",
        "group",
        "vnet",
        "peering",
        "nsg",
        "routes",
        "route",
        "vpn",
        "bgp",
        "expressroute",
        "route-server",
        "nva",
        "route-server-peers",
        "nva-routes",
        "hybrid-routes",
        "coexistence",
    ):
        p = show_cmd.add_parser(target)
        if target == "vnet":
            p.add_argument("--name")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    state = load_state()

    if args.resource == "show":
        if not getattr(args, "show_target", None):
            args.show_target = "running-config"
        show_resource(args, state)
        return

    if args.resource == "nsg" and args.command == "rule":
        if args.rule_command == "create":
            nsg_rule_create(args, state)
            return

        if args.rule_command == "list":
            nsg_rule_list(args, state)
            return

    handlers = {
        ("group", "create"): group_create,
        ("group", "list"): group_list,
        ("vnet", "create"): vnet_create,
        ("vnet", "list"): vnet_list,
        ("vnet", "show"): vnet_show,
        ("subnet", "create"): create_subnet,
        ("subnet", "list"): subnet_list,
        ("subnet", "associate-nsg"): subnet_associate_nsg,
        ("peering", "create"): peering_create,
        ("peering", "list"): peering_list,
        ("nsg", "create"): nsg_create,
        ("nsg", "list"): nsg_list,
        ("route", "table-create"): route_table_create,
        ("route", "table-list"): route_table_list,
        ("route", "create"): route_create,
        ("route", "list"): route_list,
        ("route", "associate"): route_associate,
        ("route", "simulate"): simulate_route,
        ("vpn", "gateway-create"): vpn_gateway_create,
        ("vpn", "gateway-list"): vpn_gateway_list,
        ("vpn", "local-create"): vpn_local_create,
        ("vpn", "local-list"): vpn_local_list,
        ("vpn", "connection-create"): vpn_connection_create,
        ("vpn", "connection-list"): vpn_connection_list,
        ("bgp", "peer-create"): bgp_peer_create,
        ("bgp", "peer-list"): bgp_peer_list,
        ("bgp", "advertise"): bgp_advertise,
        ("bgp", "learn"): bgp_learn,
        ("expressroute", "create"): expressroute_create,
        ("expressroute", "list"): expressroute_list,
        ("expressroute", "peer"): expressroute_peer,
        ("expressroute", "peer-list"): expressroute_peer_list,
        ("expressroute", "advertise"): expressroute_advertise,
        ("route-server", "create"): route_server_create,
        ("route-server", "list"): route_server_list,
        ("route-server", "peer-create"): route_server_peer_create,
        ("route-server", "peer-list"): route_server_peer_list,
        ("nva", "create"): nva_create,
        ("nva", "list"): nva_list,
        ("nva", "advertise"): nva_advertise,
        ("nva", "route-list"): nva_route_list,
        ("hybrid", "create"): hybrid_coexistence_create,
        ("hybrid", "list"): hybrid_coexistence_list,
        ("hybrid", "route-simulate"): simulate_hybrid_route,
        ("hybrid", "route-list"): hybrid_route_list,
    }

    handler = handlers.get((args.resource, args.command))

    if handler:
        handler(args, state)
    else:
        parser.error("Unsupported command")


if __name__ == "__main__":
    main()

