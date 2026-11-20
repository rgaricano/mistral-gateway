---
type: Funding Assessment
title: Informe de financiación — análisis y ranking por valor/esfuerzo
description: Análisis de vías de financiación — ranking valor/esfuerzo, criterios
  de decisión y comparativa de convocatorias abiertas.
tags:
- financiación
- ranking
- análisis
status: draft
generated:
  by: CONTA/zai-glm-5-3-flash
  at: 2026-11-19 16:15:00+01:00
verified:
- by: human:pendiente
  at: 2026-11-19 16:15:00+01:00
source:
- https://nlnet.nl/propose/
- https://www.enisa.es/
- https://www.cdti.es/
stale_after: 2027-03-31 00:00:00+02:00
---

# MAPA DE FINANCIACIÓN — ranking por valor/esfuerzo (CONTA, 18-nov-2026)

Metodología (regla del ORQ, aceptada):
· Cada convocatoria es DATO con fuente oficial + fecha de consulta (18-19-nov-2026).
  "VERIFICADO" solo si leí el documento oficial; "POR CONFIRMAR" si viene de fuente
  secundaria o resumen.
· Ranking = valor esperado / esfuerzo, no cuantía bruta.
· Filtro duro para Ricardo: ¿exige empresa constituida? (la SLNE existe — marcado).
· NO se prepara ninguna proposal hasta que Ricardo elija.

---

## FILTRO: SLNE YA CONSTITUIDA ⇒ todo lo que exija empresa está DESBLOQUEADO.

| # | Convocatoria | Cuantía | Plazo | Requisitos duros | Encaje | Esfuerzo | Valor/esfuerzo |
|---|---|---|---|---|---|---|---|
| 1 | **NLnet / Restack Open Call #2** | 5-50k € (1ª), hasta 150k (follow-on), cap vida 500k | **3-ene-2027 12:00 CET** | SLNE válida · FOSS internet-stack · sin co-financiación · proyecto abierto | **ALTO**: mistral-gateway es proxy OpenAI-compatible libre, anti-lock-in = tesis del programa | Bajo (proposal 2-3 págs sobre proyecto YA funcionando) | ⭐⭐⭐⭐⭐ |
| 2 | **Aina Hack 2026** (Barcelona, 11-12 dic) | 6.000€ premios (1º 4.000€) | inscripciones hasta **1-dic-2026** | equipo 2-4 · IA en catalán · presencial | MEDIO: agentes IA con soporte catalán (cabría entrenar/ajustar modelo con datos abiertos Aina) | Medio (preparar demo 2 días + viaje BCN) | ⭐⭐⭐⭐ |
| 3 | **Monetización directa kits/agentes** (Gumroad/Polar) | 9-299 $/kit · sin techo | continuo | ninguna específica · producto empaquetado + docs | ALTO: ya tenemos agentes + dashboards listos para empaquetar | Bajo-medio (empaquetar 1-2 tardes) | ⭐⭐⭐⭐ |
| 4 | **Artículos técnicos pagados** | 300-1.500 $/art · Airbyte 900 $, Honeybadger 500 $ | continuo (programas activos ago 2026) | experiencia demostrable · artículo 1.500-2.000 palabras · inglés | MEDIO:know-how real de agentes + gateway = contenido que ellos buscan | Medio (6-10 h por artículo, incl. código probado) | ⭐⭐⭐ |
| 5 | **CDTI Innterconecta STEP 2026** | subvención (FEDER, 150 M€ bolsa total; proyectos típicos 300k-1M) | **23-dic-2026 12:00** | consorcio ≥2 empresas · proyecto en ≥2 CCAA · subcontratación ≥10% a centro de conocimiento · I+D real | MEDIO-BJO: necesitaríamos partner + centro de conocimiento aliado | Alto (memoria técnica + partner + consorcio) | ⭐⭐ |
| 6 | **ENISA Startups y Pymes** | préstamo 25k-1,5M € · sin garantías · 2 años solo intereses | continuo (online, Portal Cliente) | SL/SA con actividad económica real · fuera inmobiliario/financiero · pyme UE · interés = Euríbor 12M + diferencial 4,00-4,50 % según rating | MEDIO: es préstamo, NO subvención — para CRECER cuando haya flujo demostrable | Bajo (solicitud online) — pero REQUIERE devolver | ⭐⭐ (solo si hay plan de devolución) |
| 7 | **Kit Digital como Agente Digitalizador** | bonos 3k/6k/12k/25k/29k € según cliente | consultar ventana (según convocatoria) | facturar ≥100k€ úlitmos 2 años o ≥50k€ último año en proyectos similares (autónomo: 70k/2a, 35k/1a) — BARRERA si la SLNE es nueva y no acumula facturación de digitalización | MEDIO: cabe "setup de agentes IA" como solución, pero hay que acreditar facturación previa | Alto si partimos de cero (adhesión + catálogo) | ⭐⭐ (barrera facturación) |
| 8 | **Kit Consulting** | 12k-24k por cliente (servicios de 6k) | ventana por convocatoria (varias cerradas 2026 — POR CONFIRMAR apertura próxima) | asesor digital adherido · misma barrera de facturación mínima (≥35k-70k) | MEDIO: misma estructura que Kit Digital, perfil consultoría | Alto (mismas barreras) | ⭐⭐ |
| 9 | **Prototype Fund (Alemania)** ⚠️ | hasta 47.500€ individual / 95.000€ equipo (ronda nueva: hasta 79k/158k con 3 líneas) | **30-nov-2026 15:00 → quedan 12 días** | individual o equipo · FOSS "de la y para la sociedad" · **residencia/coordinación en Alemania** (cláusula a CONFIRMAR para SLNE española — probablemente NO elegible) | ALTO en tesis, BAJO en elegibilidad si exige residencia DE | Medio (propuesta corta inicial) | ⭐ (si no elegible, descartar) |
| 10 | **Sovereign Tech Fund / Agency** | contrato de trabajo OSS (no grant): auditorías, hardening, releases | continuo, por invitación/convocatoria | componente OSS de infraestructura crítica con track record | MEDIO: nuestro gateway es nuevo — requeriría adoptarlo como dependencia crítica de otros | Alto (años de track record) | ⭐ (no aún) |
| 11 | **GitHub Sponsors / Polar / Ko-fi** | benchmarks reales: 73 devs >1k$/mes de ~18k perfiles; mediana baja; top 8k$/mes | continuo | audiencia previa · producto/librería OSS con usuarios | BAJO-MEDIO: requiere comunidad antes de moneda | Bajo (activar 1 tarde) | ⭐⭐ (lento pero compuesto) |

---

## LO MÁS FUERTE HOY (mi lectura como CONTA, no como decisión):

1. **NLnet/Restack** — mejor relación valor/esfuerzo Y el encaje temático es exacto.
   Ventana holgada hasta 3-ene; sin co-financiación; SLNE ya constituida.
2. **Aina Hack** — 6k € reales en 2 días, con posibilidad de ganar (nuestros agentes ya
   saben trabajar con modelos abiertos; cabría proveer solución IA en catalán con
   herramientas propias + el hardware nuevo de ricardoPC para el demo en vivo).
3. **Empaquetado de kits en Gumroad/Polar** — ingreso recurrente de bajo techo pero
   coste marginal ≈ 0 (cuota sobrante medida: 220,75 € — el margen sinoá ≈ 99%).
4. **CDTI** — la jugada de mayor cuantía (subvención real) pero mayor esfuerzo:
   SOLO si quieres construir consorcio con otra empresa + centro de conocimiento.
   Cierre 23-dic: decide pronto si va o no va.

## ROCAS EN EL CAMINO (para honestidad contable):
· Prototype Fund: EXIGE residencia/Alemania casi seguro (por confirmar en FAQ).
  Si es así, enrutar la idea vía un partner alemán no merece el esfuerzo vs NLnet.
· Kit Digital/Kit Consulting: BARRERA de facturación mínima acumulada. Si la SLNE
  no llega (facturación previa de digitalización), hay que apadrinarse con un
  agente ya adherido (comisión típica 10-20% del bono canalizado).
· ENISA: préstamo con devolución; solo con plan de negocio que lo pague.
· Todos los "programas de escritura pagada": INGLÉS obligatorio y revisión técnicа
  por el portal; disponible si quieres convertir el know-how en 300-1.500$/art.

## FUENTES (consultadas 18-19 nov 2026):
· nlnet.nl/propose · nlnet.nl/restack · eunita.eu/open-calls/restack-open-call-2 ·
  nlnet.nl/news/2026/20261103-call.html · nlnet.nl/codesupply
· prototypefund.de/en/application/details
· cidai.eu/ecosistemes/hackatons/ainahack/ · eurecat.org · appfounders.es ·
  spainhackathons.com · comunidad.madrid (hackathones COE, universitarios)
· enisa.es/servicios/financiacion/startups-y-pymes/ · enisa.es (Guia_Operativa_FEPYME_v2.pdf)
· cdti.es FAQ Innterconecta STEP 2026 + ciencia.gob.es
· acelerapyme.gob.es/kit-digital · espanadigital.gob.es (Kit Consulting) ·
  comercioconectado.gob.es (agente digitalizador, facturación mínima) ·
  mediacore.es/kit-consulting (ejemplo agente adherido)
· sovereign.tech/programs/fund · codeberg.org/mechko/awesome-maintainer-funding
· dev.to listas de "paid technical writing" + github.com/malgamves/CommunityWriterPrograms
· Gumroad listings (zaidriaz2, agentlab, agenthour) · polar.sh · jakeinsight.com ·
  gemlist.io (Sponsors benchmarks)

---

## CORRECCIÓN DE UNIDADES (19-nov-2026, posterior a la redacción)

Se detectó un error en la conversión de cuota a euros: `euro_per_quota_point()`
dividía 18,14 € entre el presupuesto de 255 € (→ 0,0711 €), pero los "puntos" que
usa la proyección son **puntos porcentuales (0-100)**, no 255avos.

- **Valor correcto: 1 pp de ciclo = 2,55 € de presupuesto incluido = 0,1814 € de lo pagado.**
- Lo que **cambia**: cualquier cifra expresada en "€ de suscripción/día" o "€ de
  suscripción acumulados" queda **×2,55** respecto a lo publicado antes.
- Lo que **NO cambia**: los porcentajes de cuota (% del ciclo), los conteos de tokens,
  los importes de las convocatorias, el ranking valor/esfuerzo y el umbral de
  10-12 k€ del informe de crédito fiscal (ese umbral está en euros de gasto real de
  I+D, no en unidades de cuota).
- Verificación automatizada: `python3 accounting/test_units.py` (4 comprobaciones).
