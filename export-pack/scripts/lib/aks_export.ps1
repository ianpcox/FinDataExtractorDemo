# AKS (Azure Kubernetes Service) Exporter
# Exports AKS cluster configuration and optionally workloads (if kubectl available)

. "$PSScriptRoot\common.ps1"

function Export-AKSCluster {
    param(
        [string]$ClusterName,
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath,
        [switch]$IncludeWorkloads,
        [switch]$UseAdminKubeconfig
    )
    
    Write-Log "INFO" "Exporting AKS cluster" @{
        ClusterName = $ClusterName
        ResourceGroup = $ResourceGroupName
        SubscriptionId = $SubscriptionId
    }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $clusterPath = Join-Path $OutputPath "aks" (Get-SafeFileName $ClusterName)
    if (-not (Test-Path $clusterPath)) {
        New-Item -ItemType Directory -Path $clusterPath -Force | Out-Null
    }
    
    # Export cluster configuration
    try {
        $cluster = az aks show --name $ClusterName --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0) {
            $redacted = Remove-SecretsFromObject $cluster
            Save-JsonFile -Path (Join-Path $clusterPath "cluster.json") -Data $redacted -RedactSecrets
            Write-Log "SUCCESS" "AKS cluster configuration exported"
        }
        else {
            Write-Log "ERROR" "Failed to get AKS cluster details"
            return
        }
    }
    catch {
        Write-Log "ERROR" "Failed to export AKS cluster" @{ Error = $_.Exception.Message }
        return
    }
    
    # Export node pools
    try {
        $nodePools = az aks nodepool list --cluster-name $ClusterName --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and $nodePools) {
            Save-JsonFile -Path (Join-Path $clusterPath "nodepools.json") -Data $nodePools -RedactSecrets
            Write-Log "SUCCESS" "Node pools exported" @{ Count = $nodePools.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export node pools" @{ Error = $_.Exception.Message }
    }
    
    # Export addon profiles if present
    if ($cluster.addonProfiles) {
        Save-JsonFile -Path (Join-Path $clusterPath "addon_profiles.json") -Data $cluster.addonProfiles -RedactSecrets
    }
    
    # Export workloads if requested and kubectl is available
    if ($IncludeWorkloads) {
        Export-AKSWorkloads -ClusterName $ClusterName -ResourceGroupName $ResourceGroupName `
            -SubscriptionId $SubscriptionId -OutputPath $clusterPath -UseAdminKubeconfig:$UseAdminKubeconfig
    }
}

function Export-AKSWorkloads {
    param(
        [string]$ClusterName,
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath,
        [switch]$UseAdminKubeconfig
    )
    
    # Check if kubectl is available
    try {
        $null = kubectl version --client --output json 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Log "WARN" "kubectl not available, skipping workload export"
            return
        }
    }
    catch {
        Write-Log "WARN" "kubectl not available, skipping workload export"
        return
    }
    
    Write-Log "INFO" "Exporting AKS workloads" @{ ClusterName = $ClusterName }
    
    $workloadsPath = Join-Path $OutputPath "workloads"
    if (-not (Test-Path $workloadsPath)) {
        New-Item -ItemType Directory -Path $workloadsPath -Force | Out-Null
    }
    
    # Get kubeconfig
    try {
        $kubeconfigArgs = @(
            "aks", "get-credentials",
            "--name", $ClusterName,
            "--resource-group", $ResourceGroupName,
            "--file", (Join-Path $workloadsPath "kubeconfig")
        )
        
        if ($UseAdminKubeconfig) {
            $kubeconfigArgs += "--admin"
        }
        
        & az $kubeconfigArgs 2>&1 | Out-Null
        
        if ($LASTEXITCODE -ne 0) {
            Write-Log "WARN" "Failed to get kubeconfig, skipping workload export"
            return
        }
        
        $env:KUBECONFIG = Join-Path $workloadsPath "kubeconfig"
    }
    catch {
        Write-Log "WARN" "Failed to get kubeconfig" @{ Error = $_.Exception.Message }
        return
    }
    
    # Export namespaces
    try {
        $namespaces = kubectl get namespaces -o json 2>&1 | ConvertFrom-Json
        if ($namespaces.items) {
            Save-JsonFile -Path (Join-Path $workloadsPath "namespaces.json") -Data $namespaces.items
        }
    }
    catch {
        Write-Log "WARN" "Failed to export namespaces" @{ Error = $_.Exception.Message }
    }
    
    # Export deployments
    try {
        $deployments = kubectl get deployments -A -o json 2>&1 | ConvertFrom-Json
        if ($deployments.items) {
            Save-JsonFile -Path (Join-Path $workloadsPath "deployments.json") -Data $deployments.items
        }
    }
    catch {
        Write-Log "WARN" "Failed to export deployments" @{ Error = $_.Exception.Message }
    }
    
    # Export statefulsets
    try {
        $statefulsets = kubectl get statefulsets -A -o json 2>&1 | ConvertFrom-Json
        if ($statefulsets.items) {
            Save-JsonFile -Path (Join-Path $workloadsPath "statefulsets.json") -Data $statefulsets.items
        }
    }
    catch {
        Write-Log "WARN" "Failed to export statefulsets" @{ Error = $_.Exception.Message }
    }
    
    # Export daemonsets
    try {
        $daemonsets = kubectl get daemonsets -A -o json 2>&1 | ConvertFrom-Json
        if ($daemonsets.items) {
            Save-JsonFile -Path (Join-Path $workloadsPath "daemonsets.json") -Data $daemonsets.items
        }
    }
    catch {
        Write-Log "WARN" "Failed to export daemonsets" @{ Error = $_.Exception.Message }
    }
    
    # Export services
    try {
        $services = kubectl get services -A -o json 2>&1 | ConvertFrom-Json
        if ($services.items) {
            Save-JsonFile -Path (Join-Path $workloadsPath "services.json") -Data $services.items
        }
    }
    catch {
        Write-Log "WARN" "Failed to export services" @{ Error = $_.Exception.Message }
    }
    
    # Export ingresses
    try {
        $ingresses = kubectl get ingresses -A -o json 2>&1 | ConvertFrom-Json
        if ($ingresses.items) {
            Save-JsonFile -Path (Join-Path $workloadsPath "ingresses.json") -Data $ingresses.items
        }
    }
    catch {
        Write-Log "WARN" "Failed to export ingresses" @{ Error = $_.Exception.Message }
    }
    
    # Export configmaps
    try {
        $configmaps = kubectl get configmaps -A -o json 2>&1 | ConvertFrom-Json
        if ($configmaps.items) {
            Save-JsonFile -Path (Join-Path $workloadsPath "configmaps.json") -Data $configmaps.items
        }
    }
    catch {
        Write-Log "WARN" "Failed to export configmaps" @{ Error = $_.Exception.Message }
    }
    
    # Export secrets (NAMES ONLY - no data)
    try {
        $secrets = kubectl get secrets -A -o json 2>&1 | ConvertFrom-Json
        if ($secrets.items) {
            # Redact all data, keep only metadata
            $secretNames = $secrets.items | Select-Object `
                @{Name='namespace'; Expression={$_.metadata.namespace}}, `
                @{Name='name'; Expression={$_.metadata.name}}, `
                @{Name='type'; Expression={$_.type}}, `
                @{Name='creationTimestamp'; Expression={$_.metadata.creationTimestamp}}
            
            Save-JsonFile -Path (Join-Path $workloadsPath "secrets_names_only.json") -Data $secretNames
            Write-Log "INFO" "Exported secret names only (data redacted)" @{ Count = $secretNames.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export secrets" @{ Error = $_.Exception.Message }
    }
    
    # Export Helm releases if available
    try {
        $null = helm version --short 2>&1
        if ($LASTEXITCODE -eq 0) {
            $helmReleases = helm list -A -o json 2>&1 | ConvertFrom-Json
            if ($helmReleases) {
                Save-JsonFile -Path (Join-Path $workloadsPath "helm_releases.json") -Data $helmReleases
                
                # Export values for each release
                $helmValuesPath = Join-Path $workloadsPath "helm_values"
                if (-not (Test-Path $helmValuesPath)) {
                    New-Item -ItemType Directory -Path $helmValuesPath -Force | Out-Null
                }
                
                foreach ($release in $helmReleases) {
                    try {
                        $values = helm get values $release.name -n $release.namespace -o json 2>&1
                        if ($LASTEXITCODE -eq 0) {
                            $safeName = Get-SafeFileName "$($release.namespace)_$($release.name)"
                            Set-Content -Path (Join-Path $helmValuesPath "$safeName.json") -Value $values -Encoding UTF8
                        }
                    }
                    catch {
                        Write-Log "WARN" "Failed to get Helm values for release" @{
                            Release = $release.name
                            Namespace = $release.namespace
                        }
                    }
                }
                
                Write-Log "SUCCESS" "Helm releases exported" @{ Count = $helmReleases.Count }
            }
        }
    }
    catch {
        Write-Log "INFO" "Helm not available, skipping Helm export"
    }
    
    Write-Log "SUCCESS" "AKS workloads exported" @{ ClusterName = $ClusterName }
}

# Functions available when dot-sourced

