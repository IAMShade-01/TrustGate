-- SQLCMD mode: supply TenantId for an authorized development tenant.
SET XACT_ABORT ON;
DECLARE @tenant uniqueidentifier = CONVERT(uniqueidentifier, N'$(TenantId)');
DECLARE @device uniqueidentifier = '6bff350d-5019-4981-94a9-0dad04da5dbc';
DECLARE @package uniqueidentifier = '49c209d1-cd87-4d58-a04c-17c8fc15dbbb';

BEGIN TRANSACTION;
IF NOT EXISTS (SELECT 1 FROM dbo.Devices WHERE TenantId = @tenant AND Id = @device)
    INSERT INTO dbo.Devices (TenantId, Id, Name) VALUES (@tenant, @device, N'Example Lab Workstation');
IF NOT EXISTS (SELECT 1 FROM dbo.Software WHERE TenantId = @tenant AND Id = @package)
    INSERT INTO dbo.Software (TenantId, Id, Name, Version, Method)
    VALUES (@tenant, @package, N'Example Office App', N'1.0', N'winget (sample metadata only)');
COMMIT;
