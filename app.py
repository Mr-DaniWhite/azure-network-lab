import argparse
import json
from pathlib import Path


STATE_FILE = Path("data/state.json")


# ============================================================
# STATE
# ============================================================

DEFAULT_STATE = {
    "resource_groups": {},
    "vnets": {},
    "peerings": {},
    "nsgs": {},
}


def load_state():
    """Load and normalize simulator state."""

    if not STATE_FILE.exists() or STATE_FILE.stat().st_size == 0:
        return DEFAULT_STATE.copy()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)

    except json.JSONDecodeError:
        print("⚠ Invalid state.json. Creating a new state.")
        return DEFAULT_STATE.copy()

    # Compatibility with previous versions
    state.setdefault("resource_groups", {})
    state.setdefault("vnets", {})
    state.setdefault("peerings", {})
    state.setdefault("nsgs", {})

    # Old VNets may not have subnets
    for vnet in state["vnets"].values():
        vnet.setdefault("subnets", {})

    # Old NSGs may not have rules
    for nsg in state["nsgs"].values():
        nsg.setdefault("rules", {})

    return state


def save_state(state):
    """Save simulator state."""

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
# RESOURCE GROUPS
# ============================================================

def create_group(args, state):

    if args.name in state["resource_groups"]:
        print(
            f"✗ Resource group "
            f"'{args.name}' already exists"
        )
        return

    state["resource_groups"][args.name] = {
        "location": args.location
    }

    save_state(state)

    print()
    print("✓ Resource group created")
    print(f"  Name:     {args.name}")
    print(f"  Location: {args.location}")
    print("  Mode:     LOCAL SIMULATION")


def list_groups(state):

    print()
    print("NAME          LOCATION")
    print("-" * 40)

    if not state["resource_groups"]:
        print("No resource groups")
        return

    for name, group in state[
        "resource_groups"
    ].items():

        print(
            f"{name:<14}"
            f"{group['location']}"
        )


# ============================================================
# VNET
# ============================================================

def create_vnet(args, state):

    if args.resource_group not in state[
        "resource_groups"
    ]:
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

        "resource_group":
            args.resource_group,

        "location":
            location,

        "address_prefix":
            args.address_prefix,

        "subnets":
            {},
    }

    save_state(state)

    print()
    print("✓ Virtual network created")
    print(f"  Name:           {args.name}")
    print(
        f"  Resource Group: "
        f"{args.resource_group}"
    )
    print(f"  Region:         {location}")
    print(
        f"  Address Space: "
        f"{args.address_prefix}"
    )
    print("  Mode:            LOCAL SIMULATION")


def list_vnets(state):

    print()
    print(
        "NAME          REGION          ADDRESS SPACE"
    )
    print("-" * 60)

    if not state["vnets"]:
        print("No virtual networks")
        return

    for name, vnet in state[
        "vnets"
    ].items():

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

    vnet.setdefault(
        "subnets",
        {}
    )

    print()
    print("VIRTUAL NETWORK")
    print("-" * 50)

    print(
        f"Name:           {args.name}"
    )

    print(
        f"Resource Group: "
        f"{vnet['resource_group']}"
    )

    print(
        f"Region:         "
        f"{vnet['location']}"
    )

    print(
        f"Address Space:  "
        f"{vnet['address_prefix']}"
    )

    print()
    print("SUBNETS")
    print("-" * 50)

    if not vnet["subnets"]:
        print("No subnets")
        return

    for name, subnet in vnet[
        "subnets"
    ].items():

        print(
            f"{name:<16}"
            f"{subnet['address_prefix']}"
        )


# ============================================================
# SUBNETS
# ============================================================

def create_subnet(args, state):

    if args.resource_group not in state[
        "resource_groups"
    ]:
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

    # Compatibility with older VNets
    vnet.setdefault(
        "subnets",
        {}
    )

    if args.name in vnet["subnets"]:
        print(
            f"✗ Subnet "
            f"'{args.name}' already exists"
        )
        return

    vnet["subnets"][args.name] = {

        "address_prefix":
            args.address_prefix,

        "nsg":
            None,
    }

    save_state(state)

    print()
    print("✓ Subnet created")
    print(f"  Name:          {args.name}")
    print(f"  VNet:          {args.vnet}")
    print(
        f"  Address Space: "
        f"{args.address_prefix}"
    )
    print("  NSG:            None")
    print("  Mode:           LOCAL SIMULATION")


def list_subnets(args, state):

    if args.vnet not in state["vnets"]:
        print(
            f"✗ VNet "
            f"'{args.vnet}' not found"
        )
        return

    vnet = state["vnets"][args.vnet]

    vnet.setdefault(
        "subnets",
        {}
    )

    save_state(state)

    print()
    print(
        "SUBNET        VNET          "
        "ADDRESS SPACE      NSG"
    )
    print("-" * 75)

    if not vnet["subnets"]:
        print("No subnets")
        return

    for name, subnet in vnet[
        "subnets"
    ].items():

        print(
            f"{name:<14}"
            f"{args.vnet:<14}"
            f"{subnet['address_prefix']:<19}"
            f"{subnet.get('nsg') or 'None'}"
        )


# ============================================================
# VNET PEERING
# ============================================================

def create_peering(args, state):

    if args.source_vnet not in state[
        "vnets"
    ]:
        print(
            f"✗ Source VNet "
            f"'{args.source_vnet}' not found"
        )
        return

    if args.remote_vnet not in state[
        "vnets"
    ]:
        print(
            f"✗ Remote VNet "
            f"'{args.remote_vnet}' not found"
        )
        return

    if args.source_vnet == args.remote_vnet:
        print(
            "✗ A VNet cannot peer "
            "with itself"
        )
        return

    peering_id = (
        f"{args.source_vnet}"
        f"->{args.remote_vnet}"
    )

    if peering_id in state[
        "peerings"
    ]:
        print(
            "✗ Peering already exists"
        )
        return

    source = state[
        "vnets"
    ][args.source_vnet]

    remote = state[
        "vnets"
    ][args.remote_vnet]

    state["peerings"][peering_id] = {

        "source_vnet":
            args.source_vnet,

        "remote_vnet":
            args.remote_vnet,

        "source_region":
            source["location"],

        "remote_region":
            remote["location"],

        "state":
            "Connected",
    }

    save_state(state)

    print()
    print("✓ VNet peering created")

    print(
        f"  Source:  "
        f"{args.source_vnet}"
    )

    print(
        f"  Remote:  "
        f"{args.remote_vnet}"
    )

    print(
        f"  Regions: "
        f"{source['location']} → "
        f"{remote['location']}"
    )

    print("  State:   Connected")
    print("  Mode:    LOCAL SIMULATION")


def list_peerings(state):

    print()
    print(
        "SOURCE VNET     "
        "REMOTE VNET     "
        "STATE"
    )

    print("-" * 60)

    if not state["peerings"]:
        print("No peerings")
        return

    for peering in state[
        "peerings"
    ].values():

        print(
            f"{peering['source_vnet']:<16}"
            f"{peering['remote_vnet']:<16}"
            f"{peering['state']}"
        )


# ============================================================
# NSG
# ============================================================

def create_nsg(args, state):

    state.setdefault(
        "nsgs",
        {}
    )

    if args.resource_group not in state[
        "resource_groups"
    ]:
        print(
            f"✗ Resource group "
            f"'{args.resource_group}' not found"
        )
        return

    if args.name in state["nsgs"]:
        print(
            f"✗ NSG "
            f"'{args.name}' already exists"
        )
        return

    location = state[
        "resource_groups"
    ][args.resource_group]["location"]

    state["nsgs"][args.name] = {

        "resource_group":
            args.resource_group,

        "location":
            location,

        "rules":
            {},
    }

    save_state(state)

    print()
    print(
        "✓ Network Security Group created"
    )

    print(
        f"  Name:     {args.name}"
    )

    print(
        f"  RG:       "
        f"{args.resource_group}"
    )

    print(
        f"  Location: "
        f"{location}"
    )

    print("  Mode:     LOCAL SIMULATION")


def list_nsgs(state):

    print()
    print(
        "NAME          "
        "RESOURCE GROUP     "
        "REGION"
    )

    print("-" * 65)

    if not state["nsgs"]:
        print("No NSGs")
        return

    for name, nsg in state[
        "nsgs"
    ].items():

        print(
            f"{name:<14}"
            f"{nsg['resource_group']:<20}"
            f"{nsg['location']}"
        )


def create_nsg_rule(args, state):

    state.setdefault(
        "nsgs",
        {}
    )

    if args.nsg not in state[
        "nsgs"
    ]:
        print(
            f"✗ NSG "
            f"'{args.nsg}' not found"
        )
        return

    nsg = state[
        "nsgs"
    ][args.nsg]

    nsg.setdefault(
        "rules",
        {}
    )

    if args.name in nsg[
        "rules"
    ]:
        print(
            f"✗ Rule "
            f"'{args.name}' already exists"
        )
        return

    # Prevent duplicate priorities
    for rule in nsg[
        "rules"
    ].values():

        if rule["priority"] == args.priority:

            print(
                f"✗ Priority "
                f"{args.priority} "
                f"already exists"
            )

            return

    nsg["rules"][args.name] = {

        "priority":
            args.priority,

        "direction":
            args.direction,

        "access":
            args.access,

        "protocol":
            args.protocol,

        "source_prefix":
            args.source_prefix,

        "destination_port":
            args.destination_port,
    }

    save_state(state)

    print()
    print("✓ NSG rule created")

    print(
        f"  Name:       "
        f"{args.name}"
    )

    print(
        f"  Priority:   "
        f"{args.priority}"
    )

    print(
        f"  Direction:  "
        f"{args.direction}"
    )

    print(
        f"  Access:     "
        f"{args.access}"
    )

    print(
        f"  Protocol:   "
        f"{args.protocol}"
    )

    print(
        f"  Source:     "
        f"{args.source_prefix}"
    )

    print(
        f"  Port:       "
        f"{args.destination_port}"
    )

    print(
        "  Mode:       "
        "LOCAL SIMULATION"
    )


def list_nsg_rules(args, state):

    state.setdefault(
        "nsgs",
        {}
    )

    if args.nsg not in state[
        "nsgs"
    ]:
        print(
            f"✗ NSG "
            f"'{args.nsg}' not found"
        )
        return

    rules = state[
        "nsgs"
    ][args.nsg].get(
        "rules",
        {}
    )

    print()
    print(
        "NAME          "
        "PRIORITY  "
        "DIRECTION  "
        "ACCESS  "
        "PROTOCOL  "
        "SOURCE       "
        "PORT"
    )

    print("-" * 100)

    if not rules:
        print("No NSG rules")
        return

    for name, rule in sorted(
        rules.items(),
        key=lambda item:
        item[1]["priority"]
    ):

        print(
            f"{name:<14}"
            f"{rule['priority']:<10}"
            f"{rule['direction']:<11}"
            f"{rule['access']:<8}"
            f"{rule['protocol']:<10}"
            f"{rule['source_prefix']:<13}"
            f"{rule['destination_port']}"
        )


# ============================================================
# NSG ASSOCIATION TO SUBNET
# ============================================================

def associate_nsg(args, state):

    if args.vnet not in state[
        "vnets"
    ]:
        print(
            f"✗ VNet "
            f"'{args.vnet}' not found"
        )
        return

    if args.nsg not in state[
        "nsgs"
    ]:
        print(
            f"✗ NSG "
            f"'{args.nsg}' not found"
        )
        return

    vnet = state[
        "vnets"
    ][args.vnet]

    vnet.setdefault(
        "subnets",
        {}
    )

    if args.subnet not in vnet[
        "subnets"
    ]:
        print(
            f"✗ Subnet "
            f"'{args.subnet}' not found"
        )
        return

    subnet = vnet[
        "subnets"
    ][args.subnet]

    subnet["nsg"] = args.nsg

    save_state(state)

    print()
    print("✓ NSG associated to subnet")

    print(
        f"  VNet:    "
        f"{args.vnet}"
    )

    print(
        f"  Subnet:  "
        f"{args.subnet}"
    )

    print(
        f"  NSG:     "
        f"{args.nsg}"
    )

    print(
        "  Mode:    "
        "LOCAL SIMULATION"
    )


# ============================================================
# CLI
# ============================================================

def build_parser():

    parser = argparse.ArgumentParser(

        prog="azsim",

        description=(
            "Azure Network Simulator "
            "- LOCAL MODE"
        ),
    )

    sub = parser.add_subparsers(
        dest="resource"
    )

    # ========================================================
    # GROUP
    # ========================================================

    group = sub.add_parser(
        "group",
        help="Manage resource groups"
    )

    group_sub = group.add_subparsers(
        dest="action"
    )

    group_create = group_sub.add_parser(
        "create"
    )

    group_create.add_argument(
        "--name",
        required=True
    )

    group_create.add_argument(
        "--location",
        required=True
    )

    group_sub.add_parser(
        "list"
    )

    # ========================================================
    # VNET
    # ========================================================

    vnet = sub.add_parser(
        "vnet",
        help="Manage virtual networks"
    )

    vnet_sub = vnet.add_subparsers(
        dest="action"
    )

    vnet_create = vnet_sub.add_parser(
        "create"
    )

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

    vnet_sub.add_parser(
        "list"
    )

    vnet_show = vnet_sub.add_parser(
        "show"
    )

    vnet_show.add_argument(
        "--name",
        required=True
    )

    # ========================================================
    # SUBNET
    # ========================================================

    subnet = sub.add_parser(
        "subnet",
        help="Manage subnets"
    )

    subnet_sub = subnet.add_subparsers(
        dest="action"
    )

    subnet_create = subnet_sub.add_parser(
        "create"
    )

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

    subnet_list = subnet_sub.add_parser(
        "list"
    )

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

    peering = sub.add_parser(
        "peering",
        help="Manage VNet peerings"
    )

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

    peering_sub.add_parser(
        "list"
    )

    # ========================================================
    # NSG
    # ========================================================

    nsg = sub.add_parser(
        "nsg",
        help="Manage Network Security Groups"
    )

    nsg_sub = nsg.add_subparsers(
        dest="action"
    )

    nsg_create = nsg_sub.add_parser(
        "create"
    )

    nsg_create.add_argument(
        "--resource-group",
        required=True
    )

    nsg_create.add_argument(
        "--name",
        required=True
    )

    nsg_sub.add_parser(
        "list"
    )

    # --------------------------------------------------------
    # NSG RULE
    # --------------------------------------------------------

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

    return parser


# ============================================================
# MAIN
# ============================================================

def main():

    parser = build_parser()

    args = parser.parse_args()

    state = load_state()

    # ========================================================
    # GROUP
    # ========================================================

    if (
        args.resource == "group"
        and args.action == "create"
    ):
        create_group(
            args,
            state
        )

    elif (
        args.resource == "group"
        and args.action == "list"
    ):
        list_groups(
            state
        )

    # ========================================================
    # VNET
    # ========================================================

    elif (
        args.resource == "vnet"
        and args.action == "create"
    ):
        create_vnet(
            args,
            state
        )

    elif (
        args.resource == "vnet"
        and args.action == "list"
    ):
        list_vnets(
            state
        )

    elif (
        args.resource == "vnet"
        and args.action == "show"
    ):
        show_vnet(
            args,
            state
        )

    # ========================================================
    # SUBNET
    # ========================================================

    elif (
        args.resource == "subnet"
        and args.action == "create"
    ):
        create_subnet(
            args,
            state
        )

    elif (
        args.resource == "subnet"
        and args.action == "list"
    ):
        list_subnets(
            args,
            state
        )

    elif (
        args.resource == "subnet"
        and args.action == "associate-nsg"
    ):
        associate_nsg(
            args,
            state
        )

    # ========================================================
    # PEERING
    # ========================================================

    elif (
        args.resource == "peering"
        and args.action == "create"
    ):
        create_peering(
            args,
            state
        )

    elif (
        args.resource == "peering"
        and args.action == "list"
    ):
        list_peerings(
            state
        )

    # ========================================================
    # NSG
    # ========================================================

    elif (
        args.resource == "nsg"
        and args.action == "create"
    ):
        create_nsg(
            args,
            state
        )

    elif (
        args.resource == "nsg"
        and args.action == "list"
    ):
        list_nsgs(
            state
        )

    elif (
        args.resource == "nsg"
        and args.action == "rule"
        and args.rule_action == "create"
    ):
        create_nsg_rule(
            args,
            state
        )

    elif (
        args.resource == "nsg"
        and args.action == "rule"
        and args.rule_action == "list"
    ):
        list_nsg_rules(
            args,
            state
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()