# Coldfish v4

Para instalar el proyecto se debe tener los siguientes requisitos.
## Python 3.10+
Opcionalmente: Pyinstaller (ver en siguiente seccion).
Sistema operativo (Linux, MacOs, Windows) en condiciones.
## Crear un entorno virtual para mejor control de dependencias:
```bash
python -m venv .venv
source .venv/bin/activate  
.venv\Scripts\activate
```
## Instalar la unica dependencia externa requerida (python-chess):
```bash
pip install python-chess
```
Si se quiere ejecutar el motor directamente en una GUI tipo CuteChess/Chess Arenae se debe convertir el archivo en unico ejecutable .exe o equivalente segun la plataforma usando Pyinstaller.
```bash
python -m PyInstaller --onefile --name ColdFish4 \
  --collect-all chess \
  --add-data "openings.bin:." \
  main.py
```

Esto creara diversas carpetas dentro del directorio donde contenga el main.py y en la carpeta dir se contendra el **ejecutable**, una ves creado podra moverlo a otra carpeta, mas comoda, para luego apuntarlo con su motor GUI.


El motor puede probarse directamente desde la terminal mediante comandos interactivos gracias al protocolo UCI:
```bash
python main.py
```
una vez abierto, se pueden enviar comandos de texto estandar —>

```shell
uci
isready
position startpos moves e2e4 e7e5
go depth 4
```
