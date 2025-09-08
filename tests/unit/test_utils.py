import unittest
from unittest.mock import patch, MagicMock

from arpx.utils import check_dependencies

class TestUtils(unittest.TestCase):

    @patch('shutil.which')
    def test_check_dependencies_all_found(self, mock_which):
        """Test that check_dependencies returns True when all tools are found."""
        mock_which.return_value = '/usr/bin/some_tool'
        self.assertTrue(check_dependencies(['ip', 'arping']))
        self.assertEqual(mock_which.call_count, 2)

    @patch('shutil.which')
    @patch('arpx.utils.logger')
    def test_check_dependencies_some_missing(self, mock_logger, mock_which):
        """Test that check_dependencies returns False and logs errors for missing tools."""
        def which_side_effect(tool):
            if tool == 'ip':
                return '/usr/bin/ip'
            return None

        mock_which.side_effect = which_side_effect
        self.assertFalse(check_dependencies(['ip', 'arping', 'mkcert']))
        self.assertEqual(mock_which.call_count, 3)

        # Verify that error messages were logged for the missing tools
        self.assertTrue(any("Missing required system dependencies" in call.args[0] for call in mock_logger.error.call_args_list))
        self.assertTrue(any("'arping' not found" in call.args[0] for call in mock_logger.error.call_args_list))
        self.assertTrue(any("'mkcert' not found" in call.args[0] for call in mock_logger.error.call_args_list))

    @patch('shutil.which')
    def test_check_dependencies_empty_list(self, mock_which):
        """Test that check_dependencies returns True for an empty list of tools."""
        self.assertTrue(check_dependencies([]))
        mock_which.assert_not_called()

if __name__ == '__main__':
    unittest.main()
