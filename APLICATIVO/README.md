# InoLabel - executavel

Esta pasta recebe o aplicativo gerado pelo build.

Para gerar o executavel, rode a partir da raiz do repositorio:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\build.ps1
```

Ao final, o executavel fica em:

```text
APLICATIVO\InoLabel\InoLabel.exe
```

O conteudo de `APLICATIVO\InoLabel\` e gerado automaticamente e nao deve ser commitado.
