# 📦 PackageHound

**PackageHound** is a Python 3 tool designed to sniff out and verify the presence of development packages in your internal Artifactory instance. By cross-referencing a provided list of packages against configured repositories, it delivers a comprehensive report of what’s found, what’s missing, and where each package lives.

---

## 🔍 Purpose

The goal of PackageHound is to automate the verification of package availability across multiple artifact types in Artifactory. It is especially useful for auditing internal package usage, prepping for migration, or identifying missing dependencies before deployment.

---

## 🧾 Input

- A CSV file containing a list of development packages.
- Each row includes:
  - `package_name` (i.e. maven-authorized/org/springframework/boot/spring-boot-starter-parent/2.1.4.RELEASE/spring-boot-starter-parent-2.1.4.RELEASE.pom)
  - `package_type` (one of: Python, NPM, Maven, NuGet, Terraform, Docker)

---

## 🔄 What It Does

For each package in the input list, PackageHound:

1. **Identifies relevant repositories** based on the package type.
2. **Queries the Artifactory REST API**, authenticated via an API key.
3. **Searches for the package** across all applicable repositories.
4. **Retrieves the latest version available**, if the package is found.
5. **Records all repositories** where the package appears.

---

## 🧾 Output

A results CSV file including the following columns:

- `package_name`
- `package_type`
- `found` (True/False)
- `latest_version` (if found)
- `repositories_found_in` (comma-separated list)

---

## 🧠 Design Considerations

- **Repository Mapping**: Clearly defined, extensible logic for associating package types with their respective repository paths.
- **Modular Codebase**: Readable and maintainable functions with minimal coupling.
- **Robust Error Handling**: Graceful failure when packages aren't found, or if Artifactory queries return unexpected results.
- **Optimized Queries**: Efficient use of the Artifactory API to minimize redundant requests.

---

## ✅ Review Focus Areas

- **Logic completeness**: Are all edge cases and package types covered appropriately?
- **Artifactory API usage**: Are API calls properly authenticated, and do they fetch the correct metadata?
- **Modularity & readability**: Is the script easy to maintain and extend?
- **Error handling**: Are unexpected results, timeouts, or missing packages handled well?
