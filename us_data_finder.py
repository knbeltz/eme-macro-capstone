"""Download and audit the U.S. extension; never rewrite the original EME panel."""
import argparse
from eme_pipeline.http import Client
from eme_pipeline.us import build


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline',action='store_true',help='Replay saved API responses without network access or credentials')
    args=parser.parse_args()
    build(Client(offline=args.offline))


if __name__=='__main__': main()
