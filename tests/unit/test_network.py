import unittest
from unittest.mock import patch, MagicMock

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

if __name__ == '__main__':
    unittest.main()
