FROM node:24-bookworm-slim AS web
WORKDIR /src
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
ARG VITE_ENTRA_TENANT_ID
ARG VITE_ENTRA_SPA_CLIENT_ID
ARG VITE_ENTRA_API_CLIENT_ID
RUN npm run build

FROM mcr.microsoft.com/dotnet/sdk:10.0 AS api
WORKDIR /src
COPY api/ ./
RUN dotnet publish -c Release -o /app
COPY --from=web /src/dist/ /app/wwwroot/

FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=api /app/ ./
EXPOSE 8080
USER $APP_UID
ENTRYPOINT ["dotnet", "TrustGate.Api.dll"]
