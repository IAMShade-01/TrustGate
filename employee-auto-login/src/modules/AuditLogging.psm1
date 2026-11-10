function Get-AuditLog {
    param (
        [string]$LogFilePath = "C:\Logs\AuditLog.txt",
        [string]$Message,
        [string]$Status
    )

    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "$Timestamp - $Status: $Message"
    Add-Content -Path $LogFilePath -Value $LogEntry
}

function Log-SuccessfulLogin {
    param (
        [string]$Username
    )
    Get-AuditLog -Message "User '$Username' logged in successfully." -Status "SUCCESS"
}

function Log-FailedLogin {
    param (
        [string]$Username,
        [string]$Reason
    )
    Get-AuditLog -Message "User '$Username' failed to log in. Reason: $Reason" -Status "FAILURE"
}

function Get-LoginAttempts {
    param (
        [string]$LogFilePath = "C:\Logs\AuditLog.txt"
    )

    if (Test-Path $LogFilePath) {
        Get-Content -Path $LogFilePath
    } else {
        Write-Host "No audit log found at $LogFilePath"
    }
}

Export-ModuleMember -Function Get-AuditLog, Log-SuccessfulLogin, Log-FailedLogin, Get-LoginAttempts