function Get-Credential {
    param (
        [string]$Username,
        [string]$Password
    )
    $securePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    $credential = New-Object System.Management.Automation.PSCredential($Username, $securePassword)
    return $credential
}

function Save-Credential {
    param (
        [string]$FilePath,
        [string]$Username,
        [string]$Password
    )
    $credential = Get-Credential -Username $Username -Password $Password
    $credential | Export-Clixml -Path $FilePath
}

function Get-SavedCredential {
    param (
        [string]$FilePath
    )
    if (Test-Path $FilePath) {
        return Import-Clixml -Path $FilePath
    } else {
        throw "Credential file not found."
    }
}

function Remove-Credential {
    param (
        [string]$FilePath
    )
    if (Test-Path $FilePath) {
        Remove-Item -Path $FilePath -Force
    } else {
        throw "Credential file not found."
    }
}

Export-ModuleMember -Function Get-Credential, Save-Credential, Get-SavedCredential, Remove-Credential