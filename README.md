# ☁️ Azure Network Simulator

> **Local Azure Networking Lab for AZ-700 and Hybrid Networking practice**

A lightweight Python CLI for simulating Azure networking concepts locally, without an Azure subscription or real cloud resources.

## 🎯 Goals

Practice:

- IPv4 / CIDR
- Virtual Networks and Subnets
- VNet Peering
- Network Security Groups
- Routing and route simulation
- VPN Gateway
- Local Network Gateway
- IPsec VPN
- BGP
- Hybrid networking

The simulator stores its topology locally in `data/state.json`.

---

## 🚀 Requirements

- Python 3.12+
- Git
- [uv](https://docs.astral.sh/uv/)

Run the simulator with:

```powershell
uv run .\app.py --help
```

General syntax:

```text
uv run .\app.py <resource> <command> [options]
```

Useful help commands:

```powershell
uv run .\app.py group --help
uv run .\app.py vnet --help
uv run .\app.py subnet --help
uv run .\app.py peering --help
uv run .\app.py nsg --help
uv run .\app.py route --help
uv run .\app.py vpn --help
uv run .\app.py bgp --help
```

---

# 📚 Current Functionality

| Area | Status |
|---|:---:|
| Resource Groups | ✅ |
| Virtual Networks | ✅ |
| Subnets | ✅ |
| VNet Peering | ✅ |
| Network Security Groups | ✅ |
| Route simulation | ✅ |
| VPN Gateway | ✅ |
| Local Network Gateway | ✅ |
| IPsec VPN connection | ✅ |
| BGP peers | ✅ |
| BGP route advertisement | ✅ |
| BGP learned routes | ✅ |
| Hybrid route simulation | ✅ |
| Azure Route Server | 🚧 |
| NVA | 🚧 |
| ExpressRoute | 🚧 |
| Virtual WAN | 🚧 |

`🚧` means planned functionality, not currently implemented.

---

# 🌐 Virtual Networks

Create a VNet:

```powershell
uv run .\app.py vnet create --resource-group rg-weu --name vnet-weu --address-prefix 10.10.0.0/16
```

List VNets:

```powershell
uv run .\app.py vnet list
```

Show a VNet:

```powershell
uv run .\app.py vnet show --name vnet-weu
```

Example topology:

```text
vnet-weu
10.10.0.0/16
│
├── web
│   └── 10.10.1.0/24
│
└── app
    └── 10.10.2.0/24
```

---

# 📦 Subnets

Create a subnet:

```powershell
uv run .\app.py subnet create --resource-group rg-weu --vnet vnet-weu --name web --address-prefix 10.10.1.0/24
```

Create another subnet:

```powershell
uv run .\app.py subnet create --resource-group rg-weu --vnet vnet-weu --name app --address-prefix 10.10.2.0/24
```

List subnets:

```powershell
uv run .\app.py subnet list --vnet vnet-weu
```

---

# 🔗 VNet Peering

Example:

```text
┌──────────────────────┐
│      vnet-weu        │
│    10.10.0.0/16      │
└──────────┬───────────┘
           │
           │ VNet Peering
           │
┌──────────┴───────────┐
│      vnet-neu        │
│    10.20.0.0/16      │
└──────────────────────┘
```

Create a peering:

```powershell
uv run .\app.py peering create --source-vnet vnet-weu --remote-vnet vnet-neu
```

List peerings:

```powershell
uv run .\app.py peering list
```

---

# 🛡️ Network Security Groups

Create an NSG:

```powershell
uv run .\app.py nsg create --resource-group rg-weu --name nsg-web
```

List NSGs:

```powershell
uv run .\app.py nsg list
```

---

# 🛣️ Route Simulation

The simulator can evaluate a destination against the simulated topology.

Example:

```powershell
uv run .\app.py route simulate --source 10.10.1.10 --destination 10.20.1.10
```

The result identifies the source VNet/subnet, destination classification and the simulated routing path when one exists.

---

# 🔐 Hybrid Networking

The current hybrid scenario models Azure connectivity to an external/on-premises network using IPsec and BGP.

```text
                     AZURE
              ┌──────────────────┐
              │    vnet-weu       │
              │  10.10.0.0/16     │
              │                   │
              │   Web subnet      │
              │  10.10.1.0/24    │
              │        │          │
              │        ▼          │
              │  VPN Gateway      │
              │    ASN 65515      │
              └────────┬──────────┘
                       │
                    IPsec VPN
                       │
                      BGP
                       │
                       ▼
              ┌──────────────────┐
              │     ON-PREM      │
              │    ASN 65010     │
              │                  │
              │  10.100.0.0/16   │
              └──────────────────┘
```

## VPN Gateway

```powershell
uv run .\app.py vpn gateway-create --name vpn-gw-weu --vnet vnet-weu --sku VpnGw1 --asn 65515
```

## Local Network Gateway

```powershell
uv run .\app.py vpn local-create --name onprem-weu --ip-address 203.0.113.10 --address-prefixes 10.100.0.0/16 --asn 65010 --bgp-peering-address 10.100.255.1
```

## VPN Connection

```powershell
uv run .\app.py vpn connection-create --name vpn-onprem-weu --vpn-gateway vpn-gw-weu --local-gateway onprem-weu --bgp
```

---

# 🛰️ BGP

The simulator models basic BGP route exchange:

- local ASN
- remote ASN
- local and remote BGP addresses
- peer state
- advertised prefixes
- learned prefixes

## Create a BGP Peer

```powershell
uv run .\app.py bgp peer-create --name bgp-onprem --local-device vpn-gw-weu --local-asn 65515 --local-ip 10.100.255.2 --remote-device onprem-router --remote-asn 65010 --remote-ip 10.100.255.1
```

## List BGP Peers

```powershell
uv run .\app.py bgp peer-list
```

## Advertise a Prefix

```powershell
uv run .\app.py bgp advertise --peer bgp-onprem --prefix 10.100.0.0/16
```

## Learn a Prefix

```powershell
uv run .\app.py bgp learn --peer bgp-onprem --prefix 10.100.0.0/16
```

---

# 🔍 Hybrid Route Simulation

After configuring the VPN and BGP objects, simulate a route from Azure to on-premises:

```powershell
uv run .\app.py route simulate --source 10.10.1.10 --destination 10.100.1.10
```

Expected result:

```text
✓ HYBRID ROUTE
Transport: IPsec VPN
VPN Gateway: vpn-gw-weu
Local Network: onprem-weu
Routing: BGP
Destination Prefix: 10.100.0.0/16
```

Logical path:

```text
10.10.1.10
    │
    ▼
Azure VNet
    │
    ▼
VPN Gateway
    │
    │ IPsec
    ▼
BGP
    │
    ▼
On-Premises
10.100.0.0/16
    │
    ▼
10.100.1.10
```

> **Important:** IPsec represents the connectivity/transport mechanism, while BGP represents dynamic route exchange in this simulation.

---

# 🧪 Complete Hybrid Lab

Run the following sequence to reproduce the current working hybrid scenario.

### 1. Resource Group

```powershell
uv run .\app.py group create --name rg-weu --location westeurope
```

### 2. VNet

```powershell
uv run .\app.py vnet create --resource-group rg-weu --name vnet-weu --address-prefix 10.10.0.0/16
```

### 3. Web Subnet

```powershell
uv run .\app.py subnet create --resource-group rg-weu --vnet vnet-weu --name web --address-prefix 10.10.1.0/24
```

### 4. VPN Gateway

```powershell
uv run .\app.py vpn gateway-create --name vpn-gw-weu --vnet vnet-weu --sku VpnGw1 --asn 65515
```

### 5. Local Network Gateway

```powershell
uv run .\app.py vpn local-create --name onprem-weu --ip-address 203.0.113.10 --address-prefixes 10.100.0.0/16 --asn 65010 --bgp-peering-address 10.100.255.1
```

### 6. VPN Connection

```powershell
uv run .\app.py vpn connection-create --name vpn-onprem-weu --vpn-gateway vpn-gw-weu --local-gateway onprem-weu --bgp
```

### 7. BGP Peer

```powershell
uv run .\app.py bgp peer-create --name bgp-onprem --local-device vpn-gw-weu --local-asn 65515 --local-ip 10.100.255.2 --remote-device onprem-router --remote-asn 65010 --remote-ip 10.100.255.1
```

### 8. Advertise the On-Premises Prefix

```powershell
uv run .\app.py bgp advertise --peer bgp-onprem --prefix 10.100.0.0/16
```

### 9. Learn the Route

```powershell
uv run .\app.py bgp learn --peer bgp-onprem --prefix 10.100.0.0/16
```

### 10. Simulate the Route

```powershell
uv run .\app.py route simulate --source 10.10.1.10 --destination 10.100.1.10
```

---

# 🧠 Learning Model

The project is designed to connect the concepts instead of treating them as isolated commands:

```text
VPN
 │
 ├── provides connectivity
 │
 └── IPsec
       │
       ▼
     BGP
       │
       ├── exchanges prefixes
       │
       └── provides routing information
              │
              ▼
        Route Selection
              │
              ▼
        Destination Network
```

---

# 📊 Networking Coverage

| Concept | Status |
|---|:---:|
| IPv4 / CIDR | ✅ |
| VNet | ✅ |
| Subnet | ✅ |
| VNet Peering | ✅ |
| NSG | ✅ |
| VPN Gateway | ✅ |
| Local Network Gateway | ✅ |
| IPsec VPN | ✅ |
| BGP | ✅ |
| BGP Peer | ✅ |
| BGP Advertisement | ✅ |
| BGP Learned Route | ✅ |
| Hybrid Route Simulation | ✅ |
| Route Server | 🚧 |
| NVA | 🚧 |
| ExpressRoute | 🚧 |
| Virtual WAN | 🚧 |

---

# 🚧 Roadmap

The next stages are focused on advanced Azure networking and eventually Service Provider / Telco scenarios.

## Routing

- [ ] More complete route tables
- [ ] User Defined Routes
- [ ] Longest Prefix Match
- [ ] System routes
- [ ] Route propagation
- [ ] Next-hop inspection
- [ ] Route visualization

## Hybrid Networking

- [ ] Azure Route Server
- [ ] NVA
- [ ] BGP between NVA and Route Server
- [ ] Multiple BGP peers
- [ ] Route propagation through NVA
- [ ] Active/active scenarios

## Enterprise Connectivity

- [ ] ExpressRoute
- [ ] ExpressRoute private peering
- [ ] ExpressRoute Gateway
- [ ] ExpressRoute + VPN coexistence
- [ ] Virtual WAN
- [ ] Virtual Hub

## Azure Network Services

- [ ] Azure Firewall
- [ ] NAT Gateway
- [ ] Load Balancer
- [ ] Application Gateway
- [ ] Private Endpoint
- [ ] Private DNS

## Service Provider / Telco

- [ ] Multiple ASNs
- [ ] Provider Edge / Customer Edge concepts
- [ ] BGP route reflection concepts
- [ ] Multi-region connectivity
- [ ] EVPN / VXLAN concepts
- [ ] Internet edge scenarios
- [ ] CGNAT concepts
- [ ] Hybrid cloud / Telco architectures

---

# ⚠️ Educational Scope

This project is a **local networking simulator**, not an Azure emulator.

It does not:

- create real Azure resources
- send real network packets
- establish real IPsec tunnels
- establish real BGP sessions
- connect to Azure
- require an Azure subscription

Some Azure behavior is intentionally simplified so that the underlying networking concepts are easier to experiment with.

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
```

---

# 💾 Local State

The simulated environment is stored in:

```text
data/state.json
```

Resources created through the CLI remain available between executions.

---

# 🔧 Git Workflow

Check changes:

```powershell
git status
```

Stage changes:

```powershell
git add .
```

Commit:

```powershell
git commit -m "feat: describe the change"
```

Push:

```powershell
git push
```

---

# 🎓 Learning Path

The intended progression is:

```text
Azure Fundamentals
        │
        ▼
VNet / Subnets
        │
        ▼
Peering / NSG
        │
        ▼
Routing / UDR
        │
        ▼
VPN / IPsec
        │
        ▼
BGP
        │
        ▼
Hybrid Networking
        │
        ▼
Route Server / NVA
        │
        ▼
ExpressRoute / Virtual WAN
        │
        ▼
Service Provider / Telco
```

---

## ☁️ Local. Free. No Azure Subscription.

**Learn Azure Networking by building the network yourself.**
