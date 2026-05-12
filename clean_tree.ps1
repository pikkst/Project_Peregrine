Get-Content project_structure.txt |
    Where-Object {
        $_ -notmatch "UE4CC" -and
        $_ -notmatch "CrashReportClient" -and
        $_ -notmatch "AppData" -and
        $_ -notmatch "Saved\\Config\\CrashReportClient"
    } |
    Set-Content project_structure_clean.txt
