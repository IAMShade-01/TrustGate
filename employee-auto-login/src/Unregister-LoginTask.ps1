# This script unregisters the scheduled task for employee login automation.

param (
    [string]$TaskName = "EmployeeAutoLoginTask"
)

try {
    # Check if the scheduled task exists
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    if ($task) {
        # Unregister the scheduled task
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Scheduled task '$TaskName' has been unregistered successfully."
    }
} catch {
    Write-Host "Error: Scheduled task '$TaskName' does not exist or could not be unregistered."
}