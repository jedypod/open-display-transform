# OpenDRT

## Overview

OpenDRT is an open-source [Picture Formation](https://github.com/sobotka/scise/wiki/Picture-Formation) Transform, designed to create an aesthetically pleasing picture out of raw camera image data. It enables image authors by allowing creative control over image appearance. This is accomplished through both a simple preset system, and a more extensive set of look development modules.


## Installation

OpenDRT is available as a DaVinci Resolve DCTL and as a node for The Foundry's Nuke.


### DaVinci Resolve

1. Open your DaVinci Resolve LUT folder:
    * **macOS:** `/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/`
    * **Windows:** `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\`
    * **Linux:** `~/.config/Blackmagic Design/LUT/`
2. Copy the DCTL files into this location.
3. Restart Resolve.
4. OpenDRT will be now available to apply with a DCTL node.

Due to the limited user interface capabilities of DCTL, by default OpenDRT for Resolve only includes look presets and user parameters to control HDR image rendering. For access to the full parameter set, the user can load the so-called "StickShift" version of OpenDRT (included in the [releases](https://github.com/jedypod/open-display-transform/releases)). Use with caution however, as the user experience will be extremely unweildy. Consider designing a preset in Nuke and adding it to the DCTL code instead.

[![OpenDRT Resolve Installation and Usage](https://github.com/user-attachments/assets/66fd7b31-4483-4de6-bf53-470c151f7f75)](https://www.youtube.com/watch?v=RpadynEOGRI)


### Nuke

OpenDRT for Nuke is provided as a group node. To load it, just drag and drop the `.nk` file into the node graph, or copy paste the contents using a text editor. All modules and parameters are available and split into a tabbed interface.

[![OpenDRT Nuke Installation and Usage](https://github.com/user-attachments/assets/6e0e91c8-d9f2-4568-8840-19e00f94103b)](https://www.youtube.com/watch?v=RYmANRwCNc4)


### OpenColorIO
OpenDRT is also provided as an OCIO config in the [releases](https://github.com/jedypod/open-display-transform/releases), for use in VFX DCC software such as Nuke, Maya, Houdini, Gaffer, etc.

[![OpenDRT OCIO Installation and Usage](https://github.com/user-attachments/assets/7e9868ee-e256-48ae-bbe2-3edbcfcae931)](https://www.youtube.com/watch?v=pKddV18pSMA)


## [More Information](docs/)

For more information, [continue reading the documentation](docs/).

* [OpenDRT Modules and Parameters Overview](docs/opendrt-parameters.md)
* [OpenDRT Tonescale](docs/opendrt-tonescale.md)
* [Release Notes](docs/opendrt-release-notes.md) for all the various OpenDRT versions.

