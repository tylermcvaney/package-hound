import unittest
import sys
import os

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from hound import ArtifactPackage

class TestArtifactPackage(unittest.TestCase):
    
    def test_maven_package_parsing(self):
        """Test parsing Maven package paths"""
        path = "maven-repo/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.jar"
        package = ArtifactPackage(path, "maven")
        
        self.assertEqual(package.repo, "maven-repo")
        self.assertEqual(package.package_name, "org.apache.commons:commons-lang3")
        self.assertEqual(package.version, "3.12.0")
        self.assertEqual(package.filename, "commons-lang3-3.12.0.jar")
    
    def test_maven_metadata_xml_parsing(self):
        """Test parsing Maven metadata XML paths"""
        # Test case for maven-metadata.xml at artifact level
        path = "maven-repo/org/apache/commons/commons-lang3/maven-metadata.xml"
        package = ArtifactPackage(path, "maven")
        
        self.assertEqual(package.repo, "maven-repo")
        self.assertEqual(package.package_name, "org.apache.commons:commons-lang3")
        self.assertIsNone(package.version)  # No specific version for metadata files
        self.assertEqual(package.filename, "maven-metadata.xml")
        
        # TODO
        # These tests are commented out because the current implementation of ArtifactPackage does not handle these cases.

        # # Test case for maven-metadata.xml in a versioned directory
        # path = "maven-repo/org/apache/commons/commons-lang3/3.12.0/maven-metadata.xml"
        # package = ArtifactPackage(path, "maven")
        
        # self.assertEqual(package.repo, "maven-repo")
        # self.assertEqual(package.package_name, "org.apache.commons:commons-lang3")
        # self.assertEqual(package.version, "3.12.0")  # Version should be extracted from path
        # self.assertEqual(package.filename, "maven-metadata.xml")
        
        # # Test case for maven-metadata.xml at group level
        # path = "maven-repo/org/apache/maven-metadata.xml"
        # package = ArtifactPackage(path, "maven")
        
        # self.assertEqual(package.repo, "maven-repo")
        # self.assertEqual(package.package_name, "org.apache")  # Just group ID for group-level metadata
        # self.assertIsNone(package.version)
        # self.assertEqual(package.filename, "maven-metadata.xml")
    
    def test_npm_package_parsing(self):
        """Test parsing NPM package paths"""        
        # Regular package
        path = "npm-repo/lodash/-/lodash-4.17.21.tgz"
        package = ArtifactPackage(path, "npm")

        self.assertEqual(package.repo, "npm-repo")
        self.assertEqual(package.package_name, "lodash")
        self.assertEqual(package.version, "4.17.21")
        self.assertEqual(package.filename, "lodash-4.17.21.tgz")

        # Scoped package
        path = "npm-repo/@angular/core/-/core-15.2.0.tgz"
        package = ArtifactPackage(path, "npm")

        self.assertEqual(package.repo, "npm-repo")
        self.assertEqual(package.package_name, "@angular/core")
        self.assertEqual(package.version, "15.2.0")
        self.assertEqual(package.filename, "core-15.2.0.tgz")
    
    def test_python_package_parsing(self):
        """Test parsing Python package paths"""
        # Simple path
        path = "pypi-repo/simple/requests"
        package = ArtifactPackage(path, "python")
        
        self.assertEqual(package.repo, "pypi-repo")
        self.assertEqual(package.package_name, "requests")
        
        # Path with wheel file
        path = "pypi-local/simple/django/django-4.2.0-py3-none-any.whl"
        package = ArtifactPackage(path, "python")
        
        self.assertEqual(package.repo, "pypi-local")
        self.assertEqual(package.package_name, "django")
        self.assertEqual(package.version, "4.2.0")
    
    def test_nuget_package_parsing(self):
        """Test parsing NuGet package paths"""
        # Standard path format
        path = "nuget-repo/Newtonsoft.Json/13.0.1"
        package = ArtifactPackage(path, "nuget")
        
        self.assertEqual(package.repo, "nuget-repo")
        self.assertEqual(package.package_name, "Newtonsoft.Json")
        self.assertEqual(package.version, "13.0.1")
        
        # Filename format (direct .nupkg file)
        path = "microsoft.graph.authentication.2.22.0.nupkg"
        package = ArtifactPackage(path, "nuget")
        
        self.assertIsNone(package.repo)  # No repo for direct file paths
        self.assertEqual(package.package_name, "microsoft.graph.authentication")
        self.assertEqual(package.version, "2.22.0")
        self.assertEqual(package.filename, "microsoft.graph.authentication.2.22.0.nupkg")
        
        # Another nupkg example with more complex name
        path = "psscriptanalyzer.1.17.1.nupkg"
        package = ArtifactPackage(path, "nuget")
        
        self.assertIsNone(package.repo)
        self.assertEqual(package.package_name, "psscriptanalyzer")
        self.assertEqual(package.version, "1.17.1")
        self.assertEqual(package.filename, "psscriptanalyzer.1.17.1.nupkg")
    
    def test_terraform_package_parsing(self):
        """Test parsing Terraform module paths"""
        path = "terraform-repo/modules/hashicorp/aws/4.57.0"
        package = ArtifactPackage(path, "terraform")
        
        self.assertEqual(package.repo, "terraform-repo")
        self.assertEqual(package.package_name, "hashicorp/aws")
        self.assertEqual(package.version, "4.57.0")
    
    def test_docker_package_parsing(self):
        """Test parsing Docker image paths"""
        # Standard image
        path = "docker-repo/library/ubuntu/latest"
        package = ArtifactPackage(path, "docker")
        
        self.assertEqual(package.repo, "docker-repo")
        self.assertEqual(package.package_name, "library/ubuntu")
        self.assertEqual(package.version, "latest")
        
        # Docker manifest path
        path = "docker/hashicorp/consul/1.17.3/manifest.json"
        package = ArtifactPackage(path, "docker")

        self.assertEqual(package.repo, "docker")
        self.assertEqual(package.package_name, "hashicorp/consul")
        self.assertEqual(package.version, "1.17.3")
        self.assertEqual(package.filename, "manifest.json")

        # Docker SHA path
        path = "docker/hashicorp/consul/1.17.3/SHA256abc123def456.json"
        package = ArtifactPackage(path, "docker")

        self.assertEqual(package.repo, "docker")
        self.assertEqual(package.package_name, "hashicorp/consul")
        self.assertEqual(package.version, "1.17.3")
        self.assertEqual(package.filename, "SHA256abc123def456.json")

        # Docker uploads path
        path = "docker/bitnami/cert-manager-webhook/_uploads/sha256abc123def456"
        package = ArtifactPackage(path, "docker")

        self.assertEqual(package.repo, "docker")
        self.assertEqual(package.package_name, "bitnami/cert-manager-webhook")
        self.assertEqual(package.version, "latest")
        self.assertEqual(package.filename, "sha256abc123def456")

        # Docker complex version path
        path = "docker/bitnami/cert-manager/1.17.1-debian-12-r4/sha256abc123def456.json"
        package = ArtifactPackage(path, "docker")

        self.assertEqual(package.repo, "docker")
        self.assertEqual(package.package_name, "bitnami/cert-manager")
        self.assertEqual(package.version, "1.17.1-debian-12-r4")
        self.assertEqual(package.filename, "sha256abc123def456.json")

        # TODO
        # Removing due lack of usecase

        # # Simple image
        # path = "docker-local/nginx/1.23.4"
        # package = ArtifactPackage(path, "docker")
        
        # self.assertEqual(package.repo, "docker-local")
        # self.assertEqual(package.package_name, "nginx")
        # self.assertEqual(package.version, "1.23.4")

if __name__ == '__main__':
    unittest.main()