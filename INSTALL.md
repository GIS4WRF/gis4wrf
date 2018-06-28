# Installation
We currently support Windows, macOS and Ubuntu however, do let us know if you would like us to support other Linux distributions by [opening an issue](issues)! The installation of GIS4WRF requires users to have **QGIS 3** installed on their system — here, simply referred to as QGIS. Please make sure that you follow the same steps in the same order as described in [How to install QGIS](#how-to-install-qgis) and [How to install GIS4WRF](#how-to-install-gis4wrf) to avoid problems. You will, most likely, only need to follow these steps once; after QGIS and GIS4WRF have been installed, you will be notified when updates become available directly in QGIS.

*Tip: for the best experience and easiest installation, install on Windows.*

## Table of Contents
- [Installation](#installation)
    - [Table of Contents](#table-of-contents)
    - [How to install QGIS](#how-to-install-qgis)
        - [Windows](#windows)
        - [macOS](#macos)
        - [Ubuntu](#ubuntu)
    - [How to install GIS4WRF](#how-to-install-gis4wrf)

## How to install QGIS
QGIS is supported on Windows, macOS and various Linux distributions. Here we specifically detail the installation instructions for installing QGIS on Windows, macOS and Ubuntu.

### Windows
Download the latest version of ***QGIS Standalone Installer*** from the [QGIS download page](https://www.qgis.org/en/site/forusers/download#windows) and install it using the guided installation. After QGIS has been installed, go to [How to install GIS4WRF](#how-to-install-gis4wrf).

### macOS
On macOS, install QGIS using the  [Homebrew package manager](https://brew.sh/). If you do not have homebrew installed on your machine please see [How to install Homebrew](https://brew.sh#install).

To install QGIS, copy and paste the following in the Terminal prompt:

```bash
TODO: link to QGIS formulae
```
After QGIS has been installed, go to [How to install GIS4WRF](#how-to-install-gis4wrf).

### Ubuntu
Below are the instructions on how to install QGIS on Ubuntu 16.x, 17.x, and 18.x. The installation of QGIS on Ubuntu is slightly different for the three releases. If you are running an older version of Ubuntu, you must upgrade to the most recent version. If do not know what version of Ubuntu you are running, run `lsb_release -a | grep Release` in you Terminal prompt.

- Ubuntu 16.x

    Copy, paste and execute the following in your Terminal prompt:
    ```bash
    sudo apt-get install -y software-properties-common &&
    sudo add-apt-repository -s 'deb https://qgis.org/ubuntugis xenial main' &&
    sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-key CAEB3DC3BDF7FB45 &&
    sudo add-apt-repository -s -y ppa:ubuntugis/ubuntugis-unstable &&
    sudo apt-get update &&
    sudo apt-get install -y qgis python-qgis gfortran &&
    sudo apt-get install -y python3-pyqt5.qtwebkit &&
    sudo apt-get install -y python3-pip &&
    sudo pip3 install f90nml pyyaml netCDF4 wrf-python
    ```
    After QGIS has been installed, go to [How to install GIS4WRF](#how-to-install-gis4wrf).

- Ubuntu 17.x

    Copy, paste and execute the following in your Terminal prompt:
    ```bash
    sudo apt-get install -y software-properties-common &&
    sudo add-apt-repository -s 'deb https://qgis.org/debian artful main' &&
    sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-key CAEB3DC3BDF7FB45 &&
    sudo apt-get update &&
    sudo apt-get install -y qgis python-qgis gfortran &&
    sudo apt-get install -y python3-pyqt5.qtwebkit &&
    sudo apt-get install -y python3-pip &&
    sudo pip3 install f90nml pyyaml netCDF4 wrf-python
    ```
    After QGIS has been installed, go to [How to install GIS4WRF](#how-to-install-gis4wrf).

- Ubuntu 18.x

    Copy, paste and execute the following in your Terminal prompt:
    ```bash
    sudo apt-get install -y software-properties-common &&
    sudo add-apt-repository -s 'deb https://qgis.org/debian bionic main' &&
    sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-key CAEB3DC3BDF7FB45 &&
    sudo apt-get update &&
    sudo apt-get install -y qgis python-qgis gfortran &&
    sudo apt-get install -y python3-pyqt5.qtwebkit &&
    sudo apt-get install -y python3-pip &&
    sudo pip3 install f90nml pyyaml netCDF4 wrf-python
    ```
    After QGIS has been installed, go to [How to install GIS4WRF](#how-to-install-gis4wrf).

## How to install GIS4WRF
To install the latest version of GIS4WRF, launch QGIS and navigate to `Plugins` > `Manage and Install Plugins...` > `All`. From the search-bar, you can filter for `GIS4WRF`, or scroll down the list until you find `GIS4WRF`. Then, to install, select `GIS4WRF` from the list and click on `Install Plugin`. You can now launch GIS4WRF from the `Plugins` > `GIS4WRF` > `GIS4WRF` menu. Documentation on how to use GIS4WRF is displayed when launching GIS4WRF under the `Home` tab. Don't forget to reference GIS4WRF in your study — please see [How to reference GIS4WRF](#how-to-reference-gis4wrf) for guidelines. If you find a bug with the software, or you would like to suggest a new feature, please let us know by [opening an issue](https://github.com/GIS4WRF/gis4wrf/issues). Have fun now!