# ☁️ Azure Network Simulator

> 🧪 **Local Azure Networking Lab**
>
> A lightweight CLI-based simulator for learning and practicing
> **Azure Networking, AZ-700 concepts and Hybrid Networking**
> without an Azure subscription or cloud resources.

---

## 🎯 What is this?

Azure Network Simulator is a **local networking laboratory** written in Python.

It does **not** create real Azure resources.

Instead, it models Azure networking concepts locally so you can practice:

- 🌐 Virtual Networks
- 📦 Subnets
- 🔗 VNet Peering
- 🛡️ Network Security Groups
- 🛣️ Route Tables
- 🧭 User Defined Routes
- 🔍 Route selection
- 🔐 VPN Gateway
- 🏢 Local Network Gateway
- 🔒 IPsec VPN connections
- 🛰️ BGP
- 📡 Azure Route Server
- 🧱 Network Virtual Appliances
- ⚡ ExpressRoute
- 🌍 Virtual WAN
- 🔀 Hybrid routing

The simulator stores its topology locally in:

```text
data/state.json

🏗️ Architecture

The project is intentionally simple:

                   ┌───────────────────────────┐
                   │       Azure Simulator     │
                   │                           │
                   │        app.py             │
                   │                           │
                   │   CLI + Network Logic     │
                   └─────────────┬─────────────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │  state.json   │
                         │               │
                         │  Local State  │
                         └───────────────┘

Everything runs locally.

No:

❌ Azure subscription
❌ Azure CLI authentication
❌ Credit card
❌ Cloud resources
❌ Virtual machines
❌ Real network traffic
❌ Internet connectivity
🚀 Installation
Requirements
Python 3.12+
Git
uv
▶️ Run the simulator

From the project directory:

uv run .\app.py --help

General syntax:

uv run .\app.py <resource> <action> [options]
📚 Supported Resources
Resource	Purpose
group	Resource Groups
vnet	Virtual Networks
subnet	Subnets
peering	VNet Peering
nsg	Network Security Groups
route	Route Tables, UDR and route simulation
vpn	VPN Gateway and hybrid VPN
bgp	BGP peers and routes
route-server	Azure Route Server
nva	Network Virtual Appliances
expressroute	ExpressRoute
wan	Virtual WAN
📦 Resource Groups

Resource Groups are used to logically organize Azure resources.

Create
uv run .\app.py group create `
  --name rg-weu `
  --location westeurope
List
uv run .\app.py group list

Example:

NAME          LOCATION
----------------------------------------
rg-weu        westeurope
rg-neu        northeurope
🌐 Virtual Networks

Create Azure Virtual Networks.

Create
uv run .\app.py vnet create `
  --resource-group rg-weu `
  --name vnet-weu `
  --address-prefix 10.10.0.0/16

Create another region:

uv run .\app.py vnet create `
  --resource-group rg-neu `
  --name vnet-neu `
  --address-prefix 10.20.0.0/16
List
uv run .\app.py vnet list
Show VNet
uv run .\app.py vnet show `
  --name vnet-weu

Example:

VIRTUAL NETWORK
----------------------------------------------------------------------

Name:           vnet-weu
Region:         westeurope
Address Space:  10.10.0.0/16

SUBNETS
----------------------------------------------------------------------

web             10.10.1.0/24
📦 Subnets

Create subnets inside a VNet.

Create
uv run .\app.py subnet create `
  --resource-group rg-weu `
  --vnet vnet-weu `
  --name web `
  --address-prefix 10.10.1.0/24

Another subnet:

uv run .\app.py subnet create `
  --resource-group rg-weu `
  --vnet vnet-weu `
  --name app `
  --address-prefix 10.10.2.0/24
List
uv run .\app.py subnet list `
  --vnet vnet-weu
🔗 VNet Peering

Simulate communication between VNets.

Example topology:

┌────────────────────┐
│     vnet-weu       │
│   10.10.0.0/16     │
└─────────┬──────────┘
          │
          │ VNet Peering
          │
┌─────────┴──────────┐
│     vnet-neu       │
│   10.20.0.0/16     │
└────────────────────┘
Create
uv run .\app.py peering create `
  --source-vnet vnet-weu `
  --remote-vnet vnet-neu
List
uv run .\app.py peering list
🛡️ Network Security Groups

NSGs allow you to model Azure security rules.

Create NSG
uv run .\app.py nsg create `
  --resource-group rg-weu `
  --name nsg-web
List
uv run .\app.py nsg list
🔐 Create NSG Rule

Example: allow HTTP.

uv run .\app.py nsg rule create `
  --nsg nsg-web `
  --name allow-http `
  --priority 100 `
  --direction inbound `
  --access allow `
  --protocol tcp `
  --source-prefix Internet `
  --destination-port 80

Example: deny SSH.

uv run .\app.py nsg rule create `
  --nsg nsg-web `
  --name deny-ssh `
  --priority 200 `
  --direction inbound `
  --access deny `
  --protocol tcp `
  --source-prefix Internet `
  --destination-port 22
List rules
uv run .\app.py nsg rule list `
  --nsg nsg-web
🔌 Associate NSG with a Subnet
uv run .\app.py subnet associate-nsg `
  --vnet vnet-weu `
  --subnet web `
  --nsg nsg-web
🛣️ Route Tables

Create a route table:

uv run .\app.py route table-create `
  --resource-group rg-weu `
  --name rt-weu
List route tables
uv run .\app.py route table-list
🧭 User Defined Routes

Example:

10.10.0.0/16
      │
      ▼
     NVA
  10.10.2.10

Create the route:

uv run .\app.py route create `
  --route-table rt-weu `
  --name to-firewall `
  --address-prefix 10.20.0.0/16 `
  --next-hop-type virtual-appliance `
  --next-hop-ip 10.10.2.10
List routes
uv run .\app.py route list `
  --route-table rt-weu
🔗 Associate Route Table
uv run .\app.py route associate `
  --vnet vnet-weu `
  --subnet web `
  --route-table rt-weu
🔍 Route Simulation

The simulator can evaluate how a packet would be routed.

Example:

uv run .\app.py route simulate `
  --source 10.10.1.10 `
  --destination 10.20.1.10

Possible results:

✓ SAME SUBNET

or:

✓ SYSTEM ROUTE
Next Hop: VIRTUAL NETWORK

or:

✓ VNET PEERING
Next Hop: VIRTUAL NETWORK PEERING

or:

✓ USER DEFINED ROUTE
Next Hop: virtual-appliance
Next Hop IP: 10.10.2.10

or:

✓ HYBRID ROUTE
Transport: IPsec VPN
Routing:   BGP
🔐 VPN Gateway

Create a simulated Azure VPN Gateway.

uv run .\app.py vpn gateway-create `
  --name vpn-gw-weu `
  --vnet vnet-weu `
  --sku VpnGw1 `
  --asn 65515
List
uv run .\app.py vpn gateway-list
🏢 Local Network Gateway

Represents the on-premises network.

Example:

Azure
10.10.0.0/16
       │
       │ IPsec
       │
       ▼
On-Prem
10.100.0.0/16

Create:

uv run .\app.py vpn local-create `
  --name onprem-weu `
  --ip-address 203.0.113.10 `
  --address-prefixes 10.100.0.0/16 `
  --asn 65010 `
  --bgp-peering-address 10.100.255.1
List
uv run .\app.py vpn local-list
🔒 VPN Connection

Create an IPsec VPN connection.

uv run .\app.py vpn connection-create `
  --name vpn-onprem-weu `
  --vpn-gateway vpn-gw-weu `
  --local-gateway onprem-weu `
  --bgp
List
uv run .\app.py vpn connection-list
🛰️ BGP

The simulator supports basic BGP concepts.

You can model:

AS numbers
BGP peers
BGP sessions
Advertised routes
Learned routes
Create BGP Peer
uv run .\app.py bgp peer-create `
  --name bgp-onprem `
  --local-device vpn-gw-weu `
  --local-asn 65515 `
  --local-ip 10.100.255.2 `
  --remote-device onprem-router `
  --remote-asn 65010 `
  --remote-ip 10.100.255.1
List BGP Peers
uv run .\app.py bgp peer-list

Expected:

NAME          LOCAL ASN   REMOTE ASN   STATE
-------------------------------------------------
bgp-onprem    65515       65010        Established
Advertise a Route

Simulate the on-prem router advertising:

10.100.0.0/16
uv run .\app.py bgp advertise `
  --peer bgp-onprem `
  --prefix 10.100.0.0/16
Learn a BGP Route
uv run .\app.py bgp learn `
  --peer bgp-onprem `
  --prefix 10.100.0.0/16
🔀 Hybrid Networking Lab

A complete VPN + BGP scenario can be represented as:

                    AZURE
        ┌────────────────────────┐
        │       vnet-weu         │
        │                        │
        │   10.10.0.0/16         │
        │                        │
        │   ┌──────────────┐     │
        │   │ VPN Gateway  │     │
        │   │ ASN 65515    │     │
        │   └──────┬───────┘     │
        └──────────┼─────────────┘
                   │
                IPsec VPN
                   │
                  BGP
                   │
        ┌──────────┴─────────────┐
        │        ON-PREM         │
        │                        │
        │   ASN 65010            │
        │                        │
        │   10.100.0.0/16        │
        └────────────────────────┘

Then:

uv run .\app.py route simulate `
  --source 10.10.1.10 `
  --destination 10.100.1.10

Expected:

✓ HYBRID ROUTE

Transport: IPsec VPN
Routing:   BGP
📡 Azure Route Server

Azure Route Server allows network virtual appliances to exchange routes dynamically using BGP.

Conceptually:

                  Azure VNet
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
   Route Server                   NVA
   ASN 65515                    ASN 65050
        │                           │
        └──────────── BGP ──────────┘
Create
uv run .\app.py route-server create `
  --name ars-weu `
  --vnet vnet-weu `
  --subnet RouteServerSubnet `
  --asn 65515
List
uv run .\app.py route-server list
Add Route Server Peer
uv run .\app.py route-server peer `
  --route-server ars-weu `
  --peer nva-fw
🧱 Network Virtual Appliance

Create a simulated NVA.

Examples:

Firewall
Router
SD-WAN appliance
Network security appliance
uv run .\app.py nva create `
  --name nva-fw `
  --vnet vnet-weu `
  --subnet app `
  --ip-address 10.10.2.10 `
  --asn 65050
List
uv run .\app.py nva list
⚡ ExpressRoute

ExpressRoute represents a private connectivity model between Azure and an external network.

Example:

                    Azure
                      │
                      │
               ExpressRoute
                      │
                      │
                ISP / Provider
                      │
                      │
                   On-Prem
Create Circuit
uv run .\app.py expressroute create `
  --name er-weu `
  --provider Contoso `
  --location Amsterdam `
  --bandwidth 1Gbps `
  --asn 65010
Configure Peering
uv run .\app.py expressroute peer `
  --circuit er-weu `
  --peering-type private `
  --vlan 100 `
  --peer-asn 65010 `
  --peer-ip 192.0.2.2
List
uv run .\app.py expressroute list
🌍 Virtual WAN

Virtual WAN provides a hub-based architecture for large-scale connectivity.

Conceptually:

                    Azure Virtual WAN
                           │
             ┌─────────────┴─────────────┐
             │                           │
          Hub WEU                     Hub NEU
             │                           │
       ┌─────┴─────┐               ┌─────┴─────┐
       │            │               │           │
      VNet         VPN             VNet        VPN
Create Virtual WAN
uv run .\app.py wan create `
  --name vwan-global `
  --type Standard
Create Hub
uv run .\app.py wan hub-create `
  --wan vwan-global `
  --name hub-weu `
  --vnet vnet-weu `
  --location westeurope
List
uv run .\app.py wan list
🧪 Example AZ-700 Lab

Recommended topology:

                         ┌───────────────────────┐
                         │     Azure WEU         │
                         │                       │
                         │    vnet-weu           │
                         │    10.10.0.0/16       │
                         │                       │
                         │  ┌───────────────┐    │
                         │  │ Web Subnet    │    │
                         │  │ 10.10.1.0/24  │    │
                         │  └───────────────┘    │
                         │                       │
                         │  ┌───────────────┐    │
                         │  │ NVA           │    │
                         │  │ 10.10.2.10    │    │
                         │  └───────┬───────┘    │
                         │          │             │
                         │    Route Server        │
                         │          │             │
                         │    VPN Gateway         │
                         └──────────┼─────────────┘
                                    │
                                 IPsec
                                    │
                                   BGP
                                    │
                         ┌──────────┴─────────────┐
                         │       ON-PREM          │
                         │                        │
                         │ ASN 65010              │
                         │                        │
                         │ 10.100.0.0/16          │
                         └────────────────────────┘
🧭 Recommended Learning Path

If you are using this project to prepare for AZ-700, follow this order.

🟢 Level 1 — Core Networking
 Resource Groups
 VNets
 Subnets
 VNet Peering
🟡 Level 2 — Security
 NSGs
 NSG rules
 Subnet associations
🟠 Level 3 — Routing
 Route Tables
 UDR
 Next Hop
 Route simulation
🔵 Level 4 — Hybrid
 VPN Gateway
 Local Network Gateway
 IPsec
 BGP
 Hybrid route simulation
🟣 Level 5 — Advanced Networking
 Route Server
 NVA
 BGP with NVA
 ExpressRoute
 Virtual WAN
🧠 Networking Concepts Covered
Concept	Simulator
IPv4 addressing	✅
CIDR	✅
VNet	✅
Subnet	✅
VNet Peering	✅
NSG	✅
NSG Rules	✅
Route Tables	✅
UDR	✅
Next Hop	✅
Route Selection	✅
VPN Gateway	✅
IPsec	✅
BGP	✅
ASN	✅
Route Server	✅
NVA	✅
ExpressRoute	✅
Virtual WAN	✅
Hybrid Routing	✅
⚠️ Important

This project is an educational simulator.

It does not reproduce every internal Azure routing behavior.

For example:

Azure control-plane behavior is simplified.
Real BGP timers are not implemented.
No real packets are transmitted.
No IPsec tunnel is established.
No actual Azure resources are deployed.
Route propagation is simulated.
ExpressRoute is simulated.
Route Server is simulated.

The goal is to understand:

Architecture, routing decisions, connectivity models and networking concepts.

It is not intended to emulate Azure's complete dataplane.

🛠️ Project Structure
Azure/
│
├── app.py
├── main.py
├── README.md
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .python-version
│
├── data/
│   └── state.json
│
└── simulator/
    ├── __init__.py
    ├── cli.py
    └── state.py
💾 State

The simulator stores its topology in:

data/state.json

Resources created with the CLI remain available between executions.

Example:

uv run .\app.py vnet list

will show the VNets previously created.

🔎 Useful Commands

Show general help:

uv run .\app.py --help

Show resource-specific help:

uv run .\app.py group --help
uv run .\app.py vnet --help
uv run .\app.py subnet --help
uv run .\app.py peering --help
uv run .\app.py nsg --help
uv run .\app.py route --help
uv run .\app.py vpn --help
uv run .\app.py bgp --help
uv run .\app.py route-server --help
uv run .\app.py nva --help
uv run .\app.py expressroute --help
uv run .\app.py wan --help
🧪 End-to-End Hybrid Scenario

Create the resource group:

uv run .\app.py group create `
  --name rg-weu `
  --location westeurope

Create the VNet:

uv run .\app.py vnet create `
  --resource-group rg-weu `
  --name vnet-weu `
  --address-prefix 10.10.0.0/16

Create the subnet:

uv run .\app.py subnet create `
  --resource-group rg-weu `
  --vnet vnet-weu `
  --name web `
  --address-prefix 10.10.1.0/24

Create VPN Gateway:

uv run .\app.py vpn gateway-create `
  --name vpn-gw-weu `
  --vnet vnet-weu `
  --sku VpnGw1 `
  --asn 65515

Create on-premises network:

uv run .\app.py vpn local-create `
  --name onprem-weu `
  --ip-address 203.0.113.10 `
  --address-prefixes 10.100.0.0/16 `
  --asn 65010 `
  --bgp-peering-address 10.100.255.1

Create VPN connection:

uv run .\app.py vpn connection-create `
  --name vpn-onprem-weu `
  --vpn-gateway vpn-gw-weu `
  --local-gateway onprem-weu `
  --bgp

Create BGP peer:

uv run .\app.py bgp peer-create `
  --name bgp-onprem `
  --local-device vpn-gw-weu `
  --local-asn 65515 `
  --local-ip 10.100.255.2 `
  --remote-device onprem-router `
  --remote-asn 65010 `
  --remote-ip 10.100.255.1

Advertise the on-premises network:

uv run .\app.py bgp advertise `
  --peer bgp-onprem `
  --prefix 10.100.0.0/16

Learn the route:

uv run .\app.py bgp learn `
  --peer bgp-onprem `
  --prefix 10.100.0.0/16

Finally simulate:

uv run .\app.py route simulate `
  --source 10.10.1.10 `
  --destination 10.100.1.10
🎓 Project Goal

The long-term goal is to provide a free local networking lab for practicing:

Azure Networking
       │
       ├── VNet
       ├── Subnet
       ├── NSG
       ├── UDR
       ├── Peering
       │
       ├── VPN
       ├── BGP
       ├── Route Server
       ├── NVA
       ├── ExpressRoute
       └── Virtual WAN

without requiring an Azure subscription.

🚧 Roadmap

Future versions may include:

🔄 BGP route propagation
🧠 Longest Prefix Match visualization
🗺️ Interactive topology
🔥 Azure Firewall simulation
🌐 NAT Gateway
🔀 Azure Load Balancer
🚪 Application Gateway
🌍 Private Endpoints
🔐 Private DNS
🧩 Azure Firewall + Route Server
🛰️ SD-WAN scenarios
🌎 Multi-region architectures
📡 Service Provider / Telco scenarios
📊 Route table visualization
🧮 More realistic BGP path selection
🧭 AS-path simulation
🏷️ Route tagging
🔁 Route propagation
🛡️ Security policy simulation
👨‍💻 Educational Project

Built as a personal Azure Networking / AZ-700 laboratory.

The focus is on understanding:

How Azure networking works, how routes are selected and how Azure connects to external networks.

☁️ Learn Azure Networking Without Spending Money

Local. Free. No subscription required.