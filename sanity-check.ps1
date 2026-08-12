$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " AZSIM FULL SANITY CHECK" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

$tests = @(
    @{ Name = "Main CLI"; Args = @("--help") },

    # SHOW
    @{ Name = "Show running configuration"; Args = @("show") },
    @{ Name = "Show VNets"; Args = @("show", "vnet") },
    @{ Name = "Show VPN"; Args = @("show", "vpn") },
    @{ Name = "Show BGP"; Args = @("show", "bgp") },
    @{ Name = "Show ExpressRoute"; Args = @("show", "expressroute") },
    @{ Name = "Show routes"; Args = @("show", "routes") },
    @{ Name = "Show Route Server"; Args = @("show", "route-server") },
    @{ Name = "Show NVA"; Args = @("show", "nva") },
    @{ Name = "Show Route Server peers"; Args = @("show", "route-server-peers") },
    @{ Name = "Show NVA routes"; Args = @("show", "nva-routes") },
    @{ Name = "Show coexistence"; Args = @("show", "coexistence") },

    # LIST
    @{ Name = "List resource groups"; Args = @("group", "list") },
    @{ Name = "List VNets"; Args = @("vnet", "list") },
    @{ Name = "List subnets"; Args = @("subnet", "list", "--vnet", "vnet-weu") },
    @{ Name = "List VNet peerings"; Args = @("peering", "list") },
    @{ Name = "List NSGs"; Args = @("nsg", "list") },
    @{ Name = "List route tables"; Args = @("route", "table-list") },
    @{ Name = "List VPN gateways"; Args = @("vpn", "gateway-list") },
    @{ Name = "List local network gateways"; Args = @("vpn", "local-list") },
    @{ Name = "List VPN connections"; Args = @("vpn", "connection-list") },
    @{ Name = "List BGP peers"; Args = @("bgp", "peer-list") },
    @{ Name = "List ExpressRoute circuits"; Args = @("expressroute", "list") },
    @{ Name = "List ExpressRoute peerings"; Args = @("expressroute", "peer-list") },
    @{ Name = "List Route Servers"; Args = @("route-server", "list") },
    @{ Name = "List Route Server peers"; Args = @("route-server", "peer-list") },
    @{ Name = "List NVAs"; Args = @("nva", "list") },
    @{ Name = "List NVA routes"; Args = @("nva", "route-list") },
    @{ Name = "List hybrid profiles"; Args = @("hybrid", "list") },
    @{ Name = "List hybrid routes"; Args = @("hybrid", "route-list") },

    # ROUTING SIMULATION
    @{
        Name = "Simulate ExpressRoute route"
        Args = @(
            "route", "simulate",
            "--source", "10.10.1.10",
            "--destination", "10.100.1.10"
        )
    },
    @{
        Name = "Simulate NVA / Route Server route"
        Args = @(
            "hybrid", "route-simulate",
            "--source", "10.10.1.10",
            "--destination", "10.200.1.10"
        )
    }
)

$passed = 0
$failed = 0
$results = @()

foreach ($test in $tests) {
    Write-Host "--------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "[TEST] $($test.Name)" -ForegroundColor Yellow
    Write-Host ("uv run .\app.py " + ($test.Args -join " ")) -ForegroundColor DarkGray
    Write-Host ""

    & uv run .\app.py @($test.Args)
    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0) {
        Write-Host "[PASS]" -ForegroundColor Green
        $passed++
        $results += [PSCustomObject]@{
            Status = "PASS"
            Test   = $test.Name
        }
    }
    else {
        Write-Host "[FAIL] Exit code: $exitCode" -ForegroundColor Red
        $failed++
        $results += [PSCustomObject]@{
            Status = "FAIL"
            Test   = $test.Name
        }
    }

    Write-Host ""
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " SANITY CHECK SUMMARY" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$results | Format-Table -AutoSize

Write-Host ("Passed : " + $passed) -ForegroundColor Green
Write-Host ("Failed : " + $failed) -ForegroundColor Red
Write-Host ("Total  : " + ($passed + $failed))
Write-Host ""

if ($failed -eq 0) {
    Write-Host "[OK] ALL TESTS PASSED" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "[FAIL] SOME TESTS FAILED" -ForegroundColor Red
    exit 1
}
