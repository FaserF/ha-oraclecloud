# <img src="custom_components/oraclecloud/brand/logo.png" height="50"> Oracle Cloud Infrastructure (OCI) for Home Assistant

[![GitHub Release](https://img.shields.io/github/release/FaserF/ha-oraclecloud.svg?style=flat-square)](https://github.com/FaserF/ha-oraclecloud/releases)
[![License](https://img.shields.io/github/license/FaserF/ha-oraclecloud.svg?style=flat-square)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-custom-orange.svg?style=flat-square)](https://hacs.xyz)
[![CI Orchestrator](https://github.com/FaserF/ha-oraclecloud/actions/workflows/ci-orchestrator.yml/badge.svg)](https://github.com/FaserF/ha-oraclecloud/actions/workflows/ci-orchestrator.yml)
[![Renovate](https://img.shields.io/badge/renovate-enabled-brightgreen.svg?style=flat-square)](https://renovatebot.com)

Monitor and manage your Oracle Cloud Infrastructure (OCI) Free Tier virtual machines directly from Home Assistant. Track resource usage, monitor instance health, and control your cloud servers with ease.

## 🧭 Quick Links

| | | | |
| :--- | :--- | :--- | :--- |
| [✨ Features](#-features) | [📦 Installation](#-installation) | [⚙️ Configuration](#️-configuration) | [🛡️ Security](SECURITY.md) |
| [🧱 Entities](#-entities) | [📖 Automations](#-automation-examples) | [❓ FAQ](#-troubleshooting--faq) | [🧑‍💻 Development](#-development) |
| [💖 Support](#️-support-this-project) | [📄 License](#-license) | | |

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=FaserF&repository=ha-oraclecloud&category=integration)

### Why use this integration?
Oracle Cloud's Always Free tier is highly popular for hosting OpenClaw or HA companion services (like VPNs, databases, or game servers). This integration provides **native monitoring** via the OCI SDK, allowing you to track CPU/Memory/Network usage and control your instances (Start/Stop/Reboot) directly from your Home Assistant dashboard.

No manual script-polling or complex setup is required — everything is handled via a modern, auto-discovering Config Flow.

## ✨ Features

- **Resource Monitoring**:
  - **CPU & Memory**: Real-time utilization tracking for your ARM/AMD instances.
  - **Network & Disk**: Detailed I/O monitoring with 2-decimal precision.
  - **Device Tracker**: Integrated device tracker with hardware specs (CPU, RAM, OS).
- **Instance Management**:
  - **Power Control**: Native buttons for Start, Stop, and Reboot.
  - **Public/Private IP**: Track IP addresses for dynamic DNS or connectivity monitoring.
- **Account Monitoring**:
  - **Budgets**: Track actual monthly spend, forecasted costs, and spend percentage.
  - **Resource Usage**: Real-time tracking of "Always Free" resource consumption (Used OCPUs, Memory).
  - **Announcements**: Monitor active maintenance and security notices.
- **Storage Analytics**:
  - **Block Volumes**: Monitor size and lifecycle state of all attached volumes.
  - **Object Storage**: Track bucket sizes and object counts.
- **Proactive Alerting**:
  - **Budget Alert**: Native binary sensor that triggers on your predefined budget thresholds.
- **Native Experience**:
  - **Full Localization**: English and German translations included.
  - **Modern UI**: High-quality icons and branding for a premium dashboard look.

## ❤️ Support This Project

> I maintain this integration in my **free time alongside my regular job** — bug hunting, new features, and keeping up with OCI updates. Every donation helps me stay independent and dedicate more time to open-source work.
>
> **This project is and will always remain 100% free.**
>
> Donations are completely voluntary — but the more support I receive, the more time I can realistically invest into these projects. 💪

<div align="center">

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor%20on-GitHub-%23EA4AAA?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/FaserF)&nbsp;&nbsp;
[![PayPal](https://img.shields.io/badge/Donate%20via-PayPal-%2300457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/FaserF)

</div>

## 📦 Installation

### HACS (Recommended)

1. Open HACS in Home Assistant.
2. Click the three dots -> **Custom repositories**.
3. Add `FaserF/ha-oraclecloud` with category **Integration**.
4. Search for **Oracle Cloud Infrastructure**.
5. Install and restart Home Assistant.

### Manual Installation

1. Copy the `custom_components/oraclecloud` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## ⚙️ Configuration

### 1. OCI API Key Setup (Required)
The integration requires an API Key to communicate with Oracle Cloud.

1. Log in to your [Oracle Cloud Console](https://cloud.oracle.com/).
2. Click your **Profile Icon** (top right) -> **User Settings**.
3. Scroll down to **Resources** (bottom left) and click **API Keys**.
4. Click **Add API Key**.
5. Select **Generate API Key Pair**.
6. **Important**: Download the **Private Key** (PEM). You will need its content for Home Assistant.
7. Click **Add**.
8. A "Configuration File Preview" will appear. **Copy these four values**:
   - `tenancy` (Tenancy OCID)
   - `user` (User OCID)
   - `fingerprint`
   - `region` (e.g., `eu-frankfurt-1`)

### 2. Home Assistant Integration Setup
1. Go to **Settings > Devices & Services**.
2. Click **Add Integration** and search for **Oracle Cloud Infrastructure**.
3. Fill in the fields using the values from Step 1.
4. Paste the entire content of the **Private Key** PEM file you downloaded into the "Private Key" field.
5. (Optional) Provide a **Compartment OCID** if you only want to monitor a specific group of VMs.
6. The integration will now auto-discover all instances and add them as devices.

## 🧱 Entities

The integration provides a wide range of entities to monitor your cloud resources. Most advanced metrics are **disabled by default** to keep your dashboard clean. You can enable them in the entity settings.

### Compute Instances
- **Sensors**: CPU Utilization, Memory Utilization (GB/%), Disk Utilization, Network I/O (Bytes/Drops/Errors), Public/Private IP, Instance State, Fault/Availability Domain, Region, Shape, Time Created.
- **Buttons**: Start, Stop, Reboot (Soft Reset).
- **Device Tracker**: A native tracker showing `home`/`not_home` with hardware specs (OCPUs, Memory, OS) as attributes.

### Account & Storage (Tenancy-wide)
- **Budgets**: Actual Spend, Forecasted Spend.
- **Resource Usage**: ARM OCPU and Memory consumption (Always Free tracking).
- **Announcements**: Total count of active maintenance and security notices.
- **Block Storage**: Size and Lifecycle State of all volumes in the compartment.
- **Object Storage**: Approximate Size and Object Count for every bucket.
- **Binary Sensors**: Budget Alert (Triggers when spend exceeds threshold).

## 📖 Automation Examples

<details>
<summary><strong>🚨 Notification on Public IP Change</strong></summary>

```yaml
alias: "OCI: Public IP Updated"
trigger:
  - platform: state
    entity_id: sensor.my_vm_public_ip
action:
  - service: notify.notify
    data:
      title: "🌐 OCI Instance IP Changed"
      message: "New Public IP: {{ trigger.to_state.state }}"
```
</details>

<details>
<summary><strong>🔁 Auto-Restart on High Load</strong></summary>

```yaml
alias: "OCI: Auto-Reboot on CPU Spike"
trigger:
  - platform: numeric_state
    entity_id: sensor.my_vm_cpu_utilization
    above: 99
    for:
      minutes: 10
action:
  - service: button.press
    target:
      entity_id: button.my_vm_reboot_instance
```
</details>

<details>
<summary><strong>🛡️ Security: Notification on State Change</strong></summary>

```yaml
alias: "OCI: Instance State Alert"
trigger:
  - platform: state
    entity_id: sensor.my_vm_instance_state
    from: "RUNNING"
action:
  - service: notify.notify
    data:
      title: "⚠️ OCI Instance Stopped"
      message: "Your VM was stopped! Current state: {{ trigger.to_state.state }}"
```
</details>

<details>
<summary><strong>🌙 Night Mode: Stop Instance at Midnight</strong></summary>

```yaml
alias: "OCI: Stop VM at Night"
trigger:
  - platform: time
    at: "23:00:00"
action:
  - service: button.press
    target:
      entity_id: button.my_vm_stop_instance
```
</details>

<details>
<summary><strong>💰 Budget: Alert on Spend Limit</strong></summary>

```yaml
alias: "OCI: Budget Threshold Exceeded"
trigger:
  - platform: state
    entity_id: binary_sensor.oracle_budget_alert
    to: "on"
action:
  - service: notify.notify
    data:
      title: "💸 OCI Budget Warning"
      message: "The OCI spend limit has been exceeded! Actual spend: {{ states('sensor.budget_actual_spend') }}$"
```
</details>

<details>
<summary><strong>📅 Maintenance: New OCI Announcement</strong></summary>

```yaml
alias: "OCI: Maintenance Notification"
trigger:
  - platform: state
    entity_id: sensor.account_announcements_count
action:
  - condition: template
    value_template: "{{ trigger.to_state.state | int > trigger.from_state.state | int }}"
  - service: notify.notify
    data:
      title: "🛠️ OCI Maintenance Alert"
      message: "A new OCI announcement has been posted. Please check the OCI Console."
```
</details>

<details>
<summary><strong>📦 Storage: Large Bucket Size Alert</strong></summary>

```yaml
alias: "OCI: Bucket Size Warning"
trigger:
  - platform: numeric_state
    entity_id: sensor.bucket_my_backups_size
    above: 100
action:
  - service: notify.notify
    data:
      title: "⚠️ OCI Storage Warning"
      message: "Bucket 'my-backups' has exceeded 100 GB!"
```
</details>

## ❓ Troubleshooting & FAQ

### "Failed to connect to Oracle Cloud API"
- Double-check your **User OCID** and **Tenancy OCID**.
- Ensure the **Fingerprint** matches the one generated in the OCI console.
- Ensure the **Private Key** includes the `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----` lines.

### Only some VMs are found
- By default, the integration searches the root compartment. If your VMs are in a sub-compartment, provide that **Compartment OCID** in the integration configuration.

### Metrics are showing `Unavailable` or `Unknown`
The OCI Monitoring API relies on several factors. If sensors show as "Unknown" or "Unavailable", check the following:

#### 🖥️ Compute Instance Sensors (CPU, RAM, Network, Disk)
- **Agent Dependency**: These metrics require the **Oracle Cloud Agent** to be installed and running on the VM.
- **Plugin Status**: In the OCI Console, go to **Instance Details > Resources > Compute Agent**. Ensure the **Compute Instance Monitoring** plugin is enabled and status is `Running`.
- **Latency**: OCI Monitoring data has a 2-5 minute propagation delay. The integration uses a sliding window to ensure data is available.
- **Disk Utilization**: This specific metric is often disabled by default. Ensure `oci-utils` is installed on your Linux VM for the agent to report filesystem usage.
- **Throttling & Conntrack**: These require VNIC-level monitoring to be active. They are disabled by default in Home Assistant.
- **Plural Naming**: Newer versions (2.2.0+) of the OCI agent use plural metric names (e.g., `NetworksBytesIn`). This integration automatically handles both singular and plural names.

#### 💰 Account & Budget Sensors
- **Scope**: Budgets and Announcements are tenancy-wide. Ensure your API user has `inspect` permissions at the **Root** compartment (Tenancy) level.
- **ARM Usage**: Used OCPU/Memory sensors now sum consumption across all **Availability Domains**.

#### 📦 Storage Sensors (Volumes, Buckets)
- **Compartment Scope**: By default, the integration searches the compartment you provided (or the Root). If your storage resources are in a different compartment, they will not appear unless you configure a specific Compartment OCID.

### 🛡️ Dependency Workaround (Technical Note)
As of early 2026, the official OCI Python SDK on PyPI has a restrictive version cap on `pyOpenSSL` and `cryptography` that conflicts with modern Home Assistant environments. We use a patched fork to resolve this:

```json
// Original: "oci>=2.168.3"
// Workaround: https://github.com/FaserF/oci-python-sdk (Patched to remove PyOpenSSL caps)
"requirements": ["git+https://github.com/FaserF/oci-python-sdk.git@master#oci"]
```
This is a temporary measure until a official PR fix is merged and released by Oracle.

## 🧑‍💻 Development

```bash
# Setup development environment
pip install -r requirements_test.txt

# Run tests
pytest tests/
```

## 📄 License
MIT License. See [LICENSE](LICENSE) for details.
