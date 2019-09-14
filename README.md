## NFHL Floodplain Updates

This is a pythonic ETL package that checks for new Letters of Map Revision (LOMR) and Letters of Map Ammendment (LOMA) within Boulder city limits by using requests based on REST services.

### Installation and Set Up

Clone this repository to your preferred project location:

```
cd your/preferred/project/location
git clone "https://github.com/jessenestler/floodplains"
```

This package makes use of both the `arcgis` and `arcpy` libraries using Python 3. The easiest way to install and use these packages is by cloning the conda environment that ships with Pro. First, make sure that the path to Pro's read-only conda environment is in you system `PATH`. For instructions on this, visit [this tutorial](https://helpdeskgeek.com/windows-10/add-windows-path-environment-variable/). Once this is complete, clone the environment in the command line:

```
conda create --name floodplains_env --clone arcgispro-py3
```

ArcGIS Pro 2.1+ ships with the `arcgis` API pre-installed, but you should make sure to update it. If you are working with earlier vesrions of Pro, [ESRI's documentation](https://developers.arcgis.com/python/guide/install-and-set-up/) is helpful:

```
conda activate floodplains_env
conda upgrade -c esri arcgis
```

For those without the default conda environment shipped with Pro, ESRI has instructions on installing the `arcgis` API [here](https://developers.arcgis.com/python/guide/install-and-set-up/#Offline-install), although this author could not get the API to work within a default conda environment without getting a `ConnectionResetError: [Errno 54] Connection reset by peer` when trying to query FEMA data. If you can figure out how to make this API play nice in sandboxes, please let me know!
