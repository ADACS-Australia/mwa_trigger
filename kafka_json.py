from base64 import b64decode
from io import BytesIO
import json
import os
from pprint import pprint
import sys

from astropy.table import Table
import astropy_healpix as ah
from gcn_kafka import Consumer
import numpy as np


def parse_notice(record):
    record = json.loads(record)

    # # Only respond to mock events. Real events have GraceDB IDs like
    # # S1234567, mock events have GraceDB IDs like M1234567.
    # # NOTE NOTE NOTE replace the conditional below with this commented out
    # # conditional to only parse real events.
    # # if record['superevent_id'][0] != 'S':
    # #    return
    # if record['superevent_id'][0] != 'M':
    #     return

    # if record['alert_type'] == 'RETRACTION':
    #     print(record['superevent_id'], 'was retracted')
    #     return

    # # Respond only to 'CBC' events. Change 'CBC' to 'Burst' to respond to
    # # only unmodeled burst events.
    # if record['event']['group'] != 'CBC':
    #     return

    # # Parse sky map
    # skymap_str = record.get('event', {}).pop('skymap')
    # if skymap_str:
    #     # Decode, parse skymap, and print most probable sky location
    #     skymap_bytes = b64decode(skymap_str)
    #     skymap = Table.read(BytesIO(skymap_bytes))

    #     level, ipix = ah.uniq_to_level_ipix(
    #         skymap[np.argmax(skymap['PROBDENSITY'])]['UNIQ']
    #     )
    #     ra, dec = ah.healpix_to_lonlat(ipix, ah.level_to_nside(level),
    #                                    order='nested')
    #     print(f'Most probable sky location (RA, Dec) = ({ra.deg}, {dec.deg})')

    #     # Print some information from FITS header
    #     print(f'Distance = {skymap.meta["DISTMEAN"]} +/- {skymap.meta["DISTSTD"]}')

    # Print remaining fields
    if "event" in record:
        record.get("event", {}).pop("skymap")

    print("Record:")
    pprint(record)


# Environment variables
GCN_KAFKA_CLIENT = os.getenv("GCN_KAFKA_CLIENT")
GCN_KAFKA_SECRET = os.getenv("GCN_KAFKA_SECRET")

consumer = Consumer(client_id=GCN_KAFKA_CLIENT, client_secret=GCN_KAFKA_SECRET)
consumer.subscribe(
    [
        # 'igwn.gwalert',
        "gcn.notices.swift.bat.guano"
    ]
)
print("starting kafka")
# with open('kafka.json', 'a') as f:
for message in consumer.consume():
    # f.write(str(message.value))
    # f.write('\n')
    parse_notice(message.value())
