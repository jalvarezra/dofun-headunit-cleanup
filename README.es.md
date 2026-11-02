# Limpieza de radios DoFun

Herramientas para dueños de radios chinos con Android sobre la plataforma DoFun/TS (paquetes
`com.tw.*` y `com.dofun.*`) que ya saben usar ADB:

- **`tools/headunit.py check`**: informe de solo lectura sobre qué es realmente tu radio, cómo están
  las apps del fabricante y una revisión contra indicadores de malware publicados por Kaspersky.
- **`lists/disable.txt`**: apps del fabricante con telemetría o capacidad de instalar a distancia.
- **`launcher/`**: una pantalla de inicio mínima, sin permisos, que usa 21-28 MB en vez de 128-157 MB.

[English](README.md) · [Lo que medimos (en inglés)](docs/FINDINGS.md)

> [!WARNING]
> Probado en **un solo radio**. Puede dañar funciones del tuyo, incluida la **cámara de reversa**.
> Trabajá con el carro detenido, cambiá una cosa a la vez y probá la cámara y el audio después de
> cada cambio. Perdés las actualizaciones remotas del fabricante. Sin garantía; ver la
> [licencia](LICENSE).

## Por qué

Kaspersky [informó en agosto de 2026](https://securelist.com/android-head-unit-malware/121106/) que
el actualizador de los radios DoFun, `com.tw.core`, se usó para instalar malware. En nuestro radio,
esa misma app mantenía una conexión abierta con Alibaba Cloud en el puerto 1883, y el launcher se
conectaba hacia afuera por HTTP sin cifrar. Además dice tener Android 14 y 4 GB de RAM, y en realidad
tiene Android 10 y unos 2 GB.

## Requisitos

Python 3 y [Android platform-tools](https://developer.android.com/tools/releases/platform-tools). Sin
root. Para compilar el launcher: un JDK y el SDK de Android.

## Pasos

Activá la depuración USB o inalámbrica en Opciones de desarrollador. Buscá el radio, que puede no
usar el puerto 5555:

```bash
adb mdns services
adb connect <ip-del-radio>:<puerto>
```

Si el aviso del radio se cierra muy rápido, corré `adb kill-server` y conectá otra vez. Elegí
**Permitir siempre**.

Revisar, sin cambiar nada:

```bash
python3 tools/headunit.py check <ip-del-radio>:<puerto>
```

Que diga "No indicators found" no prueba que el radio esté limpio.

Desactivar las apps, con confirmación en cada una:

```bash
python3 tools/headunit.py apply <ip-del-radio>:<puerto>
```

Deshacer:

```bash
python3 tools/headunit.py revert <ip-del-radio>:<puerto>
```

Para el launcher, seguí la [sección 4 en inglés](README.md#4-replace-the-launcher-optional): tiene los
comandos para instalarlo, quitar el del fabricante y volver atrás.

## Para tener en cuenta

- **No reinicies por ADB con la llave quitada.** Nuestro radio se quedó encendido con el carro
  apagado, lo que puede gastar la batería. Se arregló poniendo y quitando la llave.
- **Después de un reset o una actualización de firmware,** corré `check` otra vez: las apps pueden
  volver.
- **Puede haber telemetría en apps que no están en la lista.** Solo cubre lo que medimos.
