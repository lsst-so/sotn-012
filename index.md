# Nominal Behavior and Failure Signatures of the Glycol Refrigeration Systems

```{abstract}
The Vera C. Rubin Observatory relies on a network of glycol refrigeration systems to cool the telescope, the LSST Camera (LSSTCam), the M1M3 mirror, and facility spaces. Since first light, failures in these systems have repeatedly interrupted night operations. Existing documentation covers the architecture, response procedures, and individual failure reports, but no document defines nominal behavior in telemetry, which makes it hard to distinguish a developing failure from routine variation. In this technical note, we characterize the nominal operating envelope of each glycol loop using Engineering and Facility Database (EFD) telemetry, then compare the telemetry preceding catalogued failure events against that envelope to identify failure signatures and possible precursors. The result is intended as a common baseline for defining alarm thresholds.
```

# RSO-901 Glycol Set Point Analysis

[RSO-901](https://rubinobs.atlassian.net/browse/RSO-901) asks whether the glycol chiller set points changed suddenly during 2026, and whether those changes line up with the catalogued glycol failures. We read every `lsst.sal.HVAC.logevent_chillerConfiguration` event, which publishes a chiller's `activeSetpoint` each time it is (re)configured, and plotted the set points against the incidents in `notebooks/glycol_catastrophic_faults.csv`.

We found **no set-point signature that consistently precedes a failure**. The main result is that frequent set-point changes on Chillers 01 and 02 are expected. The Environmental Awareness System (EAS) commands them automatically and moves them whenever the glycol-to-ambient temperature difference leaves a configured band. A set-point change on those two chillers is therefore routine, not an anomaly by itself.

## What drives the set points

The EAS CSC ([`ts_eas`](https://github.com/lsst-ts/ts_eas)) sends `HVAC.configChiller` to exactly two chillers ([`N_CHILLERS = 2`](https://github.com/lsst-ts/ts_eas/blob/df201f886e74f07d61069ba0ce0d8199fb877849/python/lsst/ts/eas/hvac_model.py#L44)): `coldGlycolChiller01` (device 101) and `coldGlycolChiller02` (device 102). It never commands `comfortGlycolChiller03` (103) or `coatingGlycolChiller04` (104) ([`DeviceId` enum](https://github.com/lsst-ts/ts_xml/blob/853318b5ca33cfa23150c20a3400156e6a946ae4/python/lsst/ts/xml/enums/HVAC.py#L41-L44)). Two loops in `HvacModel` set the values:

1. **Once a day, at noon** ([`adjust_glycol_chillers_at_noon`](https://github.com/lsst-ts/ts_eas/blob/df201f886e74f07d61069ba0ce0d8199fb877849/python/lsst/ts/eas/hvac_model.py#L706-L745)), EAS computes new set points from the previous night's minimum indoor temperature, read from the indoor ESS (SAL index 113).
2. **Every 60 s** ([`monitor_glycol_chillers`](https://github.com/lsst-ts/ts_eas/blob/df201f886e74f07d61069ba0ce0d8199fb877849/python/lsst/ts/eas/hvac_model.py#L650-L704)), EAS checks the difference between the average of the two set points and the *current* indoor temperature ([`check_glycol_setpoint`](https://github.com/lsst-ts/ts_eas/blob/df201f886e74f07d61069ba0ce0d8199fb877849/python/lsst/ts/eas/hvac_model.py#L625-L648)). If that difference falls outside `[glycol_band_low, glycol_band_high]`, EAS recomputes both set points from the current indoor temperature and sends them.

In both cases [`compute_glycol_setpoints`](https://github.com/lsst-ts/ts_eas/blob/df201f886e74f07d61069ba0ce0d8199fb877849/python/lsst/ts/eas/hvac_model.py#L558-L623) targets an average of `ambient + glycol_average_offset`. It raises that target if needed to stay above the night's maximum indoor dew point plus a margin, then splits it into two set points `glycol_setpoints_delta` apart, with Chiller 01 the warmer one. The result is clamped to the absolute minimum and maximum. The summit values ([`ts_config_ocs` `EAS/v9/_init.yaml`](https://github.com/lsst-ts/ts_config_ocs/blob/8c215dac5d45fc766953adec2c27bc4fe3451151/EAS/v9/_init.yaml#L12-L18)) are:

| Parameter | Value | Meaning |
|---|---|---|
| `glycol_average_offset` | −7.5 °C | Nominal average set point relative to indoor ambient |
| `glycol_band_low` / `glycol_band_high` | −10.0 / −5.0 °C | Allowed (average set point − ambient) before a recompute |
| `glycol_setpoints_delta` | 1.0 °C | Chiller 01 − Chiller 02 |
| `glycol_dew_point_margin` | 1.0 °C | Margin above the nightly maximum indoor dew point |
| `glycol_absolute_minimum` / `_maximum` | −10.0 / 10.0 °C | Clamps on the colder / warmer set point |

Only the absolute maximum changed in 2026: it was 9 °C until 2026-02-23, then 20 °C until 2026-04-11, then 10 °C. Until `ts_eas` v0.15.0, EAS stopped adjusting the glycol at night. [OSW-2128](https://rubinobs.atlassian.net/browse/OSW-2128) ([ts_eas#79](https://github.com/lsst-ts/ts_eas/pull/79), merged 2026-04-08, released 2026-05-06) removed that exception, so the band check now runs around the clock. [RSO-580](https://rubinobs.atlassian.net/browse/RSO-580) follows up on the related FRACAS-387 case, where Chiller 2 tripped on the day EAS changed its set point.

## Expected behavior per chiller

The telemetry matches the code (1 January to 31 May 2026, 151 `day_obs`):

* **Chillers 01 and 02 (cold glycol, EAS-controlled): many updates.** They changed set point 326 and 339 times, on 144 and 147 of the 151 days. The median step was 1.0 °C. In 109 of 119 near-simultaneous updates, Chiller 01 was exactly 1.0 °C warmer than Chiller 02, which is the configured `glycol_setpoints_delta`. The changes cluster at two fixed local times, and both clusters shift by one hour in UTC at the 5 April DST change. One is local noon (15 UTC, then 16 UTC), the daily reset. The other is about 07:00 local, around sunrise (10 UTC, then 11 UTC). The remaining changes are spread through the day, as expected from band-triggered recomputes.
* **Chiller 03 (comfort glycol, not EAS-controlled): few updates.** It changed 101 times, but on only 24 days. Almost all of those changes are short bursts that toggle between 0 °C and 2 °C within seconds to minutes. Because EAS does not command this chiller, these changes come from outside EAS (e.g. manual changes or the facility controls).
* **Chiller 04 (coating glycol): no telemetry.** `logevent_chillerConfiguration` has no events for device 104 in the analysed range.

## Interactive figure

Figure 1 shows the set points (top) and the number of set-point changes per week (bottom). Drag to pan, scroll to zoom the time axis, hover for values, and click a legend entry to hide that chiller. Dashed gray lines mark catalogued cooling incidents #7 ([FRACAS-366](https://rubinobs.atlassian.net/browse/FRACAS-366), 2026-03-20) and #8 ([FRACAS-383](https://rubinobs.atlassian.net/browse/FRACAS-383), [FRACAS-384](https://rubinobs.atlassian.net/browse/FRACAS-384), 2026-05-07). The figure currently covers January to May 2026. The *Date Range* notebook regenerates it for any `day_obs` range.

```{raw} html
<iframe src="plots/chiller_setpoints_20260101_20260531.html"
        title="Interactive plot of HVAC chiller set points, January to May 2026"
        style="width: 100%; height: 700px; border: 0;"
        loading="lazy"></iframe>
<p><em>Figure 1. HVAC chiller active set points from <code>lsst.sal.HVAC.logevent_chillerConfiguration</code>, 2026-01-01 to 2026-05-31 (UTC).
<a href="plots/chiller_setpoints_20260101_20260531.html">Open the figure full screen.</a></em></p>
```

## Reproducing the analysis

The notebooks are in the [`notebooks/`](https://github.com/lsst-so/sotn-012/tree/main/notebooks) folder of this repository and must run on the RSP (they query the EFD):

* `RSO-901 Glycol Set Points - Date Range.ipynb` builds the change-log table, the incident overlay and Figure 1 (via `setpoint_plots.py`).
* `RSO-901 Glycol Set Points - Monthly.ipynb` and `RSO-901 Glycol Set Points - Single Day.ipynb` show the same event over one month or one night.
* `ai_notes.md` surveys the HVAC topics and explains how to interpret `chillerConfiguration`.

# Existing References

The list below is an extensive compilation of tickets and Confluence pages related to the Glycol Systems generated using Claude.ai. The FRACAS tickets are filtered to contain only tickets with the LSSTCam installed on Simonyi Telescope.

## Main FRACAS Tickets

* [FRACAS-430](https://rubinobs.atlassian.net/browse/FRACAS-430) Glycol System Failures  
Epic created in August 2026 to group glycol outage failure reports.  
Together with FRACAS-435, it is the closest thing to a curated event catalog.
* [FRACAS-435](https://rubinobs.atlassian.net/browse/FRACAS-435) PCS Chiller Issues  
Epic grouping failure reports for the LSSTCam Pumped Coolant System (PCS) chiller
* [FRACAS-277](https://rubinobs.atlassian.net/browse/FRACAS-277) Glycol Chiller #2: Failure to Restart after Switching to Generator Power
On 2025-04-05, Chiller #2 did not restart automatically after the switch to generator power. Glycol to the camera Cryo system and the PCS chiller was lost for about 30 minutes.
* [FRACAS-279](https://rubinobs.atlassian.net/browse/FRACAS-279) Glycol Chiller #3 -- Short Flow Interruption on April 29, 2025
A one-second flow interruption to the PCS chiller, coincident with a generator voltage spike (companion to FRACAS-278). The thread records that Level 2 and Level 4 loads were starving Level 7 flow, that throttling Level 2 doubled the flow on Level 7, and which consumers Chiller 3 feeds.
* [FRACAS-280](https://rubinobs.atlassian.net/browse/FRACAS-280) LSSTCam -- Loss of Cooling Capacity
On 2025-05-05, around 03:00 to 04:00 UTC and while on sky, the LSSTCam cryo plate temperature started to deviate from -127 °C.
* [FRACAS-282](https://rubinobs.atlassian.net/browse/FRACAS-282) Glycol Chiller #3: Flow lost at 16:26 May 21, 2025 (UTC) after a Power Glitch
Loss of glycol flow after a power glitch, followed by a camera recovery from the resulting failure.
* [FRACAS-310](https://rubinobs.atlassian.net/browse/FRACAS-310) Glycol System -- Degradation Affected the Dynalene Chiller #1 Normal Operational Capability
October 2025. Utility trunk and Dynalene temperatures rose while getting on sky. Resetting chiller01 produced only a short-lived temperature plateau.
* [FRACAS-314](https://rubinobs.atlassian.net/browse/FRACAS-314) Commercial Power -- Loss affecting Dynalene, PCS, and Cryo #6 Cooling Systems
November 2025. A brief power outage took down the PCS, Cryo 6, and Dynalene at the same time.
* [FRACAS-321](https://rubinobs.atlassian.net/browse/FRACAS-321) Dynalene -- Flow Lost After Returning to Commercial Power
November 2025. After 20 to 30 seconds without power, glycol flow recovered but Dynalene did not respond to the usual troubleshooting. Restoring Dynalene flow required a full power cycle of Chiller 2.
* [FRACAS-322](https://rubinobs.atlassian.net/browse/FRACAS-322) Glycol -- (cold) temperature was wrongly set by EAS after the OS update of 18th Nov 2025
After an OS and Kubernetes update, the Environmental Awareness System (EAS) set the cold glycol too warm (17 °C), and Cryo 6 was lost. The ticket notes that by design the cold glycol (Chillers 1 and 2) has a floating setpoint and the comfort glycol (Chiller 3) a fixed one.
* [FRACAS-336](https://rubinobs.atlassian.net/browse/FRACAS-336) Dynalene System Failure -- cRIO Controller Rebooting due to Dynalene Leaking on a Sensor
January 2026. The Dynalene system stopped cooling LSSTCam for several hours after a leak onto a sensor caused its controller to reboot.
* [FRACAS-344](https://rubinobs.atlassian.net/browse/FRACAS-344) Glycol Controlling - VM Rebooting
February 2026. The glycol control virtual machine rebooted and took all glycol chillers offline. OBS-1606 documents the stale telemetry published during this event.
* [FRACAS-352](https://rubinobs.atlassian.net/browse/FRACAS-352) LSSTCam PCS Chiller -- Flow Variations during a Power Cut and when Connected to the Glycol Chiller #3
February 2026. Automatic recirculation on Chillers 1 and 2 protected Dynalene and the Cryo compressors during a power cut. Chiller 3 took about 75 s to recover, which disturbed the PCS chiller and the camera cold plate.
* [FRACAS-364](https://rubinobs.atlassian.net/browse/FRACAS-364) LSSTCam PCS Chiller -- Flow Variations when Connecting to the Glycol Chiller #1 and #2
March 2026. The PCS chiller received lower glycol flow after it was connected to Chillers 1 and 2.
* [FRACAS-366](https://rubinobs.atlassian.net/browse/FRACAS-366) LSSTCam PCS Chiller -- E2 Compressor 1 Failure
2026-03-20 at 03:44 UTC. A compressor failure alarm was followed by low-flow alarms. Cold plate, cryo plate, and PCS inlet and outlet temperatures rose rapidly, while general glycol temperatures dropped from about 18 to 4 °C.
* [FRACAS-371](https://rubinobs.atlassian.net/browse/FRACAS-371) HVAC Server Restart left the Glycol Chillers off
April 2026. An HVAC server reboot during OS updates left Chillers 2, 3, and 4 off, with no Chronograf telemetry available during the upgrade. The reporter believes it happened twice.
* [FRACAS-384](https://rubinobs.atlassian.net/browse/FRACAS-384) Low Glycol Flow in Camera Cooling System -- due to a PCS Clogged Filter
May 2026. A clogged PCS filter reduced glycol flow to the camera cooling system over roughly two days before the report. Supersedes FRACAS-383; permanent fix and root cause still required.
* [FRACAS-387](https://rubinobs.atlassian.net/browse/FRACAS-387) Glycol Chiller 2 -- Failing at High Output
Chiller 2 repeatedly tripped shortly after reaching 100% output, even with a slower ramp and a 75% cap, and was moved to bypass pending maintenance. RSO-580 follows up on the EAS setpoint change at the time of the trip.
* [FRACAS-402](https://rubinobs.atlassian.net/browse/FRACAS-402) Investigate Glycol temperature set point reset after power outage
After multiple outages, Chillers 1 and 2 came back with incorrect setpoints. The ticket investigates why the Niagara system does not store or apply the values commanded by the HVAC CSC.
* [FRACAS-414](https://rubinobs.atlassian.net/browse/FRACAS-414) Storm, Jul 2026 -- Summit Glycol System went off after the Generator Power became Unstable
July 2026 storm. The glycol chillers shut down when the main generator stopped providing a stable 480 V supply.
* [FRACAS-415](https://rubinobs.atlassian.net/browse/FRACAS-415) Storm, Jul 2026 -- Summit Dynalene System Went off after Losing the Glycol Coolant Supply
Same event. Dynalene shut down after the glycol chillers and their recirculation system stopped supplying coolant, a clear example of the glycol-to-Dynalene cascade.

## Related RSO Tickets

* [RSO-899](https://rubinobs.atlassian.net/browse/RSO-899) Glycol issue systematic analysis
Epic to analyze 2026 glycol flow and temperature telemetry and look for patterns preceding flow loss after power glitches and setpoint changes.
* [RSO-900](https://rubinobs.atlassian.net/browse/RSO-900) Analyse the glycol flow for the year of 2026
Looks for lost flow or large flow changes during 2026 and their connection to power glitches.
* [RSO-901](https://rubinobs.atlassian.net/browse/RSO-901) Analyse the glycol temperature set points for the year of 2026
Looks for sudden setpoint changes during 2026 and their connection to Niagara losses or glycol system stops.
* [RSO-909](https://rubinobs.atlassian.net/browse/RSO-909) Analyze the input pressure and output pressures in each of the glycol chillers ~2h before each major fault
Pressure-focused precursor analysis for each glycol chiller.
* [RSO-580](https://rubinobs.atlassian.net/browse/RSO-580) Investigate how the EAS controlled the Glycol Chiller at the time of the failure
Action from FRACAS-387: Chiller 2 tripped on the day the EAS changed its setpoint.
* [RSO-635](https://rubinobs.atlassian.net/browse/RSO-635) Taxonomy - Facilities Refrigeration System
Taxonomy for the refrigeration systems. The Dynalene portion is done and the glycol portion is pending.
* [RSO-887](https://rubinobs.atlassian.net/browse/RSO-887) Documentation for Glycol issues troubleshooting and monitoring
Plans new emergency and monitoring procedures covering Grafana monitoring, chiller recovery by the observing specialists, and Niagara recovery.
* [RSO-557](https://rubinobs.atlassian.net/browse/RSO-557) LSSTCam Cryogenic, Dynalene, and Glycol System Inter-dependence
Proposed Docushare page describing how the LSSTCam cryogenic systems depend on the Dynalene and glycol systems.
* [RSO-907](https://rubinobs.atlassian.net/browse/RSO-907) Update diagram in the Glycol documentation page
Lists the corrections needed in the architecture diagram, such as TMA thermal cabinets, whether Chiller 4 feeds the control room and offices, and the valve from Chiller 3 to the Level 2 CRACs.

## Related OBS Tickets

* [OBS-830](https://rubinobs.atlassian.net/browse/OBS-830) HVAC subsystems report zeros (or fixed values) when component is disconnected
The HVAC CSC publishes zeros or frozen values as real telemetry when it loses the connection. This is relevant when filtering data for a nominal baseline.
* [OBS-930](https://rubinobs.atlassian.net/browse/OBS-930) Uncommanded Chiller / HVAC setpoint changes
May 2025. The dome HVAC setpoint and the Chiller #4 setpoint changed without being commanded.
* [OBS-1225](https://rubinobs.atlassian.net/browse/OBS-1225) Glycol Chiller Telemetry Lost and HVAC not commandable
All glycol chiller telemetry was lost for about 30 minutes while the chillers themselves kept running. Cause attributed to cabling and communication with the Niagara controller.
* [OBS-1606](https://rubinobs.atlassian.net/browse/OBS-1606) HVAC CSC publishes stale data, investigate how to fix telemetry being published
Old telemetry was republished as if current during FRACAS-344. The ticket proposes adding a measurement timestamp.
* [OBS-1649](https://rubinobs.atlassian.net/browse/OBS-1649) Watcher alarms for dynalene chillers
Requests Watcher alarms for Dynalene so observers are alerted before, or in parallel with, camera alerts.
* [OBS-1660](https://rubinobs.atlassian.net/browse/OBS-1660) Review/add additional watcher alarms for chillers
Chiller 2 stayed off after a March 2026 glitch with no alarm for over an hour. The flow alarm limit was likely set too low, and only some of the Watcher fields were populated.

## Confluence Pages

### System description

* [Glycol/Dynalene Flow Path and Cooling System Architecture](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/1065943153)
Floor-by-floor description of the cooling system, from the Level 1 chiller plant to the PCS chiller and Cryo circuits on Pier 7, including installed equipment, alarm resets, the Dynalene control and telemetry path, and dashboards. Still a draft, and its diagram is being corrected under RSO-907.
* [Introduction to Chillers](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/949944397)
Overview of the site's nine chillers linked to the cooling system and the Oil Supply System: the glycol chillers on Level 1, the Dynalene chillers on Level 5, and the PCS chiller on Level 7.
* [Environmental Awareness System Overview](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/465240158)
Describes how the EAS sets glycol setpoints from ambient sensors or a forecast to keep the dome isothermal and track outside temperature. States that EAS keeps the coolant 5 to 10 °C below inside ambient at night.
* [Dynalene System](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/228392976)
Introduction to the Dynalene system as used in operations, with a note that a flow stop requires a coordinated response within about 30 minutes.
* [Camera PCS Chiller [chiller2] and the Coldplate](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/1300332685)
Explains how the PCS cools the camera cold plate to about -40 °C through vacuum-insulated lines from the chiller cabinet on Level 7.
* [Plan/Proposal for switching cryo compressors to cold (tracking) Glycol on level 7](https://rubinobs.atlassian.net/wiki/spaces/CAM/pages/1723957276)
Describes the cold water circuit of the LSSTCam cryo modules and its flow and temperature needs, and proposes moving the compressors to the cold, tracking glycol loop.

### Monitoring and response

* [Glycol Cooling System Monitoring and Response Guide](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/847446349)
Main operator guide: dashboards to watch, design conditions (40% ethylene glycol, 12.7 barg, inlet 5 °C below ambient, temperature tolerances), flow thresholds of about 1.5 gpm for concern and below 1 gpm for emergency, and the note that the PCS usually survives glycol outages shorter than about 90 s.
* [Monitoring and Response Procedures for Dynalene Chillers and Glycol Flow Rate](https://rubinobs.atlassian.net/wiki/spaces/~pvenegas/pages/1805778961)
Checklist-style monitoring for the Dynalene chillers, including glycol feed flow thresholds above about 55 LPM for each chiller and where to check them in the Dynalene UI and Chronograf.
* [Power Outage - Dynalene Monitoring](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/1211662339)
What to monitor during a power outage, pointing to the dashboard covering the Level 5 Dynalene chillers and the Level 1 glycol chillers.
* [Glycol, Dynalene, PCS, Cryo or Power Failure](https://rubinobs.atlassian.net/wiki/spaces/OOD/pages/763232393)
Emergency response for glycol, Dynalene, PCS chiller, Cryo, and full power failures, starting with calling Facilities and the Camera team. Draft that requires training.
* [PCS Chiller Troubleshooting Guide](https://rubinobs.atlassian.net/wiki/spaces/~712020071056b447a84bfe9d0fd25503c7b3a2/pages/2003435560)
Troubleshooting reference for PCS chiller outages and restart readiness, focused on telling a true chiller fault from a protection trip or an environmental condition. Under active editing (RSO-896).

### Analysis, incidents, and maintenance

* [Glycol Flow Telemetry Issue Identification Framework](https://rubinobs.atlassian.net/wiki/spaces/~pvenegas/pages/2031419439)
Draft for RSO-900. Groups 2026 glycol issues into three classes (true flow outages, telemetry outages that mimic flow loss, and setpoint anomalies) and starts an event register. Notes that no normal flow range is documented for the chiller loops.
* [20260320 PCS Failure](https://rubinobs.atlassian.net/wiki/spaces/~fanning/pages/1540456464)
Incident write-up for FRACAS-366, with the sequence of alerts raised by the PCS chiller.
* [GP and Cold Glycol filters checkout log](https://rubinobs.atlassian.net/wiki/spaces/LTS/pages/50086177)
Record of checkouts, cleanings, and filter states on the general-purpose and cold glycol circuits. Useful for relating clogging events like FRACAS-384 to maintenance history.
* [10 Dynalene main filters/strainer checkout log](https://rubinobs.atlassian.net/wiki/spaces/LTS/pages/50086350)
The same kind of log for the Dynalene circuits.
* [Organizing glycol & dynalene contents for OS](https://rubinobs.atlassian.net/wiki/spaces/~jseron/pages/1067581452)
Tentative structure for observing-specialist documentation on glycol and Dynalene. Useful to check so the technote does not overlap with it.

## Other References

* [Fluid Distribution System (092-308-F-M-01000)](https://docushare.lsst.org/docushare/dsweb/Get/Document-45445/092-308-F-M-01000-Ed002.pdf)
Docushare design document for the fluid distribution system.
* [LSST Camera Value Engineering / Alternative Analyses Collection (LCA-399)](https://docushare.lsst.org/docushare/dsweb/Get/LCA-399/LSST%20Camera%20Value%20engineering-Alternative%20Analyses%20Collection--LCA-399.pdf)
Camera trade studies referenced from the monitoring guide.
* [Facilities Temperatures Reports (Times Square)](https://usdf-rsp.slac.stanford.edu/times-square/github/lsst-sitcom/reports-performance-summary/sst/nights/facilities_temperatures_reports)
Nightly facilities temperature report. A possible starting point for the nominal baseline.