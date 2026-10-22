[![Website](https://img.shields.io/badge/sotn--012-lsst.io-brightgreen.svg)](https://sotn-012.lsst.io)
[![CI](https://github.com/lsst-so/sotn-012/actions/workflows/ci.yaml/badge.svg)](https://github.com/lsst-so/sotn-012/actions/workflows/ci.yaml)

# What Changes the Glycol Chiller Set Points, and Does It Precede Failures?

## SOTN-012

The glycol chillers that cool the Simonyi Telescope, the LSST Camera (LSSTCam) and facility spaces do not hold a fixed supply temperature: the Environmental Awareness System (EAS) re-commands their set points automatically, many times a day. Because glycol failures have repeatedly interrupted night operations, a set-point change near an incident invites the reading that it caused or foreshadowed the failure. In this technical note we establish what actually drives those changes, using the `lsst.sal.HVAC.logevent_chillerConfiguration` events from 1 January to 20 July 2026 together with the EAS source and configuration, and we test them against a catalogue of cooling incidents. We find no set-point signature that consistently precedes a failure, and we show that frequent changes on the two EAS-controlled chillers are expected behaviour rather than an anomaly. This note is scoped to the set points only; the nominal flow, temperature and pressure envelopes of the glycol loops are left to separate analyses.

**Links:**

- Publication URL: https://sotn-012.lsst.io
- Alternative editions: https://sotn-012.lsst.io/v
- GitHub repository: https://github.com/lsst-so/sotn-012
- Build system: https://github.com/lsst-so/sotn-012/actions/


## Build this technical note

You can clone this repository and build the technote locally if your system has Python 3.11 or later:

```sh
git clone https://github.com/lsst-so/sotn-012
cd sotn-012
make init
make html
```

Repeat the `make html` command to rebuild the technote after making changes.
If you need to delete any intermediate files for a clean build, run `make clean`.

The built technote is located at `_build/html/index.html`.

## Publishing changes to the web

This technote is published to https://sotn-012.lsst.io whenever you push changes to the `main` branch on GitHub.
When you push changes to a another branch, a preview of the technote is published to https://sotn-012.lsst.io/v.

## Editing this technical note

The main content of this technote is in `index.md` (a Markdown file parsed as [CommonMark/MyST](https://myst-parser.readthedocs.io/en/latest/index.html)).
Metadata and configuration is in the `technote.toml` file.
For guidance on creating content and information about specifying metadata and configuration, see the Documenteer documentation: https://documenteer.lsst.io/technotes.
