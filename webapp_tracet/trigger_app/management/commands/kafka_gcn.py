from django.core.management.base import BaseCommand, CommandError
from gcn_kafka import Consumer
import os
from datetime import datetime
import voeventparse
import logging

from trigger_app.views import parse_and_save_xml

logger = logging.getLogger(__name__)
from trigger_app.models import CometLog, Status

# Environment variables
GCN_KAFKA_CLIENT = os.getenv("GCN_KAFKA_CLIENT")
GCN_KAFKA_SECRET = os.getenv("GCN_KAFKA_SECRET")


class Command(BaseCommand):
    help = "Kafka Consume"

    def handle(self, *args, **kwargs):
        try:
            consumer = Consumer(
                client_id=GCN_KAFKA_CLIENT, client_secret=GCN_KAFKA_SECRET
            )
            consumer.subscribe(
                [
                    "gcn.classic.voevent.AMON_NU_EM_COINC",
                    "gcn.classic.voevent.FERMI_GBM_ALERT",
                    "gcn.classic.voevent.FERMI_GBM_FIN_POS",
                    "gcn.classic.voevent.FERMI_GBM_FLT_POS",
                    "gcn.classic.voevent.FERMI_GBM_GND_POS",
                    "gcn.classic.voevent.FERMI_GBM_POS_TEST",
                    "gcn.classic.voevent.FERMI_GBM_SUBTHRESH",
                    "gcn.classic.voevent.FERMI_LAT_MONITOR",
                    "gcn.classic.voevent.FERMI_LAT_OFFLINE",
                    "gcn.classic.voevent.FERMI_LAT_POS_TEST",
                    "gcn.classic.voevent.FERMI_POINTDIR",
                    "gcn.classic.voevent.LVC_EARLY_WARNING",
                    "gcn.classic.voevent.LVC_INITIAL",
                    "gcn.classic.voevent.LVC_PRELIMINARY",
                    "gcn.classic.voevent.LVC_UPDATE",
                    "gcn.classic.voevent.LVC_RETRACTION",
                    "gcn.classic.voevent.SWIFT_ACTUAL_POINTDIR",
                    # 'gcn.classic.voevent.SWIFT_BAT_GRB_ALERT',
                    "gcn.classic.voevent.SWIFT_BAT_GRB_LC",
                    "gcn.classic.voevent.SWIFT_BAT_GRB_POS_ACK",
                    "gcn.classic.voevent.SWIFT_BAT_GRB_POS_TEST",
                    "gcn.classic.voevent.SWIFT_BAT_QL_POS",
                    "gcn.classic.voevent.SWIFT_BAT_SCALEDMAP",
                    "gcn.classic.voevent.SWIFT_BAT_TRANS",
                    "gcn.classic.voevent.SWIFT_FOM_OBS",
                    "gcn.classic.voevent.SWIFT_POINTDIR",
                    "gcn.classic.voevent.SWIFT_SC_SLEW",
                    "gcn.classic.voevent.SWIFT_TOO_FOM",
                    "gcn.classic.voevent.SWIFT_TOO_SC_SLEW",
                    "gcn.classic.voevent.SWIFT_UVOT_DBURST",
                    "gcn.classic.voevent.SWIFT_UVOT_DBURST_PROC",
                    "gcn.classic.voevent.SWIFT_UVOT_EMERGENCY",
                    "gcn.classic.voevent.SWIFT_UVOT_FCHART",
                    "gcn.classic.voevent.SWIFT_UVOT_FCHART_PROC",
                    "gcn.classic.voevent.SWIFT_UVOT_POS",
                    "gcn.classic.voevent.SWIFT_UVOT_POS_NACK",
                    "gcn.classic.voevent.SWIFT_XRT_CENTROID",
                    "gcn.classic.voevent.SWIFT_XRT_IMAGE",
                    "gcn.classic.voevent.SWIFT_XRT_IMAGE_PROC",
                    "gcn.classic.voevent.SWIFT_XRT_LC",
                    "gcn.classic.voevent.SWIFT_XRT_POSITION",
                    "gcn.classic.voevent.SWIFT_XRT_SPECTRUM",
                    "gcn.classic.voevent.SWIFT_XRT_SPECTRUM_PROC",
                    "gcn.classic.voevent.SWIFT_XRT_SPER",
                    "gcn.classic.voevent.SWIFT_XRT_SPER_PROC",
                    "gcn.classic.voevent.SWIFT_XRT_THRESHPIX",
                    "gcn.classic.voevent.SWIFT_XRT_THRESHPIX_PROC",
                ]
            )

            startDate = datetime.today()
            # 2023-03-09T02:43:10+0000

            kafka_status = Status.objects.get(name="kafka")
            kafka_status.status = 0
            kafka_status.save()
            self.stdout.write(
                f'{startDate.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Started'
            )
            CometLog.objects.create(
                log=f'{startDate.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Started'
            )
            while True:
                for message in consumer.consume(timeout=1):
                    try:
                        value = message.value()
                        messageDate = datetime.today()
                        v = voeventparse.loads(value)

                        self.stdout.write(
                            f'{messageDate.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Recieved {v.attrib["ivorn"]}'
                        )
                        CometLog.objects.create(
                            log=f'{messageDate.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Recieved {v.attrib["ivorn"]}'
                        )

                        self.stdout.write(
                            f'{messageDate.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Saving {v.attrib["ivorn"]}'
                        )
                        CometLog.objects.create(
                            log=f'{messageDate.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Saving {v.attrib["ivorn"]}'
                        )

                        voevent_string = voeventparse.prettystr(v)

                        new_event = parse_and_save_xml(voevent_string)
                        new_event_id = new_event.data["id"]

                        self.stdout.write(
                            f'{messageDate.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Saved event: {new_event_id}'
                        )
                        CometLog.objects.create(
                            log=f'{messageDate.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Saved event: {new_event_id}'
                        )

                    except Exception as e:
                        errorDate = datetime.today()
                        self.stdout.write(
                            f'{errorDate.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Error processing event: {e}'
                        )
                        CometLog.objects.create(
                            log=f'{errorDate.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Error processing event: {e}'
                        )

        except Exception as e:
            errorDate = datetime.today()
            self.stdout.write(
                f'{errorDate.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Error {e}'
            )
            CometLog.objects.create(
                log=f'{errorDate.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Error {e}'
            )
            # kafka_status = Status.objects.get(name='kafka')
            # kafka_status.status = 2
            # kafka_status.save()
