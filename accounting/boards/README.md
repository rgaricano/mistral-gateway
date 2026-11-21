---
type: Readme
title: "Tableros de diseño — copias estáticas de PINTO"
description: "Procedencia, hashes verificados y protocolo de recopia de los tableros de diseño servidos en /boards/."
tags: [boards, diseño, copias, verificación]
status: verified
generated: 2026-11-21T00:10:00+01:00
source:
  - "gentle-companion-aesthetic/design/ (árbol de PINTO)"
verified: 2026-11-21
stale_after: 2026-12-15
---

# Tableros de diseño — copias, no originales

Los tableros los crea **PINTO** en
`/home/ricardo/Trabajo/IAI/gentle-companion-aesthetic/design/`. Aquí se sirven
**copias**, no el árbol de trabajo: una edición a medias o un `git checkout` allí
no debe cambiar lo que Ricardo está mirando en mitad de una revisión.

## Estado verificado de las copias

Los md5 son del **cuerpo servido** (sin la cabecera OKF que se añade al copiar),
calculados sobre lo que devuelve el servidor, no sobre el disco:

| Tablero | md5 del cuerpo | Estado de la decisión |
|---|---|---|
| `01-clay-tint.html` | `3f48414e920b0dc165257d0ff2ce8c6e` | **decidido**: A1 ámbar |
| `02-icon-weight.html` | `7d5fad3b502c049668f5408e07346d8c` | abierto: B1/B2/B3 |
| `system.html` | `09f9785ec1cc1662bd2b730af1434fbc` | referencia |

## Protocolo de recopia (acordado con PINTO, 21-nov)

1. **PINTO envía**: ruta + md5 + una línea de qué cambió.
2. **Se copia**, se añade la cabecera OKF y se **comprueba el md5 del cuerpo
   contra el que ella declaró**.
3. **Se responde con el md5 verificado**, y ella recarga la URL servida para
   confirmar que coincide.

El tercer paso es el que evita que alguien publique un tablero obsoleto sin darse
cuenta: un hash solo sirve de algo si alguien vuelve a comprobar los bytes que
realmente se están sirviendo.

## Qué se compara, y por qué cambió

Antes este documento decía: *«la cabecera se antepone al copiar, así que el fichero
servido nunca coincidirá; compara el cuerpo desde `<!doctype`»*.

**Eso ya no es cierto para nuestros tableros.** Los originales de PINTO **ya traen
su cabecera**, así que no se antepone nada y **el fichero entero coincide**. Comparar
el cuerpo sería seguir usando el procedimiento complicado para un caso que se volvió
simple — y ese procedimiento tenía el defecto descrito abajo.

Sigue siendo cierto en el otro caso: si algún día se copia un original **sin**
cabecera, la nuestra lo desalinea y hay que comparar el cuerpo.

## El defecto que obligó a cambiar el procedimiento

La versión anterior de esta sección explicaba cómo quitar un bloque y comparar el
resto, con su precondición. **Ese procedimiento pasaba mientras destruía lo que
decía proteger:** con dos cabeceras presentes —la del autor y la del copiador— el
«resto» seguía conteniendo la del autor, así que la comparación medía un tramo que
nadie había declarado.

**No se arregló endureciendo la comprobación. Se arregló eliminándola**, copiando
byte a byte. Un protocolo que no puede pasar sobre el tramo equivocado vale más que
uno que documenta cómo no hacerlo.

Aviso de PINTO que se conserva porque es independiente de todo esto: su primer
sondeo dio un desajuste falso porque buscaba `<!DOCTYPE` en mayúsculas y el fichero
empieza en minúsculas. **Un desajuste de hash es una afirmación sobre una
comparación, y la comparación misma puede ser lo que está roto.**

### Dos ramas, y solo una tiene ancla

| Caso | Procedimiento | Verificación |
|---|---|---|
| **El original ya trae su cabecera** (lo normal ahora) | copia **byte a byte**, no se añade nada | el md5 de la copia **es** el del original: una igualdad exacta |
| **El original no la trae** | se estampa la nuestra nombrando el origen, y se guarda su md5 en `original_md5` | el cuerpo servido, tras retirar **un** bloque, debe coincidir con el original |

La primera rama no tiene ancla, ni precondición, ni forma de pasar sobre el tramo
equivocado: **no hay nada que comparar mal, porque se comparan ficheros enteros.**

La segunda sí necesita el ancla del `<doctype` y su precondición — un solo añadido
antes del doctype. Solo aplica a originales sin estampar, que hoy no tenemos.

**Por qué esto importa:** el procedimiento anterior quitaba un bloque y comparaba
el resto. Con dos cabeceras presentes, ese «resto» seguía conteniendo la cabecera
del autor, así que la comprobación **pasaba mientras destruía la procedencia que
decía proteger**. Una comprobación que aprueba mientras rompe lo comprobado es
peor que no tenerla.

**Regla que evita repetirlo:** cuando un hash no cuadra, **sospecha del
procedimiento antes que del fichero.** Así se encontró este.


### Cómo se compara (y cómo no)

**Hashea los dos lados con el mismo comando, en la misma tubería.**

Dos incidentes reales, ambos de comparación y ninguno de datos:

- Buscar `<!DOCTYPE` en mayúsculas en un fichero que empieza en minúsculas → el
  índice devuelve -1 y se corta basura.
- Hashear un lado con `printf '%s'` (que **elimina el salto de línea final**) y el
  otro con `md5sum` → tres ficheros idénticos reportados como distintos.

Dos procedimientos de hash distintos no son una comprobación más débil: **son otra
pregunta.** `curl | md5sum` en ambos lados es una comparación; uno con `printf` y
otro con `md5sum` es una resta de cosas distintas que casualmente devuelve texto
con forma de resultado.

## Reglas para añadir un tablero

- Solo ficheros **autocontenidos**: 0 referencias externas, sin CDN.
- Cabecera OKF nombrando la ruta de origen.
- `check_number_format.py` lo escaneará salvo que se añada **por nombre de
  fichero** a `SKIP_FILES`, con motivo escrito. Eximir la carpeta entera haría
  que un tablero futuro con cifras reales pasara sin revisar.
