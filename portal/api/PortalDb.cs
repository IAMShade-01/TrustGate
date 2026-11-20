using System.Security.Claims;
using Microsoft.EntityFrameworkCore;

public readonly record struct PrincipalScope(Guid TenantId, Guid ActorId)
{
    public static bool TryRead(ClaimsPrincipal? user, out PrincipalScope result)
    {
        result = default;
        if (!Guid.TryParse(user?.FindFirstValue("tid"), out var tenant) || tenant == Guid.Empty
            || !Guid.TryParse(user?.FindFirstValue("oid"), out var actor) || actor == Guid.Empty
            || user?.FindFirstValue("scp")?.Split(' ').Contains("Deployments.Access") != true)
            return false;
        result = new(tenant, actor);
        return true;
    }

    public static PrincipalScope Read(ClaimsPrincipal user) =>
        TryRead(user, out var result) ? result : throw new InvalidOperationException("Missing validated user scope.");
}

public sealed class PortalDb(DbContextOptions<PortalDb> options) : DbContext(options)
{
    public DbSet<Device> Devices => Set<Device>();
    public DbSet<Software> Software => Set<Software>();
    public DbSet<Deployment> Deployments => Set<Deployment>();
    public DbSet<AuditEntry> Audit => Set<AuditEntry>();

    protected override void OnModelCreating(ModelBuilder model)
    {
        model.Entity<Device>().HasKey(row => new { row.TenantId, row.Id });
        model.Entity<Device>().Property(row => row.Name).HasMaxLength(200);
        model.Entity<Software>().HasKey(row => new { row.TenantId, row.Id });
        model.Entity<Software>().Property(row => row.Name).HasMaxLength(200);
        model.Entity<Software>().Property(row => row.Version).HasMaxLength(100);
        model.Entity<Software>().Property(row => row.Method).HasMaxLength(50);
        model.Entity<Deployment>().HasKey(row => new { row.TenantId, row.Id });
        model.Entity<Deployment>().HasIndex(row => new { row.TenantId, row.RequestedAt });
        model.Entity<Deployment>().HasOne(row => row.Device).WithMany()
            .HasForeignKey(row => new { row.TenantId, row.DeviceId }).OnDelete(DeleteBehavior.Restrict);
        model.Entity<Deployment>().HasOne(row => row.Software).WithMany()
            .HasForeignKey(row => new { row.TenantId, row.SoftwareId }).OnDelete(DeleteBehavior.Restrict);
        model.Entity<AuditEntry>().HasKey(row => new { row.TenantId, row.Id });
        model.Entity<AuditEntry>().Property(row => row.Action).HasMaxLength(100);
        model.Entity<AuditEntry>().HasOne<Deployment>().WithMany()
            .HasForeignKey(row => new { row.TenantId, row.DeploymentId }).OnDelete(DeleteBehavior.Restrict);
    }
}

public sealed record Device(Guid TenantId, Guid Id, string Name);
public sealed record Software(Guid TenantId, Guid Id, string Name, string Version, string Method);
public sealed record Deployment(Guid TenantId, Guid Id, Guid DeviceId, Guid SoftwareId, DateTimeOffset RequestedAt)
{
    public Device Device { get; set; } = null!;
    public Software Software { get; set; } = null!;
}
public sealed record AuditEntry(Guid TenantId, Guid Id, Guid ActorId, Guid DeploymentId, string Action, DateTimeOffset OccurredAt);
public sealed record DeploymentInput(Guid DeviceId, Guid SoftwareId);
public sealed record DeploymentView(Guid Id, Guid DeviceId, Guid SoftwareId, DateTimeOffset RequestedAt,
    string DeviceName, string SoftwareName, string Version)
{
    public string Status => "RecordedOnly";
}

public sealed class DeploymentRequests(PortalDb db)
{
    public async Task<DeploymentView?> RecordAsync(PrincipalScope scope, DeploymentInput input, CancellationToken ct)
    {
        var device = await db.Devices.FindAsync([scope.TenantId, input.DeviceId], ct);
        var software = await db.Software.FindAsync([scope.TenantId, input.SoftwareId], ct);
        if (device is null || software is null)
            return null;

        var deployment = new Deployment(scope.TenantId, Guid.NewGuid(), input.DeviceId,
            input.SoftwareId, DateTimeOffset.UtcNow);
        db.Deployments.Add(deployment);
        db.Audit.Add(new AuditEntry(scope.TenantId, Guid.NewGuid(), scope.ActorId, deployment.Id,
            "DeploymentRequestRecorded", deployment.RequestedAt));
        await db.SaveChangesAsync(ct);
        return new DeploymentView(deployment.Id, input.DeviceId, input.SoftwareId, deployment.RequestedAt,
            device.Name, software.Name, software.Version);
    }
}
