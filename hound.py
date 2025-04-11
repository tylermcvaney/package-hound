#!/usr/bin/env python3
import csv
import argparse
import requests
import json
import sys
import os
import re
from urllib.parse import quote
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('artifactory_checker')

# Default repository mappings (can be overridden)
DEFAULT_REPO_MAPPINGS = {
    'python': ['pypi-local', 'pypi-remote', 'pypi-virtual'],
    'npm': ['npm-local', 'npm-remote', 'npm-virtual'],
    'maven': ['maven-local', 'maven-remote', 'maven-virtual', 'libs-release', 'maven-authorized'],
    'nuget': ['nuget-local', 'nuget-remote', 'nuget-virtual'],
    'terraform': ['terraform-local', 'terraform-remote', 'terraform-virtual'],
    'docker': ['docker-local', 'docker-remote', 'docker-virtual']
}

class ArtifactPackage:
    """Class to represent a package from Artifactory path"""
    
    def __init__(self, path, package_type):
        self.path = path.strip()
        self.package_type = package_type.strip().lower()
        self.repo = self._extract_repo()
        self.package_name = self._extract_package_name()
        self.version = self._extract_version()
        self.filename = os.path.basename(self.path)
    
    def _extract_repo(self):
        """Extract repository name from path"""
        if '/' in self.path:
            return self.path.split('/')[0]
        return None
    
    def _extract_package_name(self):
        """Extract package name from path based on type"""
        if self.package_type == 'maven':
            # Extract group and artifact ID for Maven
            parts = self.path.split('/')
            if len(parts) >= 4:  # repo/group/artifact/version/...
                # Group ID is the path between repo and artifact
                group_path = '/'.join(parts[1:-2])
                artifact_id = parts[-3]
                group_id = group_path.replace('/', '.')
                return f"{group_id}:{artifact_id}"
            return None
        
        elif self.package_type == 'npm':
            # NPM package paths typically have @scope/package or just package
            parts = self.path.split('/')
            if len(parts) >= 3:
                if parts[1].startswith('@'):  # Scoped package
                    return f"{parts[1]}/{parts[2]}"
                else:
                    return parts[1]
            return None
        
        elif self.package_type == 'python':
            # Python packages usually have the format: repo/simple/package/package-version.whl
            parts = self.path.split('/')
            if len(parts) >= 3:
                # Try to get the package name from the path
                package_name = parts[2] if len(parts) > 2 else None
                
                # If we have a filename, extract name from it
                if self.filename:
                    # Extract package name from file (package-version.whl)
                    match = re.match(r'(.+?)-\d+', self.filename)
                    if match:
                        return match.group(1)
                
                return package_name
            return None
        
        elif self.package_type == 'nuget':
            # NuGet packages: repo/package-id/version/package-id.version.nupkg
            parts = self.path.split('/')
            if len(parts) >= 3:
                return parts[1]
            return None
        
        elif self.package_type == 'terraform':
            # Terraform modules: repo/modules/namespace/name/version
            parts = self.path.split('/')
            if len(parts) >= 5 and parts[1] == 'modules':
                return f"{parts[2]}/{parts[3]}"
            return None
        
        elif self.package_type == 'docker':
            # Docker images: repo/namespace/image/tag
            parts = self.path.split('/')
            if len(parts) >= 3:
                return f"{parts[1]}/{parts[2]}" if len(parts) > 3 else parts[1]
            return None
        
        # Default fallback: use the second path component as package name
        parts = self.path.split('/')
        if len(parts) >= 2:
            return parts[1]
        return None
    
    def _extract_version(self):
        """Extract version from path based on type"""
        if self.package_type == 'maven':
            # Maven version is typically after the artifact ID
            parts = self.path.split('/')
            if len(parts) >= 5:  # repo/group/artifact/version/...
                return parts[-2]  # Version is typically second to last segment
            
            # Try to extract from filename
            if self.filename:
                # Look for artifact-version.extension pattern
                if '-' in self.filename and '.' in self.filename:
                    artifact_id = self.package_name.split(':')[-1] if self.package_name else None
                    if artifact_id:
                        # Extract version between artifact ID and extension
                        pattern = f"{artifact_id}-(.+)\\."
                        match = re.search(pattern, self.filename)
                        if match:
                            return match.group(1)
            return None
        
        elif self.package_type == 'npm':
            # NPM version is typically after the package name
            parts = self.path.split('/')
            if len(parts) >= 4:  # For scoped: repo/@scope/package/version/...
                return parts[3] if parts[1].startswith('@') else parts[2]
            return None
        
        elif self.package_type == 'python':
            # Extract version from filename (package-version.whl)
            if self.filename:
                match = re.search(r'-(\d+[.\w]+)', self.filename)
                if match:
                    return match.group(1)
            return None
        
        elif self.package_type == 'nuget':
            # NuGet version is typically the third path component
            parts = self.path.split('/')
            if len(parts) >= 4:  # repo/package/version/file
                return parts[2]
            return None
        
        elif self.package_type == 'terraform':
            # Terraform version is typically the fifth path component
            parts = self.path.split('/')
            if len(parts) >= 5:  # repo/modules/namespace/name/version
                return parts[4]
            return None
        
        elif self.package_type == 'docker':
            # Docker tag is typically the fourth path component or 'latest'
            parts = self.path.split('/')
            if len(parts) >= 4:  # repo/namespace/image/tag
                return parts[3]
            return 'latest'  # Default tag
        
        # Default fallback: try to find version-like string in path
        version_match = re.search(r'(\d+\.\d+(\.\d+)?([.-]\w+)?)', self.path)
        if version_match:
            return version_match.group(1)
        return None
    
    def __str__(self):
        return f"{self.package_name} ({self.version}) in {self.repo}"

class ArtifactoryPackageChecker:
    def __init__(self, base_url, api_key, repo_mappings=None, max_workers=10):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.repo_mappings = repo_mappings or DEFAULT_REPO_MAPPINGS
        self.max_workers = max_workers
        self.session = self._create_session()
        
    def _create_session(self):
        """Create a requests session with authentication headers"""
        session = requests.Session()
        session.headers.update({
            'X-JFrog-Art-Api': self.api_key,
            'Content-Type': 'application/json'
        })
        return session
    
    def check_artifactory_connection(self):
        """Test the connection to Artifactory"""
        try:
            url = f"{self.base_url}/api/system/ping"
            response = self.session.get(url)
            if response.status_code == 200 and response.text == "OK":
                logger.info("Connection to Artifactory successful")
                return True
            else:
                logger.error(f"Failed to connect to Artifactory. Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error connecting to Artifactory: {str(e)}")
            return False
    
    def get_repositories(self):
        """Get a list of all repositories in Artifactory"""
        url = f"{self.base_url}/api/repositories"
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                repos = response.json()
                repo_dict = {repo['key']: repo['packageType'] for repo in repos}
                logger.info(f"Found {len(repos)} repositories")
                return repo_dict
            else:
                logger.error(f"Failed to get repositories. Status: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Error getting repositories: {str(e)}")
            return {}
    
    def update_repository_mappings(self, available_repos):
        """Update repository mappings based on available repositories"""
        # Get all available repositories by package type
        repos_by_type = {}
        for repo_key, pkg_type in available_repos.items():
            repos_by_type.setdefault(pkg_type, []).append(repo_key)
        
        # Update mappings to only include repositories that actually exist
        for pkg_type, repos in self.repo_mappings.items():
            matching_type = None
            
            # Map package types to Artifactory package types
            if pkg_type == 'python':
                matching_type = 'pypi'
            elif pkg_type == 'npm':
                matching_type = 'npm'
            elif pkg_type == 'maven':
                matching_type = 'maven'
            elif pkg_type == 'nuget':
                matching_type = 'nuget'
            elif pkg_type == 'terraform':
                matching_type = 'terraform'
            elif pkg_type == 'docker':
                matching_type = 'docker'
            
            if matching_type and matching_type in repos_by_type:
                # Filter the current mapping to only include repos that exist
                existing_repos = [r for r in repos if r in available_repos]
                
                # If none of our default repos exist, use all repos of this type from Artifactory
                if not existing_repos:
                    self.repo_mappings[pkg_type] = repos_by_type[matching_type]
                else:
                    self.repo_mappings[pkg_type] = existing_repos
                    
        logger.info("Updated repository mappings based on available repositories")
        for pkg_type, repos in self.repo_mappings.items():
            logger.info(f"{pkg_type}: {', '.join(repos)}")
    
    def check_package_exists(self, artifact_package):
        """Check if a specific package version exists in Artifactory"""
        if not artifact_package.package_name or not artifact_package.version:
            return {
                'path': artifact_package.path,
                'package_name': artifact_package.package_name,
                'package_type': artifact_package.package_type,
                'version': artifact_package.version,
                'found': False,
                'repository': None,
                'error': 'Unable to extract package name or version from path'
            }
            
        # Build direct URL to check if package exists
        check_url = None
        
        # If the original repo is available, check there first
        original_repo = artifact_package.repo
        
        # Prepare the list of repositories to check
        repos_to_check = []
        if original_repo:
            repos_to_check.append(original_repo)
        
        # Add other repos of the same type to check
        pkg_type_repos = self.repo_mappings.get(artifact_package.package_type, [])
        for repo in pkg_type_repos:
            if repo != original_repo:
                repos_to_check.append(repo)
        
        for repo in repos_to_check:
            # First, try direct path check
            if artifact_package.path.startswith(f"{repo}/"):
                # Use the exact path provided
                check_url = f"{self.base_url}/{artifact_package.path}"
            else:
                # Build path based on package type
                if artifact_package.package_type == 'maven':
                    # Maven packages
                    if ':' in artifact_package.package_name:
                        group_id, artifact_id = artifact_package.package_name.split(':', 1)
                        group_path = group_id.replace('.', '/')
                        check_url = f"{self.base_url}/{repo}/{group_path}/{artifact_id}/{artifact_package.version}/{artifact_id}-{artifact_package.version}.jar"
                        
                        # Also try POM if JAR doesn't exist
                        pom_url = f"{self.base_url}/{repo}/{group_path}/{artifact_id}/{artifact_package.version}/{artifact_id}-{artifact_package.version}.pom"
                
                elif artifact_package.package_type == 'npm':
                    # NPM packages
                    if '/' in artifact_package.package_name:  # Scoped package
                        check_url = f"{self.base_url}/{repo}/{quote(artifact_package.package_name)}/{artifact_package.version}"
                    else:
                        check_url = f"{self.base_url}/{repo}/{artifact_package.package_name}/{artifact_package.version}"
                
                elif artifact_package.package_type == 'python':
                    # Python packages
                    check_url = f"{self.base_url}/{repo}/simple/{artifact_package.package_name}"
                    # For specific version check would need metadata parsing
                
                elif artifact_package.package_type == 'nuget':
                    # NuGet packages
                    check_url = f"{self.base_url}/{repo}/{artifact_package.package_name}/{artifact_package.version}"
                
                elif artifact_package.package_type == 'terraform':
                    # Terraform modules
                    if '/' in artifact_package.package_name:
                        namespace, name = artifact_package.package_name.split('/', 1)
                        check_url = f"{self.base_url}/{repo}/modules/{namespace}/{name}/{artifact_package.version}"
                    else:
                        check_url = f"{self.base_url}/{repo}/modules/{artifact_package.package_name}/{artifact_package.version}"
                
                elif artifact_package.package_type == 'docker':
                    # Docker images
                    if '/' in artifact_package.package_name:
                        check_url = f"{self.base_url}/{repo}/{artifact_package.package_name}/manifests/{artifact_package.version}"
                    else:
                        check_url = f"{self.base_url}/{repo}/{artifact_package.package_name}/manifests/{artifact_package.version}"
            
            try:
                logger.debug(f"Checking URL: {check_url}")
                response = self.session.head(check_url, timeout=10)
                
                if response.status_code == 200:
                    return {
                        'path': artifact_package.path,
                        'package_name': artifact_package.package_name,
                        'package_type': artifact_package.package_type,
                        'version': artifact_package.version,
                        'found': True,
                        'repository': repo,
                        'error': None
                    }
            except Exception as e:
                logger.debug(f"Error checking {check_url}: {str(e)}")
                continue
        
        # If we get here, package wasn't found
        return {
            'path': artifact_package.path,
            'package_name': artifact_package.package_name,
            'package_type': artifact_package.package_type,
            'version': artifact_package.version,
            'found': False,
            'repository': None,
            'error': f"Package not found in repositories: {', '.join(repos_to_check)}"
        }
    
    def get_package_info(self, package_type, package_name, repository=None):
        """Get detailed information about a package including latest version"""
        # Define the API endpoint based on package type
        api_endpoint = None
        
        # Determine which repositories to check
        repos_to_check = []
        if repository:
            repos_to_check.append(repository)
        else:
            repos_to_check = self.repo_mappings.get(package_type, [])
        
        for repo in repos_to_check:
            if package_type == 'maven':
                # For Maven, we need to convert group:artifact format
                if ':' in package_name:
                    group_id, artifact_id = package_name.split(':', 1)
                    group_path = group_id.replace('.', '/')
                    api_endpoint = f"{self.base_url}/api/storage/{repo}/{group_path}/{artifact_id}"
                else:
                    continue
            
            elif package_type == 'npm':
                if '/' in package_name:  # Scoped package
                    api_endpoint = f"{self.base_url}/api/npm/{repo}/{quote(package_name)}"
                else:
                    api_endpoint = f"{self.base_url}/api/npm/{repo}/{package_name}"
            
            elif package_type == 'python':
                api_endpoint = f"{self.base_url}/api/pypi/{repo}/simple/{package_name}"
            
            elif package_type == 'nuget':
                api_endpoint = f"{self.base_url}/api/nuget/{repo}/packages/{package_name}"
            
            elif package_type == 'terraform':
                if '/' in package_name:
                    namespace, name = package_name.split('/', 1)
                    api_endpoint = f"{self.base_url}/api/terraform/{repo}/modules/{namespace}/{name}"
                else:
                    api_endpoint = f"{self.base_url}/api/terraform/{repo}/modules/{package_name}"
            
            elif package_type == 'docker':
                if '/' in package_name:
                    api_endpoint = f"{self.base_url}/api/docker/{repo}/{package_name}/tags"
                else:
                    api_endpoint = f"{self.base_url}/api/docker/{repo}/{package_name}/tags"
            
            if api_endpoint:
                try:
                    response = self.session.get(api_endpoint)
                    if response.status_code == 200:
                        return {
                            'repository': repo,
                            'data': response.json(),
                            'error': None
                        }
                except Exception as e:
                    logger.debug(f"Error getting package info from {api_endpoint}: {str(e)}")
        
        return {
            'repository': None,
            'data': None,
            'error': f"Failed to get package info for {package_name} ({package_type})"
        }
    
    def process_package_list(self, input_file, output_file):
        """Process a list of packages from a CSV file and check if they exist in Artifactory"""
        # Check connection first
        if not self.check_artifactory_connection():
            logger.error("Failed to connect to Artifactory. Exiting.")
            return False
        
        # Get repositories and update mappings
        available_repos = self.get_repositories()
        if not available_repos:
            logger.error("Failed to get repository list from Artifactory. Exiting.")
            return False
        
        self.update_repository_mappings(available_repos)
        
        # Read input file
        packages = []
        try:
            with open(input_file, 'r', newline='') as f:
                reader = csv.reader(f)
                header = next(reader, None)  # Skip header row
                
                # Validate header
                if not header or len(header) < 2:
                    logger.error("Invalid CSV format. Expected at least two columns: package_path and package_type")
                    return False
                
                # Read packages
                for row in reader:
                    if len(row) >= 2:
                        package_path = row[0].strip()
                        package_type = row[1].strip().lower()
                        
                        if package_type not in self.repo_mappings:
                            logger.warning(f"Unsupported package type: {package_type} for {package_path}")
                            continue
                        
                        packages.append(ArtifactPackage(package_path, package_type))
        
        except Exception as e:
            logger.error(f"Error reading input file: {str(e)}")
            return False
        
        logger.info(f"Loaded {len(packages)} packages to check")
        
        # Check packages in parallel
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for package in packages:
                future = executor.submit(self.check_package_exists, package)
                futures[future] = package
            
            for future in as_completed(futures):
                package = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    status = "FOUND" if result['found'] else "NOT FOUND"
                    logger.info(f"{status}: {package.package_name} ({package.version})")
                except Exception as e:
                    logger.error(f"Error checking {package.package_name}: {str(e)}")
                    results.append({
                        'path': package.path,
                        'package_name': package.package_name,
                        'package_type': package.package_type,
                        'version': package.version,
                        'found': False,
                        'repository': None,
                        'error': str(e)
                    })
        
        # Write results to output file
        try:
            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(['Package Path', 'Package Name', 'Type', 'Version', 'Found', 'Repository', 'Error'])
                
                # Write results
                for r in results:
                    writer.writerow([
                        r['path'],
                        r['package_name'],
                        r['package_type'],
                        r['version'],
                        r['found'],
                        r['repository'] or '',
                        r['error'] or ''
                    ])
            
            logger.info(f"Results written to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing output file: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Check packages in Artifactory')
    parser.add_argument('--input', required=True, help='Input CSV file with package names and types')
    parser.add_argument('--output', required=True, help='Output CSV file for results')
    parser.add_argument('--base-url', required=True, help='Artifactory base URL')
    parser.add_argument('--api-key', required=True, help='Artifactory API key')
    parser.add_argument('--workers', type=int, default=10, help='Number of concurrent workers')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Create and run the checker
    checker = ArtifactoryPackageChecker(
        base_url=args.base_url,
        api_key=args.api_key,
        max_workers=args.workers
    )
    
    success = checker.process_package_list(args.input, args.output)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()