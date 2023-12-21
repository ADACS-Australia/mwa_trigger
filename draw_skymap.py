import os
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy import units as u
from matplotlib import pyplot as plt
from ligo.skymap.plot.marker import reticle
import numpy as np
import json
from ligo.skymap import io, version, plot, postprocess, bayestar, kde

url = "https://dcc.ligo.org/public/0146/G1701985/001/bayestar_no_virgo.fits.gz"
center = SkyCoord.from_name("NGC 4993")

fig = plt.figure(figsize=(4, 4), dpi=100)
ax = plt.axes(projection="astro hours mollweide")

ax.imshow_hpx(url, cmap="cylon")
# def calc_sinalt(ra, dec, lon=116.6288746, lat=-26.6969812):
#     part_1 = np.sin(np.deg2rad(dec))*np.sin(np.deg2rad(lat))
#     part_2 = np.cos(np.deg2rad(dec))*np.cos(np.deg2rad(lat))*np.cos(np.deg2rad(lon-ra))
#     return part_1+part_2

# def angular_dist(ra2, dec2, i=147827): # arguments in radians, default center is the maximum response point
#     ra1 = ra[i]
#     dec1 = dec[i]
#     cos_sep = np.sin(dec1)*np.sin(dec2)+np.cos(dec1)*np.cos(dec2)*np.cos(ra1-ra2)
#     sep = np.arccos(cos_sep)
#     return sep

# fss = np.zeros_like(ra)
# horizon = np.zeros_like(ra)
# for i in range(len(fss)):
#     ###
#     sinalt = calc_sinalt(np.rad2deg(ra[i]), np.rad2deg(dec[i]))
# #    if sinalt > np.sin(np.deg2rad(55)): # for single dipole
#     if sinalt > np.sin(np.deg2rad(30)): # for elevation above 30deg
#         horizon[i] = 1
#     else:
#         horizon[i] = 0

# # Create a meshgrid of x and y values
# x = np.linspace(-2, 2, 120)
# y = np.linspace(-2, 2, 120)
# X, Y = np.meshgrid(x, y)

# # Calculate the z values for the meshgrid
# z = np.sin(np.sqrt(X**2 + Y**2))

# # Plot the contour lines
# ax.contour_hpx(X, Y, z, 12, colors='black')

geojson_filename = os.path.join(
    os.path.dirname(plot.__file__), "ne_simplified_coastline.json"
)
with open(geojson_filename, "r") as geojson_file:
    geoms = json.load(geojson_file)["geometries"]
verts = [coord for geom in geoms for coord in zip(*geom["coordinates"])]


plt.tick_params(both=False)
plt.plot(*verts, color="0.5", linewidth=0.5, transform=ax.get_transform("world"))


ax.grid(linewidth=0.3)

ax.plot(
    center.ra.deg,
    center.dec.deg,
    transform=ax.get_transform("world"),
    marker=plot.reticle(),
    markersize=30,
    markeredgewidth=3,
)
# Add markers
# ax.contour_hpx(horizon, dlon=-np.deg2rad(116.62), linewidths=1, linestyles='-', colors='red')
plt.show()
