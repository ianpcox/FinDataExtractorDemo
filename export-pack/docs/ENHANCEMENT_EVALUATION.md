# Export Pack Enhancement Evaluation

## Overview

This document evaluates proposed enhancements to the Azure Export & Rebuild Pack to improve coverage and reduce manual follow-up work.

## Evaluation Criteria

- **Security**: Maintains read-only, no-secrets-by-default principles
- **Value**: Significantly reduces manual work for NetOps
- **Feasibility**: Can be implemented with Azure CLI and standard tools
- **Complexity**: Reasonable implementation and maintenance effort
- **Portability**: Outputs remain usable across tenants

---

## 1. Optional Key Vault Secret Export (Opt-In)

### Approach
Generate operator-assisted scripts per vault that:
- Iterate secret names (from ARM export)
- Prompt operator to pull values via `az keyvault secret show`
- Save to secure, local-only JSON (never committed)

### Evaluation

**✅ High Value**
- Key Vault secrets are the #1 manual gap
- Reduces hours of manual secret lookup/entry
- Critical for application functionality

**✅ Security Compliant**
- Opt-in only (not automatic)
- Secure prompts (Read-Host -AsSecureString)
- Local-only storage with clear warnings
- Scripts can include "DO NOT COMMIT" guards

**✅ Feasible**
- Secret names visible in ARM export
- `az keyvault secret show` works with proper permissions
- Can generate per-vault scripts automatically

**✅ Implementation Complexity: Low-Medium**
- Add Key Vault detection in inventory
- Generate script template per vault
- Include secret name enumeration from ARM

**Recommendation: ✅ IMPLEMENT (Priority: P0)**

**Implementation Notes:**
- Script should warn about secret storage
- Include option to export as encrypted JSON (DPAPI on Windows)
- Generate separate script per vault for isolation
- Include secret metadata (content type, tags, attributes)

---

## 2. Azure AD (Entra) App Registration/Service Principal Stubs

### Approach
- Emit CSV/JSON of discovered app IDs/object IDs referenced in resources
- Generate script to recreate app registrations with placeholders
- Document required permissions/scopes

### Evaluation

**✅ High Value**
- App registrations are tenant-level (not exported by ARM)
- Service principals are critical for automation
- Manual recreation is error-prone

**✅ Security Compliant**
- Only exports IDs (not secrets)
- Placeholders for secrets/certificates
- Clear documentation of what's needed

**⚠️ Feasibility: Medium**
- Can discover app IDs from:
  - Managed identity references
  - Service principal assignments in RBAC
  - App ID references in resource configs
- `az ad app show` requires Graph API permissions
- May need separate authentication for Graph API

**⚠️ Implementation Complexity: Medium**
- Need to parse resource configs for app references
- Graph API calls require different auth context
- Service principal creation scripts need careful parameterization

**Recommendation: ✅ IMPLEMENT (Priority: P1)**

**Implementation Notes:**
- Detect app IDs from:
  - RBAC assignments (service principals)
  - Managed identity configurations
  - Application settings (App Service, Functions)
  - Key Vault access policies
- Generate CSV with: App ID, Display Name, Object ID, Referenced In
- Create script template for app registration recreation
- Document required Graph API permissions

---

## 3. Private DNS and Networking Deltas Report

### Approach
- Produce "network gaps" report flagging:
  - Private endpoints
  - DNS zones
  - VNet peerings
  - Route tables
- Include skeleton Bicep/ARM snippets for each

### Evaluation

**✅ High Value**
- Networking is complex and often missed
- Private endpoints require DNS configuration
- Peerings are cross-subscription/tenant sensitive
- Route tables are easy to miss

**✅ Security Compliant**
- No secrets involved
- Read-only network configuration

**✅ Feasible**
- Private endpoints: `az network private-endpoint list`
- DNS zones: `az network private-dns zone list`
- Peerings: `az network vnet peering list`
- Route tables: `az network route-table list`

**✅ Implementation Complexity: Low-Medium**
- Add network resource detection
- Generate gap report with detected resources
- Create Bicep snippets from exported ARM templates

**Recommendation: ✅ IMPLEMENT (Priority: P1)**

**Implementation Notes:**
- Create `network_gaps_report.md` per subscription
- Include:
  - Private endpoint → DNS zone mappings
  - Cross-subscription peering details
  - Route table → subnet associations
  - NSG rule summaries
- Generate Bicep snippets for each gap
- Flag resources that need manual attention

---

## 4. Workbook/Saved Query Export Hooks for Monitor

### Approach
- Optional operator scripts to enumerate:
  - Log Analytics workbooks
  - Saved searches/queries
- Export via REST/CLI to JSON

### Evaluation

**✅ Medium Value**
- Workbooks contain valuable monitoring logic
- Saved queries are reusable
- Current export may miss these

**✅ Security Compliant**
- No secrets (queries may contain resource IDs, but those are visible)

**✅ Feasible**
- Workbooks: `az monitor workbook list` (or REST API)
- Saved searches: Log Analytics REST API
- Can export to JSON

**✅ Implementation Complexity: Low**
- Add to monitor_export.ps1
- Use REST API or CLI commands
- Save to JSON files

**Recommendation: ✅ IMPLEMENT (Priority: P2)**

**Implementation Notes:**
- Add workbook export to `monitor_export.ps1`
- Use `az monitor workbook show` or REST API
- Export saved queries from Log Analytics workspace
- Include in monitor export folder structure

---

## 5. Enhanced Data-Plane Helpers for Storage/SQL/Redis

### Approach
- Enrich existing operator scripts with:
  - Pre-validated AzCopy/BACPAC command scaffolds
  - Source/destination placeholders
  - Checksum guidance for verification

### Evaluation

**✅ Medium Value**
- Current scripts are basic
- Enhanced scaffolds reduce errors
- Checksum verification adds confidence

**✅ Security Compliant**
- Still requires operator input for secrets
- No secrets in generated commands

**✅ Feasible**
- Can generate AzCopy command templates
- BACPAC commands are straightforward
- Checksum commands can be included

**✅ Implementation Complexity: Low**
- Enhance existing scripts
- Add command validation helpers
- Include checksum examples

**Recommendation: ✅ IMPLEMENT (Priority: P2)**

**Implementation Notes:**
- Enhance `storage_export.ps1` with AzCopy command templates
- Add checksum verification commands (AzCopy supports this)
- Enhance SQL export script with BACPAC best practices
- Include Redis data export guidance (if applicable)

---

## 6. Classic Resource Detection Report

### Approach
- Detector that lists classic/ASM resources
- Suggest ARM/Bicep equivalents
- Provide manual steps

### Evaluation

**✅ Medium Value**
- Classic resources can't be exported
- Prevents surprises during rebuild
- Helps with migration planning

**✅ Security Compliant**
- Read-only detection

**✅ Feasible**
- `az resource list` can filter by API version
- Classic resources have specific API versions
- Can detect and list them

**✅ Implementation Complexity: Low**
- Add classic resource detection to inventory
- Generate report with detected resources
- Link to migration documentation

**Recommendation: ✅ IMPLEMENT (Priority: P2)**

**Implementation Notes:**
- Detect resources with API versions containing "classic" or "2014-*"
- Generate `classic_resources_report.md`
- Include:
  - Resource type
  - Resource name
  - Suggested ARM equivalent
  - Migration documentation links

---

## 7. Quota/SKU Feasibility Check for Target Regions

### Approach
- Preflight file prompting operator to validate:
  - Quotas in destination tenant/region
  - SKU availability
- For each exported resource type

### Evaluation

**✅ High Value**
- Prevents deployment failures
- Saves time during rebuild
- Critical for production migrations

**✅ Security Compliant**
- Read-only checks
- No secrets

**⚠️ Feasibility: Medium-High**
- Quota checks: `az vm list-usage --location`
- SKU availability: `az vm list-sizes --location`
- But need to check for each resource type
- Some quotas are subscription-level, some are regional

**⚠️ Implementation Complexity: Medium**
- Need to detect all resource types
- Generate checklist per resource type
- Include commands to check quotas/SKUs
- May need REST API for some checks

**Recommendation: ✅ IMPLEMENT (Priority: P1)**

**Implementation Notes:**
- Generate `quota_sku_checklist.md` per subscription
- For each resource type, include:
  - Current SKU/size
  - Command to check availability in target region
  - Quota check commands
- Flag resources that may need SKU changes
- Include target region parameter

---

## 8. Environment Parity Checklist

### Approach
- Auto-generate markdown checklist summarizing:
  - All operator-assisted actions required
  - Search schemas, OpenAI deployments, SQL BACPAC
  - Storage data, secrets, AAD apps, DNS, quotas
- Ensure nothing gets missed

### Evaluation

**✅ Very High Value**
- Single source of truth for manual work
- Prevents missed steps
- Critical for successful migration

**✅ Security Compliant**
- Just a checklist, no secrets

**✅ Feasible**
- Can generate from export summary
- Track which services were found
- List all operator scripts generated

**✅ Implementation Complexity: Low**
- Generate from export_summary.json
- Include all detected services
- Link to operator scripts

**Recommendation: ✅ IMPLEMENT (Priority: P0)**

**Implementation Notes:**
- Generate `ENVIRONMENT_PARITY_CHECKLIST.md` in output root
- Include sections for:
  - Infrastructure deployment
  - Data migration
  - Secret/key migration
  - Identity setup
  - Network configuration
  - Monitoring setup
  - Validation steps
- Checkboxes for each item
- Links to relevant scripts/docs

---

## Implementation Priority Summary

### P0 (Critical - Implement First)
1. **Environment Parity Checklist** - Single source of truth
2. **Optional Key Vault Secret Export** - Biggest manual gap

### P1 (High Value - Implement Next)
3. **Azure AD App Registration Stubs** - Identity is critical
4. **Private DNS and Networking Deltas** - Complex, often missed
5. **Quota/SKU Feasibility Check** - Prevents deployment failures

### P2 (Nice to Have)
6. **Workbook/Saved Query Export** - Monitoring artifacts
7. **Enhanced Data-Plane Helpers** - Improve existing scripts
8. **Classic Resource Detection** - Migration planning

---

## Implementation Plan

### Phase 1: Quick Wins (P0)
- Environment Parity Checklist generator
- Key Vault secret export scripts

### Phase 2: High Value (P1)
- Azure AD app detection and stubs
- Network gaps report
- Quota/SKU checklist

### Phase 3: Enhancements (P2)
- Monitor workbook/query export
- Enhanced data migration scripts
- Classic resource detection

---

## Security Considerations

All enhancements maintain security principles:
- ✅ No secrets in automated exports
- ✅ Opt-in for sensitive operations
- ✅ Secure prompts for secret input
- ✅ Local-only storage with warnings
- ✅ Clear documentation of risks

---

## Next Steps

1. Review and approve enhancement priorities
2. Implement P0 items first
3. Test with real Azure environment
4. Iterate based on feedback

