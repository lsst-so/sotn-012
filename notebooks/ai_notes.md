# RSO-901 Analyse the glycol temperature set points for the year of 2026

We want to check the telemetry of the glycol temperature set points for the whole year of 2026 and 
see if there are major fluctuations (sudden changes in the glycol set point temperature) over time. 
We also want to check all the times we had glycol set point temperature problems connected to the loss of Niagra or the glycol system stopping. 
Is there a pattern we can see? 

The easiest way is to take a look at the flowmeters that we have on the Crio and the PCS cabinets. 
The Crio cabinet has input and output temperatures and the PCS has at least the input temperature.

## Analysis cadence

We run the analysis one `day_obs` at a time. `day_obs` is an integer like `20260119` and
covers a single observing night. Following the standard Rubin convention, the observatory day rolls
over at **UTC−12**: the window **starts at 12:00 UTC** on `day_obs` and **ends at 11:59:59 UTC the next
day** (09:00/08:00 Chilean local, depending on DST), so a full night is never split across two `day_obs`.

In notebooks, don't hand-roll the timezone math — use the helpers, which already encode the noon
boundary and return UTC `astropy.time.Time` objects for EFD queries:

```python
from lsst.summit.utils.dateTime import getDayObsStartTime, getDayObsEndTime
from lsst.summit.utils.efdUtils import getEfdData, makeEfdClient

efd_client = makeEfdClient()
day_obs = 20260119
begin = getDayObsStartTime(day_obs)   # 12:00 UTC on day_obs
end   = getDayObsEndTime(day_obs)     # 11:59:59 UTC the next day

df = getEfdData(efd_client, "lsst.sal.HVAC.glycolSensor", begin=begin, end=end)
```

To scan the whole of 2026, loop over `day_obs` from `20260101` to `20261231` and either cache one CSV
per day or concatenate into a yearly frame (cache to `consdb_*`-style CSVs so the notebook re-runs offline).

## Candidate SAL topics (ts-xml)

All the glycol data is published by the **`HVAC`** CSC (`lsst.sal.HVAC.*`). Source of truth:
`ts_xml` → `sal_interfaces/HVAC/HVAC_{Telemetry,Events,Commands}.xml`, rendered at
<https://ts-xml.lsst.io/sal_interfaces/HVAC.html>. Units below: temperature `deg_C`, pressure `Pa`,
flow `l/min`. `Crio`/`PCS` are local cabinet nicknames and do **not** appear literally in the XML — the
matching data is in the loops listed below (chiller/OSS/TMA supply+return sensors).

> **Pick the topics you want to keep** by checking the boxes.

### Telemetry — measured temperatures / flows (the flowmeters)

- [ ] **`lsst.sal.HVAC.glycolSensor`** — *primary flowmeter topic.* For each cooling loop it carries
      `supplyTemp*` / `retTemp*` (input/output temperature), `supplyPress*` / `retPress*`, and
      `supplyFlow*`. Loops include: `Chiller01/02/03`, `Slac`, `Oss`, `Floor2` (+`comfort*Floor02`),
      `WhiteRoom`, `CleanRoom`, `AhuLower1..4`, and flow-only `supplyFlowTma / supplyFlowAhus / supplyFlowComfort`.
      This is where the "input and output temperatures + flowmeter" for the cabinets lives.
- [ ] **`lsst.sal.HVAC.chiller01P01`** (and `chiller02P01`, `chiller03P01`, `chiller04P01`) — per-chiller:
      `activeSetpoint` (the **actual set point being tracked** — key for the fluctuation question),
      `waterEvaporatorSupplyTemp` / `waterEvaporatorReturnTemp`, `availableChillerCapacity`,
      `workingCapacity`, `operationalMode`, `unitState`, `switchedOn`, `compressorNNWorking`,
      `compressorNNAlarm`, `generalAlarm`. Best signal for "glycol system stopping" (unit state /
      switchedOn / alarms) and for tracking set-point changes over time.
- [ ] **`lsst.sal.HVAC.dynaleneP05`** — Dynalene glycol loop (TMA & Test Area manifolds): supply/return
      temperature, pressure, flow (`dynTMAsupTS01`, `dynTMAretTS02`, `dynTMAsupFS03`, …), per-chiller
      glycol channel temps/flows (`dynCH01supCGLYtemp`, `dynCH01retCGLYtemp`, `dynCH1supCGLYflow`, …),
      tank levels (`dynCH01LS01`, `dynCH02LS02`) and thermal power dissipation (`*tpd`, kW).
- [ ] **`lsst.sal.HVAC.coldWaterPump01`** — pump `workingState` / `switchedOn` (glycol circulation on/off).
- [ ] **`lsst.sal.HVAC.valveP01`** — mixing-valve states (`valve03..12State`).
- [ ] **`lsst.sal.HVAC.generalP01`** — building `ambientTemperature` (context / correlation).

### Events — set points & incidents

- [ ] **`lsst.sal.HVAC.logevent_chiller01P01`** (…`02P01`, `03P01`, `04P01`) — chiller state changes,
      emitted only on change → clean timeline of when a chiller went on/off or alarmed.
- [x] **`lsst.sal.HVAC.logevent_chillerConfiguration`** — `activeSetpoint` (deg_C): fires when the
      commanded chiller set point is (re)configured → directly answers "sudden changes in the set point".
      **← chosen for the first pass (see "Working with `chillerConfiguration`" below).**
- [ ] **`lsst.sal.HVAC.logevent_chillerValveConfiguration`** — chiller-valve configuration changes.
- [ ] **`lsst.sal.HVAC.logevent_dynaleneTankLevelAlarm`** — low-tank / fault events (candidate for the
      "loss of Niagara / glycol system stopping" incidents).

### Commands — for reference (who/when a set point was requested)

- [ ] `lsst.sal.HVAC.command_configChiller` — sets a chiller's active set point (deg_C).
- [ ] `lsst.sal.HVAC.command_dynTmaRemoteSP` / `dynTaRemoteSP` / `dynExtAirRemoteSP` — Dynalene TMA / Test
      Area / exit-air set points (deg_C).
- [ ] `lsst.sal.HVAC.command_dynCH1PressRemoteSP` / `dynCH2PressRemoteSP` — Dynalene chiller pressure set points (Pa).

### Notes on the "Niagara" / stoppage correlation

"Niagara" is the facility building-management system and is **not** a SAL CSC, so there is no
`lsst.sal.Niagara.*` topic. To detect glycol stoppages from EFD alone, look for `unitState` /
`switchedOn` transitions and `generalAlarm` in the `chillerNNP01` telemetry/events, `coldWaterPump01`
going off, and flow dropping to ~0 in `glycolSensor` / `dynaleneP05`. Cross-reference the timestamps
against the OBS/RSO fault logs for the Niagara/glycol incidents.

## Working with `chillerConfiguration`

The event is intentionally small — two payload fields plus the standard SAL metadata. Each row means
*"at time T, chiller N's set point is X °C"*; there is no old/new pair, so a change is recovered by
comparing consecutive rows **per chiller**.

| Field | Meaning |
|---|---|
| `device_id` | Which chiller — the `DeviceId_chiller` enum (see mapping below). |
| `activeSetpoint` | The configured glycol set point, in `deg_C` — the quantity the ticket cares about. |
| `private_sndStamp` (→ DataFrame index) | **When** the (re)configuration was published; this is the x-axis. |

`device_id` → chiller mapping (`lsst.ts.xml.enums.HVAC.DeviceId_chiller`):

| `device_id` | chiller |
|---|---|
| 101 | `chiller01P01` |
| 102 | `chiller02P01` |
| 103 | `chiller03P01` |
| 104 | `chiller04P01` |

### Display: step plot + change-log table

A set point is piecewise-constant (it holds until the next reconfiguration), so plot it as a **step
function**, one series per chiller, never linearly interpolated:

```python
df = getEfdData(efd_client, "lsst.sal.HVAC.logevent_chillerConfiguration",
                begin=begin, end=end)

names = {101: "chiller01", 102: "chiller02", 103: "chiller03", 104: "chiller04"}

fig, ax = plt.subplots()
for dev, g in df.groupby("device_id"):
    g = g.sort_index()
    ax.step(g.index, g["activeSetpoint"], where="post", label=names.get(dev, dev))
ax.set_ylabel("Active set point [°C]")
ax.legend()
```

Because the ticket asks about *fluctuations / sudden changes*, pair the plot with a **change-log table**
— keep only rows where the value actually moved (per chiller). This also drops redundant
re-publications (e.g. after a CSC restart the current config is re-emitted unchanged):

```python
changes = (df.sort_index()
             .groupby("device_id")["activeSetpoint"]
             .apply(lambda s: s[s.diff().ne(0)])   # first row + genuine changes only
             .reset_index())
# add another .diff() on activeSetpoint for the ΔT (°C) of each jump
```

### Gotchas

- **Events are sparse** — a row is written only when config is published, so the whole year is cheap
  to query in one shot. The per-`day_obs` loop is only needed for the *dense* flow/temperature
  telemetry (`glycolSensor`, `dynaleneP05`), not for this event.
- **De-dup by value, not by timestamp** — the step plot tolerates repeated equal points, but the change
  table must use the `diff().ne(0)` filter so restarts / heartbeat re-publishes don't masquerade as
  real fluctuations.

