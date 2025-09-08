import unittest
from unittest.mock import patch, MagicMock
from subprocess import CalledProcessError

from arpx.network import NetworkVisibleManager

class TestNetworkManager(unittest.TestCase):

    @patch('os.geteuid', return_value=0)
    def test_check_root_as_root(self, mock_geteuid):
        """Test that check_root does nothing when run as root."""
        try:
            NetworkVisibleManager.check_root()
        except SystemExit:
            self.fail("check_root should not exit when run as root")

    @patch('os.geteuid', return_value=1000)
    @patch('sys.exit')
    def test_check_root_as_non_root(self, mock_exit, mock_geteuid):
        """Test that check_root calls sys.exit when not run as root."""
        NetworkVisibleManager.check_root()
        mock_exit.assert_called_once_with(1)

    @patch('subprocess.check_output', return_value=b'wlan0\n')
    def test_auto_detect_interface_success(self, mock_check_output):
        """Test successful auto-detection of the network interface."""
        iface = NetworkVisibleManager.auto_detect_interface()
        self.assertEqual(iface, 'wlan0')
        mock_check_output.assert_called_once_with("ip route | grep default | awk '{print $5}' | head -1", shell=True)

    @patch('subprocess.check_output', side_effect=Exception('command failed'))
    def test_auto_detect_interface_failure(self, mock_check_output):
        """Test fallback to 'eth0' when interface detection fails."""
        iface = NetworkVisibleManager.auto_detect_interface()
        self.assertEqual(iface, 'eth0')

    @patch('subprocess.check_output')
    def test_get_network_details_success(self, mock_check_output):
        """Test successful parsing of network details."""
        mock_output = b'''
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc ...
    link/ether 02:42:ac:11:00:02 brd ff:ff:ff:ff:ff:ff
    inet 172.17.0.2/16 brd 172.17.255.255 scope global eth0
       valid_lft forever preferred_lft forever
'''
        mock_check_output.return_value = mock_output
        manager = NetworkVisibleManager(interface='eth0')
        ip, net, cidr, bcast = manager.get_network_details()
        self.assertEqual(ip, '172.17.0.2')
        self.assertEqual(net, '172.17.0.0')
        self.assertEqual(cidr, '16')
        self.assertEqual(bcast, '172.17.255.255')

    @patch('subprocess.check_output', return_value=b'invalid output')
    def test_get_network_details_parsing_failure(self, mock_check_output):
        """Test that None is returned when parsing of network details fails."""
        manager = NetworkVisibleManager(interface='eth0')
        details = manager.get_network_details()
        self.assertEqual(details, (None, None, None, None))

    @patch('subprocess.run')
    def test_find_free_ips_success(self, mock_run):
        """Test finding free IPs successfully."""
        # Simulate that all pings and arps fail, indicating IPs are free
        mock_run.return_value = MagicMock(returncode=1)
        manager = NetworkVisibleManager(interface='eth0')
        ips = manager.find_free_ips('192.168.1.0', '24', num_ips=2, start_ip=100)
        self.assertEqual(len(ips), 2)
        self.assertEqual(ips, ['192.168.1.100', '192.168.1.101'])
        # 2 calls for ping, 2 for arping
        self.assertEqual(mock_run.call_count, 4)

    @patch('subprocess.run')
    def test_find_free_ips_some_taken(self, mock_run):
        """Test finding free IPs when some are already taken."""
        def run_side_effect(cmd, shell, capture_output):
            ip = cmd.split()[-1]
            if ip == '192.168.1.100':
                return MagicMock(returncode=0)  # IP taken
            return MagicMock(returncode=1)      # IP free
        mock_run.side_effect = run_side_effect

        manager = NetworkVisibleManager(interface='eth0')
        ips = manager.find_free_ips('192.168.1.0', '24', num_ips=2, start_ip=100)
        self.assertEqual(len(ips), 2)
        self.assertEqual(ips, ['192.168.1.101', '192.168.1.102'])

    @patch('subprocess.run')
    @patch('arpx.network.NetworkVisibleManager.get_interface_mac', return_value='00:11:22:33:44:55')
    def test_add_virtual_ip_with_visibility_success(self, mock_get_mac, mock_run):
        """Test successfully adding a virtual IP."""
        mock_run.return_value = MagicMock(returncode=0)
        manager = NetworkVisibleManager(interface='eth0')
        result = manager.add_virtual_ip_with_visibility('192.168.1.150', 'test1', '24')

        self.assertTrue(result)
        self.assertEqual(len(manager.virtual_ips), 1)
        self.assertEqual(manager.virtual_ips[0], ('192.168.1.150', 'eth0:test1', '24'))
        # ip addr add, ip_forward, proxy_arp, arping, ip neigh, arp -s
        self.assertGreaterEqual(mock_run.call_count, 6)

    @patch('subprocess.run', side_effect=CalledProcessError(1, 'cmd'))
    def test_add_virtual_ip_with_visibility_failure(self, mock_run):
        """Test failure when adding a virtual IP."""
        manager = NetworkVisibleManager(interface='eth0')
        result = manager.add_virtual_ip_with_visibility('192.168.1.150', 'test1', '24')
        self.assertFalse(result)
        self.assertEqual(len(manager.virtual_ips), 0)

if __name__ == '__main__':
    unittest.main()
