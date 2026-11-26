# ¿Qué cambia los set points de los chillers de glicol, y precede eso a las fallas?

*English version: <https://sotn-012.lsst.io/>*

```{abstract}
Los chillers de glicol que enfrían el Telescopio Simonyi, la Cámara LSST (LSSTCam) y los espacios de la instalación no mantienen una temperatura de suministro fija: el Environmental Awareness System (EAS) vuelve a comandar sus set points de forma automática, muchas veces al día. Como las fallas del glicol han interrumpido repetidamente las operaciones nocturnas, un cambio de set point cerca de un incidente invita a pensar que lo causó o lo anticipó. En esta technote establecemos qué impulsa realmente esos cambios, usando los eventos `lsst.sal.HVAC.logevent_chillerConfiguration` del 1 de enero al 20 de julio de 2026 junto con el código fuente y la configuración del EAS, y los contrastamos con un catálogo de incidentes de refrigeración. **No encontramos una firma sistemática en los set points antes de las fallas**, y mostramos que los cambios frecuentes en los dos chillers controlados por el EAS son un comportamiento esperado y no una anomalía. Sí encontramos dos casos en que la telemetría de los set points rompió su patrón esperado: el Chiller 02 reportó 0 °C y luego se apagó a partir del 4 de mayo, dejando el circuito frío con un solo chiller durante los dos días y medio previos al calentamiento de emergencia de la cámara del 7 de mayo (cuya causa raíz fue un filtro tapado), y el 12 de julio volvió de un corte de energía con un set point por defecto 9 °C por debajo de su comando y fue corregido a mano antes de que causara daño. Al comparar cada comando del EAS con el valor reportado por el chiller, los dos chillers adoptan un nuevo set point en unos 6 s en el 99% de los casos, pero el Chiller 01 y el Chiller 02 pasaron el 1.4% y el 3.5% del tiempo evaluado reportando un set point distinto del comandado, casi todo en unos pocos períodos de varias horas después de reinicios de chillers y cortes de energía. **Recomendamos una alarma del Watcher sobre la diferencia entre los dos valores reportados y una segunda sobre el valor reportado frente al comando.** Esta nota se limita a los set points; los rangos nominales de flujo, temperatura y presión de los circuitos de glicol se dejan para análisis separados.
```

**Uso de IA.** Este trabajo se hizo con Claude, el asistente de IA de Anthropic, usado principalmente a través de Claude Code en este repositorio. Claude escribió los notebooks de análisis y [`setpoint_plots.py`](https://github.com/lsst-so/sotn-012/blob/main/notebooks/setpoint_plots.py), leyó el código fuente y la configuración de `ts_eas`, `ts_hvac` y `ts_config_ocs` para explicar qué impulsa los set points, recopiló las referencias de Jira y Confluence y el catálogo FRACAS de set points ([`notebooks/fracas_setpoint_events.csv`](https://github.com/lsst-so/sotn-012/blob/main/notebooks/fracas_setpoint_events.csv)), y redactó el texto de esta nota. El [notebook *Command Response*](https://github.com/lsst-so/sotn-012/blob/main/notebooks/RSO-901%20Glycol%20Set%20Points%20-%20Command%20Response.ipynb) fue escrito por Erik Dennihy con un agente de programación con IA, con el mismo estilo que los demás notebooks. Los autores dirigieron el análisis, ejecutaron los notebooks en el RSP, verificaron los resultados contra la telemetría y los tickets, y revisaron y editaron cada sección; son responsables de su contenido.

## Alcance y método

[RSO-901](https://rubinobs.atlassian.net/browse/RSO-901) busca entender cuáles son los criterios detrás de los cambios en los set points de los chillers de glicol, y si esos cambios coinciden con las fallas de glicol catalogadas. Leímos todos los eventos `lsst.sal.HVAC.logevent_chillerConfiguration` del 1 de enero al 20 de julio de 2026. Las observaciones se detuvieron el 17 de julio; la telemetría siguió fluyendo hasta el 20 de julio, cuando una tormenta invernal cortó la energía. Este evento publica el `activeSetpoint` de un chiller cada vez que se (re)configura, y graficamos los set points junto a los incidentes de [`notebooks/glycol_catastrophic_faults.csv`](https://github.com/lsst-so/sotn-012/blob/main/notebooks/glycol_catastrophic_faults.csv).

**No encontramos una firma sistemática en los set points antes de las fallas**, pero sí **dos casos en que la telemetría de los set points rompió su patrón esperado**, uno de ellos dos días y medio antes del incidente de la cámara del 7 de mayo (ver <a href="#watcher-alarms">Alarmas del Watcher</a>). El resultado principal sigue siendo que los cambios frecuentes de set point en los Chillers 01 y 02 son esperados. El Environmental Awareness System (EAS) los comanda automáticamente y los mueve cada vez que la diferencia de temperatura entre el glicol y el ambiente sale de una banda configurada. Un cambio de set point en esos dos chillers es, por lo tanto, rutinario y no una anomalía en sí mismo. El [notebook *Command Response*](https://github.com/lsst-so/sotn-012/blob/main/notebooks/RSO-901%20Glycol%20Set%20Points%20-%20Command%20Response.ipynb) (Erik Dennihy) compara luego cada comando `HVAC.configChiller` con ese valor reportado, para medir qué tan rápido y qué tan confiablemente los dos chillers controlados por el EAS siguen lo que se les ordena.

## Qué impulsa los set points

El CSC del EAS ([`ts_eas`](https://github.com/lsst-ts/ts_eas)) envía `HVAC.configChiller` a exactamente dos chillers ([`N_CHILLERS = 2`](https://github.com/lsst-ts/ts_eas/blob/df201f886e74f07d61069ba0ce0d8199fb877849/python/lsst/ts/eas/hvac_model.py#L44)): `coldGlycolChiller01` (dispositivo 101) y `coldGlycolChiller02` (dispositivo 102). Nunca comanda `comfortGlycolChiller03` (103) ni `coatingGlycolChiller04` (104) ([enum `DeviceId`](https://github.com/lsst-ts/ts_xml/blob/853318b5ca33cfa23150c20a3400156e6a946ae4/python/lsst/ts/xml/enums/HVAC.py#L41-L44)). Dos ciclos en `HvacModel` fijan los valores:

1. **Una vez al día, a mediodía** ([`adjust_glycol_chillers_at_noon`](https://github.com/lsst-ts/ts_eas/blob/df201f886e74f07d61069ba0ce0d8199fb877849/python/lsst/ts/eas/hvac_model.py#L706-L745)), el EAS calcula nuevos set points a partir de la temperatura interior mínima de la noche anterior, leída del ESS interior (índice SAL 113).
2. **Cada 60 s** ([`monitor_glycol_chillers`](https://github.com/lsst-ts/ts_eas/blob/df201f886e74f07d61069ba0ce0d8199fb877849/python/lsst/ts/eas/hvac_model.py#L650-L704)), el EAS revisa la diferencia entre el promedio de los dos set points y la temperatura interior *actual* ([`check_glycol_setpoint`](https://github.com/lsst-ts/ts_eas/blob/df201f886e74f07d61069ba0ce0d8199fb877849/python/lsst/ts/eas/hvac_model.py#L625-L648)). Si esa diferencia queda fuera de `[glycol_band_low, glycol_band_high]`, el EAS recalcula ambos set points a partir de la temperatura interior actual y los envía.

En ambos casos los dos set points salen de [`compute_glycol_setpoints`](https://github.com/lsst-ts/ts_eas/blob/df201f886e74f07d61069ba0ce0d8199fb877849/python/lsst/ts/eas/hvac_model.py#L558-L623), que funciona en cuatro pasos:

1. **Apuntar bajo el ambiente.** El *promedio* de los dos set points se fija en `ambient + glycol_average_offset`. El desplazamiento es negativo, así que el glicol circula más frío que la sala: con 12 °C en el interior, el promedio objetivo es 4.5 °C.
2. **No bajar del punto de rocío.** Si ese objetivo queda en o bajo el punto de rocío interior máximo de la noche más un margen, se sube para quedar por encima. Es una protección contra la condensación: un glicol más frío que el punto de rocío formaría agua en las tuberías y la óptica.
3. **Dividir el promedio en dos.** Un chiller queda la mitad de `glycol_setpoints_delta` por encima del promedio y el otro la mitad por debajo, de modo que quedan separados por `delta` y siguen promediando el objetivo. El Chiller 01 es siempre el más cálido. Con un promedio de 4.5 °C y un delta de 1 °C: Chiller 01 en 5.0 °C, Chiller 02 en 4.0 °C.
4. **Acotar a los límites fijos.** Si el set point más frío quedara bajo `glycol_absolute_minimum`, se fija ahí y el más cálido se sube para mantener la separación de 1 °C; lo mismo ocurre a la inversa en `glycol_absolute_maximum`. La separación se conserva, así que un par acotado queda exactamente en el límite; por eso los Chillers 01/02 marcan 10.0/9.0 °C cuando se alcanza el máximo.

Los valores en la cumbre ([`ts_config_ocs` `EAS/v9/_init.yaml`](https://github.com/lsst-ts/ts_config_ocs/blob/8c215dac5d45fc766953adec2c27bc4fe3451151/EAS/v9/_init.yaml#L12-L18)) son:

| Parámetro | Valor | Significado |
|---|---|---|
| `glycol_average_offset` | −7.5 °C | Set point promedio nominal relativo al ambiente interior |
| `glycol_band_low` / `glycol_band_high` | −10.0 / −5.0 °C | Rango permitido de (set point promedio − ambiente) antes de recalcular |
| `glycol_setpoints_delta` | 1.0 °C | Chiller 01 − Chiller 02 |
| `glycol_dew_point_margin` | 1.0 °C | Margen sobre el punto de rocío interior máximo de la noche |
| `glycol_absolute_minimum` / `_maximum` | −10.0 / 10.0 °C | Límites del set point más frío / más cálido |

Solo el máximo absoluto cambió en 2026: fue 9 °C hasta el 2026-02-23, luego 20 °C hasta el 2026-04-11, y después 10 °C. Hasta `ts_eas` v0.15.0, el EAS dejaba de ajustar el glicol de noche. [OSW-2128](https://rubinobs.atlassian.net/browse/OSW-2128) ([ts_eas#79](https://github.com/lsst-ts/ts_eas/pull/79), integrado el 2026-04-08, publicado el 2026-05-06) eliminó esa excepción, así que la revisión de la banda ahora corre a toda hora. [RSO-580](https://rubinobs.atlassian.net/browse/RSO-580) da seguimiento al caso relacionado FRACAS-387, en que el Chiller 2 se detuvo el mismo día en que el EAS cambió su set point.

## Comportamiento esperado por chiller

La telemetría coincide con el código (1 de enero al 20 de julio de 2026, 201 `day_obs`, 1128 eventos):

* **Chillers 01 y 02 (glicol frío, controlados por el EAS): actualizados con más frecuencia.** Cambiaron de set point 472 y 468 veces, en 188 y 192 de los 201 días. El paso mediano fue de 1.0 °C. De 348 actualizaciones casi simultáneas (dentro de 5 s), el Chiller 01 estuvo más cálido que el Chiller 02 en 339, y exactamente 1.0 °C más cálido en 305, que es el `glycol_setpoints_delta` configurado. Los cambios se agrupan en dos horas locales fijas, y ambos grupos se desplazan una hora en UTC con el cambio de horario del 5 de abril. Uno es el mediodía local (15 UTC, luego 16 UTC), el reajuste diario. El otro es alrededor de las 07:00 locales, cerca del amanecer (10 UTC, luego 11 UTC). El resto de los cambios se reparte a lo largo del día, como se espera de los recálculos activados por la banda. Los set points variaron de −4.0 a 12.5 °C en el Chiller 01 y de −3.7 a 13.0 °C en el Chiller 02, así que nunca se alcanzó el mínimo absoluto de −10 °C.
* **Chiller 03 (glicol de confort, no controlado por el EAS): actualizado con menos frecuencia.** Cambió 148 veces, pero solo en 31 días, y su primer evento es del 16 de enero. Casi todos esos cambios son ráfagas cortas que alternan entre 0 °C y 2 °C en segundos o minutos (104 de 161 intervalos consecutivos duran menos de 5 min); estuvo en 3 °C o 5 °C solo una vez cada uno. Estos valores están muy por debajo del set point "generalmente > 5 °C" que indica la página [Introduction to Chillers](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/949944397/Introduction+to+Chillers), lo que requiere seguimiento. Como el EAS no comanda este chiller, estos cambios vienen de fuera del EAS (por ejemplo, cambios manuales o los controles de la instalación).
* **Chiller 04 (exterior; `coatingGlycolChiller04` en el enum, ahora en bypass para enfriar solo la sala de computadores): sin telemetría.** Tiene un set point, y [OBS-930](https://rubinobs.atlassian.net/browse/OBS-930) reporta que cambió sin ser comandado en 2025, pero `logevent_chillerConfiguration` no tiene eventos del dispositivo 104 en el rango analizado.

Ningún documento explica el escalonamiento de 1 °C. [OSW-860](https://rubinobs.atlassian.net/browse/OSW-860) solo lo plantea como requisito. Como los Chillers 01 y 02 alimentan el mismo circuito de glicol frío, la lectura natural es una secuencia: el chiller más frío ve la carga primero y hace el trabajo, mientras que el más cálido solo aporta cuando el suministro sube cerca de 1 °C.

## Respuesta a los comandos

Las secciones anteriores leen los set points de `logevent_chillerConfiguration`, pero ese evento es el *valor reportado* por el chiller: el CSC del HVAC lo construye a partir de la telemetría del chiller, y solo mientras el chiller está encendido. El [notebook *Command Response*](https://github.com/lsst-so/sotn-012/blob/main/notebooks/RSO-901%20Glycol%20Set%20Points%20-%20Command%20Response.ipynb) (Erik Dennihy) lo compara con lo que el EAS realmente envió: cada comando `HVAC.configChiller` a los Chillers 01 y 02 en la misma ventana, cerca de uno por chiller por minuto. Un valor reportado coincide con un comando cuando está dentro de 0.1 °C, porque el chiller trunca los set points a 0.1 °C. Un comando solo se evalúa cuando su valor tiene al menos 60 s de antigüedad, para no contar como error a un chiller que aún se está moviendo a un nuevo valor, y no mientras `logevent_deviceEnabled` indica que el chiller está apagado. Esa máscara se decodifica con el orden de bits del ts_xml con que se compiló el CSC del HVAC, que cambió cuando el CSC se actualizó el 25 de febrero; decodificarla con el enum actual confunde las válvulas de conmutación del glicol con los chillers y deja fuera del análisis los meses de marzo a junio.

**Latencia.** De los 671 comandos nuevos que requerían respuesta, el 99% se respondió en menos de 60 s, con un retardo mediano de 6.4 s en el Chiller 01 y 6.0 s en el Chiller 02; 7 nunca se respondieron. **Tiempo con discrepancia.** El Chiller 01 pasó 42.1 h (1.4% de las 3062 horas evaluadas) con el valor reportado distinto del comando, y el Chiller 02 109.4 h (3.5% de 3152 h). **Magnitud.** Casi toda esa discrepancia es grande: 33.5 h y 107.0 h estuvieron desviadas en 0.5 °C o más, en 25 y 24 períodos, con un peor caso de 10.8 °C. Diez períodos de 5 a 30 h suman 115 de esas 141 h, todos entre el 4 de febrero y el 5 de julio; **34 de los 49 períodos empiezan con un valor reportado de 0.0 °C, el valor que aparece cuando un chiller o el CSC del HVAC vuelve a levantarse**, y en ocho períodos de febrero y marzo el Chiller 02 se quedó en 4.6 °C sin importar lo que comandara el EAS. Mayo y junio juntos muestran 2 h de discrepancia grande.

Las discrepancias grandes son donde aparecerían los casos FRACAS. En esta ventana el catálogo ([`notebooks/fracas_setpoint_events.csv`](https://github.com/lsst-so/sotn-012/blob/main/notebooks/fracas_setpoint_events.csv)) incluye [FRACAS-387](https://rubinobs.atlassian.net/browse/FRACAS-387) (15 de mayo, un posible set point bajo en el Chiller 02) y [FRACAS-402](https://rubinobs.atlassian.net/browse/FRACAS-402) (3 y 12 de julio, cuando los chillers volvieron de cortes de energía con los set points por defecto de Niagara en lugar de los del EAS). FRACAS-402 aparece ambos días. El 3 de julio, el Chiller 02 reportó 7.1 °C frente a un comando de −3.7 °C entre las 16:53 y las 18:50 UTC (el peor caso de 10.8 °C mencionado arriba) y el Chiller 01 reportó 2.6 °C frente a −2.7 °C entre las 17:55 y las 18:51, lo que coincide con los valores y la hora de la corrección manual del ticket. El 12 de julio la discrepancia está en el Chiller 02, que reportó su valor por defecto de Niagara de −3.7 °C frente a un comando de 5.2 °C entre las 11:39 y las 13:39 UTC, mientras el Chiller 01, en 6.1 °C, seguía su comando de 6.2 °C. El reporte de Yousuke Utsumi en el ticket da ambos valores, 6 °C y −3.7 °C; la fila 12 de nuestro catálogo marca al Chiller 01 como el erróneo, pero el EFD muestra que el error estaba en el Chiller 02. FRACAS-387 no aparece: el Chiller 02 reportó el set point comandado durante todo el 15 de mayo, así que lo que lo detuvo no fue un comando que el chiller no adoptara. Tampoco aparece el incidente de la cámara del 7 de mayo: el EAS no envió comandos `configChiller` el 3, 4, 5 y 7 de mayo, así que no hay nada que esta comparación pueda evaluar ahí, y el caso de mayo solo es visible en el valor reportado y en `deviceEnabled` (siguiente sección).

```{raw} html
<div id="figure-1"></div>
<iframe src="plots/chiller_command_response_20260101_20260720.html"
        title="Gráfico interactivo del valor reportado por los chillers frente al comando del EAS, enero a julio de 2026"
        style="width: 100%; height: 720px; border: 0;"
        loading="lazy"></iframe>
<p><em>Figura 1. Tiempo por día UTC en que los Chillers 01 y 02 reportaron un set point distinto del comando del EAS (gris: menos de 0.5 °C; color: 0.5 °C o más), y el peor error de cada uno de esos días, 2026-01-01 a 2026-07-20. Las líneas verticales discontinuas son los incidentes de refrigeración catalogados.
<a href="plots/chiller_command_response_20260101_20260720.html">Abrir la figura en pantalla completa.</a></em></p>
```

(watcher-alarms)=
## Alarmas del Watcher

Los dos set points no son independientes: el EAS siempre comanda el Chiller 01 exactamente 1 °C por encima del Chiller 02, así que sus valores reportados deberían diferir en 1 °C siempre que ambos chillers estén encendidos. Dos veces en 2026 no fue así, y en ambas la telemetría mostraba el problema antes de que alguien lo revisara.

* **4 al 7 de mayo.** El Chiller 02 reportó 0.0 °C a las 18:49 UTC del 4 de mayo y luego nada más; `deviceEnabled` lo muestra apagado desde las 21:29 UTC del 5 de mayo hasta las 21:16 UTC del 7 de mayo. Mientras tanto, el Chiller 01 marcó 6.0, 6.4 y 6.8 °C y, desde las 16:57 UTC del 7 de mayo, 10.0 °C, un valor que el EAS nunca comandó; el EAS no envió ningún comando el 3, 4, 5 y 7 de mayo. El incidente #8, el calentamiento de emergencia de la cámara ([FRACAS-383](https://rubinobs.atlassian.net/browse/FRACAS-383), [FRACAS-384](https://rubinobs.atlassian.net/browse/FRACAS-384)), ocurre a las 13:09 UTC del 7 de mayo: dos días y medio después de que el Chiller 02 quedara en silencio 6 °C por debajo de su compañero. FRACAS-384 sitúa la causa raíz en un filtro tapado del PCS, no en los chillers, pero su discusión señala que el Chiller 02 se perdió "cuando la temperatura estaba demasiado fría" y que la presión de suministro del PCS cayó a 12 psig mientras el circuito funcionaba solo con el Chiller 01. Por lo tanto, la telemetría de los set points no fue la causa, pero mostró durante 40 h que el circuito frío ya no tenía redundancia cuando el filtro terminó de taparse.
* **12 de julio.** Tras el corte de energía de las 11:38 UTC, el Chiller 01 volvió con su comando de 6.1 °C y el Chiller 02 con su valor por defecto de Niagara de −3.7 °C, 8.9 °C por debajo de su comando y 9.8 °C por debajo del Chiller 01. Yousuke Utsumi lo reportó a las 13:04 UTC como "otro caso del problema de Niagara después del corte de energía" ([FRACAS-402](https://rubinobs.atlassian.net/browse/FRACAS-402)); el Chiller 02 se detuvo y reinició tres veces entre las 13:01 y las 13:39 UTC, cuando el set point se devolvió a mano a 5.0 °C. No hubo un incidente de la cámara después, muy probablemente porque reaccionamos antes de que surgieran problemas mayores. La causa raíz del ticket es que Niagara vuelve a sus set points MQTT por defecto después de un corte de energía en lugar de los últimos valores comandados por el CSC del HVAC, y que los valores por defecto del Chiller 01 y del Chiller 03 están intercambiados; corregir esos valores requiere comandos MQTT que el proveedor no ha entregado.

La misma discrepancia el 3 y el 14 de julio (<a href="#figure-1">Figura 1</a>) no fue seguida de una detención, y la detención del Chiller 02 el 13 de julio a las 06:43 UTC no tuvo una anomalía de set point antes, así que esto no es un predictor. Es una condición que debería levantar una alarma, en el espíritu de [OBS-1660](https://rubinobs.atlassian.net/browse/OBS-1660). Dos reglas del Watcher cubrirían ambos casos:

1. **Diferencia entre valores reportados.** Alarma cuando el `chillerConfiguration.activeSetpoint` del Chiller 01 menos el del Chiller 02 no es 1.0 ± 0.2 °C mientras ambos están encendidos, o cuando uno de los dos lleva apagado, o en silencio, más de un tiempo configurable mientras el otro funciona. Es la única regla que se habría activado en mayo, cuando el EAS no estaba enviando comandos.
2. **Valor reportado frente al comando.** Alarma cuando el valor reportado por un chiller difiere del último comando `configChiller` en más de 0.5 °C durante más de 60 s. Esta regla detecta los reinicios con valores por defecto de Niagara del 3 y 12 de julio, que la regla 1 también ve, y las derivas de un solo chiller como la del 14 de julio, que la regla 1 no ve.

## Figura interactiva

La <a href="#figure-2">Figura 2</a> muestra los set points (arriba) y el número de cambios de set point por semana (abajo). Arrastre para desplazarse, use la rueda para hacer zoom en el eje de tiempo, pase el cursor para ver los valores y haga clic en una entrada de la leyenda para ocultar ese chiller. Las líneas grises discontinuas marcan los incidentes de refrigeración catalogados #7 ([FRACAS-366](https://rubinobs.atlassian.net/browse/FRACAS-366), 2026-03-20) y #8 ([FRACAS-383](https://rubinobs.atlassian.net/browse/FRACAS-383), [FRACAS-384](https://rubinobs.atlassian.net/browse/FRACAS-384), 2026-05-07). La ventana se extiende hasta el 20 de julio para cubrir la tormenta de julio ([FRACAS-414](https://rubinobs.atlassian.net/browse/FRACAS-414), [FRACAS-415](https://rubinobs.atlassian.net/browse/FRACAS-415)); ese evento aún no está en [`glycol_catastrophic_faults.csv`](https://github.com/lsst-so/sotn-012/blob/main/notebooks/glycol_catastrophic_faults.csv), por lo que no tiene línea discontinua. El [notebook *Date Range*](https://github.com/lsst-so/sotn-012/blob/main/notebooks/RSO-901%20Glycol%20Set%20Points%20-%20Date%20Range.ipynb) regenera la figura para cualquier rango de `day_obs`.

```{raw} html
<div id="figure-2"></div>
<iframe src="plots/chiller_setpoints_20260101_20260720.html"
        title="Gráfico interactivo de los set points de los chillers del HVAC, enero a julio de 2026"
        style="width: 100%; height: 700px; border: 0;"
        loading="lazy"></iframe>
<p><em>Figura 2. Set points activos de los chillers del HVAC según <code>lsst.sal.HVAC.logevent_chillerConfiguration</code>, 2026-01-01 a 2026-07-20 (UTC).
<a href="plots/chiller_setpoints_20260101_20260720.html">Abrir la figura en pantalla completa.</a></em></p>
```

## Reproducción del análisis

Los notebooks están en la carpeta [`notebooks/`](https://github.com/lsst-so/sotn-012/tree/main/notebooks) de este repositorio y deben ejecutarse en el RSP (consultan el EFD):

* [`RSO-901 Glycol Set Points - Date Range.ipynb`](https://github.com/lsst-so/sotn-012/blob/main/notebooks/RSO-901%20Glycol%20Set%20Points%20-%20Date%20Range.ipynb) construye la tabla de cambios, la superposición de incidentes y la <a href="#figure-2">Figura 2</a> (mediante [`setpoint_plots.py`](https://github.com/lsst-so/sotn-012/blob/main/notebooks/setpoint_plots.py)).
* [`RSO-901 Glycol Set Points - Command Response.ipynb`](https://github.com/lsst-so/sotn-012/blob/main/notebooks/RSO-901%20Glycol%20Set%20Points%20-%20Command%20Response.ipynb) compara cada comando `configChiller` del EAS con el valor reportado por el chiller y construye la <a href="#figure-1">Figura 1</a> (también mediante [`setpoint_plots.py`](https://github.com/lsst-so/sotn-012/blob/main/notebooks/setpoint_plots.py)).
* [`RSO-901 Glycol Set Points - Monthly.ipynb`](https://github.com/lsst-so/sotn-012/blob/main/notebooks/RSO-901%20Glycol%20Set%20Points%20-%20Monthly.ipynb) y [`RSO-901 Glycol Set Points - Single Day.ipynb`](https://github.com/lsst-so/sotn-012/blob/main/notebooks/RSO-901%20Glycol%20Set%20Points%20-%20Single%20Day.ipynb) muestran el mismo evento durante un mes o una noche.
* [`ai_notes.md`](https://github.com/lsst-so/sotn-012/blob/main/notebooks/ai_notes.md) revisa los tópicos del HVAC y explica cómo interpretar `chillerConfiguration`.

Se guardan sin salidas (lo impone `nbstripout` en [`.pre-commit-config.yaml`](https://github.com/lsst-so/sotn-012/blob/main/.pre-commit-config.yaml)), así que hay que ejecutarlos en una sesión de JupyterLab en el RSP con el kernel `LSST` para reproducir los números de arriba. Para mover la ventana, cambie `start_day_obs` / `end_day_obs` en la celda de parámetros del [notebook *Date Range*](https://github.com/lsst-so/sotn-012/blob/main/notebooks/RSO-901%20Glycol%20Set%20Points%20-%20Date%20Range.ipynb) y vuelva a ejecutarlo; escribe `../_extra/plots/chiller_setpoints_<start>_<end>.html`, que Sphinx copia al sitio, así que la ruta del `<iframe>` en este archivo debe actualizarse con el nuevo nombre de archivo.

## Referencias existentes

La lista siguiente es una recopilación extensa de tickets y páginas de Confluence relacionados con los sistemas de glicol, generada con Claude.ai. Los tickets FRACAS están filtrados para incluir solo los que ocurrieron con la LSSTCam instalada en el Telescopio Simonyi. Los títulos de tickets y páginas se mantienen en su idioma original.

### Tickets FRACAS principales

* [FRACAS-430](https://rubinobs.atlassian.net/browse/FRACAS-430) Glycol System Failures  
Épica creada en agosto de 2026 para agrupar los reportes de fallas por cortes del glicol.  
Junto con FRACAS-435, es lo más cercano a un catálogo de eventos curado.
* [FRACAS-435](https://rubinobs.atlassian.net/browse/FRACAS-435) PCS Chiller Issues  
Épica que agrupa los reportes de fallas del chiller del Pumped Coolant System (PCS) de la LSSTCam
* [FRACAS-277](https://rubinobs.atlassian.net/browse/FRACAS-277) Glycol Chiller #2: Failure to Restart after Switching to Generator Power
El 2025-04-05, el Chiller #2 no se reinició automáticamente tras el cambio a energía del generador. Se perdió el glicol hacia el sistema Cryo de la cámara y el chiller del PCS durante unos 30 minutos.
* [FRACAS-279](https://rubinobs.atlassian.net/browse/FRACAS-279) Glycol Chiller #3 -- Short Flow Interruption on April 29, 2025
Una interrupción de flujo de un segundo hacia el chiller del PCS, coincidente con un pico de voltaje del generador (complemento de FRACAS-278). El hilo registra que las cargas de los Niveles 2 y 4 le quitaban flujo al Nivel 7, que estrangular el Nivel 2 duplicó el flujo en el Nivel 7, y qué consumidores alimenta el Chiller 3.
* [FRACAS-280](https://rubinobs.atlassian.net/browse/FRACAS-280) LSSTCam -- Loss of Cooling Capacity
El 2025-05-05, entre las 03:00 y las 04:00 UTC aproximadamente y observando en cielo, la temperatura de la placa criogénica de la LSSTCam empezó a desviarse de −127 °C.
* [FRACAS-282](https://rubinobs.atlassian.net/browse/FRACAS-282) Glycol Chiller #3: Flow lost at 16:26 May 21, 2025 (UTC) after a Power Glitch
Pérdida de flujo de glicol tras una falla breve de energía, seguida de la recuperación de la cámara de la falla resultante.
* [FRACAS-310](https://rubinobs.atlassian.net/browse/FRACAS-310) Glycol System -- Degradation Affected the Dynalene Chiller #1 Normal Operational Capability
Octubre de 2025. Las temperaturas del troncal de servicios y del Dynalene subieron al salir a observar. Reiniciar el chiller01 produjo solo una meseta de temperatura de corta duración.
* [FRACAS-314](https://rubinobs.atlassian.net/browse/FRACAS-314) Commercial Power -- Loss affecting Dynalene, PCS, and Cryo #6 Cooling Systems
Noviembre de 2025. Un corte breve de energía apagó el PCS, el Cryo 6 y el Dynalene al mismo tiempo.
* [FRACAS-321](https://rubinobs.atlassian.net/browse/FRACAS-321) Dynalene -- Flow Lost After Returning to Commercial Power
Noviembre de 2025. Tras 20 a 30 segundos sin energía, el flujo de glicol se recuperó pero el Dynalene no respondió a los procedimientos habituales. Restablecer el flujo de Dynalene requirió un ciclo completo de energía del Chiller 2.
* [FRACAS-322](https://rubinobs.atlassian.net/browse/FRACAS-322) Glycol -- (cold) temperature was wrongly set by EAS after the OS update of 18th Nov 2025
Tras una actualización del sistema operativo y de Kubernetes, el Environmental Awareness System (EAS) fijó el glicol frío demasiado cálido (17 °C) y se perdió el Cryo 6. El ticket señala que, por diseño, el glicol frío (Chillers 1 y 2) tiene un set point flotante y el glicol de confort (Chiller 3) uno fijo.
* [FRACAS-336](https://rubinobs.atlassian.net/browse/FRACAS-336) Dynalene System Failure -- cRIO Controller Rebooting due to Dynalene Leaking on a Sensor
Enero de 2026. El sistema Dynalene dejó de enfriar la LSSTCam durante varias horas después de que una fuga sobre un sensor hiciera reiniciar su controlador.
* [FRACAS-344](https://rubinobs.atlassian.net/browse/FRACAS-344) Glycol Controlling - VM Rebooting
Febrero de 2026. La máquina virtual de control del glicol se reinició y dejó fuera de línea todos los chillers de glicol. OBS-1606 documenta la telemetría obsoleta publicada durante este evento.
* [FRACAS-352](https://rubinobs.atlassian.net/browse/FRACAS-352) LSSTCam PCS Chiller -- Flow Variations during a Power Cut and when Connected to the Glycol Chiller #3
Febrero de 2026. La recirculación automática en los Chillers 1 y 2 protegió el Dynalene y los compresores Cryo durante un corte de energía. El Chiller 3 tardó unos 75 s en recuperarse, lo que perturbó el chiller del PCS y la placa fría de la cámara.
* [FRACAS-364](https://rubinobs.atlassian.net/browse/FRACAS-364) LSSTCam PCS Chiller -- Flow Variations when Connecting to the Glycol Chiller #1 and #2
Marzo de 2026. El chiller del PCS recibió menos flujo de glicol después de conectarse a los Chillers 1 y 2.
* [FRACAS-366](https://rubinobs.atlassian.net/browse/FRACAS-366) LSSTCam PCS Chiller -- E2 Compressor 1 Failure
2026-03-20 a las 03:44 UTC. Una alarma de falla de compresor fue seguida de alarmas de bajo flujo. Las temperaturas de la placa fría, la placa criogénica y la entrada y salida del PCS subieron rápidamente, mientras que las temperaturas generales del glicol bajaron de unos 18 a 4 °C.
* [FRACAS-371](https://rubinobs.atlassian.net/browse/FRACAS-371) HVAC Server Restart left the Glycol Chillers off
Abril de 2026. Un reinicio del servidor del HVAC durante actualizaciones del sistema operativo dejó apagados los Chillers 2, 3 y 4, sin telemetría en Chronograf durante la actualización. Quien lo reportó cree que ocurrió dos veces.
* [FRACAS-384](https://rubinobs.atlassian.net/browse/FRACAS-384) Low Glycol Flow in Camera Cooling System -- due to a PCS Clogged Filter
Mayo de 2026. Un filtro tapado del PCS redujo el flujo de glicol hacia el sistema de refrigeración de la cámara durante unos dos días antes del reporte. Reemplaza a FRACAS-383; aún se requieren la solución permanente y la causa raíz.
* [FRACAS-387](https://rubinobs.atlassian.net/browse/FRACAS-387) Glycol Chiller 2 -- Failing at High Output
El Chiller 2 se detuvo repetidamente poco después de llegar al 100% de potencia, incluso con una rampa más lenta y un tope de 75%, y se puso en bypass a la espera de mantenimiento. RSO-580 da seguimiento al cambio de set point del EAS en el momento de la detención.
* [FRACAS-402](https://rubinobs.atlassian.net/browse/FRACAS-402) Investigate Glycol temperature set point reset after power outage
Después de varios cortes, los Chillers 1 y 2 volvieron con set points incorrectos. El ticket investiga por qué el sistema Niagara no guarda ni aplica los valores comandados por el CSC del HVAC.
* [FRACAS-414](https://rubinobs.atlassian.net/browse/FRACAS-414) Storm, Jul 2026 -- Summit Glycol System went off after the Generator Power became Unstable
Tormenta de julio de 2026. Los chillers de glicol se apagaron cuando el generador principal dejó de entregar un suministro estable de 480 V.
* [FRACAS-415](https://rubinobs.atlassian.net/browse/FRACAS-415) Storm, Jul 2026 -- Summit Dynalene System Went off after Losing the Glycol Coolant Supply
Mismo evento. El Dynalene se apagó después de que los chillers de glicol y su sistema de recirculación dejaran de suministrar refrigerante, un ejemplo claro de la cascada del glicol al Dynalene.

### Tickets RSO relacionados

* [RSO-899](https://rubinobs.atlassian.net/browse/RSO-899) Glycol issue systematic analysis
Épica para analizar la telemetría de flujo y temperatura del glicol de 2026 y buscar patrones que precedan la pérdida de flujo tras fallas breves de energía y cambios de set point.
* [RSO-900](https://rubinobs.atlassian.net/browse/RSO-900) Analyse the glycol flow for the year of 2026
Busca pérdidas de flujo o cambios grandes de flujo durante 2026 y su relación con fallas breves de energía.
* [RSO-901](https://rubinobs.atlassian.net/browse/RSO-901) Analyse the glycol temperature set points for the year of 2026
Busca cambios bruscos de set point durante 2026 y su relación con pérdidas de Niagara o detenciones del sistema de glicol.
* [RSO-909](https://rubinobs.atlassian.net/browse/RSO-909) Analyze the input pressure and output pressures in each of the glycol chillers ~2h before each major fault
Análisis de precursores centrado en la presión de cada chiller de glicol.
* [RSO-580](https://rubinobs.atlassian.net/browse/RSO-580) Investigate how the EAS controlled the Glycol Chiller at the time of the failure
Acción derivada de FRACAS-387: el Chiller 2 se detuvo el mismo día en que el EAS cambió su set point.
* [RSO-635](https://rubinobs.atlassian.net/browse/RSO-635) Taxonomy - Facilities Refrigeration System
Taxonomía de los sistemas de refrigeración. La parte del Dynalene está lista y la del glicol está pendiente.
* [RSO-887](https://rubinobs.atlassian.net/browse/RSO-887) Documentation for Glycol issues troubleshooting and monitoring
Planifica nuevos procedimientos de emergencia y monitoreo que cubren el monitoreo en Grafana, la recuperación de chillers por los especialistas de observación y la recuperación de Niagara.
* [RSO-557](https://rubinobs.atlassian.net/browse/RSO-557) LSSTCam Cryogenic, Dynalene, and Glycol System Inter-dependence
Página de Docushare propuesta que describe cómo los sistemas criogénicos de la LSSTCam dependen de los sistemas de Dynalene y glicol.
* [RSO-907](https://rubinobs.atlassian.net/browse/RSO-907) Update diagram in the Glycol documentation page
Enumera las correcciones necesarias en el diagrama de arquitectura, como los gabinetes térmicos de la TMA, si el Chiller 4 alimenta la sala de control y las oficinas, y la válvula del Chiller 3 hacia los CRAC del Nivel 2.

### Tickets OBS relacionados

* [OBS-830](https://rubinobs.atlassian.net/browse/OBS-830) HVAC subsystems report zeros (or fixed values) when component is disconnected
El CSC del HVAC publica ceros o valores congelados como telemetría real cuando pierde la conexión. Esto es relevante al filtrar datos para una línea base nominal.
* [OBS-930](https://rubinobs.atlassian.net/browse/OBS-930) Uncommanded Chiller / HVAC setpoint changes
Mayo de 2025. El set point del HVAC de la cúpula y el set point del Chiller #4 cambiaron sin ser comandados.
* [OBS-1225](https://rubinobs.atlassian.net/browse/OBS-1225) Glycol Chiller Telemetry Lost and HVAC not commandable
Se perdió toda la telemetría de los chillers de glicol durante unos 30 minutos mientras los chillers seguían funcionando. La causa se atribuyó al cableado y a la comunicación con el controlador Niagara.
* [OBS-1606](https://rubinobs.atlassian.net/browse/OBS-1606) HVAC CSC publishes stale data, investigate how to fix telemetry being published
Telemetría antigua se volvió a publicar como si fuera actual durante FRACAS-344. El ticket propone agregar una marca de tiempo de la medición.
* [OBS-1649](https://rubinobs.atlassian.net/browse/OBS-1649) Watcher alarms for dynalene chillers
Solicita alarmas del Watcher para el Dynalene, de modo que los observadores reciban aviso antes de las alertas de la cámara, o en paralelo con ellas.
* [OBS-1660](https://rubinobs.atlassian.net/browse/OBS-1660) Review/add additional watcher alarms for chillers
El Chiller 2 quedó apagado tras una falla breve en marzo de 2026 sin ninguna alarma durante más de una hora. El límite de la alarma de flujo probablemente estaba demasiado bajo, y solo algunos de los campos del Watcher estaban completos.

### Páginas de Confluence

#### Descripción del sistema

* [Glycol/Dynalene Flow Path and Cooling System Architecture](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/1065943153)
Descripción piso por piso del sistema de refrigeración, desde la planta de chillers del Nivel 1 hasta el chiller del PCS y los circuitos Cryo en el Pier 7, incluyendo el equipamiento instalado, el reinicio de alarmas, la ruta de control y telemetría del Dynalene, y los dashboards. Todavía es un borrador, y su diagrama se está corrigiendo en RSO-907.
* [Introduction to Chillers](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/949944397)
Panorama de los nueve chillers del sitio vinculados al sistema de refrigeración y al Oil Supply System: los chillers de glicol en el Nivel 1, los chillers de Dynalene en el Nivel 5 y el chiller del PCS en el Nivel 7.
* [Environmental Awareness System Overview](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/465240158)
Describe cómo el EAS fija los set points del glicol a partir de sensores de ambiente o de un pronóstico, para mantener la cúpula isoterma y seguir la temperatura exterior. Indica que el EAS mantiene el refrigerante entre 5 y 10 °C por debajo del ambiente interior durante la noche.
* [Dynalene System](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/228392976)
Introducción al sistema Dynalene tal como se usa en operaciones, con una nota de que una detención del flujo requiere una respuesta coordinada en unos 30 minutos.
* [Camera PCS Chiller [chiller2] and the Coldplate](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/1300332685)
Explica cómo el PCS enfría la placa fría de la cámara a unos −40 °C mediante líneas aisladas al vacío desde el gabinete del chiller en el Nivel 7.
* [Plan/Proposal for switching cryo compressors to cold (tracking) Glycol on level 7](https://rubinobs.atlassian.net/wiki/spaces/CAM/pages/1723957276)
Describe el circuito de agua fría de los módulos criogénicos de la LSSTCam y sus necesidades de flujo y temperatura, y propone pasar los compresores al circuito de glicol frío con seguimiento.

#### Monitoreo y respuesta

* [Glycol Cooling System Monitoring and Response Guide](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/847446349)
Guía principal para operadores: dashboards a vigilar, condiciones de diseño (40% de etilenglicol, 12.7 barg, entrada 5 °C bajo el ambiente, tolerancias de temperatura), umbrales de flujo de unos 1.5 gpm para preocupación y bajo 1 gpm para emergencia, y la nota de que el PCS normalmente sobrevive cortes de glicol de menos de unos 90 s.
* [Monitoring and Response Procedures for Dynalene Chillers and Glycol Flow Rate](https://rubinobs.atlassian.net/wiki/spaces/~pvenegas/pages/1805778961)
Monitoreo tipo lista de verificación para los chillers de Dynalene, incluyendo umbrales de flujo de alimentación de glicol sobre unos 55 LPM por chiller y dónde revisarlos en la interfaz del Dynalene y en Chronograf.
* [Power Outage - Dynalene Monitoring](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/1211662339)
Qué monitorear durante un corte de energía, con referencia al dashboard que cubre los chillers de Dynalene del Nivel 5 y los chillers de glicol del Nivel 1.
* [Glycol, Dynalene, PCS, Cryo or Power Failure](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/763232393)
Respuesta de emergencia ante fallas del glicol, del Dynalene, del chiller del PCS, del Cryo y cortes totales de energía, comenzando por llamar a Facilities y al equipo de la Cámara. Borrador que requiere capacitación.
* [PCS Chiller Troubleshooting Guide](https://rubinobs.atlassian.net/wiki/spaces/~712020071056b447a84bfe9d0fd25503c7b3a2/pages/2003435560)
Referencia para diagnosticar cortes del chiller del PCS y su disposición para reiniciar, centrada en distinguir una falla real del chiller de una detención por protección o una condición ambiental. En edición activa (RSO-896).

#### Análisis, incidentes y mantenimiento

* [Glycol Flow Telemetry Issue Identification Framework](https://rubinobs.atlassian.net/wiki/spaces/~pvenegas/pages/2031419439)
Borrador para RSO-900. Agrupa los problemas del glicol de 2026 en tres clases (cortes reales de flujo, cortes de telemetría que imitan pérdida de flujo y anomalías de set point) e inicia un registro de eventos. Señala que no hay un rango normal de flujo documentado para los circuitos de los chillers.
* [20260320 PCS Failure](https://rubinobs.atlassian.net/wiki/spaces/~fanning/pages/1540456464)
Informe del incidente de FRACAS-366, con la secuencia de alertas generadas por el chiller del PCS.
* [GP and Cold Glycol filters checkout log](https://rubinobs.atlassian.net/wiki/spaces/LTS/pages/50086177)
Registro de revisiones, limpiezas y estado de los filtros en los circuitos de glicol de uso general y de glicol frío. Útil para relacionar eventos de obstrucción como FRACAS-384 con el historial de mantenimiento.
* [10 Dynalene main filters/strainer checkout log](https://rubinobs.atlassian.net/wiki/spaces/LTS/pages/50086350)
El mismo tipo de registro para los circuitos de Dynalene.
* [Organizing glycol & dynalene contents for OS](https://rubinobs.atlassian.net/wiki/spaces/~jseron/pages/1067581452)
Estructura tentativa para la documentación de los especialistas de observación sobre glicol y Dynalene. Conviene revisarla para que la technote no se superponga con ella.

### Otras referencias

* [Fluid Distribution System (092-308-F-M-01000)](https://docushare.lsst.org/docushare/dsweb/Get/Document-45445/092-308-F-M-01000-Ed002.pdf)
Documento de diseño en Docushare del sistema de distribución de fluidos.
* [LSST Camera Value Engineering / Alternative Analyses Collection (LCA-399)](https://docushare.lsst.org/docushare/dsweb/Get/LCA-399/LSST%20Camera%20Value%20engineering-Alternative%20Analyses%20Collection--LCA-399.pdf)
Estudios de alternativas de la cámara citados desde la guía de monitoreo.
* [Facilities Temperatures Reports (Times Square)](https://usdf-rsp.slac.stanford.edu/times-square/github/lsst-sitcom/reports-performance-summary/sst/nights/facilities_temperatures_reports)
