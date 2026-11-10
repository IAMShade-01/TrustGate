# Employee Auto Login

## Overview
The Employee Auto Login project provides a solution for automating the login process for employees in various company environments. By leveraging Windows Task Scheduler, this project allows for seamless integration into existing systems, ensuring that employees can access necessary resources without manual login.

## Features
- **Automated Login**: Automatically logs in employees using scheduled tasks.
- **Company Configuration**: Adapts to different company environments through customizable settings.
- **Secure Credential Management**: Safely stores and retrieves employee credentials.
- **Audit Logging**: Maintains logs of login attempts for security and compliance.

## Getting Started

### Prerequisites
- Windows operating system
- PowerShell version 5.1 or higher
- Administrative privileges for scheduling tasks

### Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```
   cd employee-auto-login
   ```
3. Configure the company settings by editing the `config/company.example.json` file to match your company's requirements.

### Usage
1. To register the login task, run:
   ```
   .\src\Register-LoginTask.ps1
   ```
2. To invoke the employee login process, execute:
   ```
   .\src\Invoke-EmployeeLogin.ps1
   ```
3. To unregister the login task, use:
   ```
   .\src\Unregister-LoginTask.ps1
   ```

## Documentation
For detailed instructions on deployment, integration, and security best practices, please refer to the documentation in the `docs` directory.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.