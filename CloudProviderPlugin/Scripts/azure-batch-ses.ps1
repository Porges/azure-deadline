[Environment]::SetEnvironmentVariable("AZ_BATCH_ACCOUNT_URL", "$env:AZ_BATCH_ACCOUNT_URL","Machine")
[Environment]::SetEnvironmentVariable("AZ_BATCH_SOFTWARE_ENTITLEMENT_TOKEN", "$env:AZ_BATCH_SOFTWARE_ENTITLEMENT_TOKEN","Machine")

mkdir C:\ses
"$env:AZ_BATCH_ACCOUNT_URL" | out-file C:\ses\ses.txt -Force
"$env:AZ_BATCH_SOFTWARE_ENTITLEMENT_TOKEN" | out-file C:\ses\ses.txt -Append

net stop deadline10launcherservice
Start-Sleep -Seconds 5
net start deadline10launcherservice
Start-Sleep -Seconds 3600
