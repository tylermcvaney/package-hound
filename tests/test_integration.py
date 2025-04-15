import unittest
import tempfile
import os
import sys
import csv
from unittest.mock import patch

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from hound import ArtifactoryPackageChecker

class TestIntegration(unittest.TestCase):
    
    @patch('requests.Session')
    def test_end_to_end_workflow(self, mock_session):
        """Test the end-to-end workflow with a small CSV file"""
        # Create a temporary input CSV file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as input_file:
            writer = csv.writer(input_file)
            writer.writerow(['Package Path', 'Package Type'])
            writer.writerow(['maven-repo/org/example/test/1.0.0/test-1.0.0.jar', 'maven'])
            writer.writerow(['npm-repo/lodash/-/lodash-4.17.21.tgz', 'npm'])

            input_filename = input_file.name
        
        # Create a temporary output file
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        output_filename = output_file.name
        output_file.close()
        
        # Mock the responses
        session_instance = mock_session.return_value
        
        # Mock ping
        ping_response = unittest.mock.MagicMock()
        ping_response.status_code = 200
        ping_response.text = "OK"
        
        # Mock repositories response
        repos_response = unittest.mock.MagicMock()
        repos_response.status_code = 200
        repos_response.json.return_value = [
            {"key": "maven-repo", "packageType": "maven"},
            {"key": "npm-repo", "packageType": "npm"},
            {"key": "docker", "packageType": "docker"},
            {"key": "pypi-local", "packageType": "python"}        ]
        
        # Mock package check responses
        found_response = unittest.mock.MagicMock()
        found_response.status_code = 200
        
        not_found_response = unittest.mock.MagicMock()
        not_found_response.status_code = 404
        
        # Configure mock to return different responses
        def get_side_effect(url, **kwargs):
            if '/api/system/ping' in url:
                return ping_response
            elif '/api/repositories' in url:
                return repos_response
            else:
                return not_found_response
        
        def head_side_effect(url, **kwargs):
            if 'maven-repo/org/example/test' in url:
                return found_response
            else:
                return not_found_response
        
        session_instance.get.side_effect = get_side_effect
        session_instance.head.side_effect = head_side_effect
        
        # Run the test
        checker = ArtifactoryPackageChecker(
            base_url="https://artifactory.example.local/artifactory",
            api_key="dummy-api-key"
        )
        
        result = checker.process_package_list(input_filename, output_filename)
        
        # Verify the result
        self.assertTrue(result)
        
        # Check the output file was created and has the expected content
        with open(output_filename, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
            # Should have a header and two data rows
            self.assertEqual(len(rows), 3)
            
            # Check header
            self.assertEqual(rows[0], ['Package Path', 'Package Name', 'Type', 'Version', 'Found', 'Repository', 'Error'])
            
            # Check maven package was found
            self.assertEqual(rows[1][4], 'True')  # Found status
            
            # Check npm package was not found
            self.assertEqual(rows[2][4], 'False')  # Found status
        
        # Clean up
        os.unlink(input_filename)
        os.unlink(output_filename)

if __name__ == '__main__':
    unittest.main()