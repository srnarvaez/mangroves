import os 
import numpy as np
import xarray as xr

import rasterio

path = "data/raster/{}/"
save_path = "data/processed/{}_{}"

lagoons = ["mallorquin", "totumo", "virgen"]

for lagoon in lagoons:
    path_images = path.format(lagoon)
    images = os.listdir(path_images)

    for image in images:
        path_image = path_images + image

        with rasterio.open(path_image, "r") as src:
            lims = src.bounds

            if image == images[0]:
                temp = src.read(5)
                ndvi = src.read(6)
            else:
                temp = np.dstack([temp, src.read(5)])
                ndvi = np.dstack([ndvi, src.read(6)])

    t = np.array([ti[:-4] for ti in images], dtype="datetime64")
    x = np.linspace(lims[0], lims[2], ndvi.shape[1])
    y = np.flip(np.linspace(lims[1], lims[3], ndvi.shape[0]))

    temp -= 273.15

    mask = ((ndvi == -3e5) | (ndvi > 1.5) | (ndvi < -1.5))
    
    ndvi[mask] = np.nan
    temp[mask] = np.nan

    ndvi = xr.DataArray(
        data=ndvi,
        dims=("latitude", "longitude", "time"),
        coords={"longitude": x, "latitude": y, "time": t},
        name="NDVI",
        attrs={
            "description": "NDVI obtained from LANDSAT images from 1996 to 2021 on GEE."
        }
    )

    temp = xr.DataArray(
        data=temp,
        dims=("latitude", "longitude", "time"),
        coords={"longitude": x, "latitude": y, "time": t},
        name="Surface Temperature",
        attrs={
            "description": "Surface Temperature from STBAND from LANDSAT images (1996 to 2021).",
            "unit": "°C"
        }
    )

    ndvi.to_netcdf(save_path.format(lagoon, "ndvi.nc"))
    temp.to_netcdf(save_path.format(lagoon, "temperature.nc"))