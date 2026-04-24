# AAP Metrics Utility - Duplicate Host Detection

This directory contains tools and documentation for detecting duplicate host entries in Ansible Automation Platform (AAP) 2.6 containerized installations using the metrics-utility tool.

## Overview

The metrics-utility is a built-in tool in AAP that collects usage data for billing and reporting. When configured with the `main_host` collector, it can identify duplicate host definitions across inventories - a common issue where the same physical machine is defined multiple times (by hostname, IP, FQDN, etc.) and counted separately for licensing.

## Problem Statement

Organizations often have the same host defined multiple times across different inventories:
- `webserver01` with ansible_host: `192.168.1.50`
- `192.168.1.50` as a separate entry
- `webserver01.example.com` pointing to the same IP

Each entry is counted as a separate managed node, inflating license usage even though they're all the same physical machine.

## Prerequisites

- AAP 2.6 containerized installation (single-node or multi-node)
- Access to the inventory file used for installation
- SSH access to the AAP host

## Setup Instructions

### Step 1: Configure metrics-utility in Inventory File

Edit your AAP installation inventory file (typically `inventory` in the installer directory) and add/update the `[automationcontroller:vars]` section:

```ini
[automationcontroller:vars]
metrics_utility_enabled=true
metrics_utility_extra_settings=[{"setting": "METRICS_UTILITY_SHIP_TARGET", "value": "directory"}, {"setting": "METRICS_UTILITY_SHIP_PATH", "value": "/var/lib/awx/metrics_utility/"}, {"setting": "METRICS_UTILITY_REPORT_TYPE", "value": "CCSPv2"}, {"setting": "METRICS_UTILITY_PRICE_PER_NODE", "value": "100"}, {"setting": "METRICS_UTILITY_REPORT_COMPANY_NAME", "value": "Your Company"}, {"setting": "METRICS_UTILITY_REPORT_EMAIL", "value": "admin@example.com"}, {"setting": "METRICS_UTILITY_REPORT_SKU", "value": "<change_me>"}, {"setting": "METRICS_UTILITY_OPTIONAL_COLLECTORS", "value": "main_host,main_jobevent"}]
```

**Key Settings:**
- `METRICS_UTILITY_SHIP_PATH`: Must use container-internal path `/var/lib/awx/metrics_utility/` (maps to host path)
- `METRICS_UTILITY_OPTIONAL_COLLECTORS`: **Must include `main_host`** to collect host inventory data

### Step 2: Remove Existing Metrics Containers (if upgrading)

If you're adding metrics-utility to an existing installation:

```bash
podman stop metrics-utility-gather metrics-utility-build-report
podman rm metrics-utility-gather metrics-utility-build-report
systemctl --user stop metrics-utility-gather.timer metrics-utility-build-report.timer
```

### Step 3: Run the Installer

```bash
cd ~/ansible-automation-platform-containerized-setup-2.6-<version>
ansible-playbook -i inventory ansible.containerized_installer.install
```

### Step 4: Verify Installation

```bash
# Check containers were created
podman ps -a | grep metrics

# Check systemd timers are active
systemctl --user list-timers | grep metrics

# Verify the OPTIONAL_COLLECTORS setting
podman inspect metrics-utility-gather | grep OPTIONAL_COLLECTORS
```

Expected output should show: `METRICS_UTILITY_OPTIONAL_COLLECTORS=main_host,main_jobevent`

### Step 5: Trigger Data Collection

```bash
# Manually trigger metrics collection
systemctl --user start metrics-utility-gather.service

# Check status
systemctl --user status metrics-utility-gather.service
```

### Step 6: Extract and Analyze Data

The metrics data is stored in dated directories. The `main_host.csv` file is in the daily snapshot tarball (timestamp `000000+0000`):

```bash
# Find the latest daily snapshot
DAILY_SNAPSHOT=$(find ~/aap/controller/data/metrics/data/ -name "*-000000+0000-000000+0000-0.tar.gz" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -f2- -d" ")

# Extract it
mkdir -p /tmp/metrics_analysis
cd /tmp/metrics_analysis
tar -xzf "${DAILY_SNAPSHOT}"

# Verify main_host.csv exists
ls -lah main_host.csv
```

## Using the Duplicate Detection Script

The `find_duplicates.py` script analyzes `main_host.csv` and identifies duplicate host entries.

### Usage

```bash
# Copy the script to your analysis directory
cp find_duplicates.py /tmp/metrics_analysis/

# Run it
cd /tmp/metrics_analysis
python3 find_duplicates.py
```

### Example Output

```
=== DUPLICATE HOSTS (Same IP, Multiple Hostnames) ===

IP: 192.168.122.22
  Count: 3 hosts
  Hostnames: node1, node2.example.com, 192.168.122.22
```

This shows that 3 separate host entries all point to IP `192.168.122.22`, meaning the same physical machine is being counted 3 times.


## Automated Collection Schedule

metrics-utility runs on systemd timers:

- **Gather**: Runs hourly (default) - collects job and host data
- **Build Report**: Runs weekly (default) - generates XLSX reports

View schedule:
```bash
systemctl --user list-timers | grep metrics
```

Modify schedule by updating inventory and re-running installer:
```ini
metrics_utility_cronjob_gather_schedule=*:0/30  # Every 30 minutes
metrics_utility_cronjob_report_schedule=*-*-02 00:00:00  # 2nd of month at midnight
```

## Additional Resources

- [Red Hat AAP 2.6 Documentation - metrics-utility](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation/appendix-metrics-utility)
- [AAP Containerized Installation Guide](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.6/html/containerized_installation/)

## Notes

- metrics-utility data is incremental - each collection picks up where the previous one left off
- The `main_host` collection is a **daily snapshot**, not incremental like `main_jobevent`
- Reports are generated as XLSX files in the ship path directory
- Data files are organized by date: `YYYY/MM/DD/`
- For large deployments, consider increasing memory allocation for the metrics containers

---

