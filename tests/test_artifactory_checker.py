import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from hound import ArtifactoryPackageChecker, ArtifactPackage

class TestArtifactoryPackageChecker(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.base_url = "https://artifactory.example.local/artifactory"
        self.api_key = "dummy-api-key"
        
        # Create a patcher for requests.Session
        self.session_patcher = patch('requests.Session')
        self.mock_session = self.session_patcher.start()
        
        # Setup basic mock responses that all tests might need
        self.session_instance = self.mock_session.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        self.session_instance.get.return_value = mock_response
        self.session_instance.head.return_value = MagicMock(status_code=200)
        
        # Now create the checker with mock already in place
        self.checker = ArtifactoryPackageChecker(self.base_url, self.api_key)
    
    def tearDown(self):
        """Clean up after tests"""
        self.session_patcher.stop()
    
    def test_create_session(self):
        """Test session creation with proper headers"""
        # Create a new checker - this will use the mocked session
        checker = ArtifactoryPackageChecker(self.base_url, self.api_key)
        
        # Verify the headers were set correctly using the session instance we already set up
        self.session_instance.headers.update.assert_called_with({
            'X-JFrog-Art-Api': self.api_key,
            'Content-Type': 'application/json'
        })
    
    def test_check_artifactory_connection_success(self):
        """Test successful Artifactory connection"""
        # Setup this test's specific mock response
        response = MagicMock()
        response.status_code = 200
        response.text = "OK"
        self.session_instance.get.return_value = response
        
        result = self.checker.check_artifactory_connection()
        
        self.assertTrue(result)
        self.session_instance.get.assert_called_with(f"{self.base_url}/api/system/ping")
    
    def test_check_artifactory_connection_failure(self):
        """Test failed Artifactory connection"""
        response = MagicMock()
        response.status_code = 401
        response.text = "Unauthorized"
        self.session_instance.get.return_value = response
        
        result = self.checker.check_artifactory_connection()
        
        self.assertFalse(result)
    
    def test_get_repositories(self):
        """Test repository listing"""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = [
            {"key": "pypi-local", "packageType": "pypi"},
            {"key": "npm-local", "packageType": "npm"},
            {"key": "maven-local", "packageType": "maven"}
        ]
        self.session_instance.get.return_value = response
        
        result = self.checker.get_repositories()
        
        self.assertEqual(result, {
            "pypi-local": "pypi",
            "npm-local": "npm",
            "maven-local": "maven"
        })
    
    def test_check_package_exists_found(self):
        """Test package exists check when found"""
        response = MagicMock()
        response.status_code = 200
        self.session_instance.head.return_value = response
        
        # Create a package to check
        package = ArtifactPackage("maven-repo/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.jar", "maven")
        
        result = self.checker.check_package_exists(package)
        
        self.assertTrue(result['found'])
        self.assertEqual(result['repository'], "maven-repo")
    
    def test_check_package_exists_not_found(self):
        """Test package exists check when not found"""
        response = MagicMock()
        response.status_code = 404
        self.session_instance.head.return_value = response
        
        # Create a package to check
        package = ArtifactPackage("maven-repo/org/apache/commons/not-exists/1.0.0/not-exists-1.0.0.jar", "maven")
        
        result = self.checker.check_package_exists(package)
        
        self.assertFalse(result['found'])
    
    # This test has multiple patches - the mock_session here comes from the class patch
    @patch('builtins.open', new_callable=mock_open)
    @patch('csv.reader')
    @patch('csv.writer')
    @patch.object(ArtifactoryPackageChecker, 'check_artifactory_connection', return_value=True)
    @patch.object(ArtifactoryPackageChecker, 'get_repositories', return_value={"maven-repo": "maven"})
    @patch.object(ArtifactoryPackageChecker, 'check_package_exists')
    def test_process_package_list(self, mock_check_exists, mock_get_repos, mock_connection, 
                                  mock_writer, mock_reader, mock_file):
        """Test processing a package list file"""
        # Setup file open mocks
        mock_file.return_value.__enter__.return_value = MagicMock()
        
        # Setup CSV reader mock - this is crucial!
        # First, create a proper iterator that next() can be called on
        reader_iter = iter([
            ['package_path', 'package_type'],  # Header row
            ['maven-repo/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.jar', 'maven']  # Data row
        ])
        mock_reader.return_value = reader_iter
        
        # Setup check_package_exists mock
        mock_check_exists.return_value = {
            'path': 'maven-repo/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.jar',
            'package_name': 'org.apache.commons:commons-lang3',
            'package_type': 'maven',
            'version': '3.12.0',
            'found': True,
            'repository': 'maven-repo',
            'error': None
        }
        
        # Run the method
        result = self.checker.process_package_list('input.csv', 'output.csv')
        
        # Assert successful execution
        self.assertTrue(result)
        mock_connection.assert_called_once()
        mock_get_repos.assert_called_once()
        mock_check_exists.assert_called_once()

if __name__ == '__main__':
    unittest.main()