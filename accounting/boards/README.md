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

## Por qué se comprueba el cuerpo y no el fichero

La cabecera OKF se antepone al copiar, así que el fichero servido **nunca**
coincidirá byte a byte con el original. Lo que debe coincidir es el **cuerpo**,
desde `<!doctype` en adelante. Comparar el fichero entero daría un falso positivo
permanente.

Aviso aprendido de PINTO: su primer sondeo dio un desajuste falso porque buscaba
`<!DOCTYPE` en mayúsculas y el fichero empieza en minúsculas. **Un desajuste de
hash es una afirmación sobre una comparación, y la comparación misma puede ser lo
que está roto.**


### Precondición del hash del cuerpo (señalada por PINTO, 21-nov)

Comparar el cuerpo solo prueba lo que dice probar **mientras haya exactamente un
añadido antes de `<!doctype`**: la cabecera OKF que pone el copiador.

Si algún día un segundo implicado estampa algo más arriba —otra cabecera, una
marca de revisión, un comentario de otra herramienta— la comparación **seguiría
pasando** y estaría comparando un tramo distinto. Es un fallo silencioso, que es
la peor clase: el hash coincide y ya no significa lo mismo.

Precondición, por tanto: **un solo bloque antes del doctype, y lo pone el
copiador.** Si eso cambia, cambia también el punto de anclaje de la comparación.

Comprobación: el cuerpo debe empezar exactamente por `<!doctype` tras retirar
**un** bloque. Si tras retirarlo no empieza por ahí, hay más de un añadido y el
hash ya no es comparable.

## Reglas para añadir un tablero

- Solo ficheros **autocontenidos**: 0 referencias externas, sin CDN.
- Cabecera OKF nombrando la ruta de origen.
- `check_number_format.py` lo escaneará salvo que se añada **por nombre de
  fichero** a `SKIP_FILES`, con motivo escrito. Eximir la carpeta entera haría
  que un tablero futuro con cifras reales pasara sin revisar.
