function Invoke-EmployeeLogin {
    param (
        [string]$Username,
        [string]$Password
    )

    # Validate input
    if (-not $Username -or -not $Password) {
        throw "Username and Password are required."
    }

    # Load company configuration
    $config = Get-CompanyConfiguration

    # Authenticate user
    $isAuthenticated = Authenticate-User -Username $Username -Password $Password -Config $config

    if ($isAuthenticated) {
        # Perform login actions
        Start-UserSession -Username $Username
        Write-Host "Login successful for user: $Username"
    } else {
        Write-Host "Login failed for user: $Username"
        Log-Audit -Username $Username -Success $false
    }
}

# Export the function for use in other scripts
Export-ModuleMember -Function Invoke-EmployeeLogin