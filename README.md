# NewPipe CSV to JSON converter

Golang solution to convert the youtube export .csv to the NewPipe import .json format  
Not sure why this needs to exist, but apparently it does.  
Also there are other people who made this in python etc, which I've found too late.   
https://github.com/JCGdev/Newpipe-CSV-Fixer   
there's also a website to do this whole thing which is probably far more convenient anyway:
https://juandarr.github.io/json-youtube-export/

# How to use

Follow NewPipe's guide on exporting your youtube subs, copied here for your convenience:

1. Go to this URL: https://takeout.google.com/takeout/custom/youtube
2. Log in when asked
3. Click on "All data included", then on "Deselect all", then select only "subscriptions" and click "OK"
4. Click on "Next step" and then on "Create export"
5. click on the "Download" button after it appears and
6. From the downloaded takeout zip extract the .csv file (usually under "YouTube and YouTube music/subscriptions/subscriptions.csv")

After you have that .csv file, run this script on it like so
```
go run main.go subscriptions.csv
go run master.go inscritos.csv
python3 script.py inscritos.csv
```

you'll get a subscriptions.json that you should be able to import as a "PREVIOUS EXPORT" in NewPipe.


# ############ Português ############ #
# Conversor NewPipe de CSV para JSON

Solução em Golang para converter o arquivo .csv exportado pelo YouTube para o formato .json importado pelo NewPipe.
Não sei por que isso precisa existir, mas aparentemente precisa.
Também existem outras pessoas que fizeram isso em Python, etc., que descobri tarde demais.
https://github.com/JCGdev/Newpipe-CSV-Fixer
Há também um site para fazer tudo isso, que provavelmente é muito mais conveniente:
https://juandarr.github.io/json-youtube-export/

# Como usar

Siga o guia da NewPipe sobre como exportar suas inscrições do YouTube, copiado aqui para sua conveniência:

1. Acesse este URL: https://takeout.google.com/takeout/custom/youtube
2. Faça login quando solicitado.
3. Clique em "Todos os dados incluídos", depois em "Desmarcar tudo", selecione apenas "Assinaturas" e clique em "OK".
4. Clique em "Próxima etapa" e depois em "Criar exportação".
5. Clique no botão "Download" quando ele aparecer.
6. Extraia o arquivo .csv do arquivo zip do Takeout baixado (geralmente localizado em "YouTube and YouTube Music/Subscriptions/subscriptions.csv").

Após obter o arquivo .csv, execute este script nele da seguinte forma:
```
go run main.go subscriptions.csv
go run master.go inscritos.csv
python3 script.py inscritos.csv
```

Você receberá um arquivo subscriptions.json que poderá importar como uma "EXPORTAÇÃO ANTERIOR" no NewPipe.

