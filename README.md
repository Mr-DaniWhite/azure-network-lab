# ☁️ Azure Network Simulator

> 🧪 **A local Azure networking simulator for learning, testing, troubleshooting and AZ-700 practice.**

This project simulates Azure networking concepts locally through a CLI. It does **not** deploy real Azure resources and does not generate real network traffic.

The goal is to provide a small, reproducible networking lab where you can:

- create and inspect network resources
- configure routing
- simulate BGP
- simulate VPN connectivity
- simulate ExpressRoute
- work with Azure Route Server and NVAs
- model hybrid networking
- inspect the configuration like a router `show run`
- simulate route selection
- run a full sanity check

---

## 🚀 Features

### 🌐 Core Networking

- Resource Groups
- Virtual Networks
- Subnets
- VNet Peering
- Network Security Groups
- NSG Rules
- Route Tables
- User Defined Routes

### 🔐 VPN & BGP

- VPN Gateway
- Local Network Gateway
- VPN Connections
- BGP Peers
- BGP route advertisement
- BGP route learning

### ⚡ ExpressRoute

- ExpressRoute Circuits
- ExpressRoute Peerings
- Private peering
- BGP-style route advertisement

### 📡 Hybrid Networking

- Azure Route Server
- NVA
- Route Server ↔ NVA BGP peering
- NVA route advertisement
- VPN + ExpressRoute coexistence
- Hybrid route simulation

### 🔎 Operations & Troubleshooting

- `show`
- `show vnet`
- `show vpn`
- `show bgp`
- `show expressroute`
- `show routes`
- `show route-server`
- `show nva`
- `show route-server-peers`
- `show nva-routes`
- `show coexistence`
- Route simulation

---

# 🧱 Architecture

```text
                    ┌─────────────────────────┐
                    │      Azure Simulator    │
                    │                         │
                    │       state.json        │
                    └────────────┬────────────┘
                                 │
                         ┌───────▼───────┐
                         │     CLI       │
                         │    app.py     │
                         └───────┬───────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
      VNet                     VPN                  ExpressRoute
        │                        │                        │
     Subnets                    BGP                    BGP
        │                        │                        │
       NSG                       │                        │
       UDR                       │                        │
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                          Azure Route Server
                                 │
                                BGP
                                 │
                                NVA
                                 │
                         Hybrid Routing
```

---

# ⚙️ Requirements

- Windows PowerShell
- Python
- [`uv`](https://docs.astral.sh/uv/)
- Git

You do **not** need:

- ❌ Azure CLI
- ❌ an Azure subscription
- ❌ real Azure resources
- ❌ a real VPN
- ❌ a real ExpressRoute circuit
- ❌ real network traffic

Everything runs locally.

---

# ▶️ Running the simulator

From the project directory:

```powershell
uv run .\app.py --help
```

The CLI exposes the following main resources:

```text
group
vnet
subnet
peering
nsg
route
vpn
bgp
expressroute
route-server
nva
hybrid
show
```

---

# 📦 Resource Groups

## Create

```powershell
uv run .\app.py group create --name rg-weu --location westeurope
```

## List

```powershell
uv run .\app.py group list
```

---

# 🌐 Virtual Networks

## Create a VNet

```powershell
uv run .\app.py vnet create `
  --resource-group rg-weu `
  --name vnet-weu `
  --address-prefix 10.10.0.0/16
```

## List VNets

```powershell
uv run .\app.py vnet list
```

---

# 🔹 Subnets

## Create a subnet

```powershell
uv run .\app.py subnet create `
  --resource-group rg-weu `
  --vnet vnet-weu `
  --name web `
  --address-prefix 10.10.1.0/24
```

Another subnet:

```powershell
uv run .\app.py subnet create `
  --resource-group rg-weu `
  --vnet vnet-weu `
  --name app `
  --address-prefix 10.10.2.0/24
```

Dedicated subnet for the Route Server / NVA lab:

```powershell
uv run .\app.py subnet create `
  --resource-group rg-weu `
  --vnet vnet-weu `
  --name nva `
  --address-prefix 10.10.10.0/24
```

## List subnets

```powershell
uv run .\app.py subnet list --vnet vnet-weu
```

---

# 🔗 VNet Peering

## Create peering

```powershell
uv run .\app.py peering create `
  --name weu-to-neu `
  --source-vnet vnet-weu `
  --remote-vnet vnet-neu
```

## List peerings

```powershell
uv run .\app.py peering list
```

---

# 🛡️ Network Security Groups

## Create an NSG

```powershell
uv run .\app.py nsg create `
  --resource-group rg-weu `
  --name nsg-web
```

## Create an HTTPS rule

```powershell
uv run .\app.py nsg rule-create `
  --resource-group rg-weu `
  --nsg nsg-web `
  --name allow-https `
  --priority 100 `
  --direction inbound `
  --access allow `
  --protocol tcp `
  --source Internet `
  --destination-port 443
```

## Create a deny-SSH rule

```powershell
uv run .\app.py nsg rule-create `
  --resource-group rg-weu `
  --nsg nsg-web `
  --name deny-ssh `
  --priority 200 `
  --direction inbound `
  --access deny `
  --protocol tcp `
  --source Internet `
  --destination-port 22
```

## List NSGs

```powershell
uv run .\app.py nsg list
```

---

# 🛣️ Route Tables / UDR

## Create a Route Table

```powershell
uv run .\app.py route table-create `
  --resource-group rg1 `
  --name rt1
```

## Create a route

```powershell
uv run .\app.py route create `
  --resource-group rg1 `
  --route-table rt1 `
  --name r1 `
  --address-prefix 10.1.0.0/24 `
  --next-hop-type VirtualAppliance `
  --next-hop-ip 10.0.0.4
```

## List Route Tables

```powershell
uv run .\app.py route table-list
```

---

# 🔐 VPN

## Create a VPN Gateway

```powershell
uv run .\app.py vpn gateway-create `
  --name vpn-gw-weu `
  --vnet vnet-weu `
  --sku VpnGw1 `
  --asn 65515
```

## Create a Local Network Gateway

```powershell
uv run .\app.py vpn local-create `
  --name onprem-weu `
  --ip-address 203.0.113.10 `
  --address-prefixes 10.100.0.0/16 `
  --asn 65010 `
  --bgp-peering-address 10.100.255.1
```

## Create a VPN connection

```powershell
uv run .\app.py vpn connection-create `
  --name vpn-onprem-weu `
  --vpn-gateway vpn-gw-weu `
  --local-gateway onprem-weu `
  --bgp
```

## List VPN resources

```powershell
uv run .\app.py vpn gateway-list
uv run .\app.py vpn local-list
uv run .\app.py vpn connection-list
```

---

# 🛰️ BGP

## Create a BGP peer

```powershell
uv run .\app.py bgp peer-create `
  --name bgp-onprem `
  --local-device vpn-gw-weu `
  --local-asn 65515 `
  --local-ip 10.100.255.2 `
  --remote-device onprem-router `
  --remote-asn 65010 `
  --remote-ip 10.100.255.1
```

## Advertise a route

```powershell
uv run .\app.py bgp advertise `
  --peer bgp-onprem `
  --prefix 10.100.0.0/16
```

## Learn a route

```powershell
uv run .\app.py bgp learn `
  --peer bgp-onprem `
  --prefix 10.100.0.0/16
```

## List BGP peers

```powershell
uv run .\app.py bgp peer-list
```

---

# ⚡ ExpressRoute

## Create a circuit

```powershell
uv run .\app.py expressroute create `
  --name er-weu `
  --resource-group rg-weu `
  --provider Contoso `
  --location Amsterdam `
  --bandwidth 1Gbps `
  --asn 65010
```

## Create private peering

```powershell
uv run .\app.py expressroute peer-create `
  --circuit er-weu `
  --type private `
  --vlan-id 100 `
  --peer-asn 65010 `
  --peer-ip 192.0.2.2
```

## Advertise a route

```powershell
uv run .\app.py expressroute advertise `
  --circuit er-weu `
  --peering private `
  --prefix 10.100.0.0/16
```

## List ExpressRoute resources

```powershell
uv run .\app.py expressroute list
uv run .\app.py expressroute peer-list
```

---

# 📡 Azure Route Server

Azure Route Server is represented as a BGP routing component for exchanging routes dynamically with an NVA.

The Route Server uses the dedicated `nva` subnet.

## Create Route Server

```powershell
uv run .\app.py route-server create `
  --name ars-weu `
  --vnet vnet-weu `
  --subnet nva `
  --asn 65515
```

## List Route Servers

```powershell
uv run .\app.py route-server list
```

---

# 🧱 NVA

## Create an NVA

```powershell
uv run .\app.py nva create `
  --name nva-weu `
  --vnet vnet-weu `
  --subnet nva `
  --private-ip 10.10.10.4 `
  --asn 65050
```

## List NVAs

```powershell
uv run .\app.py nva list
```

---

# 🔁 Route Server ↔ NVA BGP

## Create the BGP peer

```powershell
uv run .\app.py route-server peer-create `
  --name ars-nva `
  --route-server ars-weu `
  --nva nva-weu `
  --route-server-ip 10.10.10.5
```

## List Route Server peers

```powershell
uv run .\app.py route-server peer-list
```

---

# 📢 NVA Route Advertisement

## Advertise a prefix

```powershell
uv run .\app.py nva advertise `
  --nva nva-weu `
  --prefix 10.200.0.0/16
```

## List NVA routes

```powershell
uv run .\app.py nva route-list
```

---

# 🌎 VPN + ExpressRoute Coexistence

The simulator can model a VNet using both VPN and ExpressRoute connectivity.

```text
                         ON-PREM
                            │
                  ┌─────────┴─────────┐
                  │                   │
                 VPN             ExpressRoute
                  │                   │
                 BGP                 BGP
                  │                   │
                  ▼                   ▼
             VPN Gateway        ER Circuit
                  │                   │
                  └─────────┬─────────┘
                            │
                         Azure VNet
                         vnet-weu
                            │
                    ┌───────┴────────┐
                    │                │
               Route Server          │
                    │                │
                   BGP               │
                    │                │
                   NVA               │
                    │                │
                    └───────┬────────┘
                            │
                     Hybrid Routing
```

## Create a coexistence profile

```powershell
uv run .\app.py hybrid create `
  --name coexist-weu `
  --vnet vnet-weu `
  --vpn-gateway vpn-gw-weu `
  --circuit er-weu `
  --route-server ars-weu `
  --nva nva-weu
```

## List coexistence profiles

```powershell
uv run .\app.py hybrid list
```

## List hybrid routes

```powershell
uv run .\app.py hybrid route-list
```

---

# 🔀 Route Simulation

The simulator can determine a logical route without sending any packets.

## ExpressRoute example

```powershell
uv run .\app.py route simulate `
  --source 10.10.1.10 `
  --destination 10.100.1.10
```

Example result:

```text
Source:       10.10.1.10
Destination:  10.100.1.10

Source VNet:       vnet-weu
Source Subnet:     web

Destination:       HYBRID / EXTERNAL

## RESULT

EXPRESSROUTE ROUTE
Transport: ExpressRoute
Circuit:   er-weu
Provider:  Contoso
Peering:   private
Routing:   BGP
Destination Prefix: 10.100.0.0/16
```

## NVA / Route Server example

```powershell
uv run .\app.py hybrid route-simulate `
  --source 10.10.1.10 `
  --destination 10.200.1.10
```

The logical path can be represented as:

```text
VNet
 │
 ▼
Route Server
 │
 │ BGP
 ▼
NVA
 │
 ▼
10.200.0.0/16
```

---

# 🔎 Show / Running Configuration

The main `show` command is intended to behave like a router configuration inspection command such as:

```text
show run
```

Run:

```powershell
uv run .\app.py show
```

It displays:

```text
RESOURCE GROUPS
VIRTUAL NETWORKS
VNET PEERING
NETWORK SECURITY GROUPS
ROUTE TABLES / UDR
VPN
BGP
AZURE ROUTE SERVER
NVA
ROUTE SERVER BGP PEERS
NVA ROUTES
HYBRID VPN + EXPRESSROUTE COEXISTENCE
EXPRESSROUTE
```

## Specific views

### VNets

```powershell
uv run .\app.py show vnet
```

### VPN

```powershell
uv run .\app.py show vpn
```

### BGP

```powershell
uv run .\app.py show bgp
```

### ExpressRoute

```powershell
uv run .\app.py show expressroute
```

### Route Tables

```powershell
uv run .\app.py show routes
```

### Route Server

```powershell
uv run .\app.py show route-server
```

### NVA

```powershell
uv run .\app.py show nva
```

### Route Server BGP peers

```powershell
uv run .\app.py show route-server-peers
```

### NVA routes

```powershell
uv run .\app.py show nva-routes
```

### VPN + ExpressRoute coexistence

```powershell
uv run .\app.py show coexistence
```

---

# 🧪 Sanity Check

A full PowerShell sanity check is included to verify the CLI after changes.

Run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\sanity-check-full.ps1
```

The test suite covers:

```text
✓ Main CLI
✓ show
✓ show vnet
✓ show vpn
✓ show bgp
✓ show expressroute
✓ show routes
✓ show route-server
✓ show nva
✓ show route-server-peers
✓ show nva-routes
✓ show coexistence

✓ Resource Group list
✓ VNet list
✓ Subnet list
✓ Peering list
✓ NSG list
✓ Route Table list
✓ VPN Gateway list
✓ Local Gateway list
✓ VPN Connection list
✓ BGP Peer list
✓ ExpressRoute list
✓ ExpressRoute Peer list
✓ Route Server list
✓ Route Server Peer list
✓ NVA list
✓ NVA Route list
✓ Hybrid profile list
✓ Hybrid route list

✓ ExpressRoute route simulation
✓ NVA / Route Server route simulation
```

Current validated result:

```text
=============================================
 SANITY CHECK SUMMARY
=============================================

Passed : 36
Failed : 0
Total  : 36

[OK] ALL TESTS PASSED
```

---

# 📁 Project Structure

```text
Azure/
│
├── app.py
├── main.py
├── README.md
├── pyproject.toml
├── uv.lock
├── .python-version
├── .gitignore
│
├── data/
│   └── state.json
│
├── simulator/
│   ├── __init__.py
│   ├── cli.py
│   └── state.py
│
└── sanity-check-full.ps1
```

---

# 💾 State

The simulator stores its configuration locally in:

```text
data/state.json
```

Resources created through the CLI persist between executions.

For example:

```powershell
uv run .\app.py vnet list
```

After closing PowerShell and running:

```powershell
uv run .\app.py show
```

the local configuration is still available.

> ⚠️ **Do not delete `data/state.json` if you want to keep the current lab state.**

---

# 🧠 Learning Goals

This project is designed for practicing:

- Azure Virtual Networking
- AZ-700 concepts
- Routing
- UDR
- NSG
- VNet Peering
- VPN Gateway
- BGP
- ExpressRoute
- Azure Route Server
- NVA
- Hybrid Networking
- Route selection
- Troubleshooting

The intended workflow is:

```text
CREATE
  ↓
CONFIGURE
  ↓
INSPECT
  ↓
ADVERTISE ROUTES
  ↓
SIMULATE
  ↓
TROUBLESHOOT
```

---

# ⚠️ Limitations

This is an **educational simulator**, not an implementation of Azure networking.

It does not perform:

- ❌ ping
- ❌ traceroute
- ❌ real IP connections
- ❌ real IPsec tunnels
- ❌ real BGP sessions
- ❌ real ExpressRoute connections
- ❌ Azure API calls
- ❌ Azure infrastructure deployments

Connection states, BGP sessions, routes and forwarding decisions are local representations used for learning and testing.

---

# 🧪 Example Full Lab

A complete hybrid lab can be represented as:

```text
                         ON-PREM
                            │
                  ┌─────────┴─────────┐
                  │                   │
                 VPN             ExpressRoute
                  │                   │
                 BGP                 BGP
                  │                   │
                  ▼                   ▼
             VPN Gateway        ER Circuit
                  │                   │
                  └─────────┬─────────┘
                            │
                         Azure VNet
                         vnet-weu
                            │
                    ┌───────┴────────┐
                    │                │
               Route Server          │
                    │                │
                   BGP               │
                    │                │
                   NVA               │
                    │                │
                    └───────┬────────┘
                            │
                     Hybrid Routing
```

Then inspect the whole configuration:

```powershell
uv run .\app.py show
```

Test an ExpressRoute destination:

```powershell
uv run .\app.py route simulate `
  --source 10.10.1.10 `
  --destination 10.100.1.10
```

Test an NVA destination:

```powershell
uv run .\app.py hybrid route-simulate `
  --source 10.10.1.10 `
  --destination 10.200.1.10
```

---

# 📌 Current Implementation

```text
[✓] Resource Groups
[✓] VNets
[✓] Subnets
[✓] VNet Peering
[✓] NSGs
[✓] NSG Rules
[✓] Route Tables
[✓] UDR
[✓] VPN Gateway
[✓] Local Network Gateway
[✓] VPN Connections
[✓] BGP
[✓] ExpressRoute
[✓] ExpressRoute Peering
[✓] Route Server
[✓] NVA
[✓] Route Server ↔ NVA BGP
[✓] NVA route advertisement
[✓] VPN + ExpressRoute coexistence
[✓] Route simulation
[✓] Running configuration / show
[✓] Full sanity check
```

---

## ☁️ Azure Networking Lab

This project is not intended to replace Azure.

It provides a **fast, reproducible and safe local laboratory** for understanding networking concepts, routing behavior and hybrid connectivity before implementing the same architecture in real Azure infrastructure.
