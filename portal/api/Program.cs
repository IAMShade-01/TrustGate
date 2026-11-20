using System.Security.Claims;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Authorization;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);
var sql = builder.Configuration.GetConnectionString("Sql")
    ?? throw new InvalidOperationException("Set ConnectionStrings__Sql.");
var audience = builder.Configuration["Entra:ApiClientId"];
var tenants = (builder.Configuration["Entra:Tenants"] ?? "").Split(',', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
if (!Guid.TryParse(audience, out var apiId) || apiId == Guid.Empty || tenants.Length == 0
    || tenants.Any(value => !Guid.TryParse(value, out var id) || id == Guid.Empty))
    throw new InvalidOperationException("Set Entra__ApiClientId and comma-separated Entra__Tenants to valid GUIDs.");

builder.Services.AddDbContext<PortalDb>(options => options.UseSqlServer(sql));
builder.Services.AddScoped<DeploymentRequests>();
builder.Services.AddProblemDetails();
var authentication = builder.Services.AddAuthentication();
var schemes = tenants.Select(value => Guid.Parse(value)).Distinct().Select(tenant =>
{
    var scheme = tenant.ToString();
    var authority = $"https://login.microsoftonline.com/{tenant}/v2.0";
    authentication.AddJwtBearer(scheme, options =>
    {
        options.Authority = authority;
        options.Audience = apiId.ToString();
        options.MapInboundClaims = false;
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidIssuer = authority,
            RoleClaimType = "roles",
            ClockSkew = TimeSpan.FromMinutes(1)
        };
        options.Events = new JwtBearerEvents
        {
            OnTokenValidated = context =>
            {
                if (!PrincipalScope.TryRead(context.Principal, out var scope) || scope.TenantId != tenant)
                    context.Fail("A delegated TrustGate user token from the configured tenant is required.");
                return Task.CompletedTask;
            }
        };
    });
    return scheme;
}).ToArray();

builder.Services.AddAuthorizationBuilder()
    .SetDefaultPolicy(new AuthorizationPolicyBuilder(schemes).RequireAuthenticatedUser()
        .RequireRole("Deployment.Reader", "Deployment.Operator").Build())
    .AddPolicy("operator", policy => policy.AddAuthenticationSchemes(schemes)
        .RequireAuthenticatedUser().RequireRole("Deployment.Operator"));

var app = builder.Build();
app.UseExceptionHandler();
app.Use(async (context, next) =>
{
    if (context.Request.Path.StartsWithSegments("/api"))
        context.Response.Headers.CacheControl = "no-store";
    await next();
});
app.UseAuthentication();
app.UseAuthorization();
app.MapGet("/health/live", () => Results.Ok(new { status = "live" }));
var api = app.MapGroup("/api").RequireAuthorization();
api.MapGet("/session", (ClaimsPrincipal user) => Results.Ok(new
{
    tenantId = PrincipalScope.Read(user).TenantId,
    canRequest = user.IsInRole("Deployment.Operator")
}));
api.MapGet("/devices", async (ClaimsPrincipal user, PortalDb db, CancellationToken ct) =>
    await db.Devices.AsNoTracking().Where(row => row.TenantId == PrincipalScope.Read(user).TenantId)
        .OrderBy(row => row.Name).ThenBy(row => row.Id).Take(200)
        .Select(row => new { row.Id, row.Name }).ToListAsync(ct));
api.MapGet("/catalog", async (ClaimsPrincipal user, PortalDb db, CancellationToken ct) =>
    await db.Software.AsNoTracking().Where(row => row.TenantId == PrincipalScope.Read(user).TenantId)
        .OrderBy(row => row.Name).ThenBy(row => row.Id).Take(200)
        .Select(row => new { row.Id, row.Name, row.Version, row.Method }).ToListAsync(ct));
api.MapGet("/deployments", async (ClaimsPrincipal user, PortalDb db, CancellationToken ct) =>
    await db.Deployments.AsNoTracking().Where(row => row.TenantId == PrincipalScope.Read(user).TenantId)
        .OrderByDescending(row => row.RequestedAt).ThenByDescending(row => row.Id).Take(100)
        .Select(row => new DeploymentView(row.Id, row.DeviceId, row.SoftwareId, row.RequestedAt,
            row.Device.Name, row.Software.Name, row.Software.Version)).ToListAsync(ct));
api.MapGet("/audit", async (ClaimsPrincipal user, PortalDb db, CancellationToken ct) =>
    await db.Audit.AsNoTracking().Where(row => row.TenantId == PrincipalScope.Read(user).TenantId)
        .OrderByDescending(row => row.OccurredAt).ThenByDescending(row => row.Id).Take(100)
        .Select(row => new { row.Id, row.ActorId, row.DeploymentId, row.Action, row.OccurredAt })
        .ToListAsync(ct)).RequireAuthorization("operator");
api.MapPost("/deployments", async (DeploymentInput input, ClaimsPrincipal user, DeploymentRequests requests, CancellationToken ct) =>
{
    if (input.DeviceId == Guid.Empty || input.SoftwareId == Guid.Empty)
        return Results.BadRequest(new { message = "Select a device and a catalog package." });
    var result = await requests.RecordAsync(PrincipalScope.Read(user), input, ct);
    return result is null ? Results.NotFound(new { message = "Device or package not found." }) : Results.Ok(result);
}).RequireAuthorization("operator");

app.UseDefaultFiles();
app.UseStaticFiles();
app.Run();

public partial class Program { }
