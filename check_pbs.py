#!/usr/bin/env python3
import argparse
from enum import Enum
import sys

import proxmoxer


class CheckStatus(Enum):
    OK = 0
    WARNING = 1
    CRITICAL = 2
    UNKNOWN = 3


class CheckPBS:
    def __init__(self):
        self._modes = {
            "storage": self.check_storage_usage
        }

        parser = argparse.ArgumentParser("check_pbs")
        parser.add_argument("--api-endpoint", "-e", type=str,
                            required=True,
                            help="PBS api endpoint host")
        parser.add_argument("--api-port", type=int, default=8007,
                            help="PBS api endpoint port")
        parser.add_argument("--username", "-u", type=str,
                            help="PBS api user (root@pam, icinga2@pve, ...)")
        parser.add_argument("--password", "-p", type=str,
                            help="PBS api user password")
        parser.add_argument("--token-name", type=str,
                            help="PBS api token name")
        parser.add_argument("--token-value", type=str,
                            help="PBS api token value")
        parser.add_argument("--insecure", "-k", action="store_true",
                            default=False,
                            help="Don't verify HTTPS certificate")
        parser.add_argument("--mode", "-m",
                            choices=self._modes.keys(),
                            help="Check mode to use.")
        parser.add_argument("--name", "-n", type=str,
                            help="Name of resource to check")
        parser.add_argument("--exclude", "-E", action='append', default=[],
                            help="Exclude specified resource")
        parser.add_argument("--warning", "-w", type=float,
                            help="Warning threshold")
        parser.add_argument("--critical", "-c", type=float,
                            help="Critical threshold")
        self._parser = parser
        self._args = parser.parse_args()

        self._check_status = CheckStatus.UNKNOWN
        self._description = "Something really bad happend"
        self._perfdata = []

        self._connect()

    def _connect(self):
        if self._args.token_name:
            if not self._args.token_value:
                print("")
        self._pbs = proxmoxer.ProxmoxAPI(self._args.api_endpoint, service="PBS",
                                         user=self._args.username, password=self._args.password,
                                         verify_ssl=not self._args.insecure)

    def _status(self):
        status = f"{self._check_status.name}: {self._description}"
        if self._perfdata:
            status += f" | {' '.join(self._perfdata)}"
        print(status)
        exit(self._check_status.value)

    def _storage_calculate_usage(self, datastore, perfdata=True):
        total, used = datastore["total"], datastore["used"]
        usage = used / total * 100
        if perfdata:
            self._perfdata.extend([
                f"{datastore['store']}_usage={usage:.2f}%;{self._args.warning:.2f}%;{self._args.critical:.2f}%;0%;100%",
                f"{datastore['store']}_used={used};;;0;{total}"
            ])
        status = CheckStatus.OK
        description = f"Used storage of {datastore['store']} is {usage:.2f}"
        if usage >= self._args.critical:
            status = CheckStatus.CRITICAL
            description = f"Used storage of {datastore['store']} is critically {usage:.2f}%"
        elif usage >= self._args.warning:
            status = CheckStatus.WARNING
            description = f"Used storage of {datastore['store']} is above warning {usage:.2f}%"
        return (status, description)

    def _check_single_storage(self):
        datastore_usage = self._pbs.status("datastore-usage").get()
        datastore = None
        for ds in datastore_usage:
            if ds["store"] == self._args.name:
                datastore = ds
                break

        if not datastore:
            self._description = f"Storage {self._args.name} not found"
            return self._status()

        self._check_status, self._description = self._storage_calculate_usage(datastore)
        return self._status()

    def _check_all_storage(self):
        datastore_usage = self._pbs.status("datastore-usage").get()
        self._check_status = CheckStatus.OK
        self._description = "All datastores are fine"
        for ds in sorted(datastore_usage, key=lambda x: x["store"]):
            if ds["store"] in self._args.exclude:
                continue
            dsstatus, description = self._storage_calculate_usage(ds)
            if dsstatus.value > self._check_status.value:
                self._check_status = dsstatus
                self._description = description
        return self._status()

    def check_storage_usage(self):
        if self._args.name:
            return self._check_single_storage()
        return self._check_all_storage()

    def run(self):
        if not self._args.critical:
            print("Missing --critical", file=sys.stderr)
            self._parser.print_help()
            exit(CheckStatus.UNKNOWN.value)
        if not self._args.warning:
            print("Missing --warning", file=sys.stderr)
            self._parser.print_help()
            exit(CheckStatus.UNKNOWN.value)

        self._modes[self._args.mode]()


if __name__ == "__main__":
    CheckPBS().run()