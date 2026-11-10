# This script registers a scheduled task in Windows Task Scheduler to automate the login process for employees.

param (
    [string]$TaskName = "EmployeeAutoLogin",
    [string]$ScriptPath = "C:\Path\To\Your\Invoke-EmployeeLogin.ps1",
    [string]$UserName,
    [string]$Password
)

# Create the action for the scheduled task
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File `"$ScriptPath`""

# Create the trigger for the scheduled task
$Trigger = New-ScheduledTaskTrigger -AtLogOn

# Create the principal for the scheduled task
$Principal = New-ScheduledTaskPrincipal -UserId $UserName -LogonType Password -RunLevel Highest

# Register the scheduled task
Register-ScheduledTask -Action $Action -Trigger $Trigger -Principal $Principal -TaskName $TaskName -Description "Automated login for employees" -User $UserName -Password $Password

Write-Host "Scheduled task '$TaskName' has been registered successfully."