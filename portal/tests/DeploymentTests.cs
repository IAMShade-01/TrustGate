using System.Security.Claims;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

public sealed class DeploymentTests
{
    [Fact]
    public async Task RecordsTenantRequestAndAuditButRejectsForeignTargets()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:;Foreign Keys=True");
        await connection.OpenAsync();
        await using var db = new PortalDb(new DbContextOptionsBuilder<PortalDb>().UseSqlite(connection).Options);
        await db.Database.EnsureCreatedAsync();
        var tenant = Guid.NewGuid();
        var actor = Guid.NewGuid();
        var otherTenant = Guid.NewGuid();
        var deviceId = Guid.NewGuid();
        var softwareId = Guid.NewGuid();
        var foreignId = Guid.NewGuid();
        db.Devices.AddRange(new Device(tenant, deviceId, "Lab device"), new Device(otherTenant, foreignId, "Other device"));
        db.Software.AddRange(new Software(tenant, softwareId, "Lab app", "1.0", "winget"),
            new Software(otherTenant, foreignId, "Other app", "1.0", "winget"));
        await db.SaveChangesAsync();
        db.ChangeTracker.Clear();

        var service = new DeploymentRequests(db);
        var scope = new PrincipalScope(tenant, actor);
        Assert.Null(await service.RecordAsync(scope, new(foreignId, softwareId), default));
        Assert.Null(await service.RecordAsync(scope, new(deviceId, foreignId), default));
        Assert.Empty(await db.Audit.ToListAsync());
        var request = await service.RecordAsync(scope, new(deviceId, softwareId), default);

        Assert.NotNull(request);
        Assert.Equal("RecordedOnly", request.Status);
        var deployment = await db.Deployments.SingleAsync();
        var audit = await db.Audit.SingleAsync();
        Assert.Equal(tenant, deployment.TenantId);
        Assert.Equal(tenant, audit.TenantId);
        Assert.Equal(request.Id, deployment.Id);
        Assert.Equal(deployment.Id, audit.DeploymentId);
        Assert.Equal(actor, audit.ActorId);
    }

    [Fact]
    public void RequiresDelegatedAccessScopeEvenWithADeploymentRole()
    {
        var tenant = Guid.NewGuid();
        var actor = Guid.NewGuid();
        var identity = new ClaimsIdentity([
            new("tid", tenant.ToString()), new("oid", actor.ToString()), new("roles", "Deployment.Operator")
        ]);
        var user = new ClaimsPrincipal(identity);
        Assert.False(PrincipalScope.TryRead(user, out _));
        identity.AddClaim(new("scp", "Other.Scope Deployments.Access"));
        Assert.True(PrincipalScope.TryRead(user, out var scope));
        Assert.Equal(new PrincipalScope(tenant, actor), scope);
    }
}
