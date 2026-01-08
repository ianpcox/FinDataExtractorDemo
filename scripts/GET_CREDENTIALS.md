# Getting Azure Document Intelligence Credentials

The vanilla version doesn't use Key Vault by default (to keep it simple), but you need the Document Intelligence credentials for extraction to work.

## Option 1: Fetch from Key Vault (Recommended)

1. **Add Key Vault name to `.env`:**
   ```
   AZURE_KEY_VAULT_NAME=your-key-vault-name
   # OR
   AZURE_KEY_VAULT_URL=https://your-key-vault-name.vault.azure.net/
   ```

2. **Make sure you're logged in to Azure CLI:**
   ```powershell
   az login
   ```

3. **Run the fetch script:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   python scripts\fetch_credentials_from_keyvault.py
   ```

   This will automatically update your `.env` file with:
   - `AZURE_FORM_RECOGNIZER_ENDPOINT`
   - `AZURE_FORM_RECOGNIZER_KEY`

## Option 2: Manual Setup

If you know the credentials, just add them directly to `.env`:

```bash
AZURE_FORM_RECOGNIZER_ENDPOINT=https://your-region.api.cognitive.microsoft.com/
AZURE_FORM_RECOGNIZER_KEY=your-api-key-here
```

## Finding Your Key Vault Name

If you're not sure what your Key Vault name is:

1. **Check Azure Portal:**
   - Go to Azure Portal → Key Vaults
   - Find your Key Vault and copy the name

2. **Or use Azure CLI:**
   ```powershell
   az keyvault list --query "[].name" -o table
   ```

3. **Or check the original project's `.env` file** (if you have access)

## After Getting Credentials

Once the credentials are in your `.env` file, you can:

1. **Run the demo script:**
   ```powershell
   python scripts\demo_all_features.py
   ```

2. **Test extraction:**
   ```powershell
   python scripts\test_azure_files.py
   ```

3. **Use the API** - Document Intelligence will now work for invoice extraction

