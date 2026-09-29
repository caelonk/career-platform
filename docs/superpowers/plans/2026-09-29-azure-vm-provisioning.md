# Azure VM Provisioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture the hand-built staging VM as reviewed, tested infrastructure-as-code, add automated preflight/verification checks and an idempotent host bootstrap, and bring the live VM to the state Task 8 of the platform plan expects (service account, directories, hardened SSH) without adding unintended cost.

**Architecture:** An ARM template (`deploy/azure/vm.json`) is the single source of truth for the VNet, NSG, VM, and auto-shutdown schedule; parameters that identify a person (SSH key, operator IP, email) live in an untracked parameters file. A small Python module (`scripts/azure_checks.py`) holds pure check functions over Azure CLI JSON, wrapped by a `preflight`/`verify` CLI, so every invariant we learned the hard way is pinned by pytest. A bash bootstrap script (`deploy/azure/bootstrap.sh`) prepares the host and is run through `az vm run-command`, so it works on the already-created VM.

**Tech Stack:** Azure Resource Manager templates, Azure CLI 2.90+, Python 3.12 (stdlib only: `json`, `subprocess`, `shutil`, `argparse`), pytest, bash, Ubuntu Server 24.04 LTS.

**Spec:** `docs/superpowers/specs/2026-09-15-personal-career-platform-design.md` (deployment target), `docs/superpowers/plans/2026-09-15-personal-career-platform.md` Task 8 (what the host must be ready for), and the course VM settings table (portal fields reproduced under Global Constraints).

## Current state (as built 2026-09-24, before this plan)

The VM already exists and was created by hand from the CLI; this plan codifies it rather than rebuilding it.

| Item | Value |
|---|---|
| Subscription | Azure for Students (ID: `az account show --query id -o tsv`) |
| Resource group | `rg-career-platform` (group metadata lives in `westus2`; all resources are in `northcentralus`) |
| VM | `vm-career-platform`, `Standard_B2ats_v2`, Ubuntu 24.04 LTS Gen2, `northcentralus` |
| Network | VNet `vm-career-platformVNET` `10.0.0.0/16`, subnet `vm-career-platformSubnet` `10.0.0.0/24`, NSG `vm-career-platformNSG` attached to the NIC |
| NSG rules | `Allow-SSH-Laptop`, priority 300, TCP 22 from the operator laptop's `/32` (added outside this session) |
| Delete options | OS disk, NIC, and public IP all `Delete` |
| Auto-shutdown | `shutdown-computevm-vm-career-platform`, 18:00 `Pacific Standard Time`, 30-minute email notice |
| Budget | `budget-isba4775`, $15/month, subscription scope |
| SSH key | `~/.ssh/isba4775_azure` (ed25519, no passphrase) |

## Global Constraints

- Allowed regions (subscription policy "Allowed resource deployment regions"): `northcentralus`, `canadacentral`, `denmarkeast`, `belgiumcentral`, `norwayeast`. Every resource must set `location` explicitly; nothing may inherit the resource group's `westus2`.
- VM size: `Standard_B2ats_v2` (cheapest x64 size available to this subscription; the course's `Standard_B2ts_v2` is `NotAvailableForSubscription` in every allowed region checked).
- Image: Canonical `ubuntu-24_04-lts` / `server` (Ubuntu Server 24.04 LTS, x64 Gen2).
- Authentication: SSH public key only, username `azureuser`, password authentication disabled.
- OS disk: `StandardSSD_LRS`.
- OS disk, NIC, and public IP `deleteOption`: `Delete`.
- Boot diagnostics: disabled.
- Auto-shutdown: enabled, `1800`, `Pacific Standard Time`, email notification enabled.
- Tags on every taggable resource: `course` = `isba-4775`, `environment` = `staging`.
- Inbound: SSH (22) only from a single operator `/32`; HTTP/HTTPS closed until Task 8 deploys Nginx (`allowWebTraffic` = `false`).
- Service account `career-platform`, app dir `/srv/career-platform`, snapshots `/srv/career-platform/snapshots`, env dir `/etc/career-platform` — must match `deploy/systemd/career-platform.service` and `deploy/nginx/career-platform.conf`.
- No personal data (email, IP, key) in tracked files; real values live in `deploy/azure/vm.parameters.json`, which is git-ignored.
- In Git Bash, prefix `az` commands that take resource IDs with `MSYS_NO_PATHCONV=1`.

## Review Focus

1. **Resource lands in the resource group's region (`westus2`)** → Azure denies it by policy. Expect the template never to use `resourceGroup().location` and preflight to reject a disallowed region before deploying. Pinned in Task 1 (`test_every_resource_uses_location_parameter`) and Task 2 (`test_check_region_rejects_location_outside_policy`).
2. **VM size restricted or not offered in the region** (both states occurred) → expect preflight to fail with a message naming the size and reason, including the "not offered" case where Azure returns an empty list. Pinned in Task 2 (`test_check_sku_reports_restriction`, `test_check_sku_reports_not_offered`).
3. **Deleting the VM leaves billable resources behind** → a `null` delete option (what the CLI produced the first time) must count as a failure, not a pass. Pinned in Task 2 (`test_check_vm_flags_missing_public_ip_delete_option`).
4. **SSH opened to the whole internet** by a redeploy, a portal edit, or a typo in the operator IP → verify must flag any inbound allow on port 22 from `*`/`Internet`/`0.0.0.0/0`. Pinned in Task 2 (`test_check_nsg_flags_ssh_open_to_internet`) and Task 1 (`test_ssh_rule_is_scoped_to_operator_ip`).
5. **Auto-shutdown silently runs in UTC** (the `az vm auto-shutdown` default) → the VM stops at 11 AM/10 AM Pacific instead of 6 PM. Pinned in Task 2 (`test_check_schedule_rejects_utc`).

---

## File Structure

- Create `deploy/azure/vm.json` — ARM template: VNet, NSG, VM (VM-managed NIC + public IP), auto-shutdown schedule.
- Create `deploy/azure/vm.parameters.example.json` — tracked parameters file with placeholder values.
- Create `deploy/azure/budget.example.json` — tracked body for the subscription budget with a placeholder email.
- Create `deploy/azure/bootstrap.sh` — idempotent host preparation run via `az vm run-command`.
- Create `scripts/azure_checks.py` — pure check functions plus `preflight` / `verify` CLI.
- Create `tests/operations/test_azure_template.py` — static checks on the template and example files.
- Create `tests/operations/test_azure_checks.py` — unit tests for check functions.
- Create `tests/operations/test_azure_bootstrap.py` — static and syntax checks on the bootstrap script.
- Modify `.gitignore` — ignore real parameter/budget files.
- Modify `deploy/azure/README.md` — as-built values, provisioning, cost operations, teardown.

---

### Task 1: VM template as code

**Files:**
- Create: `deploy/azure/vm.json`
- Create: `deploy/azure/vm.parameters.example.json`
- Create: `deploy/azure/budget.example.json`
- Modify: `.gitignore`
- Test: `tests/operations/test_azure_template.py`

**Interfaces:**
- Produces: template parameters `location`, `vmName`, `vmSize`, `adminUsername`, `sshPublicKey`, `operatorIp`, `shutdownEmail`, `allowWebTraffic`. Resource names derived from `vmName`: `<vmName>VNET`, `<vmName>Subnet`, `<vmName>NSG`, `<vmName>VMNic`, `<vmName>PublicIP`, `shutdown-computevm-<vmName>`. Task 2's `verify` and Task 5's deploy rely on these names.

- [ ] **Step 1: Write the failing tests**

Create `tests/operations/test_azure_template.py`:

```python
from __future__ import annotations

import json
import re
from pathlib import Path

TEMPLATE = Path("deploy/azure/vm.json")
PARAMS_EXAMPLE = Path("deploy/azure/vm.parameters.example.json")
BUDGET_EXAMPLE = Path("deploy/azure/budget.example.json")
ALLOWED_REGIONS = {"northcentralus", "canadacentral", "denmarkeast", "belgiumcentral", "norwayeast"}
EXPECTED_TAGS = {"course": "isba-4775", "environment": "staging"}


def load_template() -> dict:
    return json.loads(TEMPLATE.read_text())


def resource(template: dict, resource_type: str) -> dict:
    matches = [r for r in template["resources"] if r["type"] == resource_type]
    assert len(matches) == 1, f"expected one {resource_type}"
    return matches[0]


def test_every_resource_uses_location_parameter():
    template = load_template()
    assert "resourceGroup().location" not in TEMPLATE.read_text()
    for res in template["resources"]:
        assert res["location"] == "[parameters('location')]", res["type"]
    location = template["parameters"]["location"]
    assert location["defaultValue"] == "northcentralus"
    assert set(location["allowedValues"]) == ALLOWED_REGIONS


def test_every_resource_is_tagged():
    template = load_template()
    assert template["variables"]["tags"] == EXPECTED_TAGS
    for res in template["resources"]:
        assert res["tags"] == "[variables('tags')]", res["type"]


def test_vm_matches_course_settings():
    vm = resource(load_template(), "Microsoft.Compute/virtualMachines")
    props = vm["properties"]
    assert props["hardwareProfile"]["vmSize"] == "[parameters('vmSize')]"
    assert load_template()["parameters"]["vmSize"]["defaultValue"] == "Standard_B2ats_v2"
    image = props["storageProfile"]["imageReference"]
    assert (image["publisher"], image["offer"], image["sku"]) == ("Canonical", "ubuntu-24_04-lts", "server")
    assert props["storageProfile"]["osDisk"]["managedDisk"]["storageAccountType"] == "StandardSSD_LRS"
    linux = props["osProfile"]["linuxConfiguration"]
    assert linux["disablePasswordAuthentication"] is True
    assert "adminPassword" not in props["osProfile"]
    assert props["diagnosticsProfile"]["bootDiagnostics"]["enabled"] is False


def test_all_billable_children_delete_with_vm():
    vm = resource(load_template(), "Microsoft.Compute/virtualMachines")
    props = vm["properties"]
    assert props["storageProfile"]["osDisk"]["deleteOption"] == "Delete"
    nic = props["networkProfile"]["networkInterfaceConfigurations"][0]
    assert nic["properties"]["deleteOption"] == "Delete"
    pip = nic["properties"]["ipConfigurations"][0]["properties"]["publicIPAddressConfiguration"]
    assert pip["properties"]["deleteOption"] == "Delete"
    assert props["networkProfile"]["networkApiVersion"] == "2020-11-01"


def test_auto_shutdown_is_6pm_pacific_with_email():
    schedule = resource(load_template(), "Microsoft.DevTestLab/schedules")
    props = schedule["properties"]
    assert props["status"] == "Enabled"
    assert props["dailyRecurrence"]["time"] == "1800"
    assert props["timeZoneId"] == "Pacific Standard Time"
    assert props["notificationSettings"]["status"] == "Enabled"
    assert props["notificationSettings"]["emailRecipient"] == "[parameters('shutdownEmail')]"


def test_ssh_rule_is_scoped_to_operator_ip():
    template = load_template()
    (ssh_rule,) = template["variables"]["sshRules"]
    rule = ssh_rule["properties"]
    assert ssh_rule["name"] == "Allow-SSH-Laptop"
    assert rule["priority"] == 300
    assert rule["destinationPortRange"] == "22"
    assert rule["sourceAddressPrefix"] == "[concat(parameters('operatorIp'), '/32')]"


def test_web_ports_are_closed_by_default():
    template = load_template()
    assert template["parameters"]["allowWebTraffic"]["defaultValue"] is False
    nsg = resource(template, "Microsoft.Network/networkSecurityGroups")
    assert nsg["properties"]["securityRules"] == (
        "[if(parameters('allowWebTraffic'), concat(variables('sshRules'), variables('webRules')), variables('sshRules'))]"
    )
    ports = sorted(r["properties"]["destinationPortRange"] for r in template["variables"]["webRules"])
    assert ports == ["443", "80"]


def test_example_files_hold_placeholders_not_personal_data():
    params = json.loads(PARAMS_EXAMPLE.read_text())["parameters"]
    assert params["sshPublicKey"]["value"].startswith("ssh-ed25519 REPLACE")
    assert params["operatorIp"]["value"] == "203.0.113.10"
    assert params["shutdownEmail"]["value"] == "you@example.com"
    for path in (PARAMS_EXAMPLE, BUDGET_EXAMPLE):
        text = path.read_text()
        assert "PRIVATE KEY" not in text
        emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        assert all(email.endswith("@example.com") for email in emails)
    budget = json.loads(BUDGET_EXAMPLE.read_text())["properties"]
    assert budget["amount"] == 15
    assert budget["timeGrain"] == "Monthly"


def test_real_parameter_files_are_git_ignored():
    ignored = Path(".gitignore").read_text().splitlines()
    assert "deploy/azure/vm.parameters.json" in ignored
    assert "deploy/azure/budget.json" in ignored
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/operations/test_azure_template.py -q`
Expected: FAIL with `FileNotFoundError` for `deploy/azure/vm.json`.

- [ ] **Step 3: Write the template**

Create `deploy/azure/vm.json`. Names and the SSH rule's name/priority deliberately match the live resources so Task 5's redeploy is a no-op rather than a replacement.

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "location": {
      "type": "string",
      "defaultValue": "northcentralus",
      "allowedValues": ["northcentralus", "canadacentral", "denmarkeast", "belgiumcentral", "norwayeast"],
      "metadata": {"description": "Must be allowed by the subscription's region policy; never the resource group's location."}
    },
    "vmName": {"type": "string", "defaultValue": "vm-career-platform"},
    "vmSize": {"type": "string", "defaultValue": "Standard_B2ats_v2"},
    "adminUsername": {"type": "string", "defaultValue": "azureuser"},
    "sshPublicKey": {"type": "string", "metadata": {"description": "Contents of the .pub file (one line)."}},
    "operatorIp": {"type": "string", "metadata": {"description": "Single IPv4 address allowed to SSH, without /32."}},
    "shutdownEmail": {"type": "string"},
    "allowWebTraffic": {"type": "bool", "defaultValue": false}
  },
  "variables": {
    "tags": {"course": "isba-4775", "environment": "staging"},
    "vnetName": "[concat(parameters('vmName'), 'VNET')]",
    "subnetName": "[concat(parameters('vmName'), 'Subnet')]",
    "nsgName": "[concat(parameters('vmName'), 'NSG')]",
    "sshRules": [
      {
        "name": "Allow-SSH-Laptop",
        "properties": {
          "priority": 300,
          "direction": "Inbound",
          "access": "Allow",
          "protocol": "Tcp",
          "sourceAddressPrefix": "[concat(parameters('operatorIp'), '/32')]",
          "sourcePortRange": "*",
          "destinationAddressPrefix": "*",
          "destinationPortRange": "22"
        }
      }
    ],
    "webRules": [
      {
        "name": "Allow-HTTP",
        "properties": {
          "priority": 310,
          "direction": "Inbound",
          "access": "Allow",
          "protocol": "Tcp",
          "sourceAddressPrefix": "Internet",
          "sourcePortRange": "*",
          "destinationAddressPrefix": "*",
          "destinationPortRange": "80"
        }
      },
      {
        "name": "Allow-HTTPS",
        "properties": {
          "priority": 320,
          "direction": "Inbound",
          "access": "Allow",
          "protocol": "Tcp",
          "sourceAddressPrefix": "Internet",
          "sourcePortRange": "*",
          "destinationAddressPrefix": "*",
          "destinationPortRange": "443"
        }
      }
    ]
  },
  "resources": [
    {
      "type": "Microsoft.Network/networkSecurityGroups",
      "apiVersion": "2024-05-01",
      "name": "[variables('nsgName')]",
      "location": "[parameters('location')]",
      "tags": "[variables('tags')]",
      "properties": {
        "securityRules": "[if(parameters('allowWebTraffic'), concat(variables('sshRules'), variables('webRules')), variables('sshRules'))]"
      }
    },
    {
      "type": "Microsoft.Network/virtualNetworks",
      "apiVersion": "2024-05-01",
      "name": "[variables('vnetName')]",
      "location": "[parameters('location')]",
      "tags": "[variables('tags')]",
      "properties": {
        "addressSpace": {"addressPrefixes": ["10.0.0.0/16"]},
        "subnets": [
          {"name": "[variables('subnetName')]", "properties": {"addressPrefix": "10.0.0.0/24"}}
        ]
      }
    },
    {
      "type": "Microsoft.Compute/virtualMachines",
      "apiVersion": "2024-07-01",
      "name": "[parameters('vmName')]",
      "location": "[parameters('location')]",
      "tags": "[variables('tags')]",
      "dependsOn": [
        "[resourceId('Microsoft.Network/networkSecurityGroups', variables('nsgName'))]",
        "[resourceId('Microsoft.Network/virtualNetworks', variables('vnetName'))]"
      ],
      "properties": {
        "hardwareProfile": {"vmSize": "[parameters('vmSize')]"},
        "storageProfile": {
          "imageReference": {"publisher": "Canonical", "offer": "ubuntu-24_04-lts", "sku": "server", "version": "latest"},
          "osDisk": {
            "createOption": "FromImage",
            "deleteOption": "Delete",
            "managedDisk": {"storageAccountType": "StandardSSD_LRS"}
          }
        },
        "osProfile": {
          "computerName": "[parameters('vmName')]",
          "adminUsername": "[parameters('adminUsername')]",
          "linuxConfiguration": {
            "disablePasswordAuthentication": true,
            "ssh": {
              "publicKeys": [
                {
                  "path": "[concat('/home/', parameters('adminUsername'), '/.ssh/authorized_keys')]",
                  "keyData": "[parameters('sshPublicKey')]"
                }
              ]
            }
          }
        },
        "networkProfile": {
          "networkApiVersion": "2020-11-01",
          "networkInterfaceConfigurations": [
            {
              "name": "[concat(parameters('vmName'), 'VMNic')]",
              "properties": {
                "primary": true,
                "deleteOption": "Delete",
                "networkSecurityGroup": {"id": "[resourceId('Microsoft.Network/networkSecurityGroups', variables('nsgName'))]"},
                "ipConfigurations": [
                  {
                    "name": "ipconfig1",
                    "properties": {
                      "subnet": {"id": "[resourceId('Microsoft.Network/virtualNetworks/subnets', variables('vnetName'), variables('subnetName'))]"},
                      "publicIPAddressConfiguration": {
                        "name": "[concat(parameters('vmName'), 'PublicIP')]",
                        "sku": {"name": "Standard"},
                        "properties": {"deleteOption": "Delete", "publicIPAllocationMethod": "Static"}
                      }
                    }
                  }
                ]
              }
            }
          ]
        },
        "diagnosticsProfile": {"bootDiagnostics": {"enabled": false}}
      }
    },
    {
      "type": "Microsoft.DevTestLab/schedules",
      "apiVersion": "2018-09-15",
      "name": "[concat('shutdown-computevm-', parameters('vmName'))]",
      "location": "[parameters('location')]",
      "tags": "[variables('tags')]",
      "dependsOn": ["[resourceId('Microsoft.Compute/virtualMachines', parameters('vmName'))]"],
      "properties": {
        "status": "Enabled",
        "taskType": "ComputeVmShutdownTask",
        "dailyRecurrence": {"time": "1800"},
        "timeZoneId": "Pacific Standard Time",
        "targetResourceId": "[resourceId('Microsoft.Compute/virtualMachines', parameters('vmName'))]",
        "notificationSettings": {
          "status": "Enabled",
          "timeInMinutes": 30,
          "emailRecipient": "[parameters('shutdownEmail')]",
          "notificationLocale": "en"
        }
      }
    }
  ],
  "outputs": {
    "publicIpResourceId": {
      "type": "string",
      "value": "[resourceId('Microsoft.Network/publicIPAddresses', concat(parameters('vmName'), 'PublicIP'))]"
    }
  }
}
```

- [ ] **Step 4: Write the example parameter and budget files**

Create `deploy/azure/vm.parameters.example.json` (`203.0.113.10` is a reserved documentation address):

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "sshPublicKey": {"value": "ssh-ed25519 REPLACE_WITH_CONTENTS_OF_isba4775_azure.pub"},
    "operatorIp": {"value": "203.0.113.10"},
    "shutdownEmail": {"value": "you@example.com"},
    "allowWebTraffic": {"value": false}
  }
}
```

Create `deploy/azure/budget.example.json`:

```json
{
  "properties": {
    "category": "Cost",
    "amount": 15,
    "timeGrain": "Monthly",
    "timePeriod": {"startDate": "2026-09-01T00:00:00Z", "endDate": "2027-09-01T00:00:00Z"},
    "notifications": {
      "actual50": {"enabled": true, "operator": "GreaterThanOrEqualTo", "threshold": 50, "thresholdType": "Actual", "contactEmails": ["you@example.com"]},
      "actual100": {"enabled": true, "operator": "GreaterThanOrEqualTo", "threshold": 100, "thresholdType": "Actual", "contactEmails": ["you@example.com"]},
      "forecast100": {"enabled": true, "operator": "GreaterThanOrEqualTo", "threshold": 100, "thresholdType": "Forecasted", "contactEmails": ["you@example.com"]}
    }
  }
}
```

Append to `.gitignore`:

```gitignore

# Azure deployment values that identify a person (copy from the *.example.json files)
deploy/azure/vm.parameters.json
deploy/azure/budget.json
```

- [ ] **Step 5: Run the tests and the ARM linter to verify they pass**

Run: `pytest tests/operations/test_azure_template.py -q`
Expected: PASS (9 passed).

Run: `az bicep decompile --file deploy/azure/vm.json --stdout > /dev/null && echo TEMPLATE_OK`
Expected: `TEMPLATE_OK` (decompiling parses and type-checks the template; warnings are acceptable, errors are not).

- [ ] **Step 6: Commit**

```bash
git add deploy/azure/vm.json deploy/azure/vm.parameters.example.json deploy/azure/budget.example.json .gitignore tests/operations/test_azure_template.py
git commit -m "ops: capture Azure staging VM as an ARM template"
```

---

### Task 2: Preflight and verification checks

**Files:**
- Create: `scripts/azure_checks.py`
- Test: `tests/operations/test_azure_checks.py`

**Interfaces:**
- Consumes: resource names from Task 1 (`<vmName>NSG`, `shutdown-computevm-<vmName>`), budget name `budget-isba4775`.
- Produces (all return `list[str]` of failure messages; empty means pass):
  - `allowed_locations(assignments: list[dict]) -> set[str] | None`
  - `check_region(assignments: list[dict], location: str) -> list[str]`
  - `check_sku(skus: list[dict], size: str) -> list[str]`
  - `check_provider(provider: dict) -> list[str]`
  - `check_vm(vm: dict, nic: dict) -> list[str]`
  - `check_nsg(nsg: dict) -> list[str]`
  - `check_schedule(schedule: dict) -> list[str]`
  - `check_budget(budget: dict, max_amount: float) -> list[str]`
  - CLI: `python -m scripts.azure_checks preflight --location L --size S` and `python -m scripts.azure_checks verify --resource-group RG --vm-name N --budget-name B`; exit code 0 on pass, 1 on any failure, 2 if `az` is missing or errors.

- [ ] **Step 1: Write the failing tests**

Create `tests/operations/test_azure_checks.py`. Fixture shapes mirror real `az ... -o json` output observed on 2026-09-24.

```python
from __future__ import annotations

import copy

import pytest

from scripts.azure_checks import (
    allowed_locations,
    check_budget,
    check_nsg,
    check_provider,
    check_region,
    check_schedule,
    check_sku,
    check_vm,
)

POLICY = [
    {
        "displayName": "Allowed resource deployment regions",
        "parameters": {
            "listOfAllowedLocations": {
                "value": ["denmarkeast", "belgiumcentral", "canadacentral", "norwayeast", "northcentralus"]
            }
        },
    }
]

GOOD_VM = {
    "location": "northcentralus",
    "hardwareProfile": {"vmSize": "Standard_B2ats_v2"},
    "storageProfile": {"osDisk": {"deleteOption": "Delete", "managedDisk": {"storageAccountType": "StandardSSD_LRS"}}},
    "osProfile": {"linuxConfiguration": {"disablePasswordAuthentication": True}},
    "diagnosticsProfile": {"bootDiagnostics": {"enabled": False}},
    "networkProfile": {"networkInterfaces": [{"id": "/subscriptions/x/nic", "deleteOption": "Delete"}]},
    "tags": {"course": "isba-4775", "environment": "staging"},
}
GOOD_NIC = {"ipConfigurations": [{"publicIPAddress": {"id": "/subscriptions/x/pip", "deleteOption": "Delete"}}]}
SSH_RULE = {
    "name": "Allow-SSH-Laptop",
    "direction": "Inbound",
    "access": "Allow",
    "sourceAddressPrefix": "203.0.113.10/32",
    "destinationPortRange": "22",
    "destinationPortRanges": [],
}
GOOD_SCHEDULE = {
    "properties": {
        "status": "Enabled",
        "dailyRecurrence": {"time": "1800"},
        "timeZoneId": "Pacific Standard Time",
        "notificationSettings": {"status": "Enabled", "emailRecipient": "someone@example.com"},
    }
}
GOOD_BUDGET = {
    "properties": {
        "amount": 15.0,
        "timeGrain": "Monthly",
        "notifications": {"actual50": {"enabled": True, "contactEmails": ["someone@example.com"]}},
    }
}


def test_allowed_locations_reads_policy_parameter():
    assert allowed_locations(POLICY) == {"denmarkeast", "belgiumcentral", "canadacentral", "norwayeast", "northcentralus"}


def test_allowed_locations_is_none_without_policy():
    assert allowed_locations([]) is None


def test_check_region_accepts_allowed_location():
    assert check_region(POLICY, "northcentralus") == []


def test_check_region_rejects_location_outside_policy():
    failures = check_region(POLICY, "westus2")
    assert len(failures) == 1
    assert "westus2" in failures[0]
    assert "northcentralus" in failures[0]


def test_check_sku_passes_unrestricted_size():
    skus = [{"name": "Standard_B2ats_v2", "restrictions": []}]
    assert check_sku(skus, "Standard_B2ats_v2") == []


def test_check_sku_reports_restriction():
    skus = [{"name": "Standard_B2ts_v2", "restrictions": [{"reasonCode": "NotAvailableForSubscription"}]}]
    assert check_sku(skus, "Standard_B2ts_v2") == ["Standard_B2ts_v2 is restricted: NotAvailableForSubscription"]


def test_check_sku_reports_not_offered():
    skus = [{"name": "Standard_B2ats_v2", "restrictions": []}]
    assert check_sku(skus, "Standard_B1ls") == ["Standard_B1ls is not offered in this region"]


def test_check_provider_requires_registration():
    assert check_provider({"namespace": "Microsoft.DevTestLab", "registrationState": "Registered"}) == []
    assert check_provider({"namespace": "Microsoft.DevTestLab", "registrationState": "NotRegistered"}) == [
        "Microsoft.DevTestLab is NotRegistered; run: az provider register -n Microsoft.DevTestLab --wait"
    ]


def test_check_vm_passes_as_built_vm():
    assert check_vm(GOOD_VM, GOOD_NIC) == []


def test_check_vm_flags_missing_public_ip_delete_option():
    nic = copy.deepcopy(GOOD_NIC)
    nic["ipConfigurations"][0]["publicIPAddress"]["deleteOption"] = None
    assert check_vm(GOOD_VM, nic) == ["public IP deleteOption is None, expected Delete"]


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("storageProfile", "osDisk", "deleteOption"), "Detach", "OS disk deleteOption is Detach, expected Delete"),
        (("osProfile", "linuxConfiguration", "disablePasswordAuthentication"), False, "password authentication is enabled"),
        (("diagnosticsProfile", "bootDiagnostics", "enabled"), True, "boot diagnostics is enabled"),
        (("storageProfile", "osDisk", "managedDisk", "storageAccountType"), "Premium_LRS", "OS disk is Premium_LRS, expected StandardSSD_LRS"),
    ],
)
def test_check_vm_flags_each_drift(path, value, message):
    vm = copy.deepcopy(GOOD_VM)
    target = vm
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert check_vm(vm, GOOD_NIC) == [message]


def test_check_vm_flags_missing_tags():
    vm = copy.deepcopy(GOOD_VM)
    vm["tags"] = {"course": "isba-4775"}
    assert check_vm(vm, GOOD_NIC) == ["tag environment is None, expected staging"]


def test_check_nsg_accepts_ssh_from_single_ip():
    assert check_nsg({"securityRules": [SSH_RULE]}) == []


@pytest.mark.parametrize("source", ["*", "Internet", "0.0.0.0/0", "Any"])
def test_check_nsg_flags_ssh_open_to_internet(source):
    rule = dict(SSH_RULE, sourceAddressPrefix=source)
    assert check_nsg({"securityRules": [rule]}) == [f"rule Allow-SSH-Laptop allows SSH from {source}"]


def test_check_nsg_flags_ssh_in_port_ranges_and_wildcard_ports():
    ranged = dict(SSH_RULE, name="wide", sourceAddressPrefix="*", destinationPortRange=None, destinationPortRanges=["20-25"])
    anyport = dict(SSH_RULE, name="any", sourceAddressPrefix="Internet", destinationPortRange="*")
    assert check_nsg({"securityRules": [ranged, anyport]}) == [
        "rule wide allows SSH from *",
        "rule any allows SSH from Internet",
    ]


def test_check_nsg_ignores_deny_and_outbound_rules():
    deny = dict(SSH_RULE, name="deny", access="Deny", sourceAddressPrefix="*")
    outbound = dict(SSH_RULE, name="out", direction="Outbound", sourceAddressPrefix="*")
    assert check_nsg({"securityRules": [deny, outbound]}) == []


def test_check_schedule_passes_6pm_pacific():
    assert check_schedule(GOOD_SCHEDULE) == []


def test_check_schedule_rejects_utc():
    schedule = copy.deepcopy(GOOD_SCHEDULE)
    schedule["properties"]["timeZoneId"] = "UTC"
    assert check_schedule(schedule) == ["auto-shutdown time zone is UTC, expected Pacific Standard Time"]


def test_check_schedule_requires_enabled_notification():
    schedule = copy.deepcopy(GOOD_SCHEDULE)
    schedule["properties"]["status"] = "Disabled"
    schedule["properties"]["notificationSettings"]["status"] = "Disabled"
    assert check_schedule(schedule) == ["auto-shutdown is Disabled", "shutdown notification is Disabled"]


def test_check_budget_passes_within_limit():
    assert check_budget(GOOD_BUDGET, max_amount=15) == []


def test_check_budget_flags_high_amount_and_missing_contacts():
    budget = copy.deepcopy(GOOD_BUDGET)
    budget["properties"]["amount"] = 100.0
    budget["properties"]["notifications"] = {}
    assert check_budget(budget, max_amount=15) == [
        "budget amount 100.0 exceeds 15",
        "budget has no enabled notification with a contact email",
    ]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/operations/test_azure_checks.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.azure_checks'`.

- [ ] **Step 3: Implement the check functions and CLI**

Create `scripts/azure_checks.py`:

```python
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from typing import Any

EXPECTED_TAGS = {"course": "isba-4775", "environment": "staging"}
OPEN_SOURCES = {"*", "internet", "0.0.0.0/0", "any"}
SHUTDOWN_TIME = "1800"
SHUTDOWN_TZ = "Pacific Standard Time"


class AzError(RuntimeError):
    pass


def allowed_locations(assignments: list[dict]) -> set[str] | None:
    for assignment in assignments:
        param = (assignment.get("parameters") or {}).get("listOfAllowedLocations")
        if param:
            return set(param["value"])
    return None


def check_region(assignments: list[dict], location: str) -> list[str]:
    allowed = allowed_locations(assignments)
    if allowed is None or location in allowed:
        return []
    return [f"{location} is blocked by policy; allowed: {', '.join(sorted(allowed))}"]


def check_sku(skus: list[dict], size: str) -> list[str]:
    match = next((sku for sku in skus if sku["name"] == size), None)
    if match is None:
        return [f"{size} is not offered in this region"]
    reasons = [r["reasonCode"] for r in match.get("restrictions") or []]
    if reasons:
        return [f"{size} is restricted: {', '.join(reasons)}"]
    return []


def check_provider(provider: dict) -> list[str]:
    state = provider.get("registrationState")
    if state == "Registered":
        return []
    namespace = provider["namespace"]
    return [f"{namespace} is {state}; run: az provider register -n {namespace} --wait"]


def _dig(data: dict, *keys: str) -> Any:
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def check_vm(vm: dict, nic: dict) -> list[str]:
    failures = []
    os_delete = _dig(vm, "storageProfile", "osDisk", "deleteOption")
    if os_delete != "Delete":
        failures.append(f"OS disk deleteOption is {os_delete}, expected Delete")
    nic_delete = (_dig(vm, "networkProfile", "networkInterfaces") or [{}])[0].get("deleteOption")
    if nic_delete != "Delete":
        failures.append(f"NIC deleteOption is {nic_delete}, expected Delete")
    pip_delete = _dig((nic.get("ipConfigurations") or [{}])[0], "publicIPAddress", "deleteOption")
    if pip_delete != "Delete":
        failures.append(f"public IP deleteOption is {pip_delete}, expected Delete")
    if _dig(vm, "osProfile", "linuxConfiguration", "disablePasswordAuthentication") is not True:
        failures.append("password authentication is enabled")
    if _dig(vm, "diagnosticsProfile", "bootDiagnostics", "enabled"):
        failures.append("boot diagnostics is enabled")
    disk_sku = _dig(vm, "storageProfile", "osDisk", "managedDisk", "storageAccountType")
    if disk_sku != "StandardSSD_LRS":
        failures.append(f"OS disk is {disk_sku}, expected StandardSSD_LRS")
    tags = vm.get("tags") or {}
    for key, value in EXPECTED_TAGS.items():
        if tags.get(key) != value:
            failures.append(f"tag {key} is {tags.get(key)}, expected {value}")
    return failures


def _covers_ssh(port_range: str | None) -> bool:
    if not port_range:
        return False
    if port_range == "*":
        return True
    low, _, high = port_range.partition("-")
    return int(low) <= 22 <= int(high or low)


def check_nsg(nsg: dict) -> list[str]:
    failures = []
    for rule in nsg.get("securityRules") or []:
        if rule.get("direction") != "Inbound" or rule.get("access") != "Allow":
            continue
        ranges = [rule.get("destinationPortRange"), *(rule.get("destinationPortRanges") or [])]
        source = rule.get("sourceAddressPrefix") or ""
        if any(_covers_ssh(r) for r in ranges) and source.lower() in OPEN_SOURCES:
            failures.append(f"rule {rule['name']} allows SSH from {source}")
    return failures


def check_schedule(schedule: dict) -> list[str]:
    props = schedule.get("properties") or {}
    failures = []
    if props.get("status") != "Enabled":
        failures.append(f"auto-shutdown is {props.get('status')}")
    time = _dig(props, "dailyRecurrence", "time")
    if time != SHUTDOWN_TIME:
        failures.append(f"auto-shutdown time is {time}, expected {SHUTDOWN_TIME}")
    if props.get("timeZoneId") != SHUTDOWN_TZ:
        failures.append(f"auto-shutdown time zone is {props.get('timeZoneId')}, expected {SHUTDOWN_TZ}")
    notify = _dig(props, "notificationSettings", "status")
    if notify != "Enabled":
        failures.append(f"shutdown notification is {notify}")
    return failures


def check_budget(budget: dict, max_amount: float) -> list[str]:
    props = budget.get("properties") or {}
    failures = []
    amount = props.get("amount")
    if amount is None or amount > max_amount:
        failures.append(f"budget amount {amount} exceeds {max_amount}")
    notifications = (props.get("notifications") or {}).values()
    if not any(n.get("enabled") and n.get("contactEmails") for n in notifications):
        failures.append("budget has no enabled notification with a contact email")
    return failures


def run_az(*args: str) -> Any:
    az = shutil.which("az") or shutil.which("az.cmd")
    if az is None:
        raise AzError("Azure CLI 'az' not found on PATH")
    result = subprocess.run([az, *args, "-o", "json"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise AzError(result.stderr.strip())
    return json.loads(result.stdout or "null")


def preflight(location: str, size: str) -> list[str]:
    failures = check_region(run_az("policy", "assignment", "list"), location)
    skus = run_az("vm", "list-skus", "-l", location, "--size", size, "--resource-type", "virtualMachines")
    failures += check_sku(skus, size)
    failures += check_provider(run_az("provider", "show", "-n", "Microsoft.DevTestLab"))
    return failures


def verify(resource_group: str, vm_name: str, budget_name: str, max_budget: float) -> list[str]:
    vm = run_az("vm", "show", "-g", resource_group, "-n", vm_name)
    nic = run_az("network", "nic", "show", "--ids", vm["networkProfile"]["networkInterfaces"][0]["id"])
    nsg = run_az("network", "nsg", "show", "-g", resource_group, "-n", f"{vm_name}NSG")
    schedule = run_az(
        "resource", "show", "-g", resource_group, "-n", f"shutdown-computevm-{vm_name}",
        "--resource-type", "Microsoft.DevTestLab/schedules",
    )
    subscription = run_az("account", "show")["id"]
    budget = run_az(
        "rest", "--method", "get", "--url",
        f"https://management.azure.com/subscriptions/{subscription}/providers/Microsoft.Consumption"
        f"/budgets/{budget_name}?api-version=2023-11-01",
    )
    return check_vm(vm, nic) + check_nsg(nsg) + check_schedule(schedule) + check_budget(budget, max_budget)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Azure staging VM preflight and verification checks")
    sub = parser.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("preflight")
    pre.add_argument("--location", default="northcentralus")
    pre.add_argument("--size", default="Standard_B2ats_v2")
    ver = sub.add_parser("verify")
    ver.add_argument("--resource-group", default="rg-career-platform")
    ver.add_argument("--vm-name", default="vm-career-platform")
    ver.add_argument("--budget-name", default="budget-isba4775")
    ver.add_argument("--max-budget", type=float, default=15)
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            failures = preflight(args.location, args.size)
        else:
            failures = verify(args.resource_group, args.vm_name, args.budget_name, args.max_budget)
    except AzError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for failure in failures:
        print(f"FAIL: {failure}")
    if not failures:
        print(f"{args.command}: all checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/operations/test_azure_checks.py -q`
Expected: PASS (all tests).

- [ ] **Step 5: Run the full suite to confirm nothing else broke**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/azure_checks.py tests/operations/test_azure_checks.py
git commit -m "ops: add Azure preflight and verification checks"
```

---

### Task 3: Idempotent host bootstrap

**Files:**
- Create: `deploy/azure/bootstrap.sh`
- Test: `tests/operations/test_azure_bootstrap.py`

**Interfaces:**
- Consumes: paths and user from `deploy/systemd/career-platform.service` (`User=career-platform`, `WorkingDirectory=/srv/career-platform`, `EnvironmentFile=/etc/career-platform/.env`) and `deploy/nginx/career-platform.conf` (`/srv/career-platform/snapshots/`).
- Produces: a host where Task 8 of the platform plan can copy the systemd unit and Nginx config and start the service. Nginx is installed but stopped and disabled until Task 8 configures TLS.

- [ ] **Step 1: Write the failing tests**

Create `tests/operations/test_azure_bootstrap.py`:

```python
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path("deploy/azure/bootstrap.sh")
UNIT = Path("deploy/systemd/career-platform.service")


def script() -> str:
    return SCRIPT.read_text()


def test_script_fails_fast():
    assert script().startswith("#!/usr/bin/env bash\nset -euo pipefail\n")


def test_script_matches_systemd_unit_paths():
    unit = UNIT.read_text()
    text = script()
    user = re.search(r"^User=(.+)$", unit, re.M).group(1)
    workdir = re.search(r"^WorkingDirectory=(.+)$", unit, re.M).group(1)
    env_dir = str(Path(re.search(r"^EnvironmentFile=(.+)$", unit, re.M).group(1)).parent).replace("\\", "/")
    assert f'SERVICE_USER="{user}"' in text
    assert f'APP_DIR="{workdir}"' in text
    assert f'ENV_DIR="{env_dir}"' in text
    assert 'SNAPSHOT_DIR="$APP_DIR/snapshots"' in text


def test_user_creation_is_idempotent_and_non_login():
    text = script()
    assert 'if ! id -u "$SERVICE_USER"' in text
    assert "--shell /usr/sbin/nologin" in text
    assert "--system" in text


def test_env_dir_is_not_world_readable():
    assert 'install -d -o root -g "$SERVICE_USER" -m 0750 "$ENV_DIR"' in script()


def test_ssh_hardening_is_validated_before_reload():
    text = script()
    for line in ("PermitRootLogin no", "PasswordAuthentication no", "KbdInteractiveAuthentication no"):
        assert line in text
    assert text.index("install -d -m 0755 /run/sshd") < text.index("sshd -t")
    assert text.index("sshd -t") < text.index("systemctl try-reload-or-restart ssh")


def test_unattended_security_upgrades_enabled():
    text = script()
    assert 'APT::Periodic::Unattended-Upgrade "1";' in text
    assert "unattended-upgrades" in text


def test_swap_is_created_once_for_1gib_vm():
    text = script()
    assert "if [ ! -f /swapfile ]" in text
    assert "/swapfile none swap sw 0 0" in text


def test_nginx_stays_disabled_until_task_8():
    assert "systemctl disable --now nginx" in script()


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not installed")
def test_script_is_valid_bash():
    result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/operations/test_azure_bootstrap.py -q`
Expected: FAIL with `FileNotFoundError` for `deploy/azure/bootstrap.sh`.

- [ ] **Step 3: Write the bootstrap script**

Create `deploy/azure/bootstrap.sh` (LF line endings — add `deploy/azure/*.sh text eol=lf` to `.gitattributes` if Git on Windows converts it):

```bash
#!/usr/bin/env bash
set -euo pipefail

# Prepares an Ubuntu 24.04 host for the career-platform service.
# Safe to re-run: every step checks or overwrites to a known state.

SERVICE_USER="career-platform"
APP_DIR="/srv/career-platform"
ENV_DIR="/etc/career-platform"
SNAPSHOT_DIR="$APP_DIR/snapshots"

export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q nginx python3.12-venv unattended-upgrades

# Nginx is configured and enabled by Task 8; keep port 80 dark until then.
systemctl disable --now nginx

if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0755 "$APP_DIR"
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0755 "$SNAPSHOT_DIR"
install -d -o root -g "$SERVICE_USER" -m 0750 "$ENV_DIR"

cat > /etc/ssh/sshd_config.d/60-career-platform.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
EOF
# Ubuntu 24.04 socket-activates sshd, so the service may be idle: create its runtime dir for
# `sshd -t`, and only reload if running (new connections read the file either way).
install -d -m 0755 /run/sshd
sshd -t
systemctl try-reload-or-restart ssh

cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

# B2ats_v2 has 1 GiB RAM and no temp disk; 1 GiB swap keeps pip installs from OOM-killing.
if [ ! -f /swapfile ]; then
  fallocate -l 1G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo "/swapfile none swap sw 0 0" >> /etc/fstab
fi

echo "bootstrap complete: $(id "$SERVICE_USER")"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/operations/test_azure_bootstrap.py -q`
Expected: PASS (9 passed; `test_script_is_valid_bash` runs because Git Bash provides `bash`).

- [ ] **Step 5: Commit**

```bash
git add deploy/azure/bootstrap.sh tests/operations/test_azure_bootstrap.py
git commit -m "ops: add idempotent Azure host bootstrap"
```

---

### Task 4: Runbook reflects the as-built VM

**Files:**
- Modify: `deploy/azure/README.md` (insert new sections before `## VM hardening`; keep all existing sections)
- Test: `tests/operations/test_azure_template.py` (add one test)

**Interfaces:**
- Consumes: file names from Tasks 1–3 and CLI commands from Task 2.

- [ ] **Step 1: Write the failing test**

Append to `tests/operations/test_azure_template.py`:

```python
def test_runbook_documents_provisioning_and_cost_controls():
    runbook = Path("deploy/azure/README.md").read_text()
    for needle in (
        "## Provisioning the staging VM",
        "python -m scripts.azure_checks preflight",
        "az deployment group what-if",
        "deploy/azure/bootstrap.sh",
        "python -m scripts.azure_checks verify",
        "az vm deallocate",
        "az group delete -n rg-career-platform",
        "MSYS_NO_PATHCONV=1",
        "northcentralus",
    ):
        assert needle in runbook, needle
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/operations/test_azure_template.py::test_runbook_documents_provisioning_and_cost_controls -q`
Expected: FAIL with `AssertionError: ## Provisioning the staging VM`.

- [ ] **Step 3: Add the provisioning sections to the runbook**

Insert directly after the first paragraph of `deploy/azure/README.md`:

````markdown
## Provisioning the staging VM

The staging VM is defined by `deploy/azure/vm.json`. The Azure for Students subscription only allows
`northcentralus`, `canadacentral`, `denmarkeast`, `belgiumcentral`, and `norwayeast`, and restricts most
B-series sizes, so the VM runs as `Standard_B2ats_v2` in `northcentralus` rather than the course's
West US 2 / `Standard_B2ts_v2`. The resource group's own metadata is in `westus2`; every resource sets
its location explicitly so nothing inherits that disallowed region.

In Git Bash, export `MSYS_NO_PATHCONV=1` first so resource IDs such as `/subscriptions/...` are not
rewritten into Windows paths.

1. Copy the example files and fill in your values (both copies are git-ignored):

   ```bash
   cp deploy/azure/vm.parameters.example.json deploy/azure/vm.parameters.json
   cp deploy/azure/budget.example.json deploy/azure/budget.json
   ```

2. Check region policy, size availability, and provider registration:

   ```bash
   python -m scripts.azure_checks preflight --location northcentralus --size Standard_B2ats_v2
   ```

3. Preview, then apply. Stop if what-if shows any `Delete` or a `Create` of the VM:

   ```bash
   az deployment group what-if -g rg-career-platform --template-file deploy/azure/vm.json --parameters @deploy/azure/vm.parameters.json
   az deployment group create -g rg-career-platform -n vm-career-platform --template-file deploy/azure/vm.json --parameters @deploy/azure/vm.parameters.json
   ```

4. Prepare the host (service user, directories, SSH hardening, unattended upgrades, swap):

   ```bash
   az vm run-command invoke -g rg-career-platform -n vm-career-platform --command-id RunShellScript --scripts @deploy/azure/bootstrap.sh
   ```

5. Create or refresh the budget, then verify everything:

   ```bash
   SUB=$(az account show --query id -o tsv)
   az rest --method put --url "https://management.azure.com/subscriptions/$SUB/providers/Microsoft.Consumption/budgets/budget-isba4775?api-version=2023-11-01" --body @deploy/azure/budget.json
   python -m scripts.azure_checks verify
   ```

## Cost controls

- Auto-shutdown deallocates the VM daily at 18:00 Pacific; it does not auto-start.
- Stop billing for compute with `az vm deallocate -g rg-career-platform -n vm-career-platform`
  (`az vm stop` keeps billing). Start with `az vm start -g rg-career-platform -n vm-career-platform`.
- While deallocated, the public IP (~$3.65/month) and OS disk (~$2.40/month) still bill.
- OS disk, NIC, and public IP delete with the VM; `budget-isba4775` emails at 50%/100% actual and 100% forecast of $15/month.
- Open HTTP/HTTPS only when Task 8 deploys Nginx, by setting `allowWebTraffic` to `true` and redeploying.
- If your laptop's public IP changes, update `operatorIp` and redeploy; SSH is refused until you do.

## Teardown

Delete everything at the end of the course with `az group delete -n rg-career-platform`, then remove the
budget with `az rest --method delete --url ".../budgets/budget-isba4775?api-version=2023-11-01"`.
````

- [ ] **Step 4: Run the operations tests to verify they pass**

Run: `pytest tests/operations -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add deploy/azure/README.md tests/operations/test_azure_template.py
git commit -m "docs: document Azure staging VM provisioning and cost controls"
```

---

### Task 5: Apply to the live VM and verify

This task changes live Azure resources. Every step before `create` is read-only; stop and report if any expectation is not met.

**Files:**
- Create (untracked): `deploy/azure/vm.parameters.json`, `deploy/azure/budget.json`

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces: a live VM that passes `verify`, with the service user and directories Task 8 needs.

- [ ] **Step 1: Create the real parameter files**

Copy the examples (Task 4 runbook step 1). Set `sshPublicKey` to the output of `cat ~/.ssh/isba4775_azure.pub`, `operatorIp` to `curl -4 -s https://api.ipify.org`, and `shutdownEmail` / budget `contactEmails` to the operator's email.
Run: `git status --short deploy/azure`
Expected: no output (both files are ignored).

- [ ] **Step 2: Run preflight**

Run: `python -m scripts.azure_checks preflight`
Expected: `preflight: all checks passed`, exit code 0.

- [ ] **Step 3: Preview the redeploy**

Run: `MSYS_NO_PATHCONV=1 az deployment group what-if -g rg-career-platform --template-file deploy/azure/vm.json --parameters @deploy/azure/vm.parameters.json`
Expected: no `Delete` and no `Create` of `vm-career-platform`. `NoChange`, `Ignore`, or `Modify` limited to tags on the VNet/NSG and protocol casing (`TCP`→`Tcp`) on `Allow-SSH-Laptop` are acceptable. Anything else: stop and report the what-if output.

- [ ] **Step 4: Apply the template**

Run: `MSYS_NO_PATHCONV=1 az deployment group create -g rg-career-platform -n vm-career-platform --template-file deploy/azure/vm.json --parameters @deploy/azure/vm.parameters.json --query properties.provisioningState -o tsv`
Expected: `Succeeded`.

- [ ] **Step 5: Bootstrap the host**

Run: `MSYS_NO_PATHCONV=1 az vm run-command invoke -g rg-career-platform -n vm-career-platform --command-id RunShellScript --scripts @deploy/azure/bootstrap.sh --query "value[0].message" -o tsv`
Expected: output ends with `bootstrap complete: uid=... (career-platform) ...` and the `[stderr]` section contains no `error`. The VM must be running; if auto-shutdown deallocated it, run `az vm start` first.

- [ ] **Step 6: Verify Azure-side invariants**

Run: `python -m scripts.azure_checks verify`
Expected: `verify: all checks passed`, exit code 0.

- [ ] **Step 7: Verify host-side state over SSH**

Run:
```bash
IP=$(az vm show -d -g rg-career-platform -n vm-career-platform --query publicIps -o tsv)
ssh -i ~/.ssh/isba4775_azure azureuser@$IP 'id career-platform; stat -c "%U:%G %a %n" /srv/career-platform /srv/career-platform/snapshots /etc/career-platform; sudo sshd -T | grep -E "^(permitrootlogin|passwordauthentication) "; swapon --show=NAME,SIZE --noheadings; systemctl is-enabled nginx'
```
Expected:
```
uid=... (career-platform) gid=... (career-platform) groups=... (career-platform)
career-platform:career-platform 755 /srv/career-platform
career-platform:career-platform 755 /srv/career-platform/snapshots
root:career-platform 750 /etc/career-platform
permitrootlogin no
passwordauthentication no
/swapfile 1024M
disabled
```

- [ ] **Step 8: Re-run bootstrap to prove idempotency**

Run Step 5 again.
Expected: same `bootstrap complete` line; `grep -c swapfile /etc/fstab` over SSH still prints `1`.

- [ ] **Step 9: Leave the VM deallocated if not in use**

Run: `az vm deallocate -g rg-career-platform -n vm-career-platform`
Expected: returns without error; `az vm show -d -g rg-career-platform -n vm-career-platform --query powerState -o tsv` prints `VM deallocated`.

**Done looks like:** `verify` passes, the host has the `career-platform` user and directories matching the systemd unit, SSH rejects passwords and root, and the VM is deallocated.

---

## Self-review

- **Coverage of the course settings table:** resource group, name, region (adapted), availability (no redundancy — template declares none), image, size (adapted), auth, key, inbound ports, disk type, delete options, auto-shutdown + notification, boot diagnostics, tags → Tasks 1 and 2. The two adaptations are recorded in Global Constraints and the runbook.
- **Coverage of platform Task 8 prerequisites:** service user, `/srv/career-platform`, snapshots dir, `/etc/career-platform`, SSH only from operator range, HTTP/HTTPS opened later via `allowWebTraffic` → Tasks 1, 3, 4.
- **Placeholder scan:** example files intentionally hold placeholder values (`REPLACE_WITH...`, `203.0.113.10`, `you@example.com`) that Task 5 Step 1 replaces; these are not plan gaps.
- **Name consistency:** `<vmName>NSG`, `shutdown-computevm-<vmName>`, `budget-isba4775`, `Allow-SSH-Laptop`/300 are used identically in the template, checks, runbook, and live resources.
- **Out of scope:** Nginx/TLS/systemd installation, PostgreSQL, DNS — owned by platform plan Task 8.
