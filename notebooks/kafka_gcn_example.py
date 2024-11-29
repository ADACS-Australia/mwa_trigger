import json
import logging
import os
from datetime import datetime
from pathlib import Path

import voeventparse
from dotenv import load_dotenv
from gcn_kafka import Consumer

load_dotenv('../.env_web')


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/kafka_gcn.log'),
        ],
    )
    return logging.getLogger(__name__)


def save_voevent(topic: str, voevent_string: str) -> Path:
    """
    Save VOEvent as XML file in notebooks/data directory
    Returns the path to the saved file
    """
    try:
        # Create base directory structure
        base_dir = Path("data")
        base_dir.mkdir(parents=True, exist_ok=True)

        # Create date-based subdirectory
        date_str = datetime.now().strftime("%Y%m%d")
        date_dir = base_dir / date_str
        date_dir.mkdir(exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"event_{topic.split('.')[-1]}_{timestamp}.xml"
        filepath = date_dir / filename

        # Save to file as XML
        with open(filepath, "w") as f:
            f.write(voevent_string)

        return filepath
    except Exception as e:
        raise IOError(f"Failed to save VOEvent: {str(e)}")


def handle():
    logger = setup_logging()
    logger.info("Starting Kafka GCN consumer")

    try:
        consumer = Consumer(
            client_id=os.getenv("GCN_KAFKA_CLIENT"),
            client_secret=os.getenv("GCN_KAFKA_SECRET"),
        )

        topics = [
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

        consumer.subscribe(topics)
        logger.info(f"Subscribed to {len(topics)} topics")

        while True:
            try:
                messages = consumer.consume(timeout=1)

                for message in messages:
                    try:
                        topic = message.topic()
                        logger.info(f"Received message from topic: {topic}")

                        # Parse VOEvent and get pretty-printed XML
                        value = message.value()
                        v = voeventparse.loads(value)
                        voevent_string = voeventparse.prettystr(v)

                        # Save to file as XML
                        filepath = save_voevent(topic, voevent_string)
                        logger.info(f"Saved VOEvent to: {filepath}")

                    except voeventparse.ParseError as e:
                        logger.error(f"Failed to parse VOEvent: {str(e)}")
                    except IOError as e:
                        logger.error(f"File operation failed: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error processing message: {str(e)}")
                        continue

            except Exception as e:
                logger.error(f"Error in message consumption loop: {str(e)}")
                from time import sleep

                sleep(1)
                continue

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
    finally:
        try:
            consumer.close()
            logger.info("Consumer closed")
        except:
            pass


if __name__ == "__main__":
    handle()
