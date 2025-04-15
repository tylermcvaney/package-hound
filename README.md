# 🐕 Package Hound
A command-line tool that helps you verify if packages exist in your Artifactory instance.

## 📋 Overview

The Artifactory Package Checker (`hound.py`) reads a CSV file containing package information and queries your Artifactory instance to check if those packages exist, producing a CSV report with the results.

<img src="https://github.com/user-attachments/assets/ea515ff8-7152-4f90-baa3-128589e4d7b1" alt="Package Hound Logo" width="256" height="256">

## 🔧 Prerequisites

- Python 3.6 or higher
- The following Python packages:
  - requests
  - csv

  - argparse
  - concurrent.futures (included in Python 3.6+)

## 🚀 Installation

1. Clone or download the script to your local machine
2. Make the script executable:
   ```bash
   chmod +x hound.py
   ```

## Basic Usage

```bash
./hound.py --input packages.csv --output results.csv --base-url https://your-artifactory-instance.com/artifactory --api-key YOUR_ARTIFACTORY_API_KEY
```

## Command Line Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `--input` | Path to input CSV file | Yes |
| `--output` | Path to output CSV file | Yes |
| `--base-url` | Artifactory base URL | Yes |
| `--api-key` | Artifactory API key | Yes |
| `--workers` | Number of concurrent workers (default: 10) | No |
| `--verbose` | Enable verbose logging | No |
| `--cert-path` | Path to custom SSL certificate (PEM format) | No |
| `--no-ssl-verify` | Disable SSL verification (not recommended) | No |

## 📄 Input CSV Format

The input CSV should contain at least two columns:
1. Package path
2. Package type

Example:
```csv
Package Path,Package Type
maven-central/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.jar,maven
npm-registry/@angular/core/15.2.0,npm
pypi-repo/simple/requests,python
nuget-repo/Newtonsoft.Json/13.0.1,nuget
terraform-modules/hashicorp/aws/4.0.0,terraform
docker-registry/library/ubuntu/latest,docker
```

## 🔒 SSL Certificate Options

Package Hound now supports the following options for handling SSL certificates when connecting to Artifactory:

### Option 1: Provide a Custom Certificate (Recommended)

If your Artifactory instance uses a self-signed certificate or an internal CA, you can provide the certificate file:

```bash
./hound.py --cert-path /path/to/certificate.pem --base-url https://artifactory.example.com ...
```
The certificate file should be in PEM format. This is the most secure approach.

### Option 2: Disable SSL Verification (Not recommended for production)

For testing purposes only, you can disable SSL certificate verification:
```bash
./hound.py --no-ssl-verify --base-url https://artifactory.example.com ...
```
⚠️ Warning: This option disables SSL verification entirely and is not recommended for production use.

## 📊 Output CSV Format

The output CSV contains the following columns:
1. Package Path - The original path from the input
2. Package Name - The extracted package name
3. Type - The package type
4. Version - The extracted version
5. Found - Whether the package was found (TRUE/FALSE)
6. Repository - The repository where the package was found
7. Error - Any error message if the package wasn't found

## 🔍 Supported Package Types

| Type | Description | Default Repositories |
|------|-------------|---------------------|
| `python` | Python packages from PyPI | pypi-local, pypi-remote, pypi-virtual |
| `npm` | JavaScript/Node.js packages | npm-local, npm-remote, npm-virtual |
| `maven` | Java/JVM packages | maven-local, maven-remote, maven-virtual, libs-release, maven-authorized |
| `nuget` | .NET packages | nuget-local, nuget-remote, nuget-virtual |
| `terraform` | Terraform modules | terraform-local, terraform-remote, terraform-virtual |
| `docker` | Docker images | docker-local, docker-remote, docker-virtual |

## 💡 Examples

#### Basic Usage

```bash
./hound.py --input packages.csv --output results.csv --base-url https://artifactory.example.com/artifactory --api-key AKC123456789ABCDEF
```

#### With Increased Parallelism

```bash
./hound.py --input packages.csv --output results.csv --base-url https://artifactory.example.com/artifactory --api-key AKC123456789ABCDEF --workers 20
```

#### With Verbose Logging

```bash
./hound.py --input packages.csv --output results.csv --base-url https://artifactory.example.com/artifactory --api-key AKC123456789ABCDEF --verbose
```

#### With Self-Signed Certificate (Recommended for SSL)
```bash
./hound.py --input packages.csv --output results.csv --base-url https://artifactory.example.com/artifactory --api-key AKC123456789ABCDEF --cert-path /path/to/certificate.pem
```

#### Disabling SSL Verification (Not For Production Use)
```bash
./hound.py --input packages.csv --output results.csv --base-url https://artifactory.example.com/artifactory --api-key AKC123456789ABCDEF --no-ssl-verify
```

## ⚙️ Customizing Repository Mappings

By default, the script will look for repositories with specific names like `pypi-authorized` for Python packages. If your Artifactory instance uses different repository names, the script will attempt to automatically detect appropriate repositories by their type.

If you need to customize this behavior further, you can modify the `DEFAULT_REPO_MAPPINGS` dictionary at the top of the script.

## 🔧 Troubleshooting

1. **Connection Issues**: Ensure your Artifactory URL is correct and your API key has appropriate permissions
2. **Invalid CSV Format**: Make sure your input CSV has at least two columns
3. **Performance Issues**: For large package lists, adjust the `--workers` parameter to find the optimal value for your environment
4. **Package Type Mismatches**: Ensure your package types in the CSV match the supported types (python, npm, maven, nuget, terraform, docker)

## 📝 Logging

The script outputs logs to the console. Use the `--verbose` flag to see more detailed logs, which can be helpful for troubleshooting.

### 🧪 Running Tests

The package includes a comprehensive test suite:
```bash
# Run all tests
python3 -m unittest tests/*.py

# Run a specific test file
python3 -m unittest tests/test_artifactory_checker.py
```