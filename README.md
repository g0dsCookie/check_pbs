# check_pbs

Icinga check command for Proxmox Backup Server via API

## Setup

### Requirements

* Python >=3.7
* proxmoxer >=1.2.0
* requests

You may install all required Python modules with `pip install -r requirements.txt`

## Check examples

### Check storage usage

`./check_pbs.py -u <API-USER> -p <API_PASSWORD> -e <API_ENDPOINT> -m storage -n <STORAGE_NAME> -w 70 -c 90`