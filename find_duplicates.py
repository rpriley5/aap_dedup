#!/usr/bin/env python3
import csv
import json
from collections import defaultdict

# Read the CSV file
duplicates = defaultdict(list)

with open('/tmp/metrics_duplicate_test/main_host.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        host_name = row['host_name']
        ansible_host = row['ansible_host_variable']

        # Skip empty ansible_host values
        if ansible_host and ansible_host.strip():
            duplicates[ansible_host].append(host_name)

# Print duplicates (IPs with more than 1 hostname)
print("=== DUPLICATE HOSTS (Same IP, Multiple Hostnames) ===\n")
found_duplicates = False

for ip, hostnames in sorted(duplicates.items()):
    if len(hostnames) > 1:
        found_duplicates = True
        print(f"IP: {ip}")
        print(f"  Count: {len(hostnames)} hosts")
        print(f"  Hostnames: {', '.join(hostnames)}")
        print()

if not found_duplicates:
    print("No duplicates found!")
