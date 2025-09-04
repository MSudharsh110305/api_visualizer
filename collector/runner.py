import argparse
import logging
from . import get_collector

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')

def main():
    parser = argparse.ArgumentParser(description="API Visualizer Event Collector")
    parser.add_argument('--transport', choices=['memory', 'udp', 'redis'], default='memory', help='Transport type')
    parser.add_argument('--db', default=None, help='Path to SQLite database')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size for storing events')
    parser.add_argument('--batch-interval', type=int, default=5, help='Batch interval in seconds')

    args = parser.parse_args()

    collector = get_collector(
        transport_type=args.transport,
        batch_size=args.batch_size,
        batch_interval=args.batch_interval,
        db_path=args.db
    )

    try:
        collector.start()
    except KeyboardInterrupt:
        collector.stop()

if __name__ == '__main__':
    main()
