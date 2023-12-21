#!/usr/bin/env python

from __future__ import division

import numpy as np
import healpy as hp
import lal
import os
import json
from matplotlib import pyplot as plt
import h5py
import pandas as pd
from matplotlib import rc
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
import astropy.units as u
from astropy.time import Time
import scipy.stats as st
import pandas


from lalinference import plot

import matplotlib

params = {
    "text.latex.preamble": ["\\usepackage{gensymb}"],
    #     'image.origin': 'lower',
    #     'image.interpolation': 'nearest',
    #     'image.cmap': 'gray',
    #     'axes.grid': False,
    "savefig.dpi": 300,
    # 'axes.labelsize': 12,
    # 'axes.titlesize': 12,
    #     'font.size': 10,
    #     'legend.fontsize': 6,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "text.usetex": True,
    "font.family": "serif",
}

matplotlib.rcParams.update(params)


# ### Relation between GMST and LMST
# ${\rm GMST} = {\rm LMST} - \lambda_{\rm observer}$, where $\lambda_{\rm observer}$ is the east longitude of the observer.
#
# $\sin({\rm ALT}) = \sin({\rm DEC})\sin({\rm LAT}) + \cos({\rm DEC})\cos({\rm LAT})\cos({\rm HA})$
#
# Assuming that ${\rm GMST} = 0$, we have ${\rm HA} = \lambda_{\rm observer} - {\rm RA}$
#
# For ASKAP, $\lambda_{\rm observer} = 116.6288746 {\rm deg}$ and ${\rm LAT} = -26.6969812 {\rm deg}$


def calc_sinalt(ra, dec, lon=116.6288746, lat=-26.6969812):
    part_1 = np.sin(np.deg2rad(dec)) * np.sin(np.deg2rad(lat))
    part_2 = (
        np.cos(np.deg2rad(dec)) * np.cos(np.deg2rad(lat)) * np.cos(np.deg2rad(lon - ra))
    )
    return part_1 + part_2


def angular_dist(
    ra2, dec2, i=147827
):  # arguments in radians, default center is the maximum response point
    ra1 = ra[i]
    dec1 = dec[i]
    cos_sep = np.sin(dec1) * np.sin(dec2) + np.cos(dec1) * np.cos(dec2) * np.cos(
        ra1 - ra2
    )
    sep = np.arccos(cos_sep)
    return sep


def DeclRaToIndex(
    RA, decl, NSIDE=128
):  # find the index of (RA, Dec) in units of radians
    return hp.pixelfunc.ang2pix(NSIDE, -decl + np.pi / 2, 2 * np.pi - RA)


nside = 128
npix = hp.nside2npix(nside)
theta, phi = hp.pix2ang(nside=nside, ipix=np.arange(npix))
ra = phi
dec = 0.5 * np.pi - theta
psi = 0.0
gmst = 0.0
detectors = {
    "H": lal.CachedDetectors[lal.LHO_4K_DETECTOR].response,
    "L": lal.CachedDetectors[lal.LLO_4K_DETECTOR].response,
    "V": lal.CachedDetectors[lal.VIRGO_DETECTOR].response,
    "K": lal.CachedDetectors[lal.KAGRA_DETECTOR].response,
}
fss = np.zeros_like(ra)
horizon = np.zeros_like(ra)
for i in range(len(fss)):
    ###
    sinalt = calc_sinalt(np.rad2deg(ra[i]), np.rad2deg(dec[i]))
    #    if sinalt > np.sin(np.deg2rad(55)): # for single dipole
    if sinalt > np.sin(np.deg2rad(30)):  # for elevation above 30deg
        horizon[i] = 1
    else:
        horizon[i] = 0

    for site, response in detectors.items():
        fp, fc = lal.ComputeDetAMResponse(response, ra[i], dec[i], psi, gmst)
        fss[i] += fp**2 + fc**2

geojson_filename = os.path.join(
    os.path.dirname(plot.__file__), "ne_simplified_coastline.json"
)
# with open(geojson_filename, 'r') as geojson_file:
#     geojson = json.load(geojson_file)
# for shape in geojson['geometries']:
#     verts = np.deg2rad(shape['coordinates'])


# calculate the MWA beam pointed at the maximum response
dis_pointing = np.degrees(angular_dist(ra, dec))
beam_4 = np.zeros_like(ra)
beam_full = np.zeros_like(ra)
beam_fly_1 = np.zeros_like(ra)
beam_fly_2 = np.zeros_like(ra)
beam_fly_3 = np.zeros_like(ra)
beam_fly_4 = np.zeros_like(ra)
for i in range(len(fss)):
    if dis_pointing[i] > 28:  # 20% beam size for 4 dipoles
        beam_4[i] = 0
    else:
        beam_4[i] = 1
for i in range(len(fss)):
    if dis_pointing[i] > 17:  # 20% beam size for all dipoles
        beam_full[i] = 0
    else:
        beam_full[i] = 1

# calculate the fly eye's mode
dis_pointing = np.degrees(
    angular_dist(
        ra, dec, DeclRaToIndex(np.deg2rad(-116.6288746), np.deg2rad(-26.6969812))
    )
)
for i in range(len(fss)):
    if dis_pointing[i] > 17:
        beam_fly_1[i] = 0
    else:
        beam_fly_1[i] = 1
dis_pointing = np.degrees(angular_dist(ra, dec, 142721))
for i in range(len(fss)):
    if dis_pointing[i] > 17:
        beam_fly_2[i] = 0
    else:
        beam_fly_2[i] = 1
dis_pointing = np.degrees(angular_dist(ra, dec, 142684))
for i in range(len(fss)):
    if dis_pointing[i] > 17:
        beam_fly_3[i] = 0
    else:
        beam_fly_3[i] = 1
dis_pointing = np.degrees(angular_dist(ra, dec, 173634))
for i in range(len(fss)):
    if dis_pointing[i] > 17:
        beam_fly_4[i] = 0
    else:
        beam_fly_4[i] = 1


# load S/N from the simulated GW detections by the LVK group
bns_simulations = h5py.File("endo3_bnspop-LIGO-T2100113-v12.hdf5", mode="r")
keys = list(bns_simulations["injections"].keys())
items = []
for key in keys:
    items.append(np.array(bns_simulations["injections"][key]))

sim_df = pd.DataFrame(np.array(items).T, columns=keys)
SNR = sim_df["optimal_snr_net"]
prob = np.zeros_like(ra)
for i in range(len(fss)):
    SNR_reduced = SNR / (np.max(fss) / fss[i])
    prob[i] = len(SNR_reduced[SNR_reduced >= 6])
prob = prob / np.sum(prob)

# create probability map
fig = plt.figure(dpi=300)
ax = fig.add_subplot(111, projection="mollweide")
ax.grid(linewidth=0.3)

im = plot.healpix_heatmap(prob, dlon=-np.deg2rad(116.62))

im2 = plot.healpix_contour(
    horizon, dlon=-np.deg2rad(116.62), linewidths=1, linestyles="-", colors="red"
)
##im3 = plot.healpix_contour(beam_4, dlon=-np.deg2rad(116.62), linewidths=1, colors='cyan')
im4 = plot.healpix_contour(
    beam_full, dlon=-np.deg2rad(116.62), linewidths=1, colors="gray"
)
# im5 = plot.healpix_contour(beam_fly_1, dlon=-np.deg2rad(116.62), linewidths=1, linestyles=':', colors='magenta')
# im5 = plot.healpix_contour(beam_fly_2, dlon=-np.deg2rad(116.62), linewidths=1, linestyles=':', colors='magenta')
# im5 = plot.healpix_contour(beam_fly_3, dlon=-np.deg2rad(116.62), linewidths=1, linestyles=':', colors='magenta')
# im5 = plot.healpix_contour(beam_fly_4, dlon=-np.deg2rad(116.62), linewidths=1, linestyles=':', colors='magenta')

plt.setp(ax.get_xticklabels(), visible=False)
plt.yticks(fontsize=14)
for shape in geojson["geometries"]:
    verts = np.deg2rad(shape["coordinates"])
    ax.plot(verts[:, 0] - np.deg2rad(116.62), verts[:, 1], linewidth=0.5, color="0.2")
    ax.plot(verts[:, 0] + np.deg2rad(243.38), verts[:, 1], linewidth=0.5, color="0.2")

ax.scatter(0, np.deg2rad(-26.6969812), color="red", marker="*", s=100)
ax.scatter(
    -(np.deg2rad(116.6288746) - ra[147827]), dec[147827], color="red", marker="+", s=100
)

# ax_cb = fig.add_axes([0.2,0.1,0.6,0.03])
# cb = plt.colorbar(im, orientation='horizontal',cax=ax_cb)
cb = plt.colorbar(im, orientation="horizontal", pad=0.02)
cb.set_label("Probability density", fontsize=14)
cb.ax.tick_params(labelsize=14)
cb.ax.xaxis.get_offset_text().set_fontsize(14)
plt.rcParams["savefig.facecolor"] = "white"
# plt.savefig('Probability_map_120MHz.png',bbox_inches='tight',format='png',dpi=300)
# plt.close()
