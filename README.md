[![Website](https://img.shields.io/badge/sotn--012-lsst.io-brightgreen.svg)](https://sotn-012.lsst.io)
[![CI](https://github.com/lsst-so/sotn-012/actions/workflows/ci.yaml/badge.svg)](https://github.com/lsst-so/sotn-012/actions/workflows/ci.yaml)

# Nominal Behavior and Failure Signatures of the Glycol Refrigeration Systems

## SOTN-012

The Vera C. Rubin Observatory relies on a network of glycol refrigeration systems to cool the telescope, the LSST Camera (LSSTCam), the M1M3 mirror, and facility spaces. Since first light, failures in these systems have repeatedly interrupted night operations. Existing documentation covers the architecture, response procedures, and individual failure reports, but no document defines nominal behavior in telemetry, which makes it hard to distinguish a developing failure from routine variation. In this technical note, we characterize the nominal operating envelope of each glycol loop using Engineering and Facility Database (EFD) telemetry, then compare the telemetry preceding catalogued failure events against that envelope to identify failure signatures and possible precursors. The result is intended as a common baseline for defining alarm thresholds.

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
