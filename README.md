## NFHL Floodplain Updates

This is a pythonic ETL package that checks for new Letters of Map Revision (LOMR) and Letters of Map Ammendment (LOMA) within Boulder city limits by using requests based on REST services.

### Installation and Set Up

#### Assumptions

This package makes use of both the `arcgis` and `arcpy` libraries using Python 3. According to the [ESRI documentation](https://developers.arcgis.com/python/guide/install-and-set-up/), `arcgis` requires Python 3.5+; meanwhile, arcpy requires a license for Pro. Ergo, this package assumes:

* A Windows operating system
* Anaconda Distribution installed
  * Pro ships inside one by default
  * Python3 is included as part of the base `arcgispro-py3` conda environment
* An ArcGIS Pro2.1+ install
* Python 3.5+
* A `PATH` variable that knows the location of conda

#### Let's Go!

Clone this repository to your preferred project location:

```
cd your/preferred/project/location
git clone "https://github.com/jessenestler/floodplains"
```

Now, clone the `arcgispro-py3` environment in the command line:

```
conda create --name floodplains_env --clone arcgispro-py3
```

Enter this new conda environment and make sure to update the `arcgis` package that comes preinstalled:

```
conda activate floodplains_env
conda upgrade -c esri arcgis
```

For those without the default conda environment shipped with Pro, ESRI has instructions on installing the `arcgis` API [here](https://developers.arcgis.com/python/guide/install-and-set-up/#Offline-install), although this author could not get the API to work within a default conda environment without getting a `ConnectionResetError: [Errno 54] Connection reset by peer` when trying to query FEMA data. If you can figure out how to make this API play nice in sandboxes, please let me know!
