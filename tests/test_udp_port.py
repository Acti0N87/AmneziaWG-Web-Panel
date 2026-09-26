"""Exercise migration safety without binding sockets or accessing VPN secrets."""
from pathlib import Path
import runpy
import subprocess
import unittest
from unittest.mock import patch

HELPER = Path(__file__).resolve().parents[1] / 'roles/amneziawg/files/check-udp-port.py'


class UDPPortTests(unittest.TestCase):
    def check(self, port, listeners='', current_port='51820', current_rc=0):
        current = subprocess.CompletedProcess([], current_rc, current_port + '\n', '')
        with (
            patch('sys.argv', [str(HELPER), str(port)]),
            patch('subprocess.check_output', return_value=listeners),
            patch('subprocess.run', return_value=current),
        ):
            runpy.run_path(str(HELPER), run_name='__main__')

    def test_free_privileged_and_high_ports(self):
        for port in (1, 53, 443, 51820, 65535):
            with self.subTest(port=port):
                self.check(port)

    def test_reject_invalid_bounds(self):
        for port in (0, 65536):
            with self.subTest(port=port), self.assertRaises(AssertionError):
                self.check(port)

    def test_loopback_dns_conflicts_with_wildcard_vpn(self):
        listener = 'UNCONN 0 0 127.0.0.53:53 0.0.0.0:* users:(("systemd-resolve",pid=1,fd=2))\n'
        with self.assertRaisesRegex(AssertionError, 'occupied by another service'):
            self.check(53, listener)

    def test_existing_kernel_vpn_sockets_allow_reapply(self):
        self.check(443, 'UNCONN 0 0 0.0.0.0:443 0.0.0.0:*\nUNCONN 0 0 [::]:443 [::]:*\n', '443')

    def test_unknown_ownerless_socket_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.check(443, 'UNCONN 0 0 0.0.0.0:443 0.0.0.0:*\n', current_rc=1)

    def test_userspace_owner_is_rejected_even_at_current_vpn_port(self):
        with self.assertRaises(AssertionError):
            self.check(443, 'UNCONN 0 0 0.0.0.0:443 0.0.0.0:* users:(("other",pid=1,fd=2))\n', '443')


if __name__ == '__main__':
    unittest.main()
